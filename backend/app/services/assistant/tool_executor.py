"""
Arthsavora AI Financial Tool Executor
Securely executes registered financial service tools within the active tenant workspace.
Enforces server-side authorization, bounded queries, sensitive data masking, and error safety.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import PermissionDeniedException
from app.domain.analytics import PeriodGrouping
from app.domain.assistant import ToolCallVO, ToolResultVO
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.budget import Budget, BudgetAllocation
from app.infrastructure.database.models.goal import FinancialGoal
from app.infrastructure.database.models.recurring import RecurringDefinition, Subscription
from app.infrastructure.database.models.transaction import Transaction
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import Workspace, WorkspaceMember
from app.repositories.anomaly_repository import AnomalyRepository
from app.repositories.document_repository import DocumentRepository
from app.services.analytics.analytics_service import AnalyticsService
from app.services.assistant.tool_registry import FINANCIAL_TOOLS, get_tool_definition


class ToolExecutor:
    """Executes registered financial tools through verified backend services."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_tool(
        self,
        tool_call: ToolCallVO,
        workspace_id: uuid.UUID,
        user_permissions: Set[str],
        user_id: Optional[uuid.UUID] = None,
    ) -> ToolResultVO:
        """
        Executes a single requested tool call with permission enforcement and error normalization.
        """
        tool_def = get_tool_definition(tool_call.tool_name)
        if not tool_def:
            return ToolResultVO(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=False,
                error=f"Unrecognized tool '{tool_call.tool_name}'. Tool is not registered.",
            )

        # Enforce server-side authorization
        if tool_def.required_permission not in user_permissions:
            return ToolResultVO(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=False,
                error=f"Permission denied: Missing required permission '{tool_def.required_permission}'.",
            )

        args = tool_call.arguments or {}

        try:
            # 1. Financial Overview
            if tool_call.tool_name == "get_financial_overview":
                return await self._exec_overview(tool_call, workspace_id, args)

            # 2. Income Summary
            elif tool_call.tool_name == "get_income_summary":
                return await self._exec_income(tool_call, workspace_id, args)

            # 3. Expense Summary
            elif tool_call.tool_name == "get_expense_summary":
                return await self._exec_expense(tool_call, workspace_id, args)

            # 4. Cash Flow
            elif tool_call.tool_name == "get_cash_flow":
                return await self._exec_cash_flow(tool_call, workspace_id, args)

            # 5. Category Spending
            elif tool_call.tool_name == "get_category_spending":
                return await self._exec_category(tool_call, workspace_id, args)

            # 6. Merchant Spending
            elif tool_call.tool_name == "get_merchant_spending":
                return await self._exec_merchant(tool_call, workspace_id, args)

            # 7. Account Balances
            elif tool_call.tool_name == "get_account_balances":
                return await self._exec_account_balances(tool_call, workspace_id)

            # 8. Search Transactions
            elif tool_call.tool_name == "search_transactions":
                return await self._exec_search_transactions(tool_call, workspace_id, args)

            # 9. Budget Status
            elif tool_call.tool_name == "get_budget_status":
                return await self._exec_budget_status(tool_call, workspace_id, args)

            # 10. Goal Progress
            elif tool_call.tool_name == "get_goal_progress":
                return await self._exec_goal_progress(tool_call, workspace_id)

            # 11. Upcoming Commitments
            elif tool_call.tool_name == "get_upcoming_commitments":
                return await self._exec_upcoming_commitments(tool_call, workspace_id, args)

            # 12. Subscriptions
            elif tool_call.tool_name == "get_subscription_summary":
                return await self._exec_subscriptions(tool_call, workspace_id)

            # 13. Forecast
            elif tool_call.tool_name == "get_forecast":
                return await self._exec_forecast(tool_call, workspace_id, args)

            # 14. Anomaly Details
            elif tool_call.tool_name == "get_anomaly_details":
                return await self._exec_anomalies(tool_call, workspace_id, args)

            # 15. Search Documents & Receipts
            elif tool_call.tool_name == "search_documents":
                return await self._exec_search_documents(tool_call, workspace_id, args)

            # 16. Document Details
            elif tool_call.tool_name == "get_document_details":
                return await self._exec_document_details(tool_call, workspace_id, args)

            # 17. Unread Notifications
            elif tool_call.tool_name == "get_unread_notifications":
                return await self._exec_unread_notifications(tool_call, user_id, workspace_id, args)

            # 18. Family Overview
            elif tool_call.tool_name == "get_family_overview":
                return await self._exec_family_overview(tool_call, user_id, workspace_id, args)

            # 19. Family Settlement Summary
            elif tool_call.tool_name == "get_family_settlement_summary":
                return await self._exec_family_settlement_summary(tool_call, user_id, workspace_id, args)

            # 20. Family Commitments
            elif tool_call.tool_name == "get_family_commitments":
                return await self._exec_family_commitments(tool_call, user_id, workspace_id, args)

            # 21. Business Overview
            elif tool_call.tool_name == "get_business_overview":
                return await self._exec_business_overview(tool_call, user_id, workspace_id, args)

            # 22. Business Receivables Summary
            elif tool_call.tool_name == "get_business_receivables_summary":
                return await self._exec_business_receivables(tool_call, user_id, workspace_id, args)

            # 23. Business Payables Summary
            elif tool_call.tool_name == "get_business_payables_summary":
                return await self._exec_business_payables(tool_call, user_id, workspace_id, args)

            # 24. Business Cash Flow Summary
            elif tool_call.tool_name == "get_business_cash_flow_summary":
                return await self._exec_business_cash_flow(tool_call, user_id, workspace_id, args)

            # 25. Connected Accounts Overview
            elif tool_call.tool_name == "get_connected_accounts_overview":
                return await self._exec_connected_accounts_overview(tool_call, user_id, workspace_id)

            # 26. Connection Sync Health
            elif tool_call.tool_name == "get_connection_sync_health":
                return await self._exec_connection_sync_health(tool_call, user_id, workspace_id)

            # 27. Account Reconciliation Summary
            elif tool_call.tool_name == "get_account_reconciliation_summary":
                return await self._exec_account_reconciliation_summary(tool_call, user_id, workspace_id)

            # 28. Financial Statement Summary
            elif tool_call.tool_name == "get_financial_statement_summary":
                return await self._exec_financial_statement_summary(tool_call, workspace_id, args)

            # 29. Tax Classification Summary
            elif tool_call.tool_name == "get_tax_classification_summary":
                return await self._exec_tax_classification_summary(tool_call, workspace_id, args)

            # 30. GST Reporting Summary
            elif tool_call.tool_name == "get_gst_reporting_summary":
                return await self._exec_gst_reporting_summary(tool_call, workspace_id, args)

            # 31. Explain Report Discrepancies
            elif tool_call.tool_name == "explain_report_discrepancies":
                return await self._exec_explain_report_discrepancies(tool_call, workspace_id, args)

            # 17-20. Action Proposal Drafts
            elif tool_call.tool_name in (
                "create_budget_draft",
                "create_goal_draft",
                "create_recurring_draft",
                "prepare_transaction_filter",
            ):
                return ToolResultVO(
                    call_id=tool_call.call_id,
                    tool_name=tool_call.tool_name,
                    success=True,
                    data={"is_draft": True, "action_type": tool_call.tool_name, "parameters": args},
                )

            return ToolResultVO(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=False,
                error=f"Execution handler not implemented for '{tool_call.tool_name}'.",
            )

        except Exception as exc:
            return ToolResultVO(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                success=False,
                error=f"Error executing tool '{tool_call.tool_name}': {str(exc)}",
            )

    # -------------------------------------------------------------------------
    # Individual Tool Implementations
    # -------------------------------------------------------------------------

    async def _exec_overview(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        start_d = date.fromisoformat(args["start_date"])
        end_d = date.fromisoformat(args["end_date"])
        currency = args.get("currency", "INR")
        svc = AnalyticsService(self.db)
        res = await svc.get_overview(ws_id, start_d, end_d, currency=currency)
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=res)

    async def _exec_income(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        start_d = date.fromisoformat(args["start_date"])
        end_d = date.fromisoformat(args["end_date"])
        currency = args.get("currency", "INR")
        svc = AnalyticsService(self.db)
        res = await svc.get_category_spending(ws_id, start_d, end_d, direction="inflow", currency=currency)
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=res)

    async def _exec_expense(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        start_d = date.fromisoformat(args["start_date"])
        end_d = date.fromisoformat(args["end_date"])
        currency = args.get("currency", "INR")
        svc = AnalyticsService(self.db)
        res = await svc.get_category_spending(ws_id, start_d, end_d, direction="outflow", currency=currency)
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=res)

    async def _exec_cash_flow(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        start_d = date.fromisoformat(args["start_date"])
        end_d = date.fromisoformat(args["end_date"])
        currency = args.get("currency", "INR")
        svc = AnalyticsService(self.db)
        res = await svc.get_cash_flow_trends(ws_id, start_d, end_d, grouping=PeriodGrouping.MONTH, currency=currency)
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data={"trends": res})

    async def _exec_category(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        start_d = date.fromisoformat(args["start_date"])
        end_d = date.fromisoformat(args["end_date"])
        currency = args.get("currency", "INR")
        cat_filter = args.get("category_name")
        svc = AnalyticsService(self.db)
        res = await svc.get_category_spending(ws_id, start_d, end_d, direction="outflow", currency=currency)

        # Filter to target category if specified
        if cat_filter and "categories" in res:
            res["categories"] = [
                c for c in res["categories"]
                if cat_filter.lower() in c.get("name", "").lower()
            ]
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=res)

    async def _exec_merchant(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        start_d = date.fromisoformat(args["start_date"])
        end_d = date.fromisoformat(args["end_date"])
        currency = args.get("currency", "INR")
        limit = min(25, max(1, args.get("limit", 10)))
        svc = AnalyticsService(self.db)
        res = await svc.get_merchant_spending(ws_id, start_d, end_d, limit=limit, currency=currency)
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=res)

    async def _exec_account_balances(self, tc: ToolCallVO, ws_id: uuid.UUID) -> ToolResultVO:
        stmt = (
            select(Account)
            .where(
                Account.workspace_id == ws_id,
                Account.status == "active",
                Account.is_deleted == False,
            )
            .order_by(Account.current_book_balance_paise.desc())
        )
        res = await self.db.execute(stmt)
        accounts = res.scalars().all()

        total_liquid_paise = sum(a.current_book_balance_paise for a in accounts if a.account_type in ("checking", "savings", "wallet", "cash"))
        data = {
            "total_liquid_rupees": round(total_liquid_paise / 100.0, 2),
            "total_liquid_paise": total_liquid_paise,
            "currency": "INR",
            "account_count": len(accounts),
            "accounts": [
                {
                    "name": a.name,
                    "account_type": a.account_type,
                    "currency": a.currency,
                    "current_balance_rupees": round(a.current_book_balance_paise / 100.0, 2),
                    "current_balance_paise": a.current_book_balance_paise,
                    "masked_account_number": f"•••{a.account_number[-4:]}" if a.account_number and len(a.account_number) >= 4 else None,
                }
                for a in accounts
            ],
        }
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=data)

    async def _exec_search_transactions(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        conditions = [
            Transaction.workspace_id == ws_id,
            Transaction.is_deleted == False,
            Transaction.status == "posted",
        ]
        if args.get("start_date"):
            conditions.append(Transaction.transaction_date >= date.fromisoformat(args["start_date"]))
        if args.get("end_date"):
            conditions.append(Transaction.transaction_date <= date.fromisoformat(args["end_date"]))
        if args.get("min_amount_paise"):
            conditions.append(Transaction.amount_paise >= args["min_amount_paise"])
        if args.get("query"):
            q_str = f"%{args['query']}%"
            conditions.append(or_(
                Transaction.description.ilike(q_str),
                Transaction.merchant_name.ilike(q_str),
            ))

        limit = min(25, max(1, args.get("limit", 10)))
        stmt = (
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(*conditions)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        txs = res.scalars().all()

        data = {
            "count": len(txs),
            "transactions": [
                {
                    "date": t.transaction_date.isoformat(),
                    "description": t.description,
                    "merchant_name": t.merchant_name,
                    "category": t.category.name if t.category else None,
                    "direction": t.direction,
                    "amount_rupees": round(t.amount_paise / 100.0, 2),
                    "amount_paise": t.amount_paise,
                    "currency": t.currency,
                }
                for t in txs
            ],
        }
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=data)

    async def _exec_budget_status(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        stmt = (
            select(Budget)
            .options(
                selectinload(Budget.allocations).selectinload(BudgetAllocation.category),
            )
            .where(
                Budget.workspace_id == ws_id,
                Budget.is_deleted == False,
            )
            .order_by(Budget.created_at.desc())
            .limit(5)
        )
        res = await self.db.execute(stmt)
        budgets = res.scalars().all()

        budget_summaries = []
        for b in budgets:
            total_limit = sum(a.limit_paise for a in b.allocations)
            total_spent = sum(a.actual_spent_paise for a in b.allocations)
            util = round(total_spent / max(1, total_limit) * 100.0, 1)

            budget_summaries.append({
                "id": str(b.id),
                "name": b.name,
                "period_type": b.period_type,
                "currency": b.currency,
                "limit_rupees": round(total_limit / 100.0, 2),
                "spent_rupees": round(total_spent / 100.0, 2),
                "remaining_rupees": round(max(0, total_limit - total_spent) / 100.0, 2),
                "utilization_pct": util,
                "is_overspent": total_spent > total_limit,
                "categories": [
                    {
                        "category_name": a.category.name if a.category else "Uncategorized",
                        "limit_rupees": round(a.limit_paise / 100.0, 2),
                        "spent_rupees": round(a.actual_spent_paise / 100.0, 2),
                        "utilization_pct": round(a.actual_spent_paise / max(1, a.limit_paise) * 100.0, 1),
                    }
                    for a in b.allocations
                ],
            })

        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data={"budgets": budget_summaries})

    async def _exec_goal_progress(self, tc: ToolCallVO, ws_id: uuid.UUID) -> ToolResultVO:
        stmt = (
            select(FinancialGoal)
            .where(
                FinancialGoal.workspace_id == ws_id,
                FinancialGoal.is_deleted == False,
                FinancialGoal.status.in_(("active", "in_progress")),
            )
            .order_by(FinancialGoal.target_date.asc().nullslast())
        )
        res = await self.db.execute(stmt)
        goals = res.scalars().all()

        goal_list = []
        for g in goals:
            pct = round(g.current_saved_paise / max(1, g.target_amount_paise) * 100.0, 1)
            goal_list.append({
                "name": g.name,
                "target_amount_rupees": round(g.target_amount_paise / 100.0, 2),
                "current_saved_rupees": round(g.current_saved_paise / 100.0, 2),
                "remaining_rupees": round(max(0, g.target_amount_paise - g.current_saved_paise) / 100.0, 2),
                "progress_pct": min(100.0, pct),
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "currency": g.currency,
            })
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data={"goals": goal_list})

    async def _exec_upcoming_commitments(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        days = min(60, max(1, args.get("days_ahead", 14)))
        today = date.today()
        end_d = today + timedelta(days=days)

        stmt = (
            select(RecurringDefinition)
            .where(
                RecurringDefinition.workspace_id == ws_id,
                RecurringDefinition.is_deleted == False,
                RecurringDefinition.status == "active",
            )
            .order_by(RecurringDefinition.next_due_date.asc().nullslast())
        )
        res = await self.db.execute(stmt)
        recs = res.scalars().all()

        upcoming = []
        total_upcoming_paise = 0
        for r in recs:
            if r.next_due_date and today <= r.next_due_date <= end_d:
                total_upcoming_paise += r.expected_amount_paise
                upcoming.append({
                    "name": r.name,
                    "expected_amount_rupees": round(r.expected_amount_paise / 100.0, 2),
                    "expected_amount_paise": r.expected_amount_paise,
                    "next_due_date": r.next_due_date.isoformat(),
                    "frequency": r.frequency,
                    "currency": r.currency,
                })

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "days_ahead": days,
                "total_upcoming_rupees": round(total_upcoming_paise / 100.0, 2),
                "upcoming_commitments": upcoming,
            },
        )

    async def _exec_subscriptions(self, tc: ToolCallVO, ws_id: uuid.UUID) -> ToolResultVO:
        stmt = (
            select(Subscription)
            .where(
                Subscription.workspace_id == ws_id,
                Subscription.is_deleted == False,
                Subscription.status == "active",
            )
            .order_by(Subscription.billing_cycle_paise.desc())
        )
        res = await self.db.execute(stmt)
        subs = res.scalars().all()

        total_burn_paise = 0
        sub_list = []
        for s in subs:
            monthly_equiv = s.billing_cycle_paise
            if s.billing_cycle == "yearly":
                monthly_equiv = int(round(s.billing_cycle_paise / 12.0))
            elif s.billing_cycle == "weekly":
                monthly_equiv = int(round(s.billing_cycle_paise * 4.33))

            total_burn_paise += monthly_equiv
            sub_list.append({
                "name": s.name,
                "billing_cycle": s.billing_cycle,
                "cycle_amount_rupees": round(s.billing_cycle_paise / 100.0, 2),
                "monthly_equivalent_rupees": round(monthly_equiv / 100.0, 2),
                "currency": s.currency,
            })

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "active_subscription_count": len(subs),
                "monthly_recurring_burn_rupees": round(total_burn_paise / 100.0, 2),
                "subscriptions": sub_list,
            },
        )

    async def _exec_forecast(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        horizon = min(90, max(7, args.get("horizon_days", 30)))
        # Lightweight forward estimates based on trailing 30d daily cash flow velocity
        svc = AnalyticsService(self.db)
        today = date.today()
        hist_30 = await svc.get_overview(ws_id, today - timedelta(days=30), today)

        avg_daily_outflow = hist_30.get("total_outflow_rupees", 0.0) / 30.0
        avg_daily_inflow = hist_30.get("total_inflow_rupees", 0.0) / 30.0

        projected_outflow = round(avg_daily_outflow * horizon, 2)
        projected_inflow = round(avg_daily_inflow * horizon, 2)
        projected_net = round(projected_inflow - projected_outflow, 2)

        data = {
            "horizon_days": horizon,
            "projected_inflow_rupees": projected_inflow,
            "projected_expense_rupees": projected_outflow,
            "projected_net_cash_flow_rupees": projected_net,
            "confidence_level": "80%",
            "disclaimer": "Informational statistical estimate based on recent daily run-rate. Not a guaranteed financial outcome.",
        }
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=data)

    async def _exec_anomalies(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        limit = min(20, max(1, args.get("limit", 5)))
        repo = AnomalyRepository(self.db)
        detections, total = await repo.list_detections(ws_id, limit=limit)

        data = {
            "total_anomalies": total,
            "recent_anomalies": [
                {
                    "detection_type": d.detection_type,
                    "severity": d.severity,
                    "risk_score": d.risk_score,
                    "explanation": d.explanation,
                    "status": d.status,
                    "detected_at": d.detected_at.isoformat(),
                }
                for d in detections
            ],
        }
        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=data)

    async def _exec_search_documents(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        limit = min(20, max(1, args.get("limit", 10)))
        status_filter = args.get("status")
        doc_type = args.get("document_type")
        search_query = args.get("search")

        repo = DocumentRepository(self.db)
        docs, total = await repo.list_workspace_documents(
            workspace_id=ws_id,
            status=status_filter,
            document_type=doc_type,
            search_query=search_query,
            limit=limit,
        )

        doc_summaries = []
        for d in docs:
            latest_ext = d.extractions[0] if d.extractions else None
            structured = latest_ext.structured_data if latest_ext else {}
            doc_summaries.append({
                "id": str(d.id),
                "filename": d.original_filename,
                "status": d.status,
                "document_type": d.document_type,
                "created_at": d.created_at.isoformat(),
                "merchant_name": structured.get("merchant_name"),
                "total_amount": structured.get("total_amount"),
                "date": structured.get("receipt_date"),
                "is_linked_to_transaction": len(d.transaction_associations) > 0,
            })

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={"total_documents": total, "documents": doc_summaries},
        )

    async def _exec_document_details(self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]) -> ToolResultVO:
        doc_id_raw = args.get("document_id")
        if not doc_id_raw:
            return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=False, error="Missing required parameter 'document_id'.")

        try:
            doc_id = uuid.UUID(str(doc_id_raw))
        except ValueError:
            return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=False, error=f"Invalid UUID '{doc_id_raw}'.")

        repo = DocumentRepository(self.db)
        doc = await repo.get_document_details(doc_id, ws_id)
        if not doc:
            return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=False, error=f"Document '{doc_id}' not found.")

        latest_ext = doc.extractions[0] if doc.extractions else None

        data = {
            "id": str(doc.id),
            "filename": doc.original_filename,
            "status": doc.status,
            "document_type": doc.document_type,
            "created_at": doc.created_at.isoformat(),
            "mime_type": doc.mime_type,
            "file_size_bytes": doc.file_size,
            "extraction": {
                "ocr_provider": latest_ext.ocr_provider if latest_ext else None,
                "overall_confidence": float(latest_ext.overall_confidence) if latest_ext else 0.0,
                "validation_status": latest_ext.validation_status if latest_ext else None,
                "validation_warnings": latest_ext.validation_warnings if latest_ext else [],
                "structured_data": latest_ext.structured_data if latest_ext else {},
            } if latest_ext else None,
            "linked_transactions": [
                {
                    "association_id": str(a.id),
                    "transaction_id": str(a.transaction_id),
                    "type": a.association_type,
                }
                for a in doc.transaction_associations
            ],
        }

        return ToolResultVO(call_id=tc.call_id, tool_name=tc.tool_name, success=True, data=data)

    async def _exec_unread_notifications(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.repositories.notification_repository import NotificationRepository

        limit = int(args.get("limit", 5))
        repo = NotificationRepository(self.db)
        items, total = await repo.list_notifications(
            user_id=user_id, workspace_id=ws_id, is_read=False, limit=limit
        )
        notif_summaries = [
            {
                "id": str(n.id),
                "category": n.category,
                "title": n.title,
                "message": n.message,
                "severity": n.severity,
                "created_at": n.created_at.isoformat(),
                "action_url": n.action_url,
            }
            for n in items
        ]
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={"unread_count": total, "notifications": notif_summaries},
        )

    async def _exec_family_overview(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.infrastructure.database.models.workspace import Workspace
        from app.services.family_service import FamilyService
        from app.core.permissions import WorkspaceContext

        stmt = select(Workspace).where(Workspace.id == ws_id)
        ws = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ws or ws.type != "family":
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="Active workspace is not a family workspace.",
            )

        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one()

        member_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id,
        )
        membership = (await self.db.execute(member_stmt)).scalar_one_or_none()
        if not membership:
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="User is not a member of this family workspace.",
            )

        context = WorkspaceContext(
            workspace=ws,
            membership=membership,
            current_user=user,
            role=membership.role,
        )
        service = FamilyService(self.db)
        overview = await service.get_family_overview(context)
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data=overview.model_dump(),
        )

    async def _exec_family_settlement_summary(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.infrastructure.database.models.workspace import Workspace
        from app.services.family_service import FamilyService
        from app.core.permissions import WorkspaceContext

        stmt = select(Workspace).where(Workspace.id == ws_id)
        ws = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ws or ws.type != "family":
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="Active workspace is not a family workspace.",
            )

        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one()

        member_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id,
        )
        membership = (await self.db.execute(member_stmt)).scalar_one_or_none()
        if not membership:
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="User is not a member of this family workspace.",
            )

        context = WorkspaceContext(
            workspace=ws,
            membership=membership,
            current_user=user,
            role=membership.role,
        )
        period = args.get("period")
        service = FamilyService(self.db)
        summary = await service.get_settlement_summary(context, period)
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data=summary.model_dump(),
        )

    async def _exec_family_commitments(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.infrastructure.database.models.recurring import RecurringDefinition

        stmt = (
            select(RecurringDefinition)
            .where(
                RecurringDefinition.workspace_id == ws_id,
                RecurringDefinition.status == "active",
            )
            .order_by(RecurringDefinition.next_expected_date.asc())
            .limit(10)
        )
        res = await self.db.execute(stmt)
        defs = res.scalars().all()
        commitments = [
            {
                "id": str(d.id),
                "name": d.name,
                "amount": float(d.expected_amount),
                "currency": d.currency,
                "next_expected_date": str(d.next_expected_date) if d.next_expected_date else None,
                "interval": d.interval,
                "category": d.category.name if d.category else None,
            }
            for d in defs
        ]
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={"commitments_count": len(commitments), "commitments": commitments},
        )

    async def _exec_business_overview(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.services.business_service import BusinessService
        from app.core.permissions import WorkspaceContext

        stmt = select(Workspace).where(Workspace.id == ws_id)
        ws = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ws or ws.type != "business":
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="Active workspace is not a commercial business workspace.",
            )

        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one()

        member_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id,
        )
        membership = (await self.db.execute(member_stmt)).scalar_one_or_none()
        if not membership:
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="User is not an active member of this business workspace.",
            )

        context = WorkspaceContext(
            workspace=ws,
            membership=membership,
            current_user=user,
            role=membership.role,
        )
        service = BusinessService(self.db)
        kpis = await service.get_overview(context)
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "invoiced_revenue": f"₹{kpis['invoiced_revenue_paise'] / 100:,.2f}",
                "collected_revenue": f"₹{kpis['collected_revenue_paise'] / 100:,.2f}",
                "total_receivables": f"₹{kpis['total_receivables_paise'] / 100:,.2f}",
                "total_vendor_bills": f"₹{kpis['total_bills_paise'] / 100:,.2f}",
                "paid_vendor_bills": f"₹{kpis['paid_bills_paise'] / 100:,.2f}",
                "total_payables": f"₹{kpis['total_payables_paise'] / 100:,.2f}",
                "net_operating_result": f"₹{kpis['net_operating_result_paise'] / 100:,.2f}",
                "active_clients": kpis["active_clients_count"],
                "active_vendors": kpis["active_vendors_count"],
                "open_invoices": kpis["total_invoices_count"],
                "overdue_invoices": kpis["overdue_invoices_count"],
            },
        )

    async def _exec_business_receivables(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.services.business_service import BusinessService
        from app.core.permissions import WorkspaceContext

        stmt = select(Workspace).where(Workspace.id == ws_id)
        ws = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ws or ws.type != "business":
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="Active workspace is not a commercial business workspace.",
            )

        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one()

        member_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id,
        )
        membership = (await self.db.execute(member_stmt)).scalar_one_or_none()
        if not membership:
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="User is not an active member of this business workspace.",
            )

        context = WorkspaceContext(
            workspace=ws,
            membership=membership,
            current_user=user,
            role=membership.role,
        )
        service = BusinessService(self.db)
        ar_aging = await service.get_receivables_aging(context)
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "current": f"₹{ar_aging['current_paise'] / 100:,.2f}",
                "days_1_30": f"₹{ar_aging['days_1_30_paise'] / 100:,.2f}",
                "days_31_60": f"₹{ar_aging['days_31_60_paise'] / 100:,.2f}",
                "days_61_90": f"₹{ar_aging['days_61_90_paise'] / 100:,.2f}",
                "days_91_plus": f"₹{ar_aging['days_91_plus_paise'] / 100:,.2f}",
                "total_outstanding_receivables": f"₹{ar_aging['total_outstanding_paise'] / 100:,.2f}",
            },
        )

    async def _exec_business_payables(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.services.business_service import BusinessService
        from app.core.permissions import WorkspaceContext

        stmt = select(Workspace).where(Workspace.id == ws_id)
        ws = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ws or ws.type != "business":
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="Active workspace is not a commercial business workspace.",
            )

        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one()

        member_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id,
        )
        membership = (await self.db.execute(member_stmt)).scalar_one_or_none()
        if not membership:
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="User is not an active member of this business workspace.",
            )

        context = WorkspaceContext(
            workspace=ws,
            membership=membership,
            current_user=user,
            role=membership.role,
        )
        service = BusinessService(self.db)
        ap_aging = await service.get_payables_aging(context)
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "current": f"₹{ap_aging['current_paise'] / 100:,.2f}",
                "days_1_30": f"₹{ap_aging['days_1_30_paise'] / 100:,.2f}",
                "days_31_60": f"₹{ap_aging['days_31_60_paise'] / 100:,.2f}",
                "days_61_90": f"₹{ap_aging['days_61_90_paise'] / 100:,.2f}",
                "days_91_plus": f"₹{ap_aging['days_91_plus_paise'] / 100:,.2f}",
                "total_outstanding_payables": f"₹{ap_aging['total_outstanding_paise'] / 100:,.2f}",
            },
        )

    async def _exec_business_cash_flow(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.services.business_service import BusinessService
        from app.core.permissions import WorkspaceContext

        stmt = select(Workspace).where(Workspace.id == ws_id)
        ws = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ws or ws.type != "business":
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="Active workspace is not a commercial business workspace.",
            )

        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one()

        member_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id,
        )
        membership = (await self.db.execute(member_stmt)).scalar_one_or_none()
        if not membership:
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error="User is not an active member of this business workspace.",
            )

        context = WorkspaceContext(
            workspace=ws,
            membership=membership,
            current_user=user,
            role=membership.role,
        )
        service = BusinessService(self.db)
        kpis = await service.get_overview(context)
        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "operating_cash_inflow": f"₹{kpis['collected_revenue_paise'] / 100:,.2f}",
                "operating_cash_outflow": f"₹{kpis['paid_bills_paise'] / 100:,.2f}",
                "net_operating_cash_flow": f"₹{kpis['net_cash_result_paise'] / 100:,.2f}",
                "accrual_operating_result": f"₹{kpis['net_operating_result_paise'] / 100:,.2f}",
                "pending_client_collections": f"₹{kpis['total_receivables_paise'] / 100:,.2f}",
                "pending_vendor_payments": f"₹{kpis['total_payables_paise'] / 100:,.2f}",
            },
        )

    async def _exec_connected_accounts_overview(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID
    ) -> ToolResultVO:
        from app.repositories.financial_connection_repository import FinancialConnectionRepository

        repo = FinancialConnectionRepository(self.db)
        connections = await repo.list_connections(ws_id)

        items = []
        for conn in connections:
            refs = await repo.list_account_references(conn.id)
            for ref in refs:
                items.append({
                    "connection_id": str(conn.id),
                    "institution_name": conn.institution_name,
                    "masked_account": ref.masked_account_number,
                    "account_type": ref.account_type,
                    "link_status": ref.status,
                    "reported_balance": f"₹{(ref.current_balance_paise or 0) / 100:,.2f}" if ref.current_balance_paise is not None else "N/A",
                    "health": conn.health_status,
                    "last_synced": conn.last_successful_sync_at.isoformat() if conn.last_successful_sync_at else "Never",
                })

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={"total_connected_accounts": len(items), "accounts": items},
        )

    async def _exec_connection_sync_health(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID
    ) -> ToolResultVO:
        from app.repositories.financial_connection_repository import FinancialConnectionRepository

        repo = FinancialConnectionRepository(self.db)
        connections = await repo.list_connections(ws_id)

        items = []
        for conn in connections:
            items.append({
                "connection_id": str(conn.id),
                "institution_name": conn.institution_name,
                "status": conn.status,
                "health_status": conn.health_status,
                "last_successful_sync": conn.last_successful_sync_at.isoformat() if conn.last_successful_sync_at else "Never",
                "failure_count": conn.sync_failure_count,
                "last_error": conn.last_error_message or "None",
                "expires_at": conn.expires_at.isoformat() if conn.expires_at else "No expiry",
            })

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={"connection_count": len(items), "connections": items},
        )

    async def _exec_account_reconciliation_summary(
        self, tc: ToolCallVO, user_id: uuid.UUID, ws_id: uuid.UUID
    ) -> ToolResultVO:
        from app.repositories.financial_connection_repository import FinancialConnectionRepository

        repo = FinancialConnectionRepository(self.db)
        records = await repo.list_reconciliation_records(ws_id, limit=20)

        items = []
        for rec in records:
            items.append({
                "reconciliation_id": str(rec.id),
                "reconciliation_date": str(rec.reconciliation_date),
                "reported_balance": f"₹{rec.provider_reported_balance_paise / 100:,.2f}",
                "book_balance": f"₹{rec.calculated_book_balance_paise / 100:,.2f}",
                "variance": f"₹{rec.difference_paise / 100:,.2f}",
                "status": rec.status,
                "explanation": rec.explanation or "No explanation provided.",
            })

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={"total_records": len(items), "reconciliations": items},
        )

    async def _exec_financial_statement_summary(
        self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.domain.financial_report import calculate_indian_financial_year
        from app.services.financial_reporting_service import FinancialReportingService

        service = FinancialReportingService(self.db)
        period_type = args.get("period_type", "financial_year")
        fy = args.get("fiscal_year") or calculate_indian_financial_year(date.today())
        statement_type = args.get("statement_type", "income_statement")
        basis = args.get("basis", "cash")

        period = service.resolve_reporting_period(
            period_type=period_type,
            fiscal_year=fy,
        )

        if statement_type in ["income_statement", "income_expense"]:
            stmt = await service.generate_income_and_expense_statement(ws_id, period, basis=basis)
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=True,
                data={
                    "statement": "Income and Expense Statement",
                    "period": period.label,
                    "basis": stmt.accounting_basis.value if hasattr(stmt.accounting_basis, 'value') else str(stmt.accounting_basis),
                    "total_income": f"₹{stmt.total_income_paise / 100:,.2f}",
                    "total_expense": f"₹{stmt.total_expenses_paise / 100:,.2f}",
                    "net_result": f"₹{stmt.net_surplus_deficit_paise / 100:,.2f}",
                    "result_type": "Surplus" if stmt.net_surplus_deficit_paise >= 0 else "Deficit",
                    "line_item_count": len(stmt.income_lines) + len(stmt.expense_lines),
                },
            )
        elif statement_type in ["cash_flow", "cash_flow_statement"]:
            cf = await service.generate_cash_flow_statement(ws_id, period)
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=True,
                data={
                    "statement": "Cash Flow Statement",
                    "period": period.label,
                    "operating_cash_flow": f"₹{cf.net_operating_cash_flow_paise / 100:,.2f}",
                    "investing_cash_flow": f"₹{cf.net_investing_cash_flow_paise / 100:,.2f}",
                    "financing_cash_flow": f"₹{cf.net_financing_cash_flow_paise / 100:,.2f}",
                    "net_cash_change": f"₹{cf.net_cash_change_paise / 100:,.2f}",
                    "opening_balance": f"₹{cf.opening_cash_balance_paise / 100:,.2f}",
                    "closing_balance": f"₹{cf.closing_cash_balance_paise / 100:,.2f}",
                },
            )
        elif statement_type == "balance_sheet":
            bs = await service.generate_balance_sheet(ws_id, period.end_date)
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=True,
                data={
                    "statement": "Balance Sheet",
                    "as_of_date": str(bs.as_of_date),
                    "total_assets": f"₹{bs.total_assets_paise / 100:,.2f}",
                    "total_liabilities": f"₹{bs.total_liabilities_paise / 100:,.2f}",
                    "total_equity": f"₹{bs.total_equity_paise / 100:,.2f}",
                    "is_balanced": bs.is_balanced,
                    "discrepancy": f"₹{bs.discrepancy_paise / 100:,.2f}",
                },
            )
        elif statement_type == "trial_balance":
            tb = await service.generate_trial_balance(ws_id, period.end_date)
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=True,
                data={
                    "statement": "Trial Balance",
                    "as_of_date": str(tb.as_of_date),
                    "total_debits": f"₹{tb.total_debits_paise / 100:,.2f}",
                    "total_credits": f"₹{tb.total_credits_paise / 100:,.2f}",
                    "is_balanced": tb.is_balanced,
                    "discrepancy": f"₹{tb.discrepancy_paise / 100:,.2f}",
                },
            )
        else:
            return ToolResultVO(
                call_id=tc.call_id,
                tool_name=tc.tool_name,
                success=False,
                error=f"Unsupported statement type '{statement_type}'.",
            )

    async def _exec_tax_classification_summary(
        self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.domain.financial_report import calculate_indian_financial_year
        from app.services.financial_reporting_service import FinancialReportingService

        service = FinancialReportingService(self.db)
        fy = args.get("tax_year") or calculate_indian_financial_year(date.today())
        records = await service.report_repo.list_tax_classifications(ws_id, tax_year=fy, limit=100)

        confirmed_count = sum(1 for r in records if r.review_status in ["confirmed", "reviewed"])
        suggested_count = sum(1 for r in records if r.review_status == "suggested")
        total_deductible = sum(r.deductible_amount_paise for r in records if r.review_status in ["confirmed", "reviewed"])

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "financial_year": fy,
                "total_classified_records": len(records),
                "confirmed_count": confirmed_count,
                "pending_review_count": suggested_count,
                "confirmed_deductions": f"₹{total_deductible / 100:,.2f}",
            },
        )

    async def _exec_gst_reporting_summary(
        self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.domain.financial_report import calculate_indian_financial_year
        from app.services.financial_reporting_service import FinancialReportingService

        service = FinancialReportingService(self.db)
        fy = args.get("fiscal_year") or calculate_indian_financial_year(date.today())
        period = service.resolve_reporting_period(
            period_type=args.get("period_type", "financial_year"),
            fiscal_year=fy,
        )
        summary = await service.generate_gst_summary(ws_id, period)

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "period": period.label,
                "taxable_turnover": f"₹{summary.taxable_sales_paise / 100:,.2f}",
                "output_cgst": f"₹{summary.output_cgst_paise / 100:,.2f}",
                "output_sgst": f"₹{summary.output_sgst_paise / 100:,.2f}",
                "output_igst": f"₹{summary.output_igst_paise / 100:,.2f}",
                "total_output_gst": f"₹{summary.total_output_tax_paise / 100:,.2f}",
                "invoices_analyzed": summary.invoices_analyzed_count,
                "disclaimer": summary.data_disclaimer,
            },
        )

    async def _exec_explain_report_discrepancies(
        self, tc: ToolCallVO, ws_id: uuid.UUID, args: Dict[str, Any]
    ) -> ToolResultVO:
        from app.domain.financial_report import calculate_indian_financial_year
        from app.services.financial_reporting_service import FinancialReportingService

        service = FinancialReportingService(self.db)
        fy = args.get("fiscal_year") or calculate_indian_financial_year(date.today())
        period = service.resolve_reporting_period(period_type="financial_year", fiscal_year=fy)

        findings = await service.run_validations(ws_id, period)

        items = []
        for f in findings:
            items.append({
                "rule_code": f.rule_code,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "recommended_action": f.recommended_action,
                "is_resolved": f.is_resolved,
            })

        return ToolResultVO(
            call_id=tc.call_id,
            tool_name=tc.tool_name,
            success=True,
            data={
                "period": period.label,
                "findings_count": len(items),
                "unresolved_count": sum(1 for item in items if not item["is_resolved"]),
                "findings": items,
            },
        )
