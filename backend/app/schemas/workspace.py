"""
Arthsavora Workspace Schemas
Request and response models for multi-tenant workspace management and membership.
"""

from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.infrastructure.database.models.workspace import WorkspaceRole, WorkspaceType


class WorkspaceCreateRequest(BaseModel):
    """Payload for provisioning a new workspace."""
    name: str = Field(..., min_length=2, max_length=128, description="Human-readable workspace title")
    type: WorkspaceType = Field(default=WorkspaceType.PERSONAL, description="Workspace tenancy model")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="Base ISO currency")
    timezone: str = Field(default="Asia/Kolkata", max_length=64, description="IANA Timezone string")


class WorkspaceResponse(BaseModel):
    """Public workspace representation."""
    id: uuid.UUID
    name: str
    slug: str
    type: WorkspaceType
    owner_id: uuid.UUID
    currency: str
    timezone: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberResponse(BaseModel):
    """Membership record reflecting user's role in a workspace."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: WorkspaceRole
    status: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddMemberRequest(BaseModel):
    """Payload to invite or attach a user to a workspace."""
    email: EmailStr = Field(..., description="Email address of the user to grant access")
    role: WorkspaceRole = Field(default=WorkspaceRole.MEMBER, description="Assigned workspace role")
