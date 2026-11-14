"""
Arthsavora Financial Account Management Integration Tests
Validates Prompt 08 requirements:
- Account creation across Personal, Family, and Business workspaces
- Exact minor unit (paise) conversions and initial opening balance snapshots
- Unique constraint preventing duplicate linked provider accounts in workspace
- Currency and account type validation
- Full lifecycle state transitions (active -> archived -> restored -> closed)
- Closing date temporal validation (closing_date >= opening_date)
- Credit card specific attributes (credit_limit, available_credit, due_date)
- Loan specific attributes (original_principal, interest_rate, repayment_amount)
- Real-time balance breakdown and immutable point-in-time snapshot history
- Workspace isolation and anti-IDOR protections
- Both header-based and path-parameter-based workspace routing
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User, UserProfile, Workspace, WorkspaceMember
from app.core.security import create_access_token, get_password_hash


async def create_secondary_workspace(db_session: AsyncSession, owner_id: uuid.UUID, ws_type: str, name: str) -> Workspace:
    """Helper to provision a second workspace for cross-workspace anti-IDOR tests."""
    ws = Workspace(
        id=uuid.uuid4(),
        name=name,
        slug=f"ws-{uuid.uuid4().hex[:8]}",
        type=ws_type,
        owner_id=owner_id,
        status="active",
    )
    db_session.add(ws)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=owner_id,
        role="owner",
        status="active",
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


async def test_create_account_personal_family_business(client: AsyncClient, registered_user: dict, db_session: AsyncSession):
    """Verify account creation across Personal, Family, and Business workspaces with opening balance snapshot."""
    token = registered_user["token"]
    user_id = registered_user["user"].id
    personal_ws = registered_user["workspace"]

    # 1. Personal Workspace: Create Savings Account with Opening Balance
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(personal_ws.id),
    }
    payload_savings = {
        "name": "HDFC Salary Savings",
        "account_type": "savings",
        "account_subtype": "salary",
        "currency": "INR",
        "institution_name": "HDFC Bank",
        "masked_identifier": "XX4321",
        "opening_balance": "25000.50",
        "opening_date": "2026-01-01",
        "description": "Primary salary credit account",
    }
    res = await client.post("/api/v1/accounts/", json=payload_savings, headers=headers)
    assert res.status_code == 201
    savings_data = res.json()
    assert savings_data["name"] == "HDFC Salary Savings"
    assert savings_data["account_type"] == "savings"
    assert savings_data["account_subtype"] == "salary"
    assert savings_data["status"] == "active"
    assert savings_data["opening_date"] == "2026-01-01"
    assert savings_data["balances"]["opening_balance"] == "25000.50"
    assert savings_data["balances"]["book_balance"] == "25000.50"
    assert savings_data["balances"]["available_balance"] == "25000.50"
    savings_id = savings_data["id"]

    # Verify initial opening snapshot was recorded
    history_res = await client.get(f"/api/v1/accounts/{savings_id}/balance-history", headers=headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 1
    assert history[0]["balance_type"] == "opening"
    assert history[0]["balance_amount"] == "25000.50"

    # 2. Family Workspace: Create Joint Bank Account
    family_ws = await create_secondary_workspace(db_session, user_id, "family", "Sharma Family Finances")
    family_headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(family_ws.id),
    }
    payload_family = {
        "name": "SBI Household Joint",
        "account_type": "savings",
        "currency": "INR",
        "institution_name": "State Bank of India",
        "masked_identifier": "XX9988",
        "opening_balance": "10000.00",
    }
    res_family = await client.post("/api/v1/accounts/", json=payload_family, headers=family_headers)
    assert res_family.status_code == 201
    assert res_family.json()["workspace_id"] == str(family_ws.id)

    # 3. Business Workspace: Create Business Current Account
    biz_ws = await create_secondary_workspace(db_session, user_id, "business", "Apex Solutions LLP")
    biz_headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(biz_ws.id),
    }
    payload_biz = {
        "name": "ICICI Current Account",
        "account_type": "business_current",
        "currency": "INR",
        "institution_name": "ICICI Bank",
        "masked_identifier": "XX1122",
        "opening_balance": "150000.00",
    }
    res_biz = await client.post("/api/v1/accounts/", json=payload_biz, headers=biz_headers)
    assert res_biz.status_code == 201
    assert res_biz.json()["workspace_id"] == str(biz_ws.id)


async def test_duplicate_linked_provider_account_rejected(client: AsyncClient, registered_user: dict, db_session: AsyncSession):
    """Verify duplicate external linked provider account within the same workspace is rejected with 409 Conflict."""
    token = registered_user["token"]
    user_id = registered_user["user"].id
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    payload = {
        "name": "Linked Axis Bank",
        "account_type": "savings",
        "currency": "INR",
        "institution_name": "Axis Bank",
        "provider_name": "SetuAA",
        "provider_account_id": "setu_acc_987654",
    }

    # First creation succeeds
    res1 = await client.post("/api/v1/accounts/", json=payload, headers=headers)
    assert res1.status_code == 201

    # Second creation in same workspace with same provider details fails with 409
    res2 = await client.post("/api/v1/accounts/", json=payload, headers=headers)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "DUPLICATE_EXTERNAL_ACCOUNT"

    # But creation in a different workspace with the same provider details succeeds
    ws2 = await create_secondary_workspace(db_session, user_id, "family", "Second Workspace")
    headers2 = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws2.id),
    }
    res3 = await client.post("/api/v1/accounts/", json=payload, headers=headers2)
    assert res3.status_code == 201


async def test_account_type_and_currency_validation(client: AsyncClient, registered_user: dict):
    """Verify invalid currencies and unsupported workspace account types are cleanly rejected."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Invalid currency code
    res_curr = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "Test Acc",
            "account_type": "savings",
            "currency": "XYZ123",
        },
        headers=headers,
    )
    assert res_curr.status_code == 422

    # 2. Unsupported account type for Personal workspace (e.g. business_current)
    res_type = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "Test Acc",
            "account_type": "business_current",
            "currency": "INR",
        },
        headers=headers,
    )
    assert res_type.status_code == 422
    assert "not supported" in res_type.json()["error"]["message"].lower()


