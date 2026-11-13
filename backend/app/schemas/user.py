"""
Arthsavora User Profile Schemas
Request and response contracts for user identity preferences, locale, and display settings.
"""

from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpdateRequest(BaseModel):
    """Payload for updating user profile attributes and settings."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=128, description="User's full name")
    display_name: Optional[str] = Field(None, max_length=255, description="Preferred display/nickname")
    avatar_url: Optional[str] = Field(None, max_length=1024, description="Profile avatar image URL")
    preferred_language: Optional[str] = Field(None, min_length=2, max_length=10, description="Language code (e.g. en-IN, hi-IN)")
    locale: Optional[str] = Field(None, min_length=2, max_length=20, description="Locale identifier (e.g. en-IN)")
    default_currency: Optional[str] = Field(None, min_length=3, max_length=3, description="ISO 4217 currency code")
    timezone: Optional[str] = Field(None, max_length=50, description="IANA timezone (e.g. Asia/Kolkata)")
    country: Optional[str] = Field(None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    theme: Optional[str] = Field(None, max_length=20, description="UI theme preference ('dark', 'light', 'system')")
    notification_preferences: Optional[dict] = Field(None, description="Granular alert preferences")


class DeactivateAccountRequest(BaseModel):
    """Payload for confirming account self-deactivation."""
    confirm: bool = Field(..., description="Explicit confirmation boolean required to deactivate account")


class UserProfileResponse(BaseModel):
    """Public representation of user preferences and configuration."""
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferred_language: str = "en-IN"
    default_currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    country: str = "IN"
    locale: str = "en-IN"
    theme: str = "dark"
    notification_preferences: dict = Field(default_factory=dict)
    is_profile_complete: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """Full authenticated user identity contract."""
    id: uuid.UUID
    email: str
    full_name: str
    phone_number: Optional[str] = None
    auth_provider: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)
