"""
Arthsavora Financial Goal Repository
Data access layer for savings goals and the immutable contribution/withdrawal activity ledger.
Enforces non-negative balance consistency, atomic balance recalculations, and multi-tenant isolation.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.domain.budget import GoalActivityType, GoalStatus
from app.domain.exceptions import BusinessRuleViolationError
from app.infrastructure.database.models.goal import FinancialGoal, GoalActivity
from app.repositories.workspace_scoped import WorkspaceScopedRepository


class GoalRepository(WorkspaceScopedRepository[FinancialGoal]):
    """Repository handling all FinancialGoal persistence and activity ledger operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, FinancialGoal)

    async def get_goal_scoped(
        self,
        goal_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[FinancialGoal]:
        """Retrieves goal strictly scoped to workspace, eagerly loading recent activities."""
        stmt = (
            select(FinancialGoal)
            .options(
                selectinload(FinancialGoal.activities).selectinload(GoalActivity.performed_by),
            )
            .where(
                FinancialGoal.id == goal_id,
                FinancialGoal.workspace_id == workspace_id,
                FinancialGoal.is_deleted == False,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_goals(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        goal_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FinancialGoal], int]:
        """Lists paginated goals for workspace with optional status/type filters."""
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        conditions = [
            FinancialGoal.workspace_id == workspace_id,
            FinancialGoal.is_deleted == False,
        ]
        if status:
            conditions.append(FinancialGoal.status == status)
        if goal_type:
            conditions.append(FinancialGoal.goal_type == goal_type)

        count_stmt = select(func.count(FinancialGoal.id)).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(FinancialGoal)
            .where(*conditions)
            .order_by(FinancialGoal.created_at.desc())
            .limit(safe_limit)
            .offset(safe_offset)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def record_activity(
        self,
        goal: FinancialGoal,
        activity_type: GoalActivityType,
        amount_paise: int,
        transaction_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        performed_by_id: Optional[uuid.UUID] = None,
    ) -> GoalActivity:
        """
        Appends an entry to the goal activity ledger and atomically updates the goal balance.
        Guarantees that goal balance does not go negative on withdrawal.
        """
        if amount_paise <= 0:
            raise BusinessRuleViolationError(
                rule_name="INVALID_ACTIVITY_AMOUNT",
                message="Goal activity amount must be strictly greater than zero.",
            )

        current_balance = goal.current_amount_paise

        if activity_type in (GoalActivityType.CONTRIBUTION, GoalActivityType.TRANSFER_IN):
            new_balance = current_balance + amount_paise
        elif activity_type in (GoalActivityType.WITHDRAWAL, GoalActivityType.REVERSAL, GoalActivityType.TRANSFER_OUT):
            if amount_paise > current_balance:
                raise BusinessRuleViolationError(
                    rule_name="INSUFFICIENT_GOAL_BALANCE",
                    message=f"Cannot withdraw {amount_paise} paise: goal current balance is only {current_balance} paise.",
                )
            new_balance = current_balance - amount_paise
        else:
            new_balance = current_balance

        # Atomically update goal balance
        goal.current_amount_paise = new_balance
        goal.current_amount = Decimal(new_balance) / Decimal(100)

        # Auto-complete status if target reached
        if new_balance >= goal.target_amount_paise and goal.status == GoalStatus.ACTIVE.value:
            goal.status = GoalStatus.COMPLETED.value
        elif new_balance < goal.target_amount_paise and goal.status == GoalStatus.COMPLETED.value:
            # Reverted back below target
            goal.status = GoalStatus.ACTIVE.value

        activity = GoalActivity(
            goal_id=goal.id,
            workspace_id=goal.workspace_id,
            activity_type=activity_type.value if hasattr(activity_type, "value") else str(activity_type),
            amount_paise=amount_paise,
            amount=Decimal(amount_paise) / Decimal(100),
            currency=goal.currency,
            resulting_balance_paise=new_balance,
            transaction_id=transaction_id,
            notes=notes,
            performed_by_id=performed_by_id,
        )
        self.session.add(activity)
        return activity

    async def list_activities(
        self,
        goal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[GoalActivity], int]:
        """Retrieves paginated ledger entries for a goal."""
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        conditions = [
            GoalActivity.goal_id == goal_id,
            GoalActivity.workspace_id == workspace_id,
        ]

        count_stmt = select(func.count(GoalActivity.id)).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(GoalActivity)
            .options(selectinload(GoalActivity.performed_by))
            .where(*conditions)
            .order_by(GoalActivity.created_at.desc())
            .limit(safe_limit)
            .offset(safe_offset)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total
