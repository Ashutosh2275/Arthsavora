"""
Arthsavora V1 Workspace & Tenancy Endpoints
Manages personal, family, and business workspaces, lifecycle transitions,
centralized permission checks, member roles, invitations, and controlled ownership transfers.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import (
    get_current_user,
    get_current_workspace_context,
    require_permission,
    require_role,
)
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import WorkspaceRole
from app.infrastructure.database.session import get_db_session
from app.schemas.workspace import (
    AddMemberRequest,
    CreateInvitationRequest,
    InvitationResponse,
    OwnershipTransferRequest,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from app.services.invitation_service import InvitationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["Workspaces & Multi-Tenancy"])


# ---------------------------------------------------------------------------
# Workspace CRUD & Lifecycle
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    summary="List all accessible workspaces for current user",
)
@router.get(
    "/",
    response_model=List[WorkspaceResponse],
    include_in_schema=False,
)
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Returns all active workspaces the authenticated user belongs to."""
    workspaces = await WorkspaceService.list_user_workspaces(session, current_user.id)
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
@router.post(
    "/",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_workspace(
    data: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Provisions a new workspace (Personal, Family, or Business) and designates the user as Owner.
    Enforces personal workspace uniqueness, business profile capture, and family isolation boundaries.
    """
    workspace = await WorkspaceService.create_workspace(session, current_user.id, data)
    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace details by ID",
)
async def get_workspace(
    context: WorkspaceContext = Depends(get_current_workspace_context),
):
    """
    Retrieves workspace details.
    Guaranteed to return 404 if the user is not an active member to avoid cross-tenant enumeration.
    """
    return WorkspaceResponse.model_validate(context.workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update workspace settings and profile",
)
async def update_workspace(
    data: WorkspaceUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.UPDATE_WORKSPACE)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates workspace title, default currency, timezone, country, and business profile."""
    workspace = await WorkspaceService.update_workspace(session, context, data)
    return WorkspaceResponse.model_validate(workspace)


@router.post(
    "/{workspace_id}/archive",
    response_model=WorkspaceResponse,
    summary="Archive workspace (sets to read-only)",
)
async def archive_workspace(
    context: WorkspaceContext = Depends(require_permission(Permission.ARCHIVE_WORKSPACE)),
    session: AsyncSession = Depends(get_db_session),
):
    """Places active workspace into read-only ARCHIVED state. Financial mutations are prohibited."""
    workspace = await WorkspaceService.archive_workspace(session, context)
    return WorkspaceResponse.model_validate(workspace)


@router.post(
    "/{workspace_id}/restore",
    response_model=WorkspaceResponse,
    summary="Restore archived workspace back to active status",
)
async def restore_workspace(
    context: WorkspaceContext = Depends(require_permission(Permission.RESTORE_WORKSPACE)),
    session: AsyncSession = Depends(get_db_session),
):
    """Restores ARCHIVED workspace back to ACTIVE status."""
    workspace = await WorkspaceService.restore_workspace(session, context)
    return WorkspaceResponse.model_validate(workspace)


@router.post(
    "/{workspace_id}/ownership-transfer",
    response_model=WorkspaceResponse,
    summary="Transfer workspace ownership to another active member",
)
async def transfer_ownership(
    data: OwnershipTransferRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.TRANSFER_OWNERSHIP)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Controlled, atomic ownership transfer.
    Designates a target active member as OWNER, and updates previous owner to specified role.
    """
    workspace = await WorkspaceService.transfer_ownership(session, context, data)
    return WorkspaceResponse.model_validate(workspace)


# ---------------------------------------------------------------------------
# Membership Management
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/members",
    response_model=List[WorkspaceMemberResponse],
    summary="List members of a workspace",
)
async def list_workspace_members(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_MEMBERS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Lists all active members in the specified workspace with profile information."""
    members = await WorkspaceService.list_members(session, context.workspace.id)
    return [WorkspaceMemberResponse.model_validate(m) for m in members]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an existing registered user directly to the workspace",
)
async def add_workspace_member(
    data: AddMemberRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Directly attaches a registered user to the workspace. Requires INVITE_MEMBERS permission."""
    member = await WorkspaceService.add_member(
        session,
        context.workspace.id,
        context.current_user.id,
        data,
    )
    return WorkspaceMemberResponse.model_validate(member)


@router.patch(
    "/{workspace_id}/members/{membership_id}",
    response_model=WorkspaceMemberResponse,
    summary="Update a workspace member's role",
)
async def update_member_role(
    membership_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.UPDATE_MEMBER_ROLE)),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates a member's role with strict hierarchy validation. Prohibits demoting the owner."""
    member = await WorkspaceService.update_member_role(session, context, membership_id, data)
    return WorkspaceMemberResponse.model_validate(member)


@router.delete(
    "/{workspace_id}/members/{membership_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove or revoke a workspace member",
)
async def remove_workspace_member(
    membership_id: uuid.UUID,
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Revokes access immediately. Requires REMOVE_MEMBERS permission or self-removal.
    Prohibits removing the owner. Historical transactions retain actor attribution.
    """
    await WorkspaceService.remove_member(session, context, membership_id)
    return {
        "status": "success",
        "message": "Workspace membership revoked successfully.",
    }


# ---------------------------------------------------------------------------
# Cryptographic Workspace Invitations
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a cryptographically signed workspace invitation",
)
async def create_invitation(
    data: CreateInvitationRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Generates a secure 32-byte invitation token, stores only its SHA-256 hash,
    and returns the one-time raw token to the caller for delivery.
    """
    invitation, raw_token = await InvitationService.create_invitation(session, context, data)
    response_data = InvitationResponse.model_validate(invitation)
    response_data.invitation_token = raw_token
    return response_data


@router.get(
    "/{workspace_id}/invitations",
    response_model=List[InvitationResponse],
    summary="List workspace invitations",
)
async def list_invitations(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status ('pending', 'accepted', 'revoked', 'expired')"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_MEMBERS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Lists invitations for the active workspace. Never exposes raw tokens."""
    invitations = await InvitationService.list_invitations(session, context, status=status_filter)
    return [InvitationResponse.model_validate(i) for i in invitations]


@router.post(
    "/{workspace_id}/invitations/{invitation_id}/revoke",
    response_model=InvitationResponse,
    summary="Revoke a pending workspace invitation",
)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Revokes a pending invitation so it can no longer be accepted."""
    invitation = await InvitationService.revoke_invitation(session, context, invitation_id)
    return InvitationResponse.model_validate(invitation)
