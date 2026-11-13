"""
Arthsavora Authentication & Identity Schemas
Request and response models for user registration, authentication, tokens, and profiles.
"""

from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user."""
    email: EmailStr = Field(..., description="User's primary email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (minimum 8 characters)")
    full_name: str = Field(..., min_length=2, max_length=128, description="User's full name")
    phone: Optional[str] = Field(None, max_length=20, description="Optional phone number (with country code)")


class UserLoginRequest(BaseModel):
    """Payload for local password authentication."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class TokenResponse(BaseModel):
    """Token issuance payload containing signed JWTs and lifetime metadata."""
    access_token: str = Field(..., description="Short-lived Bearer access token")
    refresh_token: str = Field(..., description="Long-lived refresh token")
    token_type: str = Field("bearer", description="Token schema (Bearer)")
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class RefreshTokenRequest(BaseModel):
    """Payload for renewing an access token using a refresh token."""
    refresh_token: str = Field(..., description="Valid long-lived refresh token")


class UserProfileResponse(BaseModel):
    """User preferences and configuration."""
    default_currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    locale: str = "en-IN"
    theme: str = "dark"
    notification_preferences: Optional[dict] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Public user identity model."""
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)


class AuthSessionResponse(BaseModel):
    """Combined response returning user details and issued tokens on login/registration."""
    user: UserResponse
    tokens: TokenResponse
