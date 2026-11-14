"""
Arthsavora Assistant Action Confirmation Service
Safely confirms, executes, or cancels staged financial action drafts
with permission re-verification, idempotency guarantees, and audit preservation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets
from typing import Any, Dict, Optional, Set
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleViolationException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from app.core.permissions import Permission
from app.domain.assistant import ActionDraftStatus
from app.infrastructure.database.models.assistant import AssistantActionDraft
from app.infrastructure.database.models.budget import Budget, BudgetAllocation
from app.infrastructure.database.models.goal import FinancialGoal
from app.infrastructure.database.models.recurring import RecurringDefinition
from app.repositories.assistant_repository import AssistantRepository


class AssistantActionService:
    """Manages creation, verification, and execution of human-confirmed assistant actions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssistantRepository(db)

    async def create_draft(
        self,
        conversation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        action_type: str,
        parameters: Dict[str, Any],
        summary: Optional[str] = None,
        ttl_hours: int = 24,
    ) -> AssistantActionDraft:
        """Stages an action draft requiring explicit human confirmation."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        if not summary:
            summary = self._generate_summary(action_type, parameters)

        draft = AssistantActionDraft(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=action_type,
            action_summary=summary,
            parameters=parameters,
            status=ActionDraftStatus.PENDING.value,
            confirmation_token=token,
            expires_at=expires_at,
        )
        created = await self.repo.create_action_draft(draft)
        await self.db.commit()
        return created

    async def confirm_action(
        self,
        draft_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        confirmation_token: str,
        user_permissions: Set[str],
    ) -> Dict[str, Any]:
        """
        Validates token and permissions, executes backend mutation, and marks draft confirmed.
        Enforces strict idempotency: multiple confirmation calls do not execute multiple mutations.
        """
        draft = await self.repo.get_action_draft_by_id(draft_id, workspace_id)
        if not draft:
            raise NotFoundException(f"Action draft {draft_id} not found in this workspace.")

        if draft.confirmation_token != confirmation_token:
            raise ValidationException("Invalid confirmation token provided for this action.")

        # Idempotency check: Already confirmed
        if draft.status == ActionDraftStatus.CONFIRMED.value:
            return {
                "action_id": draft.id,
                "status": "already_confirmed",
                "action_type": draft.action_type,
                "message": "Action was already confirmed previously.",
                "execution_result": draft.execution_result,
            }

        if draft.status != ActionDraftStatus.PENDING.value:
            raise BusinessRuleViolationException(f"Cannot confirm action with status '{draft.status}'.")

        # Check expiration
        now = datetime.now(timezone.utc)
        if draft.expires_at < now:
            draft.status = ActionDraftStatus.EXPIRED.value
            await self.db.commit()
            raise BusinessRuleViolationException("Action confirmation window has expired. Please request a new action.")

        # Re-verify permissions before executing mutation
        required_perm = self._get_required_permission(draft.action_type)
        if required_perm not in user_permissions:
            raise PermissionDeniedException(f"Missing required permission '{required_perm}' to execute action.")

        # Execute backend mutation
        exec_res = await self._execute_mutation(draft.action_type, draft.parameters, workspace_id, user_id)

        # Update draft status
        draft.status = ActionDraftStatus.CONFIRMED.value
        draft.confirmed_at = now
        draft.execution_result = exec_res
        await self.db.commit()

        return {
            "action_id": draft.id,
            "status": "confirmed",
            "action_type": draft.action_type,
            "message": f"Successfully executed '{draft.action_summary}'.",
            "execution_result": exec_res,
        }

    async def cancel_action(
        self,
        draft_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Cancels a pending action draft without executing mutations."""
        draft = await self.repo.get_action_draft_by_id(draft_id, workspace_id)
        if not draft:
            raise NotFoundException(f"Action draft {draft_id} not found in this workspace.")

        if draft.status != ActionDraftStatus.PENDING.value:
            raise BusinessRuleViolationException(f"Cannot cancel action with status '{draft.status}'.")

        draft.status = ActionDraftStatus.CANCELLED.value
        draft.cancelled_at = datetime.now(timezone.utc)
        await self.db.commit()

        return {
            "action_id": draft.id,
            "status": "cancelled",
            "action_type": draft.action_type,
            "message": "Action was cancelled successfully.",
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _get_required_permission(self, action_type: str) -> str:
        if action_type in ("create_budget", "create_budget_draft"):
            return Permission.MANAGE_BUDGETS.value
        elif action_type in ("create_goal", "create_goal_draft"):
            return Permission.MANAGE_GOALS.value
        elif action_type in ("create_recurring", "create_recurring_draft"):
            return Permission.MANAGE_RECURRING.value
        elif action_type in ("prepare_transaction_filter", "prepare_filter"):
            return Permission.VIEW_TRANSACTIONS.value
        return Permission.USE_ASSISTANT.value

    def _generate_summary(self, action_type: str, params: Dict[str, Any]) -> str:
        if action_type in ("create_budget", "create_budget_draft"):
            amt = params.get("limit_paise") or params.get("amount_paise", 0)
            inr = amt / 100.0
            return f"Create {params.get('period', 'monthly')} budget '{params.get('name', 'Budget')}' of ₹{inr:,.2f}"
        elif action_type in ("create_goal", "create_goal_draft"):
            amt = params.get("target_amount_paise") or params.get("amount_paise", 0)
            inr = amt / 100.0
            return f"Create savings goal '{params.get('name', 'Goal')}' of ₹{inr:,.2f}"
        elif action_type in ("create_recurring", "create_recurring_draft"):
            amt = params.get("expected_amount_paise") or params.get("amount_paise", 0)
            inr = amt / 100.0
            return f"Schedule recurring payment '{params.get('name', 'Subscription')}' of ₹{inr:,.2f}"
        return f"Execute action '{action_type}'"

    async def _execute_mutation(
        self,
        action_type: str,
        params: Dict[str, Any],
        ws_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Executes authorized backend database mutation."""
        now = datetime.now(timezone.utc)

        if action_type in ("create_budget", "create_budget_draft"):
            from datetime import date
            today = date.today()
            amt_p = params.get("limit_paise") or params.get("amount_paise") or 1000000
            budget = Budget(
                workspace_id=ws_id,
                name=params.get("name", "New Budget"),
                budget_type=params.get("period", "monthly"),
                start_date=today.replace(day=1),
                end_date=(today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                currency=params.get("currency", "INR"),
                total_allocated_paise=amt_p,
                total_allocated=Decimal(amt_p) / Decimal("100.0000"),
                created_by_id=user_id,
            )
            self.db.add(budget)
            await self.db.flush()

            category_id = params.get("category_id")
            if category_id:
                alloc = BudgetAllocation(
                    budget_id=budget.id,
                    workspace_id=ws_id,
                    category_id=category_id,
                    allocated_amount_paise=amt_p,
                    allocated_amount=Decimal(amt_p) / Decimal("100.0000"),
                )
                self.db.add(alloc)
                await self.db.flush()
            return {"budget_id": str(budget.id), "name": budget.name, "limit_paise": amt_p}

        elif action_type in ("create_goal", "create_goal_draft"):
            from datetime import date
            target_d = None
            if params.get("target_date"):
                try:
                    target_d = date.fromisoformat(params["target_date"])
                except Exception:
                    pass

            amt_p = params.get("target_amount_paise") or params.get("amount_paise") or 5000000
            goal = FinancialGoal(
                workspace_id=ws_id,
                name=params.get("name", "New Goal"),
                target_amount_paise=amt_p,
                target_amount=Decimal(amt_p) / Decimal("100.0000"),
                currency=params.get("currency", "INR"),
                target_date=target_d,
                status="active",
                created_by_id=user_id,
            )
            self.db.add(goal)
            await self.db.flush()
            return {"goal_id": str(goal.id), "name": goal.name, "target_amount_paise": goal.target_amount_paise}

        elif action_type in ("create_recurring", "create_recurring_draft"):
            from datetime import date
            amt_p = params.get("expected_amount_paise") or params.get("amount_paise") or 99900
            rec = RecurringDefinition(
                workspace_id=ws_id,
                name=params.get("name", "Scheduled Commitment"),
                recurrence_type="expense",
                frequency=params.get("frequency", "monthly"),
                interval_count=1,
                expected_amount_paise=amt_p,
                currency=params.get("currency", "INR"),
                status="active",
                start_date=date.today(),
            )
            self.db.add(rec)
            await self.db.flush()
            return {"recurring_id": str(rec.id), "name": rec.name, "expected_amount_paise": rec.expected_amount_paise}

        elif action_type == "prepare_transaction_filter":
            return {"filter_applied": True, "criteria": params.get("criteria", {})}

        return {"executed": True}
