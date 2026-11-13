"""
Arthsavora API Integration Tests — Accounts and Transactions Endpoints
Verifies end-to-end HTTP request handling, workspace context resolution,
exact Money payload parsing, idempotent deduplication, and RBAC enforcement.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient


async def test_accounts_api_end_to_end(client: AsyncClient, registered_user: dict):
    """Verify creating and listing financial accounts via /api/v1/accounts/."""
    token = registered_user["token"]
    ws = registered_user["workspace"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Create a bank account
    create_payload = {
        "name": "State Bank of India Savings",
        "account_type": "savings",
        "currency": "INR",
        "institution_name": "State Bank of India",
        "masked_identifier": "XX8901",
    }
    response = await client.post("/api/v1/accounts/", json=create_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "State Bank of India Savings"
    assert data["account_type"] == "savings"
    assert data["currency"] == "INR"
    assert data["workspace_id"] == str(ws.id)
    assert "id" in data
    account_id = data["id"]

    # 2. List accounts
    list_resp = await client.get("/api/v1/accounts/", headers=headers)
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert isinstance(accounts, list)
    assert any(a["id"] == account_id for a in accounts)

    # 3. List with account_type filter
    filtered_resp = await client.get("/api/v1/accounts/?account_type=savings", headers=headers)
    assert filtered_resp.status_code == 200
    filtered_accounts = filtered_resp.json()
    assert all(a["account_type"] == "savings" for a in filtered_accounts)


async def test_accounts_api_missing_workspace_header_rejected(client: AsyncClient, registered_user: dict):
    """Verify request without X-Workspace-ID is rejected with validation error."""
    token = registered_user["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/accounts/", headers=headers)
    assert response.status_code in [400, 422]


async def test_accounts_api_unauthenticated_rejected(client: AsyncClient):
    """Verify request with workspace header but missing authentication is rejected with 401."""
    headers = {"X-Workspace-ID": str(uuid.uuid4())}
    response = await client.get("/api/v1/accounts/", headers=headers)
    assert response.status_code == 401


async def test_transactions_api_end_to_end_and_idempotency(client: AsyncClient, registered_user: dict):
    """Verify transaction creation, paginated listing, and external ID deduplication."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Create target account first
    acc_payload = {
        "name": "ICICI Salary Account",
        "account_type": "bank",
        "currency": "INR",
    }
    acc_res = await client.post("/api/v1/accounts/", json=acc_payload, headers=headers)
    assert acc_res.status_code == 201
    account_id = acc_res.json()["id"]

    # 2. Create operational transaction
    ext_id = f"UPI-{uuid.uuid4().hex[:10]}"
    tx_payload = {
        "account_id": account_id,
        "amount": "8500.75",
        "currency": "INR",
        "transaction_type": "income",
        "transaction_date": "2026-03-20",
        "description": "Freelance client milestone payment",
        "merchant_name": "Tech Corp India",
        "external_transaction_id": ext_id,
        "is_ai_predicted": False,
    }

    tx_res = await client.post("/api/v1/transactions/", json=tx_payload, headers=headers)
    assert tx_res.status_code == 201
    tx_data = tx_res.json()
    assert tx_data["account_id"] == account_id
    assert Decimal(str(tx_data["amount"])) == Decimal("8500.75")
    assert tx_data["currency"] == "INR"
    assert tx_data["transaction_type"] == "income"
    tx_id = tx_data["id"]

    # 3. Idempotent Retry: Post the exact same payload with same external_transaction_id
    retry_res = await client.post("/api/v1/transactions/", json=tx_payload, headers=headers)
    assert retry_res.status_code in [200, 201]
    retry_data = retry_res.json()
    assert retry_data["id"] == tx_id  # Must return existing transaction without creating duplicate

    # 4. List paginated transactions
    list_res = await client.get("/api/v1/transactions/?page=1&page_size=10", headers=headers)
    assert list_res.status_code == 200
    page_data = list_res.json()
    assert "items" in page_data
    assert "total" in page_data
    assert page_data["page"] == 1
    assert page_data["total"] >= 1
    assert any(t["id"] == tx_id for t in page_data["items"])


async def test_transactions_api_zero_amount_rejected(client: AsyncClient, registered_user: dict):
    """Verify transaction with zero amount is rejected."""
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # Create account
    acc_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Cash Wallet", "account_type": "wallet", "currency": "INR"},
        headers=headers,
    )
    account_id = acc_res.json()["id"]

    # Post zero amount
    zero_payload = {
        "account_id": account_id,
        "amount": "0.00",
        "currency": "INR",
        "transaction_type": "expense",
        "transaction_date": "2026-03-20",
        "description": "Zero attempt",
    }
    zero_res = await client.post("/api/v1/transactions/", json=zero_payload, headers=headers)
    assert zero_res.status_code == 422
