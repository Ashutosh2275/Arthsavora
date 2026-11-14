"""
Arthsavora Financial Goal Pydantic Request & Response Schemas
Type safety, exact integer minor units (paise), ISO dates, and progress pacing models.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class GoalCreateRequest(BaseModel):
    """Request payload to create a new financial goal."""
    name: str = Field(..., min_length=1, max_length=255, description="Goal name")
    target_amount_paise: int = Field(..., gt=0, description="Target savings amount in paise (> 0)")
    goal_type: str = Field("personal_savings", description="emergency_fund, education, travel, vehicle, home, debt_repayment, personal_savings, custom")
    currency: str = Field("INR", min_length=3, max_length=3, description="ISO 4217 3-letter currency code")
    start_date: Optional[date] = Field(None, description="Start date of the goal (defaults to today)")
    target_date: Optional[date] = Field(None, description="Target completion date")
    priority: str = Field("medium", description="low, medium, high")
    color: Optional[str] = Field("#6366f1", max_length=20)
    icon: Optional[str] = Field("target", max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    metadata_payload: Optional[Dict[str, Any]] = Field(None, description="Optional custom metadata payload")


class GoalUpdateRequest(BaseModel):
    """Request payload to update an existing goal."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_amount_paise: Optional[int] = Field(None, gt=0)
    target_date: Optional[date] = None
    status: Optional[str] = Field(None, description="active, completed, paused, archived")
    priority: Optional[str] = Field(None, description="low, medium, high")
    color: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    metadata_payload: Optional[Dict[str, Any]] = None


class GoalActivityRequest(BaseModel):
    """Request payload to record a contribution or withdrawal against a goal."""
    amount_paise: int = Field(..., gt=0, description="Activity amount in paise (> 0)")
    transaction_id: Optional[uuid.UUID] = Field(None, description="Optional linked transaction provenance")
    notes: Optional[str] = Field(None, max_length=500, description="Audit notes or memo")


# --- Responses ---

class GoalActivityResponse(BaseModel):
    """Single entry in the immutable goal activity ledger."""
    id: uuid.UUID
    goal_id: uuid.UUID
    workspace_id: uuid.UUID
    activity_type: str
    amount_paise: int
    amount: Decimal
    currency: str
    resulting_balance_paise: int
    transaction_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    performed_by_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalResponse(BaseModel):
    """Representation of a financial goal."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    goal_type: str
    currency: str
    target_amount_paise: int
    target_amount: Decimal
    current_amount_paise: int
    current_amount: Decimal
    start_date: date
    target_date: Optional[date] = None
    status: str
    priority: str
    color: Optional[str] = None
    icon: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    metadata_payload: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalProgressResponse(BaseModel):
    """Evaluated pacing, progress, and monthly contribution requirements."""
    goal_id: uuid.UUID
    name: str
    goal_type: str
    currency: str
    status: str
    priority: str
    color: Optional[str] = None
    icon: Optional[str] = None
    target_amount_paise: int
    target_amount: Decimal
    current_amount_paise: int
    current_amount: Decimal
    start_date: date
    target_date: Optional[date] = None
    as_of_date: date
    remaining_paise: int
    remaining_amount: Decimal
    completion_percentage: float
    is_completed: bool
    days_remaining: Optional[int] = None
    required_monthly_savings_paise: Optional[int] = None
    required_monthly_savings_amount: Optional[Decimal] = None
