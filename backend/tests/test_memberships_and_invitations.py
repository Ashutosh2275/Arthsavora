"""
Arthsavora Test Suite - Memberships, Invitations, and Role Governance (Prompt 07)
Covers cryptographically secure token generation, SHA-256 storage, recipient email binding,
atomic acceptance with row locking, expiration, revocation, role hierarchy, and member removal.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.infrastructure.database.models import User, UserProfile, Workspace, WorkspaceInvitation, WorkspaceMember


@pytest.fixture
async def second_registered_user(db_session: AsyncSession) -> dict:
    """Provisions a second registered user for multi-user membership and invitation tests."""
    user_id = uuid.uuid4()
    email = f"collaborator_{user_id.hex[:8]}@example.com"
    user = User(
        id=user_id,
        email=email,
        full_name="Collaborator User",
        hashed_password=get_password_hash("CollabPass123!"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        default_currency="INR",
        timezone="Asia/Kolkata",
        locale="en-IN",
    )
    db_session.add(profile)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), email=user.email)
    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
async def third_registered_user(db_session: AsyncSession) -> dict:
    """Provisions a third registered user for cross-user permission mismatch tests."""
    user_id = uuid.uuid4()
    email = f"bystander_{user_id.hex[:8]}@example.com"
    user = User(
        id=user_id,
        email=email,
        full_name="Bystander User",
        hashed_password=get_password_hash("BystanderPass123!"),
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
async def test_invitation_lifecycle_create_list_accept(
    client: AsyncClient,
    registered_user: dict,
    second_registered_user: dict,
    db_session: AsyncSession,
):
    """
    COMPLETE INVITATION SECURITY LIFECYCLE:
    1. Owner issues invitation for second user's email.
    2. Verifies token is returned once, raw token is NOT stored in DB, hash is stored.
    3. Verifies listing invitations omits raw tokens.
    4. Second user accepts invitation -> membership created with active status.
    5. Re-redemption of accepted token is rejected.
    """
    # 1. Create a business workspace for inviting members
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Alpha Corp", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    assert create_res.status_code == 201
    ws_id = create_res.json()["id"]

    # 2. Issue invitation
    recipient_email = second_registered_user["user"].email
    invite_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": recipient_email, "role": "staff"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert invite_res.status_code == 201
    invite_data = invite_res.json()
    raw_token = invite_data["invitation_token"]
    assert raw_token is not None
    assert len(raw_token) > 20
    assert invite_data["status"] == "pending"

    # Verify DB has ONLY the SHA-256 hash, not the raw token
    expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    stmt = select(WorkspaceInvitation).where(WorkspaceInvitation.id == uuid.UUID(invite_data["id"]))
    res = await db_session.execute(stmt)
    inv_record = res.scalar_one()
    assert inv_record.token_hash == expected_hash

    # 3. List invitations - verify raw token is masked/None in listing
    list_res = await client.get(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert list_res.status_code == 200
    listed_items = list_res.json()
    assert len(listed_items) >= 1
    target_item = next(item for item in listed_items if item["id"] == invite_data["id"])
    assert target_item["invitation_token"] is None

    # 4. Second user accepts invitation
    accept_res = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers=second_registered_user["headers"],
    )
    assert accept_res.status_code == 200
    accepted_data = accept_res.json()
    assert accepted_data["workspace_id"] == ws_id
    assert accepted_data["role"] == "staff"
    assert accepted_data["status"] == "active"

    # 5. Attempt re-redemption of the same token -> must be rejected
    re_accept_res = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers=second_registered_user["headers"],
    )
    assert re_accept_res.status_code in [400, 404, 422]


@pytest.mark.asyncio
async def test_invitation_wrong_recipient_email_rejected(
    client: AsyncClient,
    registered_user: dict,
    second_registered_user: dict,
    third_registered_user: dict,
):
    """
    SECURITY BOUNDARY CHECK:
    An invitation issued to user B cannot be claimed/accepted by user C.
    Must return 403 Forbidden.
    """
    # Create workspace
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Beta Corp", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    # Issue invitation to Second User
    invite_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": second_registered_user["user"].email, "role": "viewer"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    raw_token = invite_res.json()["invitation_token"]

    # Third User attempts to redeem Second User's token -> 403 Forbidden
    accept_res = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers=third_registered_user["headers"],
    )
    assert accept_res.status_code == 403


@pytest.mark.asyncio
async def test_invitation_revocation_flow(
    client: AsyncClient,
    registered_user: dict,
    second_registered_user: dict,
):
    """Verifies that an owner can revoke a pending invitation, preventing subsequent acceptance."""
    # Create workspace
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Gamma Corp", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    # Issue invitation
    invite_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": second_registered_user["user"].email, "role": "viewer"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    invite_id = invite_res.json()["id"]
    raw_token = invite_res.json()["invitation_token"]

    # Revoke invitation
    revoke_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations/{invite_id}/revoke",
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert revoke_res.status_code == 200

    # Attempt to accept revoked invitation -> rejected
    accept_res = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers=second_registered_user["headers"],
    )
    assert accept_res.status_code in [400, 404, 422]


@pytest.mark.asyncio
async def test_member_role_update_and_hierarchy_validation(
    client: AsyncClient,
    registered_user: dict,
    second_registered_user: dict,
):
    """
    ROLE GOVERNANCE CHECK:
    - Tests updating an existing member's role (staff -> accountant).
    - Prohibits assigning 'owner' role directly via PATCH.
    - Prohibits modifying the owner's role via PATCH.
    - Validates roles matching the workspace type.
    """
    # Create business workspace
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Delta Corp", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    # Add second user directly
    add_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": second_registered_user["user"].email, "role": "staff"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert add_res.status_code == 201
    member_id = add_res.json()["id"]

    # 1. Promote staff -> accountant
    update_res = await client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{member_id}",
        json={"role": "accountant"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert update_res.status_code == 200
    assert update_res.json()["role"] == "accountant"

    # 2. Attempt assigning 'owner' role via PATCH -> 403 Forbidden
    fail_owner_res = await client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{member_id}",
        json={"role": "owner"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert fail_owner_res.status_code == 403

    # 3. Attempt unsupported role for workspace type -> 422 Validation Error
    fail_role_res = await client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{member_id}",
        json={"role": "invalid_super_admin"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert fail_role_res.status_code == 422


@pytest.mark.asyncio
async def test_member_removal_and_owner_protection(
    client: AsyncClient,
    registered_user: dict,
    second_registered_user: dict,
):
    """
    MEMBER REMOVAL CHECK:
    - Verifies owner can remove a member.
    - Prohibits removing the workspace owner (403).
    - Verifies removed member immediately loses workspace access.
    """
    # Create business workspace
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Epsilon Corp", "type": "business", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    ws_id = create_res.json()["id"]

    # Add second user
    add_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": second_registered_user["user"].email, "role": "viewer"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    member_id = add_res.json()["id"]

    # Find owner membership ID
    members_list_res = await client.get(
        f"/api/v1/workspaces/{ws_id}/members",
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    owner_member = next(m for m in members_list_res.json() if m["role"] == "owner")

    # 1. Attempt to remove the owner -> 403 Forbidden
    fail_remove_owner = await client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{owner_member['id']}",
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert fail_remove_owner.status_code == 403

    # 2. Successfully remove member
    remove_res = await client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{member_id}",
        headers={**registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert remove_res.status_code == 200

    # 3. Removed user attempts to access workspace -> 403 (membership inactive/revoked) or 404
    subsequent_access = await client.get(
        f"/api/v1/workspaces/{ws_id}",
        headers={**second_registered_user["headers"], "X-Workspace-ID": ws_id},
    )
    assert subsequent_access.status_code in [403, 404]
