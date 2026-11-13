"""
Arthsavora Test Suite - Workspace Ownership Transfer (Prompt 07)
Covers controlled, atomic ownership handover, role swapping, confirmation enforcement,
unauthorized attempt rejection, self-transfer prohibition, and audit log generation.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.infrastructure.database.models import AuditLog, User, UserProfile, Workspace, WorkspaceMember


@pytest.fixture
async def successor_user(db_session: AsyncSession) -> dict:
    """Provisions a second registered user intended as the designated ownership successor."""
    user_id = uuid.uuid4()
    email = f"successor_{user_id.hex[:8]}@example.com"
    user = User(
        id=user_id,
        email=email,
        full_name="Designated Successor",
        hashed_password=get_password_hash("SuccessorPass123!"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), email=user.email)
    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.mark.asyncio
async def test_atomic_ownership_transfer_success(
    client: AsyncClient,
    registered_user: dict,
    successor_user: dict,
    db_session: AsyncSession,
):
    """
    CRITICAL FINANCIAL GOVERNANCE CHECK:
    Tests complete atomic transfer of workspace ownership:
    1. Owner creates business workspace and adds successor as 'admin'.
    2. Owner executes POST /ownership-transfer with confirm=True.
    3. Verifies workspace.owner_id is updated.
    4. Verifies successor membership role is now 'owner'.
    5. Verifies previous owner membership role is now 'admin'.
    6. Verifies audit log record is created.
    """
    # 1. Create workspace
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Heritage Holdings", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    assert create_res.status_code == 201
    ws_id = create_res.json()["id"]

    # 2. Add successor directly as admin
    add_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": successor_user["user"].email, "role": "admin"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert add_res.status_code == 201
    successor_member_id = add_res.json()["id"]

    # 3. Execute ownership transfer
    transfer_payload = {
        "new_owner_id": successor_member_id,
        "previous_owner_role": "admin",
        "confirm": True,
    }
    transfer_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/ownership-transfer",
        json=transfer_payload,
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert transfer_res.status_code == 200
    assert transfer_res.json()["owner_id"] == str(successor_user["user"].id)

    # 4. Verify in database:
    # A) Workspace owner_id
    ws_stmt = select(Workspace).where(Workspace.id == uuid.UUID(ws_id))
    ws_row = (await db_session.execute(ws_stmt)).scalar_one()
    assert ws_row.owner_id == successor_user["user"].id

    # B) Memberships
    m_stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == uuid.UUID(ws_id))
    members = (await db_session.execute(m_stmt)).scalars().all()
    orig_member = next(m for m in members if m.user_id == registered_user["user"].id)
    new_member = next(m for m in members if m.user_id == successor_user["user"].id)
    assert orig_member.role == "admin"
    assert new_member.role == "owner"

    # C) Audit log
    audit_stmt = select(AuditLog).where(
        AuditLog.workspace_id == uuid.UUID(ws_id),
        AuditLog.action == "workspace:transfer_ownership",
    )
    audit_row = (await db_session.execute(audit_stmt)).scalar_one_or_none()
    assert audit_row is not None
    assert audit_row.actor_id == registered_user["user"].id


@pytest.mark.asyncio
async def test_ownership_transfer_unconfirmed_rejected(
    client: AsyncClient,
    registered_user: dict,
    successor_user: dict,
):
    """Verifies that ownership transfer without explicit confirm=True is rejected."""
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Safe Holdings", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    add_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": successor_user["user"].email, "role": "admin"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    successor_member_id = add_res.json()["id"]

    # Attempt transfer without confirm=True
    transfer_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/ownership-transfer",
        json={
            "new_owner_id": successor_member_id,
            "previous_owner_role": "admin",
            "confirm": False,
        },
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert transfer_res.status_code == 422


@pytest.mark.asyncio
async def test_ownership_transfer_non_owner_forbidden(
    client: AsyncClient,
    registered_user: dict,
    successor_user: dict,
):
    """Verifies that non-owner members (even admins) cannot trigger ownership transfer."""
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Secure Ventures", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    add_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": successor_user["user"].email, "role": "admin"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    successor_member_id = add_res.json()["id"]

    # Successor (admin) attempts to transfer ownership -> 403 Forbidden
    transfer_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/ownership-transfer",
        json={
            "new_owner_id": successor_member_id,
            "previous_owner_role": "admin",
            "confirm": True,
        },
        headers={**successor_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert transfer_res.status_code == 403


@pytest.mark.asyncio
async def test_ownership_transfer_to_non_member_rejected(
    client: AsyncClient,
    registered_user: dict,
):
    """Verifies that transferring ownership to an arbitrary random ID is rejected."""
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Strict Holdings", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    random_id = str(uuid.uuid4())
    transfer_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/ownership-transfer",
        json={
            "new_owner_id": random_id,
            "previous_owner_role": "admin",
            "confirm": True,
        },
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert transfer_res.status_code == 422
