"""
Arthsavora Family Finance Pydantic Schemas
Defines request and response schemas for family workspaces, member management,
expense allocations, pool contributions, settlements, and privacy bridges.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


def paise_to_decimal(paise: int) -> Decimal:
    """Helper converting minor units (paise) to 2-place Decimal."""
    return (Decimal(paise) / Decimal(100)).quantize(Decimal("0.01"))


# -----------------------------------------------------------------------------
# Profile & Settings
# -----------------------------------------------------------------------------

class FamilyProfileResponse(BaseModel):
    """Configuration and preferences for a family workspace."""
    id: UUID
    workspace_id: UUID
    household_name: str
    household_currency: str
    household_timezone: str
    monthly_budget_start_day: int
    default_allocation_method: str
    contribution_reminder_day: int
    enable_shared_budget_alerts: bool
    enable_contribution_reminders: bool
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UpdateFamilyProfileRequest(BaseModel):
    """Payload for updating household profile preferences."""
    household_name: Optional[str] = Field(None, min_length=1, max_length=255)
    household_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    household_timezone: Optional[str] = Field(None, max_length=50)
    monthly_budget_start_day: Optional[int] = Field(None, ge=1, le=28)
    default_allocation_method: Optional[str] = Field(None, pattern="^(equal|fixed|percentage|custom)$")
    contribution_reminder_day: Optional[int] = Field(None, ge=1, le=28)
    enable_shared_budget_alerts: Optional[bool] = None
    enable_contribution_reminders: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


# -----------------------------------------------------------------------------
# Members & Invitations
# -----------------------------------------------------------------------------

class FamilyMemberResponse(BaseModel):
    """Enriched family member summary."""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    email: str
    full_name: str
    role: str
    status: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InviteFamilyMemberRequest(BaseModel):
    """Payload for inviting a household member."""
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member|restricted|viewer)$")


class UpdateFamilyMemberRoleRequest(BaseModel):
    """Payload for changing a family member's role."""
    role: str = Field(..., pattern="^(admin|member|restricted|viewer)$")


# -----------------------------------------------------------------------------
# Expense Allocations
# -----------------------------------------------------------------------------

class CreateAllocationRequest(BaseModel):
    """Payload for allocating a shared household transaction."""
    transaction_id: UUID
    allocation_method: str = Field(default="equal", pattern="^(equal|fixed|percentage|custom)$")
    member_user_ids: Optional[List[UUID]] = None
    member_shares_paise: Optional[Dict[str, int]] = None
    member_percentages: Optional[Dict[str, Decimal]] = None
    payer_user_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=500)


class AllocationItemResponse(BaseModel):
    """Member share within an allocated expense."""
    id: UUID
    member_user_id: UUID
    member_name: Optional[str] = None
    assigned_share_paise: int
    assigned_share_decimal: Decimal
    percentage: Optional[Decimal] = None
    is_paid_by: bool
    settlement_status: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FamilyAllocationResponse(BaseModel):
    """Full detail of an expense allocation."""
    id: UUID
    workspace_id: UUID
    transaction_id: UUID
    transaction_description: Optional[str] = None
    allocation_method: str
    total_amount_paise: int
    total_amount_decimal: Decimal
    currency: str
    status: str
    version: int
    notes: Optional[str] = None
    items: List[AllocationItemResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Member Contributions
# -----------------------------------------------------------------------------

class RecordContributionRequest(BaseModel):
    """Payload for recording or expecting a member pool contribution."""
    member_user_id: UUID
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Period in YYYY-MM format")
    contribution_type: str = Field(default="monthly", pattern="^(monthly|fixed|percentage|one_time|voluntary)$")
    expected_amount_paise: int = Field(default=0, ge=0)
    paid_amount_paise: int = Field(default=0, ge=0)
    due_date: Optional[date] = None
    recorded_transaction_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=500)


