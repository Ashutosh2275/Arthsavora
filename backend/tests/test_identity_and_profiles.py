"""
Arthsavora Test Suite - Identity and User Profiles (Prompt 07)
Covers user profile retrieval, profile updates, account deactivation,
and external auth provider identity mapping uniqueness.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.models.user import User, UserProfile
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_get_user_me_profile_success(client: AsyncClient, registered_user: dict):
    """Verifies that an authenticated user can fetch their complete identity and profile."""
    response = await client.get(
        "/api/v1/users/me",
        headers=registered_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(registered_user["user"].id)
    assert data["email"] == registered_user["user"].email
    assert data["full_name"] == "Test Investor"
    assert data["is_active"] is True
    assert "profile" in data
    assert data["profile"]["default_currency"] == "INR"
    assert data["profile"]["timezone"] == "Asia/Kolkata"
    assert data["profile"]["locale"] == "en-IN"


@pytest.mark.asyncio
async def test_get_user_me_unauthenticated_rejected(client: AsyncClient):
    """Verifies that unauthenticated requests to /users/me are rejected with 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_me_profile_success(client: AsyncClient, registered_user: dict):
    """Verifies that an authenticated user can update their display name, currency, and locale."""
    update_payload = {
        "full_name": "Senior Investor",
        "display_name": "FintechGuru",
        "default_currency": "USD",
        "timezone": "America/New_York",
        "locale": "en-US",
        "preferred_language": "en",
        "country": "US",
    }
    response = await client.patch(
        "/api/v1/users/me",
        json=update_payload,
        headers=registered_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Senior Investor"
    assert data["profile"]["display_name"] == "FintechGuru"
    assert data["profile"]["default_currency"] == "USD"
    assert data["profile"]["timezone"] == "America/New_York"
    assert data["profile"]["locale"] == "en-US"
    assert data["profile"]["country"] == "US"
    assert data["profile"]["is_profile_complete"] is True

    # Confirm persistence with GET
    get_res = await client.get("/api/v1/users/me", headers=registered_user["headers"])
    assert get_res.status_code == 200
    assert get_res.json()["profile"]["display_name"] == "FintechGuru"


@pytest.mark.asyncio
async def test_deactivate_user_me_flow(client: AsyncClient, registered_user: dict):
    """Verifies that a user can self-deactivate their account and subsequent access is denied."""
    # Attempt deactivation without explicit confirmation -> must fail
    fail_res = await client.post(
        "/api/v1/users/me/deactivate",
        json={"confirm": False},
        headers=registered_user["headers"],
    )
    assert fail_res.status_code == 422

    # Successful deactivation with confirmation
    deactivate_res = await client.post(
        "/api/v1/users/me/deactivate",
        json={"confirm": True},
        headers=registered_user["headers"],
    )
    assert deactivate_res.status_code == 200
    assert "deactivated" in deactivate_res.json()["message"].lower()

    # Subsequent request using the deactivated user's token must be rejected
    subsequent_res = await client.get(
        "/api/v1/users/me",
        headers=registered_user["headers"],
    )
    assert subsequent_res.status_code == 401


@pytest.mark.asyncio
async def test_auth_provider_id_uniqueness(db_session: AsyncSession):
    """
    CRITICAL IDENTITY INTEGRITY CHECK:
    Verifies that duplicate external auth provider identities (e.g., google sub ID)
    are strictly prohibited by database constraint uq_user_auth_provider_id.
    """
    provider = "google"
    provider_id = f"oauth_sub_{uuid.uuid4().hex[:12]}"

    user1 = User(
        email=f"oauth1_{uuid.uuid4().hex[:6]}@example.com",
        full_name="OAuth User One",
        hashed_password=get_password_hash("Pass123!"),
        auth_provider=provider,
        auth_provider_id=provider_id,
        is_active=True,
    )
    db_session.add(user1)
    await db_session.flush()

    user2 = User(
        email=f"oauth2_{uuid.uuid4().hex[:6]}@example.com",
        full_name="OAuth User Two",
        hashed_password=get_password_hash("Pass123!"),
        auth_provider=provider,
        auth_provider_id=provider_id,
        is_active=True,
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
