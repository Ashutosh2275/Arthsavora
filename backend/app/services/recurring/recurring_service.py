"""
Arthsavora Recurring Financial Activities Application Service
Manages recurring definition CRUD, lifecycle state transitions, occurrence operations,
and reminder scheduling while maintaining absolute separation from actual transactions.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.domain.exceptions import BusinessRuleViolationError
from app.domain.recurring import (
    EndOfMonthPolicy,
    OccurrenceStatus,
    RecurringFrequency,
    RecurringStatus,
    calculate_next_occurrence,
    normalize_cost_to_monthly_and_annual,
)
from app.infrastructure.database.models.recurring import (
    RecurringDefinition,
    RecurringOccurrence,
    RecurringReminder,
)
from app.repositories.recurring_repository import RecurringRepository
from app.schemas.recurring_schema import (
    OccurrenceResponse,
    RecurringDefinitionCreateRequest,
    RecurringDefinitionResponse,
    RecurringDefinitionUpdateRequest,
)
from app.services.recurring.scheduling_service import SchedulingService


class RecurringService:
    """Application service for recurring definitions and occurrences."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringRepository(db)
        self.scheduling = SchedulingService(db)

    def _to_definition_response(self, defn: RecurringDefinition) -> RecurringDefinitionResponse:
        monthly_paise, annual_paise = normalize_cost_to_monthly_and_annual(
            amount_paise=defn.expected_amount_paise,
            frequency=defn.frequency,
            cycle_interval=defn.interval,
        )
        return RecurringDefinitionResponse(
            id=defn.id,
            workspace_id=defn.workspace_id,
            name=defn.name,
            description=defn.description,
            direction=defn.direction,
            transaction_type=defn.transaction_type,
            expected_amount_paise=defn.expected_amount_paise,
            expected_amount=defn.expected_amount,
            is_variable_amount=defn.is_variable_amount,
            currency=defn.currency,
            category_id=defn.category_id,
            category_name=defn.category.name if defn.category else None,
            merchant_id=defn.merchant_id,
            merchant_name=defn.merchant.name if defn.merchant else defn.merchant_name,
            account_id=defn.account_id,
            account_name=defn.account.name if defn.account else None,
            frequency=defn.frequency,
            interval=defn.interval,
            day_of_month=defn.day_of_month,
            day_of_week=defn.day_of_week,
            end_of_month_policy=defn.end_of_month_policy,
            start_date=defn.start_date,
            end_date=defn.end_date,
            next_expected_date=defn.next_expected_date,
            timezone=defn.timezone,
            status=defn.status,
            normalized_monthly_paise=monthly_paise,
            normalized_annual_paise=annual_paise,
            created_at=defn.created_at,
            updated_at=defn.updated_at,
        )

    def _to_occurrence_response(self, occ: RecurringOccurrence) -> OccurrenceResponse:
        return OccurrenceResponse(
            id=occ.id,
            workspace_id=occ.workspace_id,
            recurring_definition_id=occ.recurring_definition_id,
            recurring_name=occ.recurring_definition.name if occ.recurring_definition else None,
            direction=occ.recurring_definition.direction if occ.recurring_definition else None,
            expected_date=occ.expected_date,
            expected_amount_paise=occ.expected_amount_paise,
            expected_amount=occ.expected_amount,
            currency=occ.currency,
            status=occ.status,
            matched_transaction_id=occ.matched_transaction_id,
            matched_amount_paise=occ.matched_amount_paise,
            matched_amount=Decimal(occ.matched_amount_paise) / Decimal("100.0000") if occ.matched_amount_paise is not None else None,
            amount_variance_paise=occ.amount_variance_paise,
            match_confidence=occ.match_confidence,
            notes=occ.notes,
            generated_at=occ.generated_at,
            confirmed_at=occ.confirmed_at,
            updated_at=occ.updated_at,
        )

    async def create_definition(
        self,
        workspace_id: uuid.UUID,
        payload: RecurringDefinitionCreateRequest,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> RecurringDefinitionResponse:
        """Creates a recurring definition, immediately generates upcoming occurrences, and sets initial reminders."""
        expected_amount_dec = Decimal(payload.expected_amount_paise) / Decimal("100.0000")

        # Initial next_expected_date starts at start_date
        next_date = payload.start_date

        definition = RecurringDefinition(
            workspace_id=workspace_id,
            name=payload.name,
            description=payload.description,
            direction=payload.direction.value,
            transaction_type=payload.transaction_type,
            expected_amount_paise=payload.expected_amount_paise,
            expected_amount=expected_amount_dec,
            is_variable_amount=payload.is_variable_amount,
            currency=payload.currency.upper(),
            category_id=payload.category_id,
            merchant_id=payload.merchant_id,
            merchant_name=payload.merchant_name,
            account_id=payload.account_id,
            frequency=payload.frequency.value,
            interval=payload.interval,
            day_of_month=payload.day_of_month,
            day_of_week=payload.day_of_week,
            end_of_month_policy=payload.end_of_month_policy.value,
            start_date=payload.start_date,
            end_date=payload.end_date,
            next_expected_date=next_date,
            timezone=payload.timezone,
            status=RecurringStatus.ACTIVE.value,
            created_by_id=created_by_id,
        )

        saved = await self.repo.create_definition(definition)

        # Generate occurrences for the next 90 days
        await self.scheduling.generate_occurrences_for_definition(saved, horizon_days=90)

        # Re-fetch with loaded relationships
        loaded = await self.repo.get_definition(saved.id, workspace_id)
        return self._to_definition_response(loaded or saved)

    async def get_definition(
        self,
        definition_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> RecurringDefinitionResponse:
        """Fetch definition by ID."""
        defn = await self.repo.get_definition(definition_id, workspace_id)
        if not defn:
            raise NotFoundException(detail=f"Recurring definition {definition_id} not found in workspace")
        return self._to_definition_response(defn)

    async def list_definitions(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        direction: Optional[str] = None,
        frequency: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[RecurringDefinitionResponse]:
        """List recurring definitions."""
        items = await self.repo.list_definitions(
            workspace_id=workspace_id,
            status=status,
            direction=direction,
            frequency=frequency,
            skip=skip,
            limit=limit,
        )
        return [self._to_definition_response(d) for d in items]

    async def update_definition(
        self,
        definition_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: RecurringDefinitionUpdateRequest,
    ) -> RecurringDefinitionResponse:
        """Update recurring definition parameters."""
        defn = await self.repo.get_definition(definition_id, workspace_id)
        if not defn:
            raise NotFoundException(detail=f"Recurring definition {definition_id} not found")

        schedule_changed = False

        if payload.name is not None:
            defn.name = payload.name
        if payload.description is not None:
            defn.description = payload.description
        if payload.expected_amount_paise is not None:
            defn.expected_amount_paise = payload.expected_amount_paise
            defn.expected_amount = Decimal(payload.expected_amount_paise) / Decimal("100.0000")
        if payload.is_variable_amount is not None:
            defn.is_variable_amount = payload.is_variable_amount
        if payload.category_id is not None:
            defn.category_id = payload.category_id
        if payload.merchant_id is not None:
            defn.merchant_id = payload.merchant_id
        if payload.merchant_name is not None:
            defn.merchant_name = payload.merchant_name
        if payload.account_id is not None:
            defn.account_id = payload.account_id
        if payload.frequency is not None and payload.frequency.value != defn.frequency:
            defn.frequency = payload.frequency.value
            schedule_changed = True
        if payload.interval is not None and payload.interval != defn.interval:
            defn.interval = payload.interval
            schedule_changed = True
        if payload.day_of_month is not None and payload.day_of_month != defn.day_of_month:
            defn.day_of_month = payload.day_of_month
            schedule_changed = True
        if payload.day_of_week is not None and payload.day_of_week != defn.day_of_week:
            defn.day_of_week = payload.day_of_week
            schedule_changed = True
        if payload.end_of_month_policy is not None and payload.end_of_month_policy.value != defn.end_of_month_policy:
            defn.end_of_month_policy = payload.end_of_month_policy.value
            schedule_changed = True
        if payload.end_date is not None:
            defn.end_date = payload.end_date
        if payload.next_expected_date is not None:
            defn.next_expected_date = payload.next_expected_date
        if payload.status is not None:
            defn.status = payload.status.value

        updated = await self.repo.update_definition(defn)

        if schedule_changed and defn.status == "active":
            # Regenerate future occurrences
            await self.scheduling.generate_occurrences_for_definition(defn, horizon_days=90)

        loaded = await self.repo.get_definition(updated.id, workspace_id)
        return self._to_definition_response(loaded or updated)

    async def pause_definition(
        self,
        definition_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> RecurringDefinitionResponse:
        """Pause an active recurring schedule."""
        defn = await self.repo.get_definition(definition_id, workspace_id)
        if not defn:
            raise NotFoundException(detail=f"Recurring definition {definition_id} not found")
        defn.status = RecurringStatus.PAUSED.value
        updated = await self.repo.update_definition(defn)
        return self._to_definition_response(updated)

    async def resume_definition(
        self,
        definition_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> RecurringDefinitionResponse:
        """Resume a paused recurring schedule."""
        defn = await self.repo.get_definition(definition_id, workspace_id)
        if not defn:
            raise NotFoundException(detail=f"Recurring definition {definition_id} not found")
        defn.status = RecurringStatus.ACTIVE.value
        # Recalculate next expected date if it has elapsed
        today = date.today()
        if defn.next_expected_date < today:
            defn.next_expected_date = calculate_next_occurrence(
                base_date=today,
                frequency=defn.frequency,
                interval=defn.interval,
                day_of_month=defn.day_of_month,
                day_of_week=defn.day_of_week,
                end_of_month_policy=defn.end_of_month_policy,
            )
        updated = await self.repo.update_definition(defn)
        await self.scheduling.generate_occurrences_for_definition(defn, horizon_days=90)
        return self._to_definition_response(updated)

    async def cancel_definition(
        self,
        definition_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> RecurringDefinitionResponse:
        """Cancel a recurring schedule."""
        defn = await self.repo.get_definition(definition_id, workspace_id)
        if not defn:
            raise NotFoundException(detail=f"Recurring definition {definition_id} not found")
        defn.status = RecurringStatus.CANCELLED.value
        updated = await self.repo.update_definition(defn)
        return self._to_definition_response(updated)

    # -------------------------------------------------------------------------
    # Occurrence Operations
    # -------------------------------------------------------------------------

    async def list_occurrences(
        self,
        workspace_id: uuid.UUID,
        definition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OccurrenceResponse]:
        """List occurrences."""
        items = await self.repo.list_occurrences(
            workspace_id=workspace_id,
            definition_id=definition_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
        )
        return [self._to_occurrence_response(o) for o in items]

    async def skip_occurrence(
        self,
        occurrence_id: uuid.UUID,
        workspace_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> OccurrenceResponse:
        """Mark an occurrence as skipped by the user."""
        occ = await self.repo.get_occurrence(occurrence_id, workspace_id)
        if not occ:
            raise NotFoundException(detail=f"Occurrence {occurrence_id} not found")

        if occ.status in (OccurrenceStatus.CONFIRMED.value, OccurrenceStatus.MATCHED.value):
            raise BusinessRuleViolationError(
                detail="Cannot skip an occurrence that is already matched or confirmed with a financial transaction",
                rule_name="CANNOT_SKIP_MATCHED_OCCURRENCE",
            )

        occ.status = OccurrenceStatus.SKIPPED.value
        if reason:
            occ.notes = f"Skipped: {reason}"
        updated = await self.repo.update_occurrence(occ)
        return self._to_occurrence_response(updated)

    async def confirm_occurrence(
        self,
        occurrence_id: uuid.UUID,
        workspace_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> OccurrenceResponse:
        """
        Manually confirms that an occurrence has taken place.
        Note: This acknowledges the occurrence without fabricating a double-entry transaction.
        """
        occ = await self.repo.get_occurrence(occurrence_id, workspace_id)
        if not occ:
            raise NotFoundException(detail=f"Occurrence {occurrence_id} not found")

        occ.status = OccurrenceStatus.CONFIRMED.value
        occ.confirmed_at = datetime.utcnow()
        if notes:
            occ.notes = notes

        updated = await self.repo.update_occurrence(occ)
        return self._to_occurrence_response(updated)
