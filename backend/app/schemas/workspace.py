"""
Arthsavora Workspace & Identity Schemas
Request and response models for multi-tenant workspace management, business profiles,
membership roles, invitations, and controlled ownership transfers.
"""

from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from app.infrastructure.database.models.workspace import WorkspaceRole, WorkspaceType


class BusinessProfileSchema(BaseModel):
    """Business entity profile and contact metadata."""
    legal_business_name: Optional[str] = Field(None, max_length=255, description="Legal registered business name")
    trade_name: Optional[str] = Field(None, max_length=255, description="Trade or brand name")
    business_name: Optional[str] = Field(None, max_length=255, description="Registered or trade business name")
    entity_type: Optional[str] = Field(None, max_length=50, description="Legal entity type (e.g. sole_proprietorship, llp, pvt_ltd)")
    business_type: Optional[str] = Field(None, max_length=50, description="Business category")
    industry: Optional[str] = Field(None, max_length=100, description="Industry sector")
    tax_identifier: Optional[str] = Field(None, max_length=50, description="Statutory tax identifier or EIN")
    financial_year_start_month: Optional[int] = Field(4, ge=1, le=12, description="Start month of financial year (default 4 for India)")
    business_email: Optional[EmailStr] = Field(None, description="Official business contact email")
    contact_number: Optional[str] = Field(None, max_length=20, description="Primary contact telephone number")
    address: Optional[dict] = Field(default_factory=dict, description="Business address fields")
    gstin: Optional[str] = Field(None, max_length=15, description="Optional GST Identification Number")
    pan: Optional[str] = Field(None, max_length=10, description="Optional Permanent Account Number")
    profile_status: str = Field("active", description="Status of the business registration profile")


class WorkspaceCreateRequest(BaseModel):
    """Payload for provisioning a new workspace."""
    name: str = Field(..., min_length=2, max_length=128, description="Human-readable workspace title")
    type: WorkspaceType = Field(default=WorkspaceType.PERSONAL, description="Workspace tenancy model")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="Base ISO currency")
    timezone: str = Field(default="Asia/Kolkata", max_length=64, description="IANA Timezone string")
    country: str = Field(default="IN", min_length=2, max_length=2, description="Country ISO 3166-1 alpha-2 code")
    business_profile: Optional[BusinessProfileSchema] = Field(None, description="Optional business profile metadata")


class WorkspaceUpdateRequest(BaseModel):
    """Payload for modifying workspace settings and profile."""
    name: Optional[str] = Field(None, min_length=2, max_length=128, description="Updated workspace title")
    timezone: Optional[str] = Field(None, max_length=64, description="Updated IANA timezone")
    default_currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Base ISO currency")
    country: Optional[str] = Field(None, min_length=2, max_length=2, description="Country code")
    business_profile: Optional[BusinessProfileSchema] = Field(None, description="Updated business profile")


class WorkspaceResponse(BaseModel):
    """Public workspace representation."""
    id: uuid.UUID
    name: str
    slug: str
    type: WorkspaceType
    owner_id: uuid.UUID
    currency: str
    default_currency: Optional[str] = None
    timezone: str
    country: str = "IN"
    status: str
    settings: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_default_currency(self):
        if not self.default_currency:
            self.default_currency = self.currency
        return self


class WorkspaceMemberResponse(BaseModel):
    """Membership record reflecting user's role in a workspace."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    status: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddMemberRequest(BaseModel):
    """Direct membership payload (for immediate attachments)."""
    email: EmailStr = Field(..., description="Email address of the registered user to grant access")
    role: WorkspaceRole = Field(default=WorkspaceRole.MEMBER, description="Assigned workspace role")


class UpdateMemberRoleRequest(BaseModel):
    """Payload for updating an existing member's role."""
    role: str = Field(..., description="Target role: owner, admin, member, viewer, accountant, approver, staff")


class OwnershipTransferRequest(BaseModel):
    """Payload for controlled, atomic workspace ownership transfer."""
    new_owner_id: uuid.UUID = Field(..., description="Active workspace member ID designated as the new owner")
    previous_owner_role: str = Field("admin", description="Role assigned to previous owner post-transfer")
    confirm: bool = Field(..., description="Explicit confirmation boolean required to execute ownership transfer")


class CreateInvitationRequest(BaseModel):
    """Payload for issuing a cryptographically signed workspace invitation."""
    email: EmailStr = Field(..., description="Target recipient email address")
    role: str = Field(default="member", description="Assigned role upon acceptance")


class InvitationResponse(BaseModel):
    """Public representation of a workspace invitation."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    role: str
    invited_by_id: uuid.UUID
    status: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime
    invitation_token: Optional[str] = Field(None, description="Raw invitation token (returned ONLY upon initial creation)")

    model_config = ConfigDict(from_attributes=True)
