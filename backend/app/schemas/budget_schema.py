"""
Arthsavora Personal Budgeting Pydantic Request & Response Schemas
Exact integer minor unit (paise) representation, ISO dates, typed validation,
and comprehensive progress/projection data models.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class BudgetAllocationCreateItem(BaseModel):
    """Initial category allocation parameter in budget creation."""
    category_id: uuid.UUID = Field(..., description="Target transaction category ID")
    allocated_amount_paise: int = Field(..., ge=0, description="Allocated amount in paise (>= 0)")
    warning_threshold_percentage: Optional[int] = Field(80, ge=1, le=100, description="Warning threshold percentage (e.g. 80)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional allocation notes")


class BudgetCreateRequest(BaseModel):
    """Request payload to create a new personal budget."""
    name: str = Field(..., min_length=1, max_length=255, description="Budget name")
    start_date: date = Field(..., description="Start date of the budget period")
    end_date: date = Field(..., description="End date of the budget period")
    total_allocated_paise: int = Field(..., ge=0, description="Total budget ceiling in paise")
    budget_type: str = Field("monthly", description="Budget type: monthly, custom_period, category, annual, flexible")
    currency: str = Field("INR", min_length=3, max_length=3, description="ISO 4217 3-letter currency code")
    recurrence_interval: str = Field("monthly", description="none, monthly, quarterly, annual")
    allocations: Optional[List[BudgetAllocationCreateItem]] = Field(None, description="Optional initial category allocations")
    settings: Optional[Dict[str, Any]] = Field(None, description="Extensible JSON settings")


class BudgetUpdateRequest(BaseModel):
    """Request payload to update an existing budget."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_allocated_paise: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, description="active, archived, closed")
    recurrence_interval: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    revision_reason: Optional[str] = Field(None, max_length=500, description="Audit reason for revision ledger")


class AllocationCreateRequest(BaseModel):
    """Request payload to add a category allocation to a budget."""
    category_id: uuid.UUID = Field(..., description="Category UUID")
    allocated_amount_paise: int = Field(..., ge=0, description="Allocated amount in paise")
    warning_threshold_percentage: Optional[int] = Field(80, ge=1, le=100)
    notes: Optional[str] = Field(None, max_length=500)
    revision_reason: Optional[str] = Field(None, max_length=500)


class AllocationUpdateRequest(BaseModel):
    """Request payload to update an existing category allocation."""
    allocated_amount_paise: Optional[int] = Field(None, ge=0)
    warning_threshold_percentage: Optional[int] = Field(None, ge=1, le=100)
    notes: Optional[str] = Field(None, max_length=500)
    revision_reason: Optional[str] = Field(None, max_length=500)


class BudgetRolloverRequest(BaseModel):
    """Request payload to roll over a budget to the subsequent period."""
    new_start_date: Optional[date] = Field(None, description="Optional custom start date")
    new_end_date: Optional[date] = Field(None, description="Optional custom end date")
    adjust_allocation_paise: Optional[int] = Field(None, ge=0, description="Optional revised total allocation")


# --- Responses ---

class BudgetAllocationResponse(BaseModel):
    """Detailed category allocation response."""
    id: uuid.UUID
    budget_id: uuid.UUID
    category_id: uuid.UUID
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    allocated_amount_paise: int
    allocated_amount: Decimal
    warning_threshold_percentage: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetRevisionResponse(BaseModel):
    """Historical audit revision log entry."""
    id: uuid.UUID
    budget_id: uuid.UUID
    revision_number: int
    change_type: str
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    reason: Optional[str] = None
    changed_by_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetAlertResponse(BaseModel):
    """Idempotent threshold crossing alert response."""
    id: uuid.UUID
    budget_id: uuid.UUID
    allocation_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    threshold_percentage: int
    triggered_at_paise: int
    triggered_at_amount: Decimal
    utilization_percentage: float
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetSummaryResponse(BaseModel):
    """Summary representation for budget listing."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    budget_type: str
    currency: str
    start_date: date
    end_date: date
    total_allocated_paise: int
    total_allocated: Decimal
    recurrence_interval: str
    status: str
    allocations_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetDetailResponse(BudgetSummaryResponse):
    """Detailed representation of a budget including all allocations."""
    allocations: List[BudgetAllocationResponse] = []
    settings: Dict[str, Any] = {}


class BudgetAllocationProgressResponse(BaseModel):
    """Evaluated progress metrics for a specific category allocation."""
    allocation_id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_color: Optional[str] = None
    allocated_paise: int
    allocated_amount: Decimal
    spent_paise: int
    spent_amount: Decimal
    remaining_paise: int
    remaining_amount: Decimal
    utilization_percentage: float
    overspent: bool
    warning_state: str
    warning_threshold_percentage: int


class BudgetLinearProjectionResponse(BaseModel):
    """Transparent linear period-end spending projection."""
    days_in_period: int
    elapsed_days: int
    remaining_days: int
    daily_run_rate_paise: int
    daily_run_rate: Decimal
    projected_period_end_spend_paise: int
    projected_period_end_spend: Decimal
    projected_variance_paise: int
    projected_variance: Decimal
    projected_overspent: bool
    methodology: str
    assumptions: str


class BudgetProgressResponse(BaseModel):
    """Comprehensive progress, pacing, projection, and allocation breakdown."""
    budget_id: uuid.UUID
    name: str
    currency: str
    start_date: date
    end_date: date
    as_of_date: date
    total_allocated_paise: int
    total_allocated_amount: Decimal
    total_spent_paise: int
    total_spent_amount: Decimal
    remaining_paise: int
    remaining_amount: Decimal
    utilization_percentage: float
    overspent: bool
    warning_state: str
    period_days: int
    elapsed_days: int
    remaining_days: int
    period_elapsed_percentage: float
    linear_projection: BudgetLinearProjectionResponse
    allocations: List[BudgetAllocationProgressResponse]
    unallocated_capacity_paise: int
    unallocated_capacity_amount: Decimal
    new_alerts_triggered: int