async def test_account_update_and_archive_lifecycle(client: AsyncClient, registered_user: dict):
    """Verify updating account details, archiving it, verifying immutability when archived, and restoring it."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Create active account
    res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "Wallet For Groceries",
            "account_type": "digital_wallet",
            "currency": "INR",
            "institution_name": "Paytm",
            "masked_identifier": "9876",
        },
        headers=headers,
    )
    assert res.status_code == 201
    account_id = res.json()["id"]

    # 2. Update metadata
    update_res = await client.patch(
        f"/api/v1/accounts/{account_id}",
        json={
            "name": "Groceries & Fuel Wallet",
            "description": "Used for daily errands",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Groceries & Fuel Wallet"
    assert update_res.json()["description"] == "Used for daily errands"

    # 3. Archive account
    archive_res = await client.post(f"/api/v1/accounts/{account_id}/archive", headers=headers)
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "archived"

    # 4. Attempting to update an archived account is rejected with 422
    invalid_update = await client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"name": "Attempt Update"},
        headers=headers,
    )
    assert invalid_update.status_code == 422
    assert "archived" in invalid_update.json()["error"]["message"].lower()

    # 5. Restore account
    restore_res = await client.post(f"/api/v1/accounts/{account_id}/restore", headers=headers)
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "active"


async def test_account_close_lifecycle_validation(client: AsyncClient, registered_user: dict):
    """Verify closing an account with temporal validation (closing_date >= opening_date)."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Create account with opening_date 2026-01-15
    res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "Old Savings Account",
            "account_type": "savings",
            "currency": "INR",
            "opening_date": "2026-01-15",
        },
        headers=headers,
    )
    assert res.status_code == 201
    account_id = res.json()["id"]

    # 2. Attempt close with closing_date earlier than opening_date -> 422
    invalid_close = await client.post(
        f"/api/v1/accounts/{account_id}/close",
        json={"closing_date": "2026-01-10"},
        headers=headers,
    )
    assert invalid_close.status_code == 422
    assert "cannot precede opening date" in invalid_close.json()["error"]["message"].lower()

    # 3. Valid close
    valid_close = await client.post(
        f"/api/v1/accounts/{account_id}/close",
        json={"closing_date": "2026-03-31"},
        headers=headers,
    )
    assert valid_close.status_code == 200
    assert valid_close.json()["status"] == "closed"
    assert valid_close.json()["closing_date"] == "2026-03-31"


