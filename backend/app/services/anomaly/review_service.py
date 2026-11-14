"""
Arthsavora Anomaly Review & Governance Service
Manages user review actions, immutable audit ledgers,
configurable detection rule thresholds, and whitelist exceptions.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.domain.anomaly import AnomalyStatus, ReviewAction
from app.infrastructure.database.models.anomaly import (
    AnomalyDetection,
    AnomalyReview,
    DetectionException,
    DetectionRule,
)
from app.repositories.anomaly_repository import AnomalyRepository
from app.schemas.anomaly_schema import (
    AnomalyDetectionResponse,
    AnomalyReviewRequest,
    DetectionExceptionCreateRequest,
    DetectionRuleUpdateRequest,
)
from app.services.anomaly.detection_service import AnomalyDetectionService


class AnomalyReviewService:
    """Handles workflow transitions, confirmations, and detection exceptions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnomalyRepository(db)

    async def review_anomaly(
        self,
        anomaly_id: uuid.UUID,
        workspace_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        request: AnomalyReviewRequest,
    ) -> AnomalyDetectionResponse:
        """Applies a human review decision to an anomaly and creates an audit record."""
        anomaly = await self.repo.get_detection(anomaly_id, workspace_id)
        if not anomaly:
            raise NotFoundException(f"Anomaly {anomaly_id} not found in workspace.")

        action = request.action.lower().strip()
        new_status = anomaly.status

        if action == ReviewAction.ACKNOWLEDGE.value:
            new_status = AnomalyStatus.ACKNOWLEDGED.value
        elif action == ReviewAction.MARK_EXPECTED.value:
            new_status = AnomalyStatus.EXPECTED_ACTIVITY.value
        elif action == ReviewAction.MARK_SUSPICIOUS.value or action == ReviewAction.ESCALATE.value:
            new_status = AnomalyStatus.ESCALATED.value
        elif action == ReviewAction.DISMISS.value:
            new_status = AnomalyStatus.DISMISSED.value
        elif action == ReviewAction.REOPEN.value:
            new_status = AnomalyStatus.NEW.value

        # 1. Update Detection Record
        updated = await self.repo.update_status(
            detection_id=anomaly_id,
            workspace_id=workspace_id,
            status=new_status,
            resolved_by_id=reviewer_id,
            notes=request.notes,
        )

        # 2. Immutable Review Log
        review = AnomalyReview(
            anomaly_id=anomaly_id,
            workspace_id=workspace_id,
            reviewer_id=reviewer_id,
            action=action,
            reason=request.reason,
            notes=request.notes,
        )
        await self.repo.create_review(review)

        # 3. Optional Whitelist Exception Creation
        if request.create_exception and anomaly.transaction:
            t = anomaly.transaction
            exp_date = (
                date.today() + timedelta(days=request.exception_expires_in_days)
                if request.exception_expires_in_days
                else None
            )

            exc = DetectionException(
                workspace_id=workspace_id,
                rule_code=anomaly.rule_code,
                merchant_id=getattr(t, "merchant_id", None),
                category_id=t.category_id,
                account_id=t.account_id,
                merchant_name_pattern=getattr(t, "merchant_name", None),
                max_amount_paise=t.amount_paise * 2,  # Set ceiling at 2x current amount
                reason=request.reason or f"User whitelisted after reviewing anomaly #{anomaly_id}",
                expires_at=exp_date,
                created_by_id=reviewer_id,
            )
            await self.repo.create_exception(exc)

        await self.db.commit()

        # Reload with updated reviews
        reloaded = await self.repo.get_detection(anomaly_id, workspace_id)
        return AnomalyDetectionService.map_to_dto(reloaded or updated)

    async def update_rule(
        self,
        rule_id: uuid.UUID,
        workspace_id: uuid.UUID,
        request: DetectionRuleUpdateRequest,
    ) -> DetectionRule:
        """Customizes or toggles a detection rule for the workspace."""
        rule = await self.repo.get_rule_by_id(rule_id, workspace_id)
        if not rule:
            raise NotFoundException(f"Detection rule {rule_id} not found.")

        # If modifying a system global rule (workspace_id IS NULL), fork a workspace-specific override
        if rule.workspace_id is None:
            new_rule = DetectionRule(
                workspace_id=workspace_id,
                rule_code=rule.rule_code,
                name=rule.name,
                description=rule.description,
                detection_category=rule.detection_category,
                severity=request.severity or rule.severity,
                threshold_config=request.threshold_config or rule.threshold_config,
                is_enabled=request.is_enabled if request.is_enabled is not None else rule.is_enabled,
                version=rule.version,
            )
            created = await self.repo.create_or_update_rule(new_rule)
            await self.db.commit()
            return created

        # Direct update on existing workspace override
        if request.is_enabled is not None:
            rule.is_enabled = request.is_enabled
        if request.severity:
            rule.severity = request.severity
        if request.threshold_config:
            rule.threshold_config = request.threshold_config

        await self.db.commit()
        return rule

    async def create_exception(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        request: DetectionExceptionCreateRequest,
    ) -> DetectionException:
        """Manually creates a detection whitelist exception."""
        exc = DetectionException(
            workspace_id=workspace_id,
            rule_code=request.rule_code,
            merchant_id=request.merchant_id,
            category_id=request.category_id,
            account_id=request.account_id,
            merchant_name_pattern=request.merchant_name_pattern,
            max_amount_paise=request.max_amount_paise,
            reason=request.reason,
            expires_at=request.expires_at,
            created_by_id=user_id,
        )
        created = await self.repo.create_exception(exc)
        await self.db.commit()
        return created
