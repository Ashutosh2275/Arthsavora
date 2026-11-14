"""
Arthsavora Intelligence & Classification Repository
Persists categorization suggestions, explainability records, and user feedback corrections.
"""

from decimal import Decimal
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.intelligence import (
    TransactionClassification,
    UserClassificationFeedback,
)


class IntelligenceRepository:
    """Manages classification records, prediction caching, and user feedback logs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_classification_by_transaction_id(
        self,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> Optional[TransactionClassification]:
        stmt = (
            select(TransactionClassification)
            .where(
                TransactionClassification.workspace_id == workspace_id,
                TransactionClassification.transaction_id == transaction_id,
            )
            .options(
                selectinload(TransactionClassification.suggested_category),
                selectinload(TransactionClassification.suggested_merchant),
                selectinload(TransactionClassification.rule),
            )
            .order_by(TransactionClassification.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def create_classification(
        self,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
        suggested_category_id: uuid.UUID,
        confidence_score: Decimal,
        confidence_band: str,
        method: str,
        explanation: str,
        suggested_merchant_id: Optional[uuid.UUID] = None,
        suggested_merchant_name: Optional[str] = None,
        rule_id: Optional[uuid.UUID] = None,
        model_version: str = "v1.0.0",
        status: str = "suggested",
    ) -> TransactionClassification:
        classification = TransactionClassification(
            workspace_id=workspace_id,
            transaction_id=transaction_id,
            suggested_category_id=suggested_category_id,
            suggested_merchant_id=suggested_merchant_id,
            suggested_merchant_name=suggested_merchant_name,
            confidence_score=confidence_score,
            confidence_band=confidence_band,
            method=method,
            rule_id=rule_id,
            model_version=model_version,
            explanation=explanation,
            status=status,
        )
        self.session.add(classification)
        await self.session.flush()
        return classification

    async def update_classification_status(
        self,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
        status: str,
    ) -> Optional[TransactionClassification]:
        classification = await self.get_classification_by_transaction_id(workspace_id, transaction_id)
        if classification:
            classification.status = status
            await self.session.flush()
        return classification

    async def create_feedback(
        self,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
        user_id: uuid.UUID,
        confirmed_category_id: uuid.UUID,
        original_method: str,
        feedback_action: str,
        classification_id: Optional[uuid.UUID] = None,
        original_category_id: Optional[uuid.UUID] = None,
        original_merchant_name: Optional[str] = None,
        confirmed_merchant_name: Optional[str] = None,
        model_version: Optional[str] = None,
        feedback_reason: Optional[str] = None,
        created_rule_id: Optional[uuid.UUID] = None,
    ) -> UserClassificationFeedback:
        feedback = UserClassificationFeedback(
            workspace_id=workspace_id,
            transaction_id=transaction_id,
            user_id=user_id,
            classification_id=classification_id,
            original_category_id=original_category_id,
            original_merchant_name=original_merchant_name,
            confirmed_category_id=confirmed_category_id,
            confirmed_merchant_name=confirmed_merchant_name,
            original_method=original_method,
            model_version=model_version,
            feedback_action=feedback_action,
            feedback_reason=feedback_reason,
            created_rule_id=created_rule_id,
        )
        self.session.add(feedback)
        await self.session.flush()
        return feedback

    async def list_feedback(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> List[UserClassificationFeedback]:
        stmt = (
            select(UserClassificationFeedback)
            .where(UserClassificationFeedback.workspace_id == workspace_id)
            .options(
                selectinload(UserClassificationFeedback.confirmed_category),
                selectinload(UserClassificationFeedback.created_rule),
            )
            .order_by(UserClassificationFeedback.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
