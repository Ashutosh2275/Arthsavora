"""
Arthsavora Test Suite - Workspace Management & Lifecycle (Prompt 07)
Covers Personal workspace uniqueness, Business workspace metadata,
Family workspace boundary initialization, and Archive/Restore lifecycle state transitions.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.infrastructure.database.models import User, UserProfile, Workspace, WorkspaceMember


@pytest.mark.asyncio
async def test_duplicate_personal_workspace_rejected(client: AsyncClient, registered_user: dict):
    """
    BUSINESS RULE CHECK:
    A user can only have ONE personal workspace. Attempting to create a second
    personal workspace must return 409 Conflict.
    """
    payload = {
        "name": "Second Personal Finances",
        "type": "personal",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "country": "IN",
    }
    response = await client.post(
        "/api/v1/workspaces",
        json=payload,
        headers=registered_user["headers"],
    )
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "DUPLICATE_PERSONAL_WORKSPACE"


@pytest.mark.asyncio
async def test_create_family_workspace_success(client: AsyncClient, registered_user: dict):
    """Verifies that a user can create a Family workspace with explicit sharing boundaries."""
    payload = {
        "name": "Mishra Family Household",
        "type": "family",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "country": "IN",
    }
    response = await client.post(
        "/api/v1/workspaces",
        json=payload,
        headers=registered_user["headers"],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "family"
    assert data["name"] == "Mishra Family Household"
    assert data["settings"]["family_settings"]["sharing_mode"] == "explicit"
    assert data["settings"]["family_settings"]["shared_account_ids"] == []


@pytest.mark.asyncio
async def test_create_business_workspace_with_profile_success(
    client: AsyncClient,
    registered_user: dict,
):
    """Verifies creation of a Business workspace with full statutory and profile metadata."""
    payload = {
        "name": "Artha Advisory Services",
        "type": "business",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "country": "IN",
        "business_profile": {
            "legal_business_name": "Artha Advisory Services LLP",
            "trade_name": "Artha Advisory",
            "entity_type": "llp",
            "gstin": "27AAACA1234A1Z5",
            "pan": "AAACA1234A",
            "industry": "Financial Consulting",
            "financial_year_start_month": 4,
        },
    }
    response = await client.post(
        "/api/v1/workspaces",
        json=payload,
        headers=registered_user["headers"],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "business"
    assert "business_profile" in data["settings"]
    profile = data["settings"]["business_profile"]
    assert profile["legal_business_name"] == "Artha Advisory Services LLP"
    assert profile["entity_type"] == "llp"
    assert profile["gstin"] == "27AAACA1234A1Z5"


@pytest.mark.asyncio
async def test_workspace_update_settings_success(
    client: AsyncClient,
    registered_user: dict,
):
    """Verifies owner can update workspace name, timezone, currency, and business profile."""
    # Create business workspace first
    create_payload = {
        "name": "Tech Corp",
        "type": "business",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "country": "IN",
    }
    create_res = await client.post(
        "/api/v1/workspaces",
        json=create_payload,
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    # Update metadata and business profile
    patch_payload = {
        "name": "Tech Corp International",
        "timezone": "UTC",
        "country": "US",
        "default_currency": "USD",
        "business_profile": {
            "legal_business_name": "Tech Corp Worldwide Inc",
            "entity_type": "corporation",
            "tax_identifier": "EIN-98-7654321",
        },
    }
    patch_res = await client.patch(
        f"/api/v1/workspaces/{ws_id}",
        json=patch_payload,
        headers={
            **registered_user["headers"],
            "X-Workspace-ID": ws_id,
        },
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["name"] == "Tech Corp International"
    assert data["timezone"] == "UTC"
    assert data["default_currency"] == "USD"
    assert data["settings"]["business_profile"]["legal_business_name"] == "Tech Corp Worldwide Inc"


@pytest.mark.asyncio
async def test_workspace_lifecycle_archive_and_restore(
    client: AsyncClient,
    registered_user: dict,
):
    """
    LIFECYCLE TRANSITION CHECK:
    Tests ACTIVE -> ARCHIVED -> ACTIVE state transitions and state validation enforcement.
    """
    create_payload = {
        "name": "Project Alpha",
        "type": "business",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "country": "IN",
    }
    create_res = await client.post(
        "/api/v1/workspaces",
        json=create_payload,
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    # 1. Archive the workspace
    archive_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/archive",
        headers={
            **registered_user["headers"],
            "X-Workspace-ID": ws_id,
        },
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "archived"

    # 2. Attempt to archive already archived workspace -> must fail validation
    re_archive_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/archive",
        headers={
            **registered_user["headers"],
            "X-Workspace-ID": ws_id,
        },
    )
    assert re_archive_res.status_code == 422
    assert re_archive_res.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # 3. Restore the workspace back to ACTIVE
    restore_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/restore",
        headers={
            **registered_user["headers"],
            "X-Workspace-ID": ws_id,
        },
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "active"

    # 4. Attempt to restore an already active workspace -> must fail validation
    re_restore_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/restore",
        headers={
            **registered_user["headers"],
            "X-Workspace-ID": ws_id,
        },
    )
    assert re_restore_res.status_code == 422
    assert re_restore_res.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