async def test_credit_card_attributes_and_liabilities(client: AsyncClient, registered_user: dict):
    """Verify credit card metrics: credit_limit, available_credit, statement_balance, minimum_due, due_date."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    card_payload = {
        "name": "Amazon Pay ICICI Card",
        "account_type": "credit_card",
        "currency": "INR",
        "institution_name": "ICICI Bank",
        "masked_identifier": "XX2040",
        "credit_limit": "250000.00",
        "statement_balance": "14200.00",
        "minimum_due": "750.00",
        "due_date": "2026-04-12",
        "outstanding_liability": "14200.00",
    }
    res = await client.post("/api/v1/accounts/", json=card_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["account_type"] == "credit_card"
    balances = data["balances"]
    assert balances["credit_limit"] == "250000.00"
    assert balances["statement_balance"] == "14200.00"
    assert balances["minimum_due"] == "750.00"
    assert balances["due_date"] == "2026-04-12"
    assert balances["outstanding_liability"] == "14200.00"
    # Available credit = limit - liability = 250000.00 - 14200.00 = 235800.00
    assert balances["available_credit"] == "235800.00"


async def test_loan_attributes_and_principal(client: AsyncClient, registered_user: dict):
    """Verify loan metrics: original_principal, outstanding_principal, interest_rate, repayment_amount, due_date."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    loan_payload = {
        "name": "SBI Home Loan",
        "account_type": "loan",
        "currency": "INR",
        "institution_name": "State Bank of India",
        "masked_identifier": "HL-99112",
        "original_principal": "4500000.00",
        "outstanding_principal": "4250000.00",
        "interest_rate": "8.50",
        "repayment_amount": "38450.00",
        "due_date": "2026-04-05",
    }
    res = await client.post("/api/v1/accounts/", json=loan_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["account_type"] == "loan"
    balances = data["balances"]
    assert balances["original_principal"] == "4500000.00"
    assert balances["outstanding_principal"] == "4250000.00"
    assert balances["interest_rate"] == 8.5
    assert balances["repayment_amount"] == "38450.00"
    assert balances["due_date"] == "2026-04-05"


async def test_record_provider_balance_snapshot_and_history(client: AsyncClient, registered_user: dict):
    """Verify recording provider balance snapshots, updating account pointer, and retrieving history."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Create Account
    res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "HDFC Demat Linked Bank",
            "account_type": "savings",
            "currency": "INR",
            "opening_balance": "5000.00",
        },
        headers=headers,
    )
    assert res.status_code == 201
    account_id = res.json()["id"]

    # 2. Record provider reported balance snapshot
    snapshot_payload = {
        "balance_type": "provider_reported",
        "balance_amount": "57890.25",
        "currency": "INR",
        "source": "account_aggregator",
        "source_reference": "sync_job_9918",
    }
    snap_res = await client.post(
        f"/api/v1/accounts/{account_id}/balances/snapshot",
        json=snapshot_payload,
        headers=headers,
    )
    assert snap_res.status_code == 201
    snap_data = snap_res.json()
    assert snap_data["balance_type"] == "provider_reported"
    assert snap_data["balance_amount"] == "57890.25"
    assert snap_data["source"] == "account_aggregator"

    # 3. Verify Account balances endpoint shows updated provider balance
    balance_res = await client.get(f"/api/v1/accounts/{account_id}/balances", headers=headers)
    assert balance_res.status_code == 200
    balances = balance_res.json()
    assert balances["provider_reported_balance"] == "57890.25"
    assert balances["provider_reported_at"] is not None

    # 4. Verify history returns both opening and provider_reported snapshots
    history_res = await client.get(f"/api/v1/accounts/{account_id}/balance-history", headers=headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 2
    types = [h["balance_type"] for h in history]
    assert "opening" in types
    assert "provider_reported" in types


async def test_account_cross_workspace_anti_idor(client: AsyncClient, registered_user: dict, db_session: AsyncSession):
    """Verify strict tenant isolation: accessing an account belonging to another workspace yields 404."""
    token = registered_user["token"]
    user_id = registered_user["user"].id
    ws1 = registered_user["workspace"]

    # Create account in Workspace 1
    headers1 = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws1.id),
    }
    res1 = await client.post(
        "/api/v1/accounts/",
        json={"name": "Confidential Account W1", "account_type": "savings", "currency": "INR"},
        headers=headers1,
    )
    assert res1.status_code == 201
    acc_id = res1.json()["id"]

    # Create Workspace 2
    ws2 = await create_secondary_workspace(db_session, user_id, "business", "Separate Business Corp")
    headers2 = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws2.id),
    }

    # Accessing W1's account while operating in W2 context returns 404
    idor_res = await client.get(f"/api/v1/accounts/{acc_id}", headers=headers2)
    assert idor_res.status_code == 404
    assert "not found" in idor_res.json()["error"]["message"].lower()

    # Path parameter route for W2 referencing W1 account also returns 404
    path_idor_res = await client.get(f"/api/v1/workspaces/{ws2.id}/accounts/{acc_id}", headers=headers2)
    assert path_idor_res.status_code == 404


async def test_workspaces_path_parameter_routes(client: AsyncClient, registered_user: dict):
    """Verify both /api/v1/workspaces/{workspace_id}/accounts and /api/v1/accounts work interchangeably."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Create via path parameter URL
    create_payload = {
        "name": "Kotak 811 Zero Balance",
        "account_type": "savings",
        "currency": "INR",
        "opening_balance": "1200.00",
    }
    res = await client.post(
        f"/api/v1/workspaces/{ws.id}/accounts",
        json=create_payload,
        headers=auth_headers,
    )
    assert res.status_code == 201
    acc_id = res.json()["id"]

    # List via path parameter URL
    list_res = await client.get(
        f"/api/v1/workspaces/{ws.id}/accounts",
        headers=auth_headers,
    )
    assert list_res.status_code == 200
    accounts = list_res.json()
    assert any(a["id"] == acc_id for a in accounts)

    # Get details via path parameter URL
    detail_res = await client.get(
        f"/api/v1/workspaces/{ws.id}/accounts/{acc_id}",
        headers=auth_headers,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Kotak 811 Zero Balance"
