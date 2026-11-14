"""
Arthsavora Financial Goal Application Service
Orchestrates personal savings goals, pacing calculations, and the auditable
contribution/withdrawal activity ledger.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.budget import (
    GoalActivityType,
    GoalPriority,
    GoalStatus,
    GoalType,
    calculate_goal_progress,
)
from app.core.exceptions import NotFoundException
from app.domain.exceptions import BusinessRuleViolationError
from app.infrastructure.database.models.goal import FinancialGoal, GoalActivity
from app.repositories.goal_repository import GoalRepository


class GoalService:
    """Service layer orchestrating target-based financial savings goals and activity ledger."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GoalRepository(session)

    def _validate_currency(self, currency: str) -> str:
        """Validates ISO 4217 3-letter currency code."""
        c = currency.strip().upper()
        if len(c) != 3 or not c.isalpha():
            raise BusinessRuleViolationError(
                rule_name="INVALID_CURRENCY",
                message=f"Currency '{currency}' must be a valid 3-letter ISO code.",
            )
        return c

    async def create_goal(
        self,
        workspace_id: uuid.UUID,
        name: str,
        target_amount_paise: int,
        goal_type: str = "personal_savings",
        currency: str = "INR",
        start_date: Optional[date] = None,
        target_date: Optional[date] = None,
        priority: str = "medium",
        color: Optional[str] = "#6366f1",
        icon: Optional[str] = "target",
        description: Optional[str] = None,
        created_by_id: Optional[uuid.UUID] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> FinancialGoal:
        """Creates a new financial savings goal with target parameters."""
        valid_curr = self._validate_currency(currency)

        if target_amount_paise <= 0:
            raise BusinessRuleViolationError(
                rule_name="INVALID_TARGET_AMOUNT",
                message="Goal target amount must be strictly greater than zero.",
            )

        eff_start_date = start_date or date.today()
        if target_date and target_date < eff_start_date:
            raise BusinessRuleViolationError(
                rule_name="INVALID_GOAL_DATES",
                message=f"Target date ({target_date}) cannot be before start date ({eff_start_date}).",
            )

        # Validate goal_type and priority enums
        valid_types = {t.value for t in GoalType}
        if goal_type not in valid_types:
            goal_type = GoalType.PERSONAL_SAVINGS.value

        valid_priorities = {p.value for p in GoalPriority}
        if priority not in valid_priorities:
            priority = GoalPriority.MEDIUM.value

        goal = FinancialGoal(
            workspace_id=workspace_id,
            name=name.strip(),
            description=description.strip() if description else None,
            goal_type=goal_type,
            currency=valid_curr,
            target_amount_paise=target_amount_paise,
            target_amount=Decimal(target_amount_paise) / Decimal(100),
            current_amount_paise=0,
            current_amount=Decimal("0.0000"),
            start_date=eff_start_date,
            target_date=target_date,
            status=GoalStatus.ACTIVE.value,
            priority=priority,
            color=color or "#6366f1",
            icon=icon or "target",
            created_by_id=created_by_id,
            metadata_payload=metadata_payload or {},
        )
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def get_goal(self, goal_id: uuid.UUID, workspace_id: uuid.UUID) -> FinancialGoal:
        """Retrieves single goal verified within workspace boundary."""
        goal = await self.repo.get_goal_scoped(goal_id, workspace_id)
        if not goal:
            raise NotFoundException(f"Financial goal {goal_id} not found in workspace {workspace_id}")
        return goal

    async def list_goals(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        goal_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FinancialGoal], int]:
        """Lists paginated goals in workspace."""
        return await self.repo.list_goals(
            workspace_id=workspace_id,
            status=status,
            goal_type=goal_type,
            limit=limit,
            offset=offset,
        )

    async def update_goal(
        self,
        goal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: Optional[str] = None,
        target_amount_paise: Optional[int] = None,
        target_date: Optional[date] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        description: Optional[str] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> FinancialGoal:
        """Updates goal attributes with validation."""
        goal = await self.get_goal(goal_id, workspace_id)

        if name is not None:
            goal.name = name.strip()
        if description is not None:
            goal.description = description.strip() if description else None

        if target_amount_paise is not None:
            if target_amount_paise <= 0:
                raise BusinessRuleViolationError(
                    rule_name="INVALID_TARGET_AMOUNT",
                    message="Target amount must be strictly positive.",
                )
            goal.target_amount_paise = target_amount_paise
            goal.target_amount = Decimal(target_amount_paise) / Decimal(100)

            # Check if this new target alters completion status
            if goal.current_amount_paise >= target_amount_paise and goal.status == GoalStatus.ACTIVE.value:
                goal.status = GoalStatus.COMPLETED.value
            elif goal.current_amount_paise < target_amount_paise and goal.status == GoalStatus.COMPLETED.value:
                goal.status = GoalStatus.ACTIVE.value

        if target_date is not None:
            if target_date < goal.start_date:
                raise BusinessRuleViolationError(
                    rule_name="INVALID_TARGET_DATE",
                    message=f"Target date cannot be earlier than goal start date ({goal.start_date}).",
                )
            goal.target_date = target_date

        if status is not None:
            valid_statuses = {s.value for s in GoalStatus}
            if status not in valid_statuses:
                raise BusinessRuleViolationError(
                    rule_name="INVALID_GOAL_STATUS",
                    message=f"Invalid goal status '{status}'.",
                )
            goal.status = status

        if priority is not None:
            valid_priorities = {p.value for p in GoalPriority}
            if priority in valid_priorities:
                goal.priority = priority

        if color is not None:
            goal.color = color
        if icon is not None:
            goal.icon = icon
        if metadata_payload is not None:
            goal.metadata_payload = metadata_payload

        await self.session.flush()
        return goal

    async def delete_goal(self, goal_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        """Soft deletes a goal."""
        goal = await self.get_goal(goal_id, workspace_id)
        goal.is_deleted = True
        goal.status = GoalStatus.ARCHIVED.value
        await self.session.flush()

    async def record_contribution(
        self,
        goal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        amount_paise: int,
        transaction_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        performed_by_id: Optional[uuid.UUID] = None,
    ) -> GoalActivity:
        """
        Records a funds contribution into the savings goal.
        Updates the accumulated balance and appends to the immutable ledger.
        """
        goal = await self.get_goal(goal_id, workspace_id)
        if goal.status == GoalStatus.ARCHIVED.value:
            raise BusinessRuleViolationError(
                rule_name="GOAL_ARCHIVED",
                message="Cannot contribute to an archived financial goal.",
            )

        activity = await self.repo.record_activity(
            goal=goal,
            activity_type=GoalActivityType.CONTRIBUTION,
            amount_paise=amount_paise,
            transaction_id=transaction_id,
            notes=notes,
            performed_by_id=performed_by_id,
        )
        await self.session.flush()
        return activity

    async def record_withdrawal(
        self,
        goal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        amount_paise: int,
        notes: Optional[str] = None,
        performed_by_id: Optional[uuid.UUID] = None,
    ) -> GoalActivity:
        """
        Records a withdrawal from the savings goal.
        Enforces that withdrawal amount does not exceed the current balance.
        """
        goal = await self.get_goal(goal_id, workspace_id)
        if goal.status == GoalStatus.ARCHIVED.value:
            raise BusinessRuleViolationError(
                rule_name="GOAL_ARCHIVED",
                message="Cannot withdraw from an archived financial goal.",
            )

        activity = await self.repo.record_activity(
            goal=goal,
            activity_type=GoalActivityType.WITHDRAWAL,
            amount_paise=amount_paise,
            notes=notes,
            performed_by_id=performed_by_id,
        )
        await self.session.flush()
        return activity

    async def get_goal_progress(
        self,
        goal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates goal pacing, completion percentage, remaining amount,
        and required monthly savings rate to hit the target date.
        """
        goal = await self.get_goal(goal_id, workspace_id)
        eval_date = as_of_date or date.today()

        progress = calculate_goal_progress(
            target_amount_paise=goal.target_amount_paise,
            current_amount_paise=goal.current_amount_paise,
            start_date=goal.start_date,
            target_date=goal.target_date,
            as_of_date=eval_date,
        )

        return {
            "goal_id": goal.id,
            "name": goal.name,
            "goal_type": goal.goal_type,
            "currency": goal.currency,
            "status": goal.status,
            "priority": goal.priority,
            "color": goal.color,
            "icon": goal.icon,
            "target_amount_paise": goal.target_amount_paise,
            "target_amount": goal.target_amount,
            "current_amount_paise": goal.current_amount_paise,
            "current_amount": goal.current_amount,
            "start_date": goal.start_date,
            "target_date": goal.target_date,
            "as_of_date": eval_date,
            "remaining_paise": progress.remaining_amount_paise,
            "remaining_amount": progress.remaining_amount,
            "completion_percentage": progress.progress_percentage,
            "is_completed": progress.is_completed,
            "days_remaining": progress.days_remaining,
            "required_monthly_savings_paise": progress.required_monthly_savings_paise,
            "required_monthly_savings_amount": progress.required_monthly_savings,
        }

    async def list_activities(
        self,
        goal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[GoalActivity], int]:
        """Lists paginated ledger activity entries for a goal."""
        # Ensure goal exists in workspace first
        await self.get_goal(goal_id, workspace_id)
        return await self.repo.list_activities(
            goal_id=goal_id,
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
        )
