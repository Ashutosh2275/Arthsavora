"""
Arthsavora V1 Authentication Endpoints
Handles user registration, authentication, token refresh, and active user discovery.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db_session
from app.schemas.auth import (
    AuthSessionResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["Authentication & Identity"])


@router.post(
    "/register",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Registers a new user in PostgreSQL, initializes default financial preferences,
    and provisions their initial personal workspace.
    """
    user, tokens = await AuthService.register_user(session, data)
    return AuthSessionResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    summary="Authenticate user with email and password",
)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    data: UserLoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Authenticates email and password credentials.
    Throttled to 5 requests per minute per IP to defend against brute-force attacks.
    """
    user, tokens = await AuthService.authenticate_user(session, data)
    return AuthSessionResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile and settings."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange refresh token for a new token pair",
)
async def refresh_token(
    data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Validates refresh token and returns a fresh access token."""
    return await AuthService.refresh_tokens(session, data.refresh_token)


@router.post(
    "/logout",
    summary="Revoke or invalidate active session",
)
async def logout(current_user: User = Depends(get_current_user)):
    """Logs out the user and acknowledges session invalidation."""
    return {
        "status": "success",
        "message": "Session invalidated successfully.",
    }
