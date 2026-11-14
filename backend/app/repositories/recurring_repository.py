"""
Arthsavora Recurring Transactions, Subscriptions & Commitments Repository
Provides safe, tenant-isolated PostgreSQL database operations with idempotency guarantees,
occurrence batching, reconciliation matching, and historical audit preservation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.recurring import (
    RecurringDefinition,
    RecurringOccurrence,
    Subscription,
    RecurringReminder,
    RecurringSuggestion,
)
from app.infrastructure.database.models.transaction import Transaction


class RecurringRepository:
    """PostgreSQL repository for recurring definitions, occurrences, subscriptions, and reminders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Recurring Definitions
    # -------------------------------------------------------------------------

    async def get_definition(
        self,
        definition_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[RecurringDefinition]:
        """Fetch recurring definition by ID with workspace boundary check."""
        stmt = (
            select(RecurringDefinition)
            .where(
                RecurringDefinition.id == definition_id,
                RecurringDefinition.workspace_id == workspace_id,
                RecurringDefinition.is_deleted.is_(False),
            )
            .options(
                selectinload(RecurringDefinition.category),
                selectinload(RecurringDefinition.merchant),
                selectinload(RecurringDefinition.account),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_definitions(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        direction: Optional[str] = None,
        frequency: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[RecurringDefinition]:
        """List recurring definitions with optional filtering and pagination."""
        stmt = (
            select(RecurringDefinition)
            .where(
                RecurringDefinition.workspace_id == workspace_id,
                RecurringDefinition.is_deleted.is_(False),
            )
            .options(
                selectinload(RecurringDefinition.category),
                selectinload(RecurringDefinition.merchant),
                selectinload(RecurringDefinition.account),
            )
            .order_by(RecurringDefinition.next_expected_date.asc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(RecurringDefinition.status == status)
        if direction:
            stmt = stmt.where(RecurringDefinition.direction == direction)
        if frequency:
            stmt = stmt.where(RecurringDefinition.frequency == frequency)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_definition(
        self,
        definition: RecurringDefinition,
    ) -> RecurringDefinition:
        """Create new recurring definition record."""
        self.db.add(definition)
        await self.db.flush()
        await self.db.refresh(definition)
        return definition

    async def update_definition(
        self,
        definition: RecurringDefinition,
    ) -> RecurringDefinition:
        """Update existing recurring definition."""
        await self.db.flush()
        await self.db.refresh(definition)
        return definition

    # -------------------------------------------------------------------------
    # Recurring Occurrences
    # -------------------------------------------------------------------------

    async def get_occurrence(
        self,
        occurrence_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[RecurringOccurrence]:
        """Fetch occurrence by ID with workspace isolation."""
        stmt = (
            select(RecurringOccurrence)
            .where(
                RecurringOccurrence.id == occurrence_id,
                RecurringOccurrence.workspace_id == workspace_id,
            )
            .options(
                selectinload(RecurringOccurrence.recurring_definition).selectinload(RecurringDefinition.category),
                selectinload(RecurringOccurrence.matched_transaction),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_occurrence_by_schedule(
        self,
        definition_id: uuid.UUID,
        expected_date: date,
    ) -> Optional[RecurringOccurrence]:
        """Check for existing occurrence on specific date to guarantee idempotency."""
        stmt = select(RecurringOccurrence).where(
            RecurringOccurrence.recurring_definition_id == definition_id,
            RecurringOccurrence.expected_date == expected_date,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_occurrences(
        self,
        workspace_id: uuid.UUID,
        definition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RecurringOccurrence]:
        """List occurrences matching filter criteria."""
        stmt = (
            select(RecurringOccurrence)
            .where(RecurringOccurrence.workspace_id == workspace_id)
            .options(
                selectinload(RecurringOccurrence.recurring_definition).selectinload(RecurringDefinition.category),
                selectinload(RecurringOccurrence.matched_transaction),
            )
            .order_by(RecurringOccurrence.expected_date.asc())
            .offset(skip)
            .limit(limit)
        )
        if definition_id:
            stmt = stmt.where(RecurringOccurrence.recurring_definition_id == definition_id)
        if status:
            stmt = stmt.where(RecurringOccurrence.status == status)
        if start_date:
            stmt = stmt.where(RecurringOccurrence.expected_date >= start_date)
        if end_date:
            stmt = stmt.where(RecurringOccurrence.expected_date <= end_date)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_occurrence_idempotent(
        self,
        occurrence: RecurringOccurrence,
    ) -> Optional[RecurringOccurrence]:
        """
        Idempotently inserts an occurrence.
        If an occurrence for the definition on this date already exists, returns the existing record.
        """
        existing = await self.get_occurrence_by_schedule(
            definition_id=occurrence.recurring_definition_id,
            expected_date=occurrence.expected_date,
        )
        if existing:
            return existing

        self.db.add(occurrence)
        await self.db.flush()
        await self.db.refresh(occurrence)
        return occurrence

    async def update_occurrence(
        self,
        occurrence: RecurringOccurrence,
    ) -> RecurringOccurrence:
        """Update existing occurrence (status, matched transaction, notes)."""
        await self.db.flush()
        await self.db.refresh(occurrence)
        return occurrence

    # -------------------------------------------------------------------------
    # Subscriptions
    # -------------------------------------------------------------------------

    async def get_subscription(
        self,
        subscription_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[Subscription]:
        """Fetch subscription by ID with workspace isolation."""
        stmt = (
            select(Subscription)
            .where(
                Subscription.id == subscription_id,
                Subscription.workspace_id == workspace_id,
                Subscription.is_deleted.is_(False),
            )
            .options(
                selectinload(Subscription.recurring_definition),
                selectinload(Subscription.merchant),
                selectinload(Subscription.category),
                selectinload(Subscription.account),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_subscriptions(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Subscription]:
        """List active/archived subscriptions."""
        stmt = (
            select(Subscription)
            .where(
                Subscription.workspace_id == workspace_id,
                Subscription.is_deleted.is_(False),
            )
            .options(
                selectinload(Subscription.recurring_definition),
                selectinload(Subscription.merchant),
                selectinload(Subscription.category),
                selectinload(Subscription.account),
            )
            .order_by(Subscription.next_billing_date.asc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Subscription.status == status)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_subscription(
        self,
        subscription: Subscription,
    ) -> Subscription:
        """Save a new subscription."""
        self.db.add(subscription)
        await self.db.flush()
        await self.db.refresh(subscription)
        return subscription

    async def update_subscription(
        self,
        subscription: Subscription,
    ) -> Subscription:
        """Update subscription parameters."""
        await self.db.flush()
        await self.db.refresh(subscription)
        return subscription

    # -------------------------------------------------------------------------
    # Reminders
    # -------------------------------------------------------------------------

    async def get_reminder(
        self,
        reminder_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[RecurringReminder]:
        """Fetch reminder by ID."""
        stmt = select(RecurringReminder).where(
            RecurringReminder.id == reminder_id,
            RecurringReminder.workspace_id == workspace_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_reminders(
        self,
        workspace_id: uuid.UUID,
        is_read: Optional[bool] = None,
        scheduled_before: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[RecurringReminder]:
        """List dispatched or pending in-app reminders."""
        stmt = (
            select(RecurringReminder)
            .where(RecurringReminder.workspace_id == workspace_id)
            .order_by(RecurringReminder.scheduled_for.desc(), RecurringReminder.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if is_read is not None:
            stmt = stmt.where(RecurringReminder.is_read == is_read)
        if scheduled_before is not None:
            stmt = stmt.where(RecurringReminder.scheduled_for <= scheduled_before)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_reminder_idempotent(
        self,
        reminder: RecurringReminder,
    ) -> Optional[RecurringReminder]:
        """
        Deduplicates reminders so the same threshold/type is not created repeatedly for an occurrence or subscription.
        """
        stmt = select(RecurringReminder).where(
            RecurringReminder.workspace_id == reminder.workspace_id,
            RecurringReminder.reminder_type == reminder.reminder_type,
            RecurringReminder.scheduled_for == reminder.scheduled_for,
        )
        if reminder.occurrence_id is not None:
            stmt = stmt.where(RecurringReminder.occurrence_id == reminder.occurrence_id)
        elif reminder.subscription_id is not None:
            stmt = stmt.where(RecurringReminder.subscription_id == reminder.subscription_id)

        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        self.db.add(reminder)
        await self.db.flush()
        await self.db.refresh(reminder)
        return reminder

    async def mark_reminder_read(
        self,
        reminder_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """Mark reminder as acknowledged."""
        stmt = (
            update(RecurringReminder)
            .where(
                RecurringReminder.id == reminder_id,
                RecurringReminder.workspace_id == workspace_id,
            )
            .values(is_read=True)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # -------------------------------------------------------------------------
    # Recurring Pattern Suggestions
    # -------------------------------------------------------------------------

    async def get_suggestion(
        self,
        suggestion_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[RecurringSuggestion]:
        """Fetch suggestion by ID."""
        stmt = (
            select(RecurringSuggestion)
            .where(
                RecurringSuggestion.id == suggestion_id,
                RecurringSuggestion.workspace_id == workspace_id,
            )
            .options(
                selectinload(RecurringSuggestion.merchant),
                selectinload(RecurringSuggestion.category),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_suggestions(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = "pending",
        skip: int = 0,
        limit: int = 50,
    ) -> List[RecurringSuggestion]:
        """List pattern suggestions."""
        stmt = (
            select(RecurringSuggestion)
            .where(RecurringSuggestion.workspace_id == workspace_id)
            .options(
                selectinload(RecurringSuggestion.merchant),
                selectinload(RecurringSuggestion.category),
            )
            .order_by(RecurringSuggestion.confidence_score.desc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(RecurringSuggestion.status == status)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save_suggestion(
        self,
        suggestion: RecurringSuggestion,
    ) -> RecurringSuggestion:
        """Save or refresh pattern suggestion."""
        # Check if identical normalized pattern exists for workspace
        stmt = select(RecurringSuggestion).where(
            RecurringSuggestion.workspace_id == suggestion.workspace_id,
            RecurringSuggestion.merchant_name == suggestion.merchant_name,
            RecurringSuggestion.direction == suggestion.direction,
            RecurringSuggestion.suggested_frequency == suggestion.suggested_frequency,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            if existing.status == "dismissed":
                # Do not resurface dismissed suggestion
                return existing
            # Refresh metrics
            existing.suggested_amount_paise = suggestion.suggested_amount_paise
            existing.suggested_amount = suggestion.suggested_amount
            existing.min_amount_paise = suggestion.min_amount_paise
            existing.max_amount_paise = suggestion.max_amount_paise
            existing.confidence_score = suggestion.confidence_score
            existing.evidence_count = suggestion.evidence_count
            existing.evidence_summary = suggestion.evidence_summary
            existing.last_seen_date = suggestion.last_seen_date
            existing.estimated_next_date = suggestion.estimated_next_date
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        self.db.add(suggestion)
        await self.db.flush()
        await self.db.refresh(suggestion)
        return suggestion

    async def update_suggestion_status(
        self,
        suggestion_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: str,
        reason: Optional[str] = None,
    ) -> Optional[RecurringSuggestion]:
        """Update suggestion status (confirmed or dismissed)."""
        suggestion = await self.get_suggestion(suggestion_id, workspace_id)
        if not suggestion:
            return None
        suggestion.status = status
        if reason:
            suggestion.dismissed_reason = reason
        await self.db.flush()
        await self.db.refresh(suggestion)
        return suggestion

    # -------------------------------------------------------------------------
    # Candidate Transactions for Matching & Intelligence
    # -------------------------------------------------------------------------

    async def find_candidate_transactions(
        self,
        workspace_id: uuid.UUID,
        min_date: date,
        max_date: date,
        direction: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Fetches posted transactions within date range for occurrence reconciliation or pattern detection.
        Excludes soft-deleted or unposted transactions.
        """
        stmt = (
            select(Transaction)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.status == "posted",
                Transaction.transaction_date >= min_date,
                Transaction.transaction_date <= max_date,
                Transaction.is_deleted.is_(False),
            )
            .order_by(Transaction.transaction_date.desc())
        )
        if direction:
            stmt = stmt.where(Transaction.direction == direction)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
