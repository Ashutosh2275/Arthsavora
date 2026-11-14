"""
Arthsavora User Classification Feedback Service
Captures user corrections, confirms categorization suggestions,
manages rule creation from corrections, and preserves audit trails.
"""

from typing import Any, Dict, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.domain.category_taxonomy import FeedbackAction
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.category_repository import CategoryRepository
from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.rule_repository import RuleRepository
from app.services.intelligence.normalizer import DescriptionNormalizer


class FeedbackService:
    """Manages user confirmation, category overrides, and rule synthesis from corrections."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.category_repo = CategoryRepository(session)
        self.rule_repo = RuleRepository(session)
        self.intel_repo = IntelligenceRepository(session)

    async def record_feedback(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        action: str,
        corrected_category_id: Optional[uuid.UUID] = None,
        corrected_merchant_name: Optional[str] = None,
        feedback_reason: Optional[str] = None,
        create_rule: bool = False,
        rule_keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience method for recording user feedback."""
        return await self.submit_feedback(
            workspace_id=workspace_id,
            transaction_id=transaction_id,
            user_id=user_id,
            action=action,
            confirmed_category_id=corrected_category_id,
            confirmed_merchant_name=corrected_merchant_name,
            feedback_reason=feedback_reason,
            create_rule=create_rule,
            rule_name=rule_keyword,
        )

    async def submit_feedback(
        self,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
        user_id: uuid.UUID,
        action: str,  # accept, correct_category, correct_merchant, mark_unknown, create_rule
        confirmed_category_id: Optional[uuid.UUID] = None,
        confirmed_merchant_name: Optional[str] = None,
        feedback_reason: Optional[str] = None,
        create_rule: bool = False,
        rule_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes user feedback and applies confirmed changes to Transaction.
        Does NOT alter double-entry accounting ledgers or posted journal balances.
        """
        # 1. Fetch transaction
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.workspace_id == workspace_id,
        )
        res = await self.session.execute(stmt)
        tx = res.scalar_one_or_none()
        if not tx:
            raise NotFoundException(f"Transaction '{transaction_id}' not found in workspace.")

        # 2. Fetch existing classification
        cl = await self.intel_repo.get_classification_by_transaction_id(workspace_id, transaction_id)
        original_cat_id = cl.suggested_category_id if cl else tx.category_id
        original_merchant = cl.suggested_merchant_name if cl else tx.merchant_name
        original_method = cl.method if cl else "manual"
        model_ver = cl.model_version if cl else None

        # 3. Resolve confirmed category
        final_category_id = confirmed_category_id
        if not final_category_id and cl:
            final_category_id = cl.suggested_category_id

        if action in (FeedbackAction.ACCEPT.value, FeedbackAction.CORRECT_CATEGORY.value, FeedbackAction.CREATE_RULE.value):
            if not final_category_id:
                raise ValidationException("Confirmed category ID is required.")
            cat = await self.category_repo.get_by_id(final_category_id)
            if not cat:
                raise NotFoundException(f"Category '{final_category_id}' not found.")

        # 4. Handle Action Transitions
        created_rule = None
        if action == FeedbackAction.ACCEPT.value:
            tx.category_id = final_category_id
            tx.is_ai_predicted = False
            if cl:
                cl.status = "accepted"

        elif action == FeedbackAction.CORRECT_CATEGORY.value:
            tx.category_id = final_category_id
            tx.is_ai_predicted = False
            if cl:
                cl.status = "corrected"

        elif action == FeedbackAction.CORRECT_MERCHANT.value:
            if confirmed_merchant_name:
                tx.merchant_name = confirmed_merchant_name.strip()
            if final_category_id:
                tx.category_id = final_category_id
                tx.is_ai_predicted = False
            if cl:
                cl.status = "corrected"

        elif action == FeedbackAction.MARK_UNKNOWN.value:
            tx.category_id = None
            tx.is_ai_predicted = False
            if cl:
                cl.status = "rejected"

        # 5. Optionally create a reusable rule
        if create_rule or action == FeedbackAction.CREATE_RULE.value:
            if not final_category_id:
                raise ValidationException("Category is required to create a rule.")

            norm_res = DescriptionNormalizer.normalize(tx.description)
            keyword = norm_res.merchant_candidate or norm_res.normalized_description.split()[0]
            r_name = rule_name or f"Always categorize '{keyword}' as {cat.name}"

            created_rule = await self.rule_repo.create_rule(
                workspace_id=workspace_id,
                name=r_name,
                conditions={
                    "description_contains": [keyword],
                    "direction": tx.direction,
                },
                suggested_category_id=final_category_id,
                priority=200,  # User rules get higher priority than default 100
                is_enabled=True,
                rule_scope="workspace",
                created_by_id=user_id,
            )
            tx.category_id = final_category_id
            tx.is_ai_predicted = False
            if cl:
                cl.status = "accepted"

        # 6. Record user feedback
        feedback = await self.intel_repo.create_feedback(
            workspace_id=workspace_id,
            transaction_id=tx.id,
            user_id=user_id,
            classification_id=cl.id if cl else None,
            original_category_id=original_cat_id,
            original_merchant_name=original_merchant,
            confirmed_category_id=final_category_id or original_cat_id,
            confirmed_merchant_name=confirmed_merchant_name or tx.merchant_name,
            original_method=original_method,
            model_version=model_ver,
            feedback_action=action,
            feedback_reason=feedback_reason,
            created_rule_id=created_rule.id if created_rule else None,
        )

        return {
            "feedback_id": str(feedback.id),
            "workspace_id": str(workspace_id),
            "transaction_id": str(transaction_id),
            "action": action,
            "confirmed_category_id": str(final_category_id) if final_category_id else None,
            "confirmed_merchant_name": tx.merchant_name,
            "created_rule_id": str(created_rule.id) if created_rule else None,
            "status": "applied",
        }
