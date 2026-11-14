"""
Arthsavora Budget Repository
Data access layer for budgets, category allocations, audit revisions,
idempotent threshold alerts, and server-side transaction spending aggregation.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import BigInteger, case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.domain.budget import BudgetStatus
from app.infrastructure.database.models.budget import (
    Budget,
    BudgetAllocation,
    BudgetRevision,
    BudgetAlert,
)
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.workspace_scoped import WorkspaceScopedRepository

# Consistent transaction types matching Prompt 13 analytics foundation
EXPENSE_TRANSACTION_TYPES = (
    "expense",
    "withdrawal",
    "bank_fee",
    "tax",
    "credit_card_purchase",
    "credit_card_fee",
    "credit_card_interest",
    "loan_interest_payment",
    "loan_fee",
    "investment_fee",
    "cash_transaction",
)

REFUND_TRANSACTION_TYPES = (
    "refund",
    "credit_card_refund",
)

EXCLUDED_TRANSFER_TYPES = (
    "transfer",
    "credit_card_payment",
    "loan_disbursal",
    "loan_principal_repayment",
    "investment_contribution",
    "investment_withdrawal",
    "adjustment",
    "reversal",
)


class BudgetRepository(WorkspaceScopedRepository[Budget]):
    """Repository handling all Budget and Allocation persistence and spending aggregations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Budget)

    async def get_budget_with_allocations(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[Budget]:
        """Retrieves budget by ID strictly scoped to workspace, eagerly loading category allocations."""
        stmt = (
            select(Budget)
            .options(
                selectinload(Budget.allocations).selectinload(BudgetAllocation.category),
            )
            .where(
                Budget.id == budget_id,
                Budget.workspace_id == workspace_id,
                Budget.is_deleted == False,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_budgets(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Budget], int]:
        """Lists paginated budgets for workspace with optional status filter."""
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        conditions = [
            Budget.workspace_id == workspace_id,
            Budget.is_deleted == False,
        ]
        if status:
            conditions.append(Budget.status == status)

        count_stmt = select(func.count(Budget.id)).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Budget)
            .options(
                selectinload(Budget.allocations).selectinload(BudgetAllocation.category),
            )
            .where(*conditions)
            .order_by(Budget.start_date.desc(), Budget.created_at.desc())
            .limit(safe_limit)
            .offset(safe_offset)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def get_allocation(
        self,
        allocation_id: uuid.UUID,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[BudgetAllocation]:
        """Retrieves specific allocation scoped to budget and workspace."""
        stmt = select(BudgetAllocation).where(
            BudgetAllocation.id == allocation_id,
            BudgetAllocation.budget_id == budget_id,
            BudgetAllocation.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_allocation_by_category(
        self,
        budget_id: uuid.UUID,
        category_id: uuid.UUID,
    ) -> Optional[BudgetAllocation]:
        """Finds existing allocation for a category in a budget to prevent duplicates."""
        stmt = select(BudgetAllocation).where(
            BudgetAllocation.budget_id == budget_id,
            BudgetAllocation.category_id == category_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def calculate_actual_spending_for_budget(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        currency: str = "INR",
        category_ids: Optional[List[uuid.UUID]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a single PostgreSQL aggregation query computing actual eligible spending
        both overall and broken down by category.
        
        Strict Rules:
        - Only posted transactions included.
        - Excludes transfers (transfer_id IS NOT NULL or type in excluded transfers).
        - Excludes credit-card payment liability settlements.
        - Refunds net against category spending.
        """
        is_posted = Transaction.status == "posted"
        is_not_transfer = (
            Transaction.transfer_id.is_(None)
            & (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES))
        )
        is_expense = (
            Transaction.transaction_type.in_(EXPENSE_TRANSACTION_TYPES)
            | ((Transaction.direction == "outflow") & (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)))
        )
        is_refund = Transaction.transaction_type.in_(REFUND_TRANSACTION_TYPES)

        base_conditions = [
            Transaction.workspace_id == workspace_id,
            Transaction.is_deleted == False,
            Transaction.currency == currency,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            is_posted,
            is_not_transfer,
            (is_expense | is_refund),
        ]

        # 1. Overall spending: sum(expenses) - sum(refunds)
        overall_stmt = select(
            func.coalesce(
                func.sum(case((is_expense, Transaction.amount_paise), else_=0)),
                0,
            ).label("gross_expenses_paise"),
            func.coalesce(
                func.sum(case((is_refund, Transaction.amount_paise), else_=0)),
                0,
            ).label("refunds_paise"),
            func.count(Transaction.id).label("transaction_count"),
        ).where(*base_conditions)

        overall_row = (await self.session.execute(overall_stmt)).one()
        gross_expenses_paise = int(overall_row.gross_expenses_paise)
        refunds_paise = int(overall_row.refunds_paise)
        net_overall_spent_paise = max(0, gross_expenses_paise - refunds_paise)

        # 2. Category-wise breakdown: sum(expenses) - sum(refunds) grouped by category_id
        cat_stmt = (
            select(
                Transaction.category_id,
                func.coalesce(
                    func.sum(case((is_expense, Transaction.amount_paise), else_=0)),
                    0,
                ).label("cat_gross_paise"),
                func.coalesce(
                    func.sum(case((is_refund, Transaction.amount_paise), else_=0)),
                    0,
                ).label("cat_refund_paise"),
                func.count(Transaction.id).label("cat_tx_count"),
            )
            .where(*base_conditions)
            .group_by(Transaction.category_id)
        )
        cat_rows = (await self.session.execute(cat_stmt)).all()

        category_spending_map: Dict[Optional[uuid.UUID], Dict[str, Any]] = {}
        for r in cat_rows:
            cat_gross = int(r.cat_gross_paise)
            cat_ref = int(r.cat_refund_paise)
            net_cat_spent = max(0, cat_gross - cat_ref)
            category_spending_map[r.category_id] = {
                "spent_paise": net_cat_spent,
                "spent": Decimal(net_cat_spent) / Decimal(100),
                "transaction_count": int(r.cat_tx_count),
            }

        return {
            "overall_spent_paise": net_overall_spent_paise,
            "overall_spent": Decimal(net_overall_spent_paise) / Decimal(100),
            "gross_expenses_paise": gross_expenses_paise,
            "refunds_paise": refunds_paise,
            "transaction_count": int(overall_row.transaction_count),
            "category_spending_map": category_spending_map,
        }

    async def record_revision(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        revision_type: str,
        previous_amount_paise: Optional[int],
        new_amount_paise: Optional[int],
        change_reason: Optional[str] = None,
        allocation_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        changed_by_id: Optional[uuid.UUID] = None,
    ) -> BudgetRevision:
        """Appends an immutable revision audit entry."""
        revision = BudgetRevision(
            budget_id=budget_id,
            workspace_id=workspace_id,
            allocation_id=allocation_id,
            category_id=category_id,
            revision_type=revision_type,
            previous_amount_paise=previous_amount_paise,
            new_amount_paise=new_amount_paise,
            change_reason=change_reason,
            changed_by_id=changed_by_id,
        )
        self.session.add(revision)
        return revision

    async def list_revisions(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> List[BudgetRevision]:
        """Retrieves ordered historical revisions for a budget."""
        stmt = (
            select(BudgetRevision)
            .options(selectinload(BudgetRevision.changed_by))
            .where(
                BudgetRevision.budget_id == budget_id,
                BudgetRevision.workspace_id == workspace_id,
            )
            .order_by(BudgetRevision.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def record_alert_idempotent(
        self,
        budget_id: uuid.UUID,
        workspace_id: uuid.UUID,
        alert_type: str,
        threshold_percentage: int,
        actual_spent_paise: int,
        allocated_amount_paise: int,
        utilization_percentage: Decimal,
        message: str,
        allocation_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
    ) -> Optional[BudgetAlert]:
        """
        Idempotently logs a threshold crossed alert using check-and-insert.
        Guarantees that crossing 80% or 100% does not send duplicate alerts on subsequent transactions.
        """
        check_conds = [
            BudgetAlert.budget_id == budget_id,
            BudgetAlert.threshold_percentage == threshold_percentage,
        ]
        if allocation_id is None:
            check_conds.append(BudgetAlert.allocation_id.is_(None))
        else:
            check_conds.append(BudgetAlert.allocation_id == allocation_id)

        existing = (await self.session.execute(select(BudgetAlert).where(*check_conds))).scalar_one_or_none()
        if existing:
            return None

        alert = BudgetAlert(
            budget_id=budget_id,
            workspace_id=workspace_id,
            allocation_id=allocation_id,
            category_id=category_id,
            alert_type=alert_type,
            threshold_percentage=threshold_percentage,
            actual_spent_paise=actual_spent_paise,
            allocated_amount_paise=allocated_amount_paise,
            utilization_percentage=utilization_percentage,
            message=message,
            is_read=False,
            delivery_status="in_app",
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def list_alerts(
        self,
        workspace_id: uuid.UUID,
        budget_id: Optional[uuid.UUID] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[BudgetAlert]:
        """Retrieves budget alerts for in-app notifications."""
        conditions = [BudgetAlert.workspace_id == workspace_id]
        if budget_id:
            conditions.append(BudgetAlert.budget_id == budget_id)
        if unread_only:
            conditions.append(BudgetAlert.is_read == False)

        stmt = (
            select(BudgetAlert)
            .where(*conditions)
            .order_by(BudgetAlert.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())
