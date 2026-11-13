"""
Arthsavora V1 User Identity & Profile Endpoints
Manages profile preferences, display names, locale, currency, and safe account deactivation.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationException
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db_session
from app.schemas.user import DeactivateAccountRequest, UserDetailResponse, UserProfileUpdateRequest
from app.services.user_service import UserService

router = APIRouter(tags=["User Profiles & Identity"])


@router.get(
    "/me",
    response_model=UserDetailResponse,
    summary="Get current user profile and settings",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves full profile details, financial preferences, and completion status."""
    user = await UserService.get_user_profile(session, current_user.id)
    return UserDetailResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserDetailResponse,
    summary="Update current user profile and preferences",
)
async def update_my_profile(
    data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Updates profile display name, avatar, preferred currency, timezone, and locale.
    Rejects unauthorized modifications to server-controlled identity fields.
    """
    user = await UserService.update_user_profile(session, current_user.id, data)
    return UserDetailResponse.model_validate(user)


@router.post(
    "/me/deactivate",
    status_code=status.HTTP_200_OK,
    summary="Deactivate user account",
)
async def deactivate_account(
    data: DeactivateAccountRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Safely marks account as inactive and terminates active sessions."""
    if not data.confirm:
        raise ValidationException(
            message="Account deactivation requires explicit confirmation.",
            field="confirm",
        )
    await UserService.deactivate_account(session, current_user.id)
    return {
        "status": "success",
        "message": "Account has been safely deactivated.",
    }