class UpdateContributionRequest(BaseModel):
    """Payload for updating paid amount or status."""
    paid_amount_paise: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(expected|partially_paid|paid|overdue|waived|cancelled)$")
    notes: Optional[str] = Field(None, max_length=500)


class FamilyContributionResponse(BaseModel):
    """Detailed member pool contribution."""
    id: UUID
    workspace_id: UUID
    member_user_id: UUID
    member_name: Optional[str] = None
    period: str
    contribution_type: str
    expected_amount_paise: int
    expected_amount_decimal: Decimal
    paid_amount_paise: int
    paid_amount_decimal: Decimal
    currency: str
    due_date: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Settlements & Net Positions
# -----------------------------------------------------------------------------

class MemberSettlementResponse(BaseModel):
    """Standing of an individual member within household settlement."""
    member_user_id: UUID
    full_name: str
    email: str
    role: str
    total_expenses_paid_paise: int
    total_expenses_paid_decimal: Decimal
    total_contributions_paid_paise: int
    total_contributions_paid_decimal: Decimal
    total_allocated_share_paise: int
    total_allocated_share_decimal: Decimal
    net_position_paise: int
    net_position_decimal: Decimal
    currency: str = "INR"
    status: str  # surplus, deficit, settled


class SettlementRecommendationResponse(BaseModel):
    """Peer-to-peer settlement recommendation."""
    from_member_id: UUID
    from_member_name: str
    to_member_id: UUID
    to_member_name: str
    amount_paise: int
    amount_decimal: Decimal
    currency: str = "INR"
    note: str


class FamilySettlementSummaryResponse(BaseModel):
    """Complete household settlement overview."""
    workspace_id: UUID
    period: Optional[str] = None
    currency: str
    total_shared_expenses_paise: int
    total_shared_expenses_decimal: Decimal
    total_contributions_paid_paise: int
    total_contributions_paid_decimal: Decimal
    total_allocated_paise: int
    total_allocated_decimal: Decimal
    member_settlements: List[MemberSettlementResponse]
    recommendations: List[SettlementRecommendationResponse]


# -----------------------------------------------------------------------------
# Shared Personal Accounts (Privacy Bridge)
# -----------------------------------------------------------------------------

class ShareAccountRequest(BaseModel):
    """Payload to share a member's personal account with the family."""
    account_id: UUID
    share_scope: str = Field(default="balance_only", pattern="^(balance_only|summary_only|full_visibility)$")
    notes: Optional[str] = Field(None, max_length=255)


class SharedAccountResponse(BaseModel):
    """Summary of a personal account selectively shared with the household."""
    id: UUID
    family_workspace_id: UUID
    account_id: UUID
    account_name: str
    account_type: str
    masked_identifier: Optional[str] = None
    shared_by_user_id: UUID
    shared_by_name: Optional[str] = None
    share_scope: str
    current_balance_paise: int
    current_balance_decimal: Decimal
    currency: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Activity & Dashboard Overview
# -----------------------------------------------------------------------------

class FamilyActivityResponse(BaseModel):
    """Timeline entry for family workspace."""
    id: UUID
    workspace_id: UUID
    actor_user_id: Optional[UUID] = None
    actor_name: Optional[str] = None
    activity_type: str
    resource_type: str
    resource_id: str
    title: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FamilyOverviewResponse(BaseModel):
    """Consolidated KPI snapshot for the Family Finance Dashboard."""
    profile: FamilyProfileResponse
    member_count: int
    total_household_income_paise: int
    total_household_income_decimal: Decimal
    total_household_expense_paise: int
    total_household_expense_decimal: Decimal
    net_household_savings_paise: int
    net_household_savings_decimal: Decimal
    shared_account_balances_paise: int
    shared_account_balances_decimal: Decimal
    budget_utilization_pct: Decimal
    active_budgets_count: int
    active_goals_count: int
    upcoming_commitments_count: int
    top_expense_categories: List[Dict[str, Any]] = Field(default_factory=list)
    recent_shared_transactions: List[Dict[str, Any]] = Field(default_factory=list)
