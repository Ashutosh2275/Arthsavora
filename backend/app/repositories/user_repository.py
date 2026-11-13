"""
Arthsavora User & Profile Repository
Data access layer for user identity, authentication mapping, and profile settings.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.infrastructure.database.models.user import User, UserProfile
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling User and UserProfile persistence and query operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_id_with_profile(self, user_id: uuid.UUID) -> Optional[User]:
        """Retrieves user with joined profile."""
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == user_id, User.is_deleted == False)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieves user by case-insensitive email."""
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == email.lower().strip(), User.is_deleted == False)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_auth_provider(
        self,
        auth_provider: str,
        auth_provider_id: str,
    ) -> Optional[User]:
        """Retrieves user by delegated OAuth or external auth provider ID."""
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(
                User.auth_provider == auth_provider,
                User.auth_provider_id == auth_provider_id,
                User.is_deleted == False,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_profile(self, user_id: uuid.UUID) -> Optional[UserProfile]:
        """Retrieves user profile preferences."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def update_profile(
        self,
        profile: UserProfile,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        preferred_language: Optional[str] = None,
        locale: Optional[str] = None,
        default_currency: Optional[str] = None,
        timezone_val: Optional[str] = None,
        country: Optional[str] = None,
        theme: Optional[str] = None,
        notification_preferences: Optional[dict] = None,
    ) -> UserProfile:
        """Applies validated updates to UserProfile."""
        if display_name is not None:
            profile.display_name = display_name.strip() or None
        if avatar_url is not None:
            profile.avatar_url = avatar_url.strip() or None
        if preferred_language is not None:
            profile.preferred_language = preferred_language.strip()
        if locale is not None:
            profile.locale = locale.strip()
        elif preferred_language is not None and not profile.locale:
            profile.locale = preferred_language.strip()
        if default_currency is not None:
            profile.default_currency = default_currency.upper().strip()
        if timezone_val is not None:
            profile.timezone = timezone_val.strip()
        if country is not None:
            profile.country = country.upper().strip()
        if theme is not None:
            profile.theme = theme.strip()
        if notification_preferences is not None:
            profile.notification_preferences = notification_preferences

        # Evaluate profile completion status
        profile.is_profile_complete = bool(
            profile.display_name and profile.timezone and profile.default_currency
        )
        return profile
