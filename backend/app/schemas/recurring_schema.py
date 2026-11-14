"""
Arthsavora Recurring Transactions, Subscriptions & Cash-Flow Commitments Pydantic Schemas
Defines request contracts with strict validation and response envelopes with exact decimal/paise representation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator

from app.domain.recurring import (
    BillingFrequency,
    EndOfMonthPolicy,
    OccurrenceStatus,
    RecurringDirection,
    RecurringFrequency,
    RecurringStatus,
    SubscriptionStatus,
    SuggestionStatus,
)


# -------------------------------------------------------------------------
# Recurring Definitions Schemas
# -------------------------------------------------------------------------

class RecurringDefinitionCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Descriptive title of recurring activity")
    description: Optional[str] = Field(None, max_length=1000)
    direction: RecurringDirection = Field(default=RecurringDirection.OUTFLOW)
    transaction_type: str = Field(default="expense", max_length=50)
    expected_amount_paise: int = Field(..., gt=0, description="Expected amount in minor units (paise)")
    is_variable_amount: bool = Field(default=False)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    category_id: Optional[uuid.UUID] = None
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = Field(None, max_length=255)
    account_id: Optional[uuid.UUID] = None

    frequency: RecurringFrequency = Field(default=RecurringFrequency.MONTHLY)
    interval: int = Field(default=1, ge=1, le=365)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    end_of_month_policy: EndOfMonthPolicy = Field(default=EndOfMonthPolicy.LAST_DAY)

    start_date: date
    end_date: Optional[date] = None
    timezone: str = Field(default="Asia/Kolkata", max_length=50)

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info: Any) -> Optional[date]:
        if v is not None and "start_date" in info.data:
            if v < info.data["start_date"]:
                raise ValueError("end_date cannot be earlier than start_date")
        return v


class RecurringDefinitionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    expected_amount_paise: Optional[int] = Field(None, gt=0)
    is_variable_amount: Optional[bool] = None
    category_id: Optional[uuid.UUID] = None
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = None
    account_id: Optional[uuid.UUID] = None
    frequency: Optional[RecurringFrequency] = None
    interval: Optional[int] = Field(None, ge=1)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    end_of_month_policy: Optional[EndOfMonthPolicy] = None
    end_date: Optional[date] = None
    next_expected_date: Optional[date] = None
    status: Optional[RecurringStatus] = None


class RecurringDefinitionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    direction: str
    transaction_type: str
    expected_amount_paise: int
    expected_amount: Decimal
    is_variable_amount: bool
    currency: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = None
    account_id: Optional[uuid.UUID] = None
    account_name: Optional[str] = None
    frequency: str
    interval: int
    day_of_month: Optional[int] = None
    day_of_week: Optional[int] = None
    end_of_month_policy: str
    start_date: date
    end_date: Optional[date] = None
    next_expected_date: date
    timezone: str
    status: str
    normalized_monthly_paise: int
    normalized_annual_paise: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Occurrence Schemas
# -------------------------------------------------------------------------

class OccurrenceMatchRequest(BaseModel):
    transaction_id: uuid.UUID = Field(..., description="Target posted transaction to reconcile against occurrence")
    notes: Optional[str] = None


class OccurrenceConfirmRequest(BaseModel):
    notes: Optional[str] = None


class OccurrenceSkipRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class OccurrenceResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    recurring_definition_id: uuid.UUID
    recurring_name: Optional[str] = None
    direction: Optional[str] = None
    expected_date: date
    expected_amount_paise: int
    expected_amount: Decimal
    currency: str
    status: str
    matched_transaction_id: Optional[uuid.UUID] = None
    matched_amount_paise: Optional[int] = None
    matched_amount: Optional[Decimal] = None
    amount_variance_paise: Optional[int] = None
    match_confidence: Optional[Decimal] = None
    notes: Optional[str] = None
    generated_at: datetime
    confirmed_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Subscription Schemas
# -------------------------------------------------------------------------

class SubscriptionCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    provider_name: Optional[str] = Field(None, max_length=255)
    merchant_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    expected_amount_paise: int = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    billing_frequency: BillingFrequency = Field(default=BillingFrequency.MONTHLY)
    billing_cycle_interval: int = Field(default=1, ge=1)
    start_date: date
    next_billing_date: date
    renewal_date: Optional[date] = None
    trial_end_date: Optional[date] = None
    account_id: Optional[uuid.UUID] = None
    payment_method_display: Optional[str] = Field(None, max_length=100)
    is_variable_pricing: bool = Field(default=False)
    notes: Optional[str] = None
    create_recurring_definition: bool = Field(default=True, description="Whether to also generate a recurring definition for cash-flow tracking")


class SubscriptionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    provider_name: Optional[str] = None
    expected_amount_paise: Optional[int] = Field(None, gt=0)
    billing_frequency: Optional[BillingFrequency] = None
    billing_cycle_interval: Optional[int] = Field(None, ge=1)
    next_billing_date: Optional[date] = None
    renewal_date: Optional[date] = None
    trial_end_date: Optional[date] = None
    cancellation_date: Optional[date] = None
    status: Optional[SubscriptionStatus] = None
    account_id: Optional[uuid.UUID] = None
    payment_method_display: Optional[str] = None
    is_variable_pricing: Optional[bool] = None
    notes: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    recurring_definition_id: Optional[uuid.UUID] = None
    name: str
    provider_name: Optional[str] = None
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    expected_amount_paise: int
    expected_amount: Decimal
    currency: str
    billing_frequency: str
    billing_cycle_interval: int
    start_date: date
    next_billing_date: date
    renewal_date: Optional[date] = None
    trial_end_date: Optional[date] = None
    cancellation_date: Optional[date] = None
    account_id: Optional[uuid.UUID] = None
    account_name: Optional[str] = None
    payment_method_display: Optional[str] = None
    status: str
    is_variable_pricing: bool
    notes: Optional[str] = None
    estimated_monthly_paise: int
    estimated_annual_paise: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Reminder Schemas
# -------------------------------------------------------------------------

class RecurringReminderResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    occurrence_id: Optional[uuid.UUID] = None
    recurring_definition_id: Optional[uuid.UUID] = None
    subscription_id: Optional[uuid.UUID] = None
    reminder_type: str
    days_before: int
    scheduled_for: date
    notification_channel: str
    is_sent: bool
    sent_at: Optional[datetime] = None
    is_read: bool
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Recurring Suggestion & Pattern Detection Schemas
# -------------------------------------------------------------------------

class RecurringDetectRequest(BaseModel):
    lookback_days: int = Field(default=180, ge=30, le=730)
    as_of_date: Optional[date] = None


class RecurringSuggestionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: str
    normalized_description: str
    direction: str
    suggested_frequency: str
    suggested_amount_paise: int
    suggested_amount: Decimal
    min_amount_paise: int
    max_amount_paise: int
    currency: str
    category_id: Optional[uuid.UUID] = None
    confidence_score: Decimal
    evidence_count: int
    evidence_summary: Dict[str, Any]
    first_seen_date: date
    last_seen_date: date
    estimated_next_date: date
    status: str
    dismissed_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SuggestionConfirmRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    category_id: Optional[uuid.UUID] = None
    account_id: Optional[uuid.UUID] = None
    adjusted_amount_paise: Optional[int] = Field(None, gt=0)
    adjusted_frequency: Optional[RecurringFrequency] = None
    is_subscription: bool = Field(default=False)


class SuggestionDismissRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


# -------------------------------------------------------------------------
# Cash-Flow Commitments & Analytics Schemas
# -------------------------------------------------------------------------

class CommitmentBreakdownByType(BaseModel):
    type_name: str
    count: int
    total_amount_paise: int
    total_amount: Decimal


class CashFlowCommitmentsResponse(BaseModel):
    workspace_id: uuid.UUID
    window_days: int
    start_date: date
    end_date: date
    total_expected_inflow_paise: int
    total_expected_inflow: Decimal
    total_expected_outflow_paise: int
    total_expected_outflow: Decimal
    net_commitment_paise: int
    net_commitment: Decimal
    active_recurring_count: int
    active_subscription_count: int
    normalized_monthly_expenses_paise: int
    normalized_monthly_expenses: Decimal
    normalized_annual_expenses_paise: int
    normalized_annual_expenses: Decimal
    commitments_by_category: List[Dict[str, Any]]
    commitments_by_type: List[CommitmentBreakdownByType]
    upcoming_occurrences: List[OccurrenceResponse]
