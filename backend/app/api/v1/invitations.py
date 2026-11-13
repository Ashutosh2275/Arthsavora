"""
Arthsavora V1 Public/Authenticated Invitation Endpoints
Handles cryptographic token verification and atomic workspace invitation acceptance.
"""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db_session
from app.schemas.workspace import WorkspaceMemberResponse
from app.services.invitation_service import InvitationService

router = APIRouter(tags=["Workspace Invitations"])


@router.post(
    "/{token}/accept",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept a workspace invitation using raw token",
)
async def accept_invitation(
    token: str = Path(..., description="Raw cryptographically secure invitation token"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Validates token SHA-256 hash, acquires row-level lock, checks expiry and recipient email binding,
    and grants the authenticated user membership in the workspace.
    """
    membership = await InvitationService.accept_invitation(session, token, current_user)
    return WorkspaceMemberResponse(
        id=membership.id,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=membership.role,
        status=membership.status,
        joined_at=membership.joined_at,
    )
