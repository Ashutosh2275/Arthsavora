"""
Arthsavora Authentication Application Service
Handles user registration, credential validation, token minting, and workspace bootstrapping.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    AccountDeletedException,
    AccountDisabledException,
    ConflictException,
    InvalidTokenException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.infrastructure.database.models.user import User, UserProfile
from app.infrastructure.database.models.workspace import (
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceType,
)
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest


class AuthService:
    """Service orchestrating identity and authentication workflows."""

    @staticmethod
    async def register_user(
        session: AsyncSession,
        data: UserRegisterRequest,
    ) -> tuple[User, TokenResponse]:
        """
        Registers a new user in PostgreSQL, initializes default profile preferences,
        and provisions their initial personal workspace.
        """
        # 1. Check for existing email
        stmt = select(User).where(User.email == data.email.lower().strip())
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictException(
                message="An account with this email address already exists.",
                code="EMAIL_ALREADY_REGISTERED",
            )

        # 2. Provision User record
        user = User(
            email=data.email.lower().strip(),
            full_name=data.full_name.strip(),
            hashed_password=get_password_hash(data.password),
            phone_number=data.phone,
            auth_provider="local",
            is_active=True,
            is_verified=False,
        )
        session.add(user)
        await session.flush()  # Generates user.id

        # 3. Provision User Profile
        profile = UserProfile(
            user_id=user.id,
            default_currency="INR",
            timezone="Asia/Kolkata",
            locale="en-IN",
            theme="dark",
            notification_preferences={
                "email": True,
                "sms": False,
                "whatsapp": False,
            },
        )
        session.add(profile)

        # 4. Provision Default Personal Workspace
        workspace = Workspace(
            name=f"{user.full_name}'s Finances",
            slug=f"personal-{user.id.hex[:8]}",
            type=WorkspaceType.PERSONAL,
            owner_id=user.id,
            default_currency="INR",
            timezone="Asia/Kolkata",
            settings={"is_default": True},
        )
        session.add(workspace)
        await session.flush()

        # 5. Assign User as Workspace Owner
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.OWNER,
            status="active",
        )
        session.add(membership)
        await session.commit()

        # 6. Re-query user with profile loaded
        user_stmt = select(User).options(selectinload(User.profile)).where(User.id == user.id)
        user_result = await session.execute(user_stmt)
        refreshed_user = user_result.scalar_one()

        # 7. Mint initial token pair
        tokens = AuthService.create_token_pair(refreshed_user)
        return refreshed_user, tokens

    @staticmethod
    async def authenticate_user(
        session: AsyncSession,
        data: UserLoginRequest,
    ) -> tuple[User, TokenResponse]:
        """Validates credentials and returns authenticated user and token pair."""
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == data.email.lower().strip())
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.hashed_password:
            raise UnauthorizedException(
                message="Invalid email or password.",
                code="INVALID_CREDENTIALS",
            )

        if not verify_password(data.password, user.hashed_password):
            raise UnauthorizedException(
                message="Invalid email or password.",
                code="INVALID_CREDENTIALS",
            )

        if user.is_deleted or user.deleted_at is not None:
            raise AccountDeletedException()

        if not user.is_active:
            raise AccountDisabledException()

        # Record successful login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        await session.commit()

        tokens = AuthService.create_token_pair(user)
        return user, tokens

    @staticmethod
    async def refresh_tokens(
        session: AsyncSession,
        refresh_token_str: str,
    ) -> TokenResponse:
        """Validates refresh token and issues a fresh token pair."""
        payload = decode_token(refresh_token_str, expected_type="refresh")
        sub = payload.get("sub")

        stmt = select(User).where(User.id == uuid.UUID(str(sub)))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or user.is_deleted or not user.is_active:
            raise InvalidTokenException("Invalid refresh token or inactive user.")

        return AuthService.create_token_pair(user)

    @staticmethod
    def create_token_pair(user: User) -> TokenResponse:
        """Generates access and refresh tokens for an authorized user."""
        access_token = create_access_token(
            subject=str(user.id),
            email=user.email,
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            email=user.email,
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
