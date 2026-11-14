"""
Arthsavora Recurrence Scheduling & Occurrence Generation Service
Manages deterministic date calculations, leap-year handling, end-of-month pinning,
and idempotent batch generation of future expected occurrences.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recurring import (
    EndOfMonthPolicy,
    OccurrenceStatus,
    RecurringFrequency,
    calculate_next_occurrence,
    generate_occurrence_dates_in_window,
)
from app.infrastructure.database.models.recurring import RecurringDefinition, RecurringOccurrence
from app.repositories.recurring_repository import RecurringRepository


class SchedulingService:
    """Orchestrates occurrence date calculations and idempotent persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringRepository(db)

    async def generate_occurrences_for_definition(
        self,
        definition: RecurringDefinition,
        horizon_days: int = 90,
        as_of_date: Optional[date] = None,
    ) -> List[RecurringOccurrence]:
        """
        Generates upcoming occurrences for a single recurring definition up to horizon_days into the future.
        Guarantees idempotency via unique schedule check.
        """
        if definition.status != "active":
            return []

        base_today = as_of_date or date.today()
        window_end = base_today + timedelta(days=horizon_days)

        start_from = definition.next_expected_date
        if start_from < definition.start_date:
            start_from = definition.start_date

        dates = generate_occurrence_dates_in_window(
            start_from=start_from,
            window_end=window_end,
            frequency=definition.frequency,
            interval=definition.interval,
            day_of_month=definition.day_of_month,
            day_of_week=definition.day_of_week,
            end_of_month_policy=definition.end_of_month_policy,
            end_date=definition.end_date,
        )

        created_occurrences: List[RecurringOccurrence] = []

        for occ_date in dates:
            # Idempotently check and create
            existing = await self.repo.get_occurrence_by_schedule(
                definition_id=definition.id,
                expected_date=occ_date,
            )
            if existing:
                continue

            status = OccurrenceStatus.SCHEDULED.value
            if occ_date < base_today:
                status = OccurrenceStatus.OVERDUE.value
            elif occ_date == base_today:
                status = OccurrenceStatus.DUE.value
            elif occ_date <= base_today + timedelta(days=3):
                status = OccurrenceStatus.UPCOMING.value

            occ = RecurringOccurrence(
                workspace_id=definition.workspace_id,
                recurring_definition_id=definition.id,
                expected_date=occ_date,
                expected_amount_paise=definition.expected_amount_paise,
                expected_amount=definition.expected_amount,
                currency=definition.currency,
                status=status,
            )
            saved = await self.repo.create_occurrence_idempotent(occ)
            if saved:
                created_occurrences.append(saved)

        # Update next_expected_date on definition if needed
        next_date = calculate_next_occurrence(
            base_date=dates[-1] if dates else definition.next_expected_date,
            frequency=definition.frequency,
            interval=definition.interval,
            day_of_month=definition.day_of_month,
            day_of_week=definition.day_of_week,
            end_of_month_policy=definition.end_of_month_policy,
        )
        definition.next_expected_date = next_date
        await self.repo.update_definition(definition)

        return created_occurrences

    async def generate_workspace_occurrences(
        self,
        workspace_id: uuid.UUID,
        horizon_days: int = 90,
    ) -> int:
        """Generates future occurrences for all active definitions in a workspace."""
        active_defs = await self.repo.list_definitions(workspace_id=workspace_id, status="active", limit=500)
        total_created = 0
        for defn in active_defs:
            created = await self.generate_occurrences_for_definition(defn, horizon_days=horizon_days)
            total_created += len(created)
        return total_created
