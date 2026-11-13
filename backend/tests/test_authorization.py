"""
Arthsavora Multi-Tenancy & Authorization Tests
Validates server-side workspace resolution, Role-Based Access Control (RBAC),
IDOR cross-tenant isolation, and privilege escalation prevention.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token, get_password_hash
from app.infrastructure.database.models import User, UserProfile, Workspace, WorkspaceMember


@pytest.fixture
async def second_user(db_session: AsyncSession) -> dict:
    """Provisions a second independent user for multi-tenant isolation testing."""
    user_id = uuid.uuid4()
    email = f"second_user_{user_id.hex[:8]}@example.com"
    user = User(
        id=user_id,
        email=email,
        full_name="Second Independent User",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        name="Second User Workspace",
        slug=f"second-ws-{user_id.hex[:8]}",
        type="personal",
        owner_id=user.id,
        default_currency="INR",
        timezone="Asia/Kolkata",
        status="active",
    )
    db_session.add(workspace)
    await db_session.flush()

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    db_session.add(membership)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), email=user.email)
    return {
        "user": user,
        "workspace": workspace,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.mark.asyncio
async def test_list_workspaces_for_user(client: AsyncClient, registered_user: dict):
    """Verifies user can view all workspaces they actively belong to."""
    response = await client.get("/api/v1/workspaces/", headers=registered_user["headers"])
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) >= 1
    assert any(w["id"] == str(registered_user["workspace"].id) for w in workspaces)


@pytest.mark.asyncio
async def test_create_new_workspace(client: AsyncClient, registered_user: dict):
    """Verifies provisioning a new Family or Business workspace designating user as OWNER."""
    payload = {
        "name": "Patil Family Household",
        "type": "family",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    }
    response = await client.post(
        "/api/v1/workspaces/",
        json=payload,
        headers=registered_user["headers"],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Patil Family Household"
    assert data["type"] == "family"
    assert data["owner_id"] == str(registered_user["user"].id)


@pytest.mark.asyncio
async def test_get_workspace_details(client: AsyncClient, registered_user: dict):
    """Verifies member can fetch workspace details using path parameter."""
    ws_id = str(registered_user["workspace"].id)
    response = await client.get(
        f"/api/v1/workspaces/{ws_id}",
        headers=registered_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["id"] == ws_id


@pytest.mark.asyncio
async def test_get_workspace_cross_tenant_idor_rejected_404(
    client: AsyncClient,
    registered_user: dict,
    second_user: dict,
):
    """
    CRITICAL SECURITY CHECK:
    User A attempts to access User B's workspace.
    Backend must return 404 Not Found (NOT 403) to prevent tenant enumeration and IDOR.
    """
    second_ws_id = str(second_user["workspace"].id)
    response = await client.get(
        f"/api/v1/workspaces/{second_ws_id}",
        headers=registered_user["headers"],  # User A's token
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_add_member_as_owner_succeeds(
    client: AsyncClient,
    registered_user: dict,
    second_user: dict,
):
    """Verifies workspace OWNER can invite an existing registered user."""
    ws_id = str(registered_user["workspace"].id)
    payload = {
        "email": second_user["user"].email,
        "role": "member",
    }
    response = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json=payload,
        headers=registered_user["headers"],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == second_user["user"].email
    assert data["role"] == "member"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_add_member_as_viewer_rejected_403(
    client: AsyncClient,
    registered_user: dict,
    second_user: dict,
    db_session: AsyncSession,
):
    """Verifies that a member with VIEWER role cannot invite or add other members (RBAC)."""
    ws = registered_user["workspace"]
    user2 = second_user["user"]

    # Attach User 2 to User 1's workspace with VIEWER role
    viewer_membership = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user2.id,
        role="viewer",
        status="active",
    )
    db_session.add(viewer_membership)
    await db_session.commit()

    # User 2 (viewer) tries to invite a third user
    payload = {
        "email": "third_user@example.com",
        "role": "member",
    }
    response = await client.post(
        f"/api/v1/workspaces/{str(ws.id)}/members",
        json=payload,
        headers=second_user["headers"],  # User 2 token
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_suspended_membership_rejected_403(
    client: AsyncClient,
    registered_user: dict,
    db_session: AsyncSession,
):
    """Verifies that a user whose membership status is suspended is rejected."""
    ws = registered_user["workspace"]
    user = registered_user["user"]

    # Query membership and set to suspended
    stmt = WorkspaceMember.__table__.update().where(
        WorkspaceMember.workspace_id == ws.id,
        WorkspaceMember.user_id == user.id,
    ).values(status="suspended")
    await db_session.execute(stmt)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/workspaces/{str(ws.id)}",
        headers=registered_user["headers"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MEMBERSHIP_INACTIVE"
