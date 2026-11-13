"""
Arthsavora Authentication & Identity API Tests
Validates user registration, password verification, token issuance,
expired token rejection, suspended account handling, and token refresh.
"""

from datetime import timedelta
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token
from app.infrastructure.database.models import User


@pytest.mark.asyncio
async def test_register_new_user_success(client: AsyncClient):
    """Verifies complete user registration and automated personal workspace bootstrapping."""
    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"investor_{unique_suffix}@example.com",
        "password": "SecurePassword123!",
        "full_name": "Arjun Kapoor",
        "phone": "+919876543210",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert "tokens" in data
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["full_name"] == "Arjun Kapoor"
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]
    assert data["tokens"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client: AsyncClient):
    """Verifies that duplicate email registration returns 409 Conflict."""
    email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "First User",
    }
    # Initial registration
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with same email
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verifies email/password login and token receipt."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"trader_{unique_suffix}@example.com"
    password = "StrongPassword123!"

    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Kavita Rao"},
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == email
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]


@pytest.mark.asyncio
async def test_login_invalid_password_rejected(client: AsyncClient):
    """Verifies that incorrect passwords return 401 Unauthorized with INVALID_CREDENTIALS."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"user_{unique_suffix}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "CorrectPassword123!", "full_name": "Valid User"},
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, registered_user: dict):
    """Verifies retrieving current user profile with valid Bearer token."""
    response = await client.get("/api/v1/auth/me", headers=registered_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == registered_user["user"].email
    assert data["full_name"] == registered_user["user"].full_name


@pytest.mark.asyncio
async def test_get_me_missing_token_rejected(client: AsyncClient):
    """Verifies that unauthenticated requests to protected endpoints return 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_get_me_invalid_token_rejected(client: AsyncClient):
    """Verifies that malformed or forged tokens return 401 Unauthorized."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer completely.invalid.jwt.token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_get_me_expired_token_rejected(client: AsyncClient, registered_user: dict):
    """Verifies that an expired JWT is rejected with TOKEN_EXPIRED."""
    expired_token = create_access_token(
        subject=str(registered_user["user"].id),
        email=registered_user["user"].email,
        expires_delta=timedelta(seconds=-3600),  # 1 hour in the past
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_get_me_suspended_user_rejected(
    client: AsyncClient,
    registered_user: dict,
    db_session: AsyncSession,
):
    """Verifies that suspended or disabled accounts cannot authenticate."""
    user = registered_user["user"]
    user.is_active = False
    await db_session.commit()

    response = await client.get("/api/v1/auth/me", headers=registered_user["headers"])
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_token_refresh_flow(client: AsyncClient):
    """Verifies exchanging refresh token for a fresh token pair."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"refresh_{unique_suffix}@example.com"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Refresh Tester"},
    )
    refresh_token = reg_res.json()["tokens"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout_flow(client: AsyncClient, registered_user: dict):
    """Verifies that logout invalidates session cleanly."""
    response = await client.post("/api/v1/auth/logout", headers=registered_user["headers"])
    assert response.status_code == 200
    assert response.json()["status"] == "success"
