"""
Arthsavora V1 Workspace & Tenancy Endpoints
Manages personal, family, and business workspaces, tenancy boundaries, and member roles.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import (
    get_current_user,
    get_current_workspace_context,
    require_role,
)
from app.core.permissions import WorkspaceContext
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.workspace import WorkspaceRole
from app.infrastructure.database.session import get_db_session
from app.schemas.workspace import (
    AddMemberRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["Workspaces & Multi-Tenancy"])


@router.get(
    "/",
    response_model=List[WorkspaceResponse],
    summary="List all accessible workspaces for current user",
)
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Returns all active workspaces the authenticated user belongs to."""
    workspaces = await WorkspaceService.list_user_workspaces(session, current_user.id)
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post(
    "/",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    data: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Provisions a new workspace (Personal, Family, or Business) and designates the user as Owner."""
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
    Guaranteed to return 404 if the user is not a member to avoid cross-tenant enumeration.
    """
    return WorkspaceResponse.model_validate(context.workspace)


@router.get(
    "/{workspace_id}/members",
    response_model=List[WorkspaceMemberResponse],
    summary="List members of a workspace",
)
async def list_workspace_members(
    context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Lists all active members in the specified workspace."""
    members = await WorkspaceService.list_members(session, context.workspace.id)
    return [WorkspaceMemberResponse.model_validate(m) for m in members]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or invite a member to the workspace",
)
async def add_workspace_member(
    data: AddMemberRequest,
    context: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Grants a registered user access to the workspace.
    Enforces that only OWNER or ADMIN roles may invite new members.
    """
    member = await WorkspaceService.add_member(
        session,
        context.workspace.id,
        context.current_user.id,
        data,
    )
    return WorkspaceMemberResponse.model_validate(member)
