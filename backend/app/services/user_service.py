"""
Arthsavora User Profile Application Service
Orchestrates profile discovery, preference updates, and safe account deactivation.
"""

from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ValidationException
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileUpdateRequest


class UserService:
    """Service orchestrating user profile preferences and identity lifecycle."""

    @staticmethod
    async def get_user_profile(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> User:
        """Retrieves user with loaded profile. Returns 404 if deleted or not found."""
        repo = UserRepository(session)
        user = await repo.get_by_id_with_profile(user_id)
        if not user:
            raise NotFoundException(message="User profile not found.")
        return user

    @staticmethod
    async def update_user_profile(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: UserProfileUpdateRequest,
    ) -> User:
        """
        Updates user profile attributes, locale, currency, and display settings.
        Rejects modifications to system-controlled identity attributes (email, provider, active status).
        """
        repo = UserRepository(session)
        user = await repo.get_by_id_with_profile(user_id)
        if not user:
            raise NotFoundException(message="User not found.")

        # Update full_name on User model if provided
        if data.full_name is not None:
            clean_name = data.full_name.strip()
            if not clean_name:
                raise ValidationException(message="Full name cannot be empty.", field="full_name")
            user.full_name = clean_name

        # Ensure user has profile initialized
        if not user.profile:
            from app.infrastructure.database.models.user import UserProfile
            user.profile = UserProfile(user_id=user.id)
            session.add(user.profile)
            await session.flush()

        # Update profile attributes through repository
        repo.update_profile(
            profile=user.profile,
            display_name=data.display_name,
            avatar_url=data.avatar_url,
            preferred_language=data.preferred_language,
            locale=data.locale,
            default_currency=data.default_currency,
            timezone_val=data.timezone,
            country=data.country,
            theme=data.theme,
            notification_preferences=data.notification_preferences,
        )

        # Audit log entry for profile update
        audit = AuditLog(
            actor_id=user.id,
            action="user:update_profile",
            entity_type="user_profile",
            entity_id=user.profile.id,
            after_state={
                "full_name": user.full_name,
                "display_name": user.profile.display_name,
                "default_currency": user.profile.default_currency,
                "timezone": user.profile.timezone,
                "country": user.profile.country,
                "locale": user.profile.locale,
            },
        )
        session.add(audit)

        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def deactivate_account(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        """Safely deactivates user account without hard deleting financial history."""
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="User not found.")

        user.is_active = False

        audit = AuditLog(
            actor_id=user.id,
            action="user:deactivate",
            entity_type="user",
            entity_id=user.id,
            after_state={"is_active": False},
        )
        session.add(audit)
        await session.commit()
