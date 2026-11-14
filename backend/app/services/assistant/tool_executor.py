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
