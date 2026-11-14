"""
Arthsavora Recurring Pattern Detection & Intelligence Service
Identifies likely recurring transactions and subscriptions from historical evidence
with explainable confidence metrics and strict user-controlled confirmation.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.domain.recurring import (
    RecurringDirection,
    RecurringFrequency,
    SuggestionStatus,
    detect_recurring_patterns_from_transactions,
)
from app.infrastructure.database.models.recurring import RecurringSuggestion
from app.repositories.recurring_repository import RecurringRepository
from app.schemas.recurring_schema import (
    RecurringDefinitionCreateRequest,
    RecurringSuggestionResponse,
    SubscriptionCreateRequest,
    SuggestionConfirmRequest,
    SuggestionDismissRequest,
)
from app.services.recurring.recurring_service import RecurringService
from app.services.recurring.subscription_service import SubscriptionService


class DetectionService:
    """Orchestrates pattern detection, suggestion persistence, and user confirmation workflows."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringRepository(db)
        self.recurring_service = RecurringService(db)
        self.subscription_service = SubscriptionService(db)

    def _to_suggestion_response(self, sugg: RecurringSuggestion) -> RecurringSuggestionResponse:
        return RecurringSuggestionResponse(
            id=sugg.id,
            workspace_id=sugg.workspace_id,
            merchant_id=sugg.merchant_id,
            merchant_name=sugg.merchant_name,
            normalized_description=sugg.normalized_description,
            direction=sugg.direction,
            suggested_frequency=sugg.suggested_frequency,
            suggested_amount_paise=sugg.suggested_amount_paise,
            suggested_amount=sugg.suggested_amount,
            min_amount_paise=sugg.min_amount_paise,
            max_amount_paise=sugg.max_amount_paise,
            currency=sugg.currency,
            category_id=sugg.category_id,
            confidence_score=sugg.confidence_score,
            evidence_count=sugg.evidence_count,
            evidence_summary=sugg.evidence_summary,
            first_seen_date=sugg.first_seen_date,
            last_seen_date=sugg.last_seen_date,
            estimated_next_date=sugg.estimated_next_date,
            status=sugg.status,
            dismissed_reason=sugg.dismissed_reason,
            created_at=sugg.created_at,
        )

    async def run_detection(
        self,
        workspace_id: uuid.UUID,
        lookback_days: int = 180,
        as_of_date: Optional[date] = None,
    ) -> List[RecurringSuggestionResponse]:
        """
        Scans historical posted transactions and detects recurring pattern candidates.
        """
        today = as_of_date or date.today()
        min_date = today - timedelta(days=lookback_days)

        transactions = await self.repo.find_candidate_transactions(
            workspace_id=workspace_id,
            min_date=min_date,
            max_date=today,
        )

        tx_dicts = [
            {
                "id": t.id,
                "amount_paise": t.amount_paise,
                "transaction_date": t.transaction_date,
                "direction": t.direction,
                "status": t.status,
                "merchant_name": t.merchant_name,
                "description": t.description,
                "category_id": t.category_id,
            }
            for t in transactions
        ]

        detected_patterns = detect_recurring_patterns_from_transactions(
            transactions=tx_dicts,
            as_of_date=today,
        )

        saved_suggestions: List[RecurringSuggestion] = []

        for p in detected_patterns:
            sugg = RecurringSuggestion(
                workspace_id=workspace_id,
                merchant_name=p.merchant_name,
                normalized_description=p.normalized_description,
                direction=p.direction,
                suggested_frequency=p.suggested_frequency.value,
                suggested_amount_paise=p.suggested_amount_paise,
                suggested_amount=Decimal(p.suggested_amount_paise) / Decimal("100.0000"),
                min_amount_paise=p.min_amount_paise,
                max_amount_paise=p.max_amount_paise,
                currency="INR",
                confidence_score=p.confidence_score,
                evidence_count=p.evidence_count,
                evidence_summary=p.evidence_summary,
                first_seen_date=p.first_seen_date,
                last_seen_date=p.last_seen_date,
                estimated_next_date=p.estimated_next_date,
                status=SuggestionStatus.PENDING.value,
            )
            saved = await self.repo.save_suggestion(sugg)
            if saved and saved.status != "dismissed":
                saved_suggestions.append(saved)

        return [self._to_suggestion_response(s) for s in saved_suggestions]

    async def list_suggestions(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = "pending",
        skip: int = 0,
        limit: int = 50,
    ) -> List[RecurringSuggestionResponse]:
        """List suggestions with status filter."""
        items = await self.repo.list_suggestions(
            workspace_id=workspace_id,
            status=status,
            skip=skip,
            limit=limit,
        )
        return [self._to_suggestion_response(s) for s in items]

    async def confirm_suggestion(
        self,
        suggestion_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: SuggestionConfirmRequest,
        confirmed_by_id: Optional[uuid.UUID] = None,
    ) -> RecurringSuggestionResponse:
        """
        User confirms a detected suggestion, creating an authoritative recurring definition (and optional subscription).
        """
        sugg = await self.repo.get_suggestion(suggestion_id, workspace_id)
        if not sugg:
            raise NotFoundException(detail=f"Recurring suggestion {suggestion_id} not found")

        name = payload.name or sugg.merchant_name
        amount_paise = payload.adjusted_amount_paise or sugg.suggested_amount_paise
        freq = payload.adjusted_frequency or RecurringFrequency(sugg.suggested_frequency)
        cat_id = payload.category_id or sugg.category_id

        if payload.is_subscription:
            # Map frequency
            from app.domain.recurring import BillingFrequency
            billing_freq = BillingFrequency.MONTHLY
            if freq == RecurringFrequency.WEEKLY:
                billing_freq = BillingFrequency.WEEKLY
            elif freq == RecurringFrequency.QUARTERLY:
                billing_freq = BillingFrequency.QUARTERLY
            elif freq == RecurringFrequency.ANNUAL:
                billing_freq = BillingFrequency.ANNUAL

            sub_req = SubscriptionCreateRequest(
                name=name,
                provider_name=sugg.merchant_name,
                merchant_id=sugg.merchant_id,
                category_id=cat_id,
                expected_amount_paise=amount_paise,
                currency=sugg.currency,
                billing_frequency=billing_freq,
                billing_cycle_interval=1,
                start_date=sugg.first_seen_date,
                next_billing_date=sugg.estimated_next_date,
                account_id=payload.account_id,
                create_recurring_definition=True,
            )
            await self.subscription_service.create_subscription(
                workspace_id=workspace_id,
                payload=sub_req,
                created_by_id=confirmed_by_id,
            )
        else:
            def_req = RecurringDefinitionCreateRequest(
                name=name,
                description=f"Inferred recurring activity: {sugg.normalized_description}",
                direction=RecurringDirection(sugg.direction),
                transaction_type="income" if sugg.direction == "inflow" else "expense",
                expected_amount_paise=amount_paise,
                currency=sugg.currency,
                category_id=cat_id,
                merchant_id=sugg.merchant_id,
                merchant_name=sugg.merchant_name,
                account_id=payload.account_id,
                frequency=freq,
                interval=1,
                day_of_month=sugg.estimated_next_date.day,
                start_date=sugg.first_seen_date,
            )
            await self.recurring_service.create_definition(
                workspace_id=workspace_id,
                payload=def_req,
                created_by_id=confirmed_by_id,
            )

        updated = await self.repo.update_suggestion_status(
            suggestion_id=suggestion_id,
            workspace_id=workspace_id,
            status=SuggestionStatus.CONFIRMED.value,
        )
        return self._to_suggestion_response(updated or sugg)

    async def dismiss_suggestion(
        self,
        suggestion_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: SuggestionDismissRequest,
    ) -> RecurringSuggestionResponse:
        """Dismisses suggestion with optional reason."""
        sugg = await self.repo.get_suggestion(suggestion_id, workspace_id)
        if not sugg:
            raise NotFoundException(detail=f"Recurring suggestion {suggestion_id} not found")

        updated = await self.repo.update_suggestion_status(
            suggestion_id=suggestion_id,
            workspace_id=workspace_id,
            status=SuggestionStatus.DISMISSED.value,
            reason=payload.reason,
        )
        return self._to_suggestion_response(updated or sugg)
