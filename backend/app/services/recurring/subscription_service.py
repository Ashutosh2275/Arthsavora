"""
Arthsavora Subscription Management Application Service
Manages software, streaming, and membership subscriptions with trial tracking,
cancellation deadlines, renewal cycles, and cost normalization.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.domain.recurring import (
    BillingFrequency,
    RecurringDirection,
    RecurringFrequency,
    RecurringStatus,
    SubscriptionStatus,
    normalize_cost_to_monthly_and_annual,
)
from app.infrastructure.database.models.recurring import RecurringDefinition, Subscription
from app.repositories.recurring_repository import RecurringRepository
from app.schemas.recurring_schema import (
    RecurringDefinitionCreateRequest,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from app.services.recurring.recurring_service import RecurringService


class SubscriptionService:
    """Application service for digital subscriptions and recurring memberships."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringRepository(db)
        self.recurring_service = RecurringService(db)

    def _to_subscription_response(self, sub: Subscription) -> SubscriptionResponse:
        monthly_paise, annual_paise = normalize_cost_to_monthly_and_annual(
            amount_paise=sub.expected_amount_paise,
            frequency=sub.billing_frequency,
            cycle_interval=sub.billing_cycle_interval,
        )
        return SubscriptionResponse(
            id=sub.id,
            workspace_id=sub.workspace_id,
            recurring_definition_id=sub.recurring_definition_id,
            name=sub.name,
            provider_name=sub.provider_name,
            merchant_id=sub.merchant_id,
            merchant_name=sub.merchant.name if sub.merchant else None,
            category_id=sub.category_id,
            category_name=sub.category.name if sub.category else None,
            expected_amount_paise=sub.expected_amount_paise,
            expected_amount=sub.expected_amount,
            currency=sub.currency,
            billing_frequency=sub.billing_frequency,
            billing_cycle_interval=sub.billing_cycle_interval,
            start_date=sub.start_date,
            next_billing_date=sub.next_billing_date,
            renewal_date=sub.renewal_date,
            trial_end_date=sub.trial_end_date,
            cancellation_date=sub.cancellation_date,
            account_id=sub.account_id,
            account_name=sub.account.name if sub.account else None,
            payment_method_display=sub.payment_method_display,
            status=sub.status,
            is_variable_pricing=sub.is_variable_pricing,
            notes=sub.notes,
            estimated_monthly_paise=monthly_paise,
            estimated_annual_paise=annual_paise,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
        )

    async def create_subscription(
        self,
        workspace_id: uuid.UUID,
        payload: SubscriptionCreateRequest,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> SubscriptionResponse:
        """Creates a subscription and optionally an underlying recurring definition for cash-flow forecasting."""
        expected_amount_dec = Decimal(payload.expected_amount_paise) / Decimal("100.0000")

        recurring_def_id: Optional[uuid.UUID] = None

        if payload.create_recurring_definition:
            # Map billing frequency to recurring frequency
            freq_map = {
                BillingFrequency.WEEKLY: RecurringFrequency.WEEKLY,
                BillingFrequency.MONTHLY: RecurringFrequency.MONTHLY,
                BillingFrequency.QUARTERLY: RecurringFrequency.QUARTERLY,
                BillingFrequency.SEMI_ANNUAL: RecurringFrequency.SEMI_ANNUAL,
                BillingFrequency.ANNUAL: RecurringFrequency.ANNUAL,
            }
            rec_freq = freq_map.get(payload.billing_frequency, RecurringFrequency.MONTHLY)

            def_req = RecurringDefinitionCreateRequest(
                name=payload.name,
                description=f"Subscription: {payload.name}" + (f" ({payload.provider_name})" if payload.provider_name else ""),
                direction=RecurringDirection.OUTFLOW,
                transaction_type="expense",
                expected_amount_paise=payload.expected_amount_paise,
                is_variable_amount=payload.is_variable_pricing,
                currency=payload.currency,
                category_id=payload.category_id,
                merchant_id=payload.merchant_id,
                merchant_name=payload.provider_name,
                account_id=payload.account_id,
                frequency=rec_freq,
                interval=payload.billing_cycle_interval,
                day_of_month=payload.next_billing_date.day,
                start_date=payload.start_date,
            )
            created_def = await self.recurring_service.create_definition(
                workspace_id=workspace_id,
                payload=def_req,
                created_by_id=created_by_id,
            )
            recurring_def_id = created_def.id

        sub_status = SubscriptionStatus.ACTIVE.value
        if payload.trial_end_date and payload.trial_end_date >= date.today():
            sub_status = SubscriptionStatus.TRIAL.value

        sub = Subscription(
            workspace_id=workspace_id,
            recurring_definition_id=recurring_def_id,
            name=payload.name,
            provider_name=payload.provider_name,
            merchant_id=payload.merchant_id,
            category_id=payload.category_id,
            expected_amount_paise=payload.expected_amount_paise,
            expected_amount=expected_amount_dec,
            currency=payload.currency.upper(),
            billing_frequency=payload.billing_frequency.value,
            billing_cycle_interval=payload.billing_cycle_interval,
            start_date=payload.start_date,
            next_billing_date=payload.next_billing_date,
            renewal_date=payload.renewal_date,
            trial_end_date=payload.trial_end_date,
            account_id=payload.account_id,
            payment_method_display=payload.payment_method_display,
            status=sub_status,
            is_variable_pricing=payload.is_variable_pricing,
            notes=payload.notes,
        )

        saved = await self.repo.create_subscription(sub)
        loaded = await self.repo.get_subscription(saved.id, workspace_id)
        return self._to_subscription_response(loaded or saved)

    async def get_subscription(
        self,
        subscription_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> SubscriptionResponse:
        """Fetch subscription detail."""
        sub = await self.repo.get_subscription(subscription_id, workspace_id)
        if not sub:
            raise NotFoundException(detail=f"Subscription {subscription_id} not found")
        return self._to_subscription_response(sub)

    async def list_subscriptions(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[SubscriptionResponse]:
        """List subscriptions."""
        items = await self.repo.list_subscriptions(
            workspace_id=workspace_id,
            status=status,
            skip=skip,
            limit=limit,
        )
        return [self._to_subscription_response(s) for s in items]

    async def update_subscription(
        self,
        subscription_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: SubscriptionUpdateRequest,
    ) -> SubscriptionResponse:
        """Update subscription parameters."""
        sub = await self.repo.get_subscription(subscription_id, workspace_id)
        if not sub:
            raise NotFoundException(detail=f"Subscription {subscription_id} not found")

        if payload.name is not None:
            sub.name = payload.name
        if payload.provider_name is not None:
            sub.provider_name = payload.provider_name
        if payload.expected_amount_paise is not None:
            sub.expected_amount_paise = payload.expected_amount_paise
            sub.expected_amount = Decimal(payload.expected_amount_paise) / Decimal("100.0000")
        if payload.billing_frequency is not None:
            sub.billing_frequency = payload.billing_frequency.value
        if payload.billing_cycle_interval is not None:
            sub.billing_cycle_interval = payload.billing_cycle_interval
        if payload.next_billing_date is not None:
            sub.next_billing_date = payload.next_billing_date
        if payload.renewal_date is not None:
            sub.renewal_date = payload.renewal_date
        if payload.trial_end_date is not None:
            sub.trial_end_date = payload.trial_end_date
        if payload.cancellation_date is not None:
            sub.cancellation_date = payload.cancellation_date
        if payload.status is not None:
            sub.status = payload.status.value
        if payload.account_id is not None:
            sub.account_id = payload.account_id
        if payload.payment_method_display is not None:
            sub.payment_method_display = payload.payment_method_display
        if payload.is_variable_pricing is not None:
            sub.is_variable_pricing = payload.is_variable_pricing
        if payload.notes is not None:
            sub.notes = payload.notes

        updated = await self.repo.update_subscription(sub)
        return self._to_subscription_response(updated)

    async def cancel_subscription(
        self,
        subscription_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> SubscriptionResponse:
        """Cancel subscription and pause associated recurring definition."""
        sub = await self.repo.get_subscription(subscription_id, workspace_id)
        if not sub:
            raise NotFoundException(detail=f"Subscription {subscription_id} not found")

        sub.status = SubscriptionStatus.CANCELLED.value
        sub.cancellation_date = date.today()
        updated = await self.repo.update_subscription(sub)

        # Pause or cancel backing recurring definition
        if sub.recurring_definition_id:
            await self.recurring_service.cancel_definition(sub.recurring_definition_id, workspace_id)

        return self._to_subscription_response(updated)
