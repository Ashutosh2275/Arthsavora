"""
Arthsavora Test Suite - Family Workspace Privacy Model & Anti-IDOR Isolation (Prompt 07)
Covers explicit boundary rules for family financial collaboration:
- Personal accounts remain private by default in their respective personal workspaces.
- Family workspace is a distinct workspace context with independent financial records.
- Anti-IDOR privacy invariant: Family admins CANNOT query or view personal accounts of family members.
- Explicit shared accounts inside family workspace are accessible to family members.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.infrastructure.database.models import User, UserProfile, Workspace, WorkspaceMember


@pytest.fixture
async def family_member_user(db_session: AsyncSession) -> dict:
    """Provisions a second user with their own personal workspace to join a family workspace."""
    user_id = uuid.uuid4()
    email = f"family_member_{user_id.hex[:8]}@example.com"
    user = User(
        id=user_id,
        email=email,
        full_name="Family Member Two",
        hashed_password=get_password_hash("FamilyPass123!"),
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

    # Member's own personal workspace
    personal_ws = Workspace(
        name="Member Two Personal Finances",
        slug=f"member-personal-{user.id.hex[:8]}",
        type="personal",
        owner_id=user.id,
        default_currency="INR",
        timezone="Asia/Kolkata",
        country="IN",
        status="active",
        settings={"is_default": True},
    )
    db_session.add(personal_ws)
    await db_session.flush()

    membership = WorkspaceMember(
        workspace_id=personal_ws.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    db_session.add(membership)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), email=user.email)
    return {
        "user": user,
        "workspace": personal_ws,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.mark.asyncio
async def test_family_privacy_boundary_and_anti_idor(
    client: AsyncClient,
    registered_user: dict,
    family_member_user: dict,
):
    """
    CRITICAL FINTECH PRIVACY INVARIANT:
    1. User A (family head) has Personal Workspace A with a private personal account.
    2. User B (family member) has Personal Workspace B with a private personal account.
    3. User A creates Family Workspace F and adds User B as member.
    4. Anti-IDOR check: User A CANNOT access User B's personal workspace or accounts (404).
    5. Anti-IDOR check: User B CANNOT access User A's personal workspace or accounts (404).
    6. In Family Workspace F, accounts created belong solely to F and are shared.
    7. Neither user's personal financial accounts leak into Family Workspace F account lists.
    """
    # 1. User A creates private personal account in Workspace A
    ws_a_id = str(registered_user["workspace"].id)
    acc_a_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "User A Private HDFC Bank", "account_type": "bank", "currency": "INR"},
        headers={**registered_user["headers"], "X-Workspace-ID": ws_a_id},
    )
    assert acc_a_res.status_code == 201
    acc_a_id = acc_a_res.json()["id"]

    # 2. User B creates private personal account in Workspace B
    ws_b_id = str(family_member_user["workspace"].id)
    acc_b_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "User B Private ICICI Bank", "account_type": "bank", "currency": "INR"},
        headers={**family_member_user["headers"], "X-Workspace-ID": ws_b_id},
    )
    assert acc_b_res.status_code == 201
    acc_b_id = acc_b_res.json()["id"]

    # 3. User A creates Family Workspace F
    family_ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Unified Family Household", "type": "family", "currency": "INR", "timezone": "Asia/Kolkata", "country": "IN"},
        headers=registered_user["headers"],
    )
    assert family_ws_res.status_code == 201
    family_ws_id = family_ws_res.json()["id"]

    # 4. User A adds User B to Family Workspace F
    add_member_res = await client.post(
        f"/api/v1/workspaces/{family_ws_id}/members",
        json={"email": family_member_user["user"].email, "role": "member"},
        headers={**registered_user["headers"], "X-Workspace-ID": family_ws_id},
    )
    assert add_member_res.status_code == 201

    # 5. User A creates a shared household account in Family Workspace F
    shared_acc_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Household Expenses SBI", "account_type": "bank", "currency": "INR"},
        headers={**registered_user["headers"], "X-Workspace-ID": family_ws_id},
    )
    assert shared_acc_res.status_code == 201
    shared_acc_id = shared_acc_res.json()["id"]

    # 6. ANTI-IDOR CHECK 1: User A (Family Head) attempts to access User B's personal account
    # Requesting Account B with User A's token under Workspace B -> 404 (User A is not a member of Workspace B)
    idor_res_1 = await client.get(
        f"/api/v1/accounts/{acc_b_id}",
        headers={**registered_user["headers"], "X-Workspace-ID": ws_b_id},
    )
    assert idor_res_1.status_code == 404

    # Requesting Account B with User A's token under Family Workspace F -> 404 (Account B does not belong to Workspace F)
    idor_res_2 = await client.get(
        f"/api/v1/accounts/{acc_b_id}",
        headers={**registered_user["headers"], "X-Workspace-ID": family_ws_id},
    )
    assert idor_res_2.status_code == 404

    # 7. ANTI-IDOR CHECK 2: User B attempts to access User A's personal account
    idor_res_3 = await client.get(
        f"/api/v1/accounts/{acc_a_id}",
        headers={**family_member_user["headers"], "X-Workspace-ID": ws_a_id},
    )
    assert idor_res_3.status_code == 404

    # 8. SHARED ACCESSIBILITY CHECK: User B CAN access the shared household account in Family Workspace F
    user_b_shared_access = await client.get(
        f"/api/v1/accounts/{shared_acc_id}",
        headers={**family_member_user["headers"], "X-Workspace-ID": family_ws_id},
    )
    assert user_b_shared_access.status_code == 200
    assert user_b_shared_access.json()["name"] == "Household Expenses SBI"

    # 9. ISOLATION CHECK: Family Workspace F's account list contains ONLY shared accounts, NOT personal accounts
    family_accounts_res = await client.get(
        "/api/v1/accounts/",
        headers={**registered_user["headers"], "X-Workspace-ID": family_ws_id},
    )
    assert family_accounts_res.status_code == 200
    family_acc_ids = [a["id"] for a in family_accounts_res.json()]
    assert shared_acc_id in family_acc_ids
    assert acc_a_id not in family_acc_ids
    assert acc_b_id not in family_acc_ids
