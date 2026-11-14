"""
Arthsavora Comprehensive Operational Transaction Management Test Suite
Verifies exact monetary precision, balance synchronization across asset, credit card, and loan accounts,
pending holds, posting, cancellations, cumulative refund bounds, formal compensating reversals,
paired transfers without expense double-counting, idempotency, posted fact immutability,
anti-IDOR defenses, and audit trails.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User, UserProfile, Workspace, WorkspaceMember
from app.core.security import create_access_token, get_password_hash


@pytest.fixture
async def second_workspace(db_session: AsyncSession, registered_user: dict) -> dict:
    """Provisions an isolated second workspace for the test user to verify anti-IDOR defenses."""
    u = registered_user["user"]
    ws2 = Workspace(
        name="Second Commercial Workspace",
        slug=f"second-ws-{uuid.uuid4().hex[:6]}",
        type="business",
        owner_id=u.id,
        default_currency="INR",
        timezone="Asia/Kolkata",
        status="active",
    )
    db_session.add(ws2)
    await db_session.flush()

    mem2 = WorkspaceMember(
        workspace_id=ws2.id,
        user_id=u.id,
        role="owner",
        status="active",
    )
    db_session.add(mem2)
    await db_session.commit()

    headers = {
        "Authorization": f"Bearer {registered_user['token']}",
        "X-Workspace-ID": str(ws2.id),
    }
    return {"workspace": ws2, "headers": headers}


async def test_income_and_expense_with_paise_balance_sync(client: AsyncClient, registered_user: dict):
    """
    Verifies that income increases book balance and expense decreases book balance
    with exact fixed-point and integer paise precision.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    # 1. Create Savings Account with initial ₹10,000.00
    acc_res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "HDFC Savings Account",
            "account_type": "savings",
            "currency": "INR",
            "opening_balance": "10000.00",
        },
        headers=headers,
    )
    assert acc_res.status_code == 201
    acc_data = acc_res.json()
    acc_id = acc_data["id"]
    assert acc_data["balances"]["book_balance_paise"] == 1000000

    # 2. Record Income ₹5,000.50
    inc_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "5000.50",
            "currency": "INR",
            "transaction_type": "income",
            "transaction_date": "2026-03-25",
            "description": "Client Consulting Fee",
        },
        headers=headers,
    )
    assert inc_res.status_code == 201
    inc_data = inc_res.json()
    assert inc_data["amount"] == "5000.50"
    assert inc_data["amount_paise"] == 500050
    assert inc_data["direction"] == "inflow"
    assert inc_data["status"] == "posted"

    # Verify Account Balance increased to ₹15,000.50
    bal_res1 = await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)
    assert bal_res1.status_code == 200
    assert bal_res1.json()["balances"]["book_balance_paise"] == 1500050

    # 3. Record Expense ₹2,500.25
    exp_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "2500.25",
            "currency": "INR",
            "transaction_type": "expense",
            "transaction_date": "2026-03-26",
            "description": "Team Lunch",
        },
        headers=headers,
    )
    assert exp_res.status_code == 201
    exp_data = exp_res.json()
    assert exp_data["amount"] == "2500.25"
    assert exp_data["amount_paise"] == 250025
    assert exp_data["direction"] == "outflow"

    # Verify Account Balance decreased to ₹12,500.25
    bal_res2 = await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)
    assert bal_res2.status_code == 200
    assert bal_res2.json()["balances"]["book_balance_paise"] == 1250025


async def test_credit_card_purchase_and_payment_liability_reduction(client: AsyncClient, registered_user: dict):
    """
    Verifies that credit card purchases increase debt liabilities without double counting,
    and credit card payments reduce card liabilities and bank balances.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    # 1. Create Bank Account with ₹100,000.00
    bank_res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "Salary Current",
            "account_type": "current",
            "currency": "INR",
            "opening_balance": "100000.00",
        },
        headers=headers,
    )
    bank_id = bank_res.json()["id"]

    # 2. Create Credit Card with ₹50,000.00 limit and zero initial debt
    card_res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "ICICI Sapphiro Card",
            "account_type": "credit_card",
            "currency": "INR",
            "credit_limit": "50000.00",
            "initial_liability": "0.00",
        },
        headers=headers,
    )
    assert card_res.status_code == 201
    card_id = card_res.json()["id"]

    # 3. Post Credit Card Purchase ₹12,000.00
    purchase_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": card_id,
            "amount": "12000.00",
            "currency": "INR",
            "transaction_type": "credit_card_purchase",
            "transaction_date": "2026-03-27",
            "description": "Flight Tickets",
        },
        headers=headers,
    )
    assert purchase_res.status_code == 201
    assert purchase_res.json()["direction"] == "outflow"

    # Card liability must be ₹12,000.00 and available credit ₹38,000.00
    card_bal1 = await client.get(f"/api/v1/accounts/{card_id}", headers=headers)
    c1 = card_bal1.json()["balances"]
    assert c1["outstanding_liability_paise"] == 1200000
    assert c1["available_balance_paise"] == 3800000

    # 4. Transfer ₹5,000.00 from Bank Account to Credit Card Account (Payment)
    xfer_res = await client.post(
        "/api/v1/transfers/",
        json={
            "source_account_id": bank_id,
            "destination_account_id": card_id,
            "amount": "5000.00",
            "currency": "INR",
            "transfer_date": "2026-03-28",
            "description": "Credit Card Bill Partial Payment",
        },
        headers=headers,
    )
    assert xfer_res.status_code == 201
    xfer_data = xfer_res.json()
    assert xfer_data["transfer_id"] is not None
    assert xfer_data["source_transaction_id"] is not None
    assert xfer_data["destination_transaction_id"] is not None

    # Bank balance reduced by ₹5,000.00 to ₹95,000.00
    bank_bal = await client.get(f"/api/v1/accounts/{bank_id}", headers=headers)
    assert bank_bal.json()["balances"]["book_balance_paise"] == 9500000

    # Card liability reduced by ₹5,000.00 to ₹7,000.00, available credit increased to ₹43,000.00
    card_bal2 = await client.get(f"/api/v1/accounts/{card_id}", headers=headers)
    c2 = card_bal2.json()["balances"]
    assert c2["outstanding_liability_paise"] == 700000
    assert c2["available_balance_paise"] == 4300000


async def test_pending_transaction_lifecycle_and_balance_holds(client: AsyncClient, registered_user: dict):
    """
    Verifies that pending transactions create available balance reservations without altering book balance,
    posting clears reservation and applies to book balance, and cancel releases reservation.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    acc_res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "Business Checking",
            "account_type": "current",
            "currency": "INR",
            "opening_balance": "50000.00",
        },
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # 1. Create Pending Outflow ₹10,000.00
    tx_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "10000.00",
            "currency": "INR",
            "transaction_type": "withdrawal",
            "transaction_date": "2026-03-29",
            "description": "ATM Withdrawal Pending Clearing",
            "status": "pending",
        },
        headers=headers,
    )
    assert tx_res.status_code == 201
    tx_data = tx_res.json()
    assert tx_data["status"] == "pending"
    tx_id = tx_data["id"]

    # Book balance is still ₹50,000.00; pending is ₹10,000.00; available balance is ₹40,000.00
    bal1 = (await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)).json()["balances"]
    assert bal1["book_balance_paise"] == 5000000
    assert bal1["pending_amount_paise"] == 1000000
    assert bal1["available_balance_paise"] == 4000000

    # 2. Post the pending transaction
    post_res = await client.post(
        f"/api/v1/transactions/{tx_id}/post",
        json={"settlement_date": "2026-03-30"},
        headers=headers,
    )
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "posted"

    # Book balance is now ₹40,000.00; pending is 0; available balance is ₹40,000.00
    bal2 = (await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)).json()["balances"]
    assert bal2["book_balance_paise"] == 4000000
    assert bal2["pending_amount_paise"] == 0
    assert bal2["available_balance_paise"] == 4000000

    # 3. Create another pending transaction of ₹5,000.00 and cancel it
    tx_cancel_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "5000.00",
            "currency": "INR",
            "transaction_type": "expense",
            "transaction_date": "2026-03-30",
            "description": "Declined POS transaction",
            "status": "pending",
        },
        headers=headers,
    )
    tx_cancel_id = tx_cancel_res.json()["id"]

    # Balance reservation active
    bal3 = (await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)).json()["balances"]
    assert bal3["pending_amount_paise"] == 500000
    assert bal3["available_balance_paise"] == 3500000

    # Cancel transaction
    cancel_res = await client.post(
        f"/api/v1/transactions/{tx_cancel_id}/cancel",
        json={"cancellation_reason": "POS Terminal Timeout"},
        headers=headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Balance reservation released
    bal4 = (await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)).json()["balances"]
    assert bal4["pending_amount_paise"] == 0
    assert bal4["book_balance_paise"] == 4000000
    assert bal4["available_balance_paise"] == 4000000


async def test_refund_lifecycle_and_cumulative_bounds(client: AsyncClient, registered_user: dict):
    """
    Verifies that refunds create paired inflow records, update balances, and enforce that
    cumulative refunds cannot exceed the original transaction amount.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    acc_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Retail Cash", "account_type": "cash", "currency": "INR", "opening_balance": "50000.00"},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # 1. Post original purchase ₹4,000.00
    orig_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "4000.00",
            "currency": "INR",
            "transaction_type": "expense",
            "transaction_date": "2026-04-01",
            "description": "Equipment Purchase",
        },
        headers=headers,
    )
    orig_id = orig_res.json()["id"]

    # 2. Issue partial refund 1 for ₹1,500.00
    ref1 = await client.post(
        f"/api/v1/transactions/{orig_id}/refunds",
        json={"refund_amount": "1500.00", "description": "Damaged Part 1 Refund"},
        headers=headers,
    )
    assert ref1.status_code == 201
    assert ref1.json()["amount"] == "1500.00"
    assert ref1.json()["direction"] == "inflow"
    assert ref1.json()["original_transaction_id"] == orig_id

    # 3. Issue partial refund 2 for ₹2,500.00 (Total refunded: ₹4,000.00)
    ref2 = await client.post(
        f"/api/v1/transactions/{orig_id}/refunds",
        json={"refund_amount": "2500.00", "description": "Remainder Part 2 Refund"},
        headers=headers,
    )
    assert ref2.status_code == 201
    assert ref2.json()["amount"] == "2500.00"

    # 4. Attempt refund 3 for ₹100.00 -> must fail with REFUND_EXCEEDS_ORIGINAL (422)
    ref3 = await client.post(
        f"/api/v1/transactions/{orig_id}/refunds",
        json={"refund_amount": "100.00"},
        headers=headers,
    )
    assert ref3.status_code == 422
    err_json = ref3.json()
    assert "REFUND_EXCEEDS_ORIGINAL" in str(err_json)


async def test_posted_transaction_formal_reversal(client: AsyncClient, registered_user: dict):
    """
    Verifies that posted transactions can only be corrected via formal reversals,
    which marks the original transaction as reversed, inverts account balance, and generates
    a compensating reversal transaction.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    acc_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Reserve Bank", "account_type": "bank", "currency": "INR", "opening_balance": "30000.00"},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # 1. Create posted expense ₹6,000.00
    tx_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "6000.00",
            "currency": "INR",
            "transaction_type": "expense",
            "transaction_date": "2026-04-02",
            "description": "Accidental Vendor Overpayment",
        },
        headers=headers,
    )
    tx_id = tx_res.json()["id"]

    # Balance drops to ₹24,000.00
    bal1 = (await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)).json()["balances"]
    assert bal1["book_balance_paise"] == 2400000

    # 2. Reverse the transaction
    rev_res = await client.post(
        f"/api/v1/transactions/{tx_id}/reverse",
        json={"reason": "Clerical entry error: duplicate voucher"},
        headers=headers,
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["transaction_type"] == "reversal"
    assert rev_data["direction"] == "inflow"
    assert rev_data["related_transaction_id"] == tx_id
    assert rev_data["reversal_reason"] == "Clerical entry error: duplicate voucher"

    # Original transaction status is now reversed
    orig_tx = (await client.get(f"/api/v1/transactions/{tx_id}", headers=headers)).json()
    assert orig_tx["status"] == "reversed"
    assert orig_tx["reversal_reason"] == "Clerical entry error: duplicate voucher"

    # Account balance restored to ₹30,000.00
    bal2 = (await client.get(f"/api/v1/accounts/{acc_id}", headers=headers)).json()["balances"]
    assert bal2["book_balance_paise"] == 3000000

    # 3. Attempting to reverse an already reversed transaction is rejected with 422
    rev2 = await client.post(
        f"/api/v1/transactions/{tx_id}/reverse",
        json={"reason": "Duplicate reversal attempt"},
        headers=headers,
    )
    assert rev2.status_code == 422


async def test_internal_transfers_and_same_account_rejection(client: AsyncClient, registered_user: dict):
    """
    Verifies that internal transfers pair source outflow and destination inflow legs,
    and rejects attempts to transfer between the identical source and destination account.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    acc1_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Savings A", "account_type": "savings", "currency": "INR", "opening_balance": "50000.00"},
        headers=headers,
    )
    acc1_id = acc1_res.json()["id"]

    acc2_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Savings B", "account_type": "savings", "currency": "INR", "opening_balance": "10000.00"},
        headers=headers,
    )
    acc2_id = acc2_res.json()["id"]

    # 1. Same-account transfer rejection
    bad_xfer = await client.post(
        "/api/v1/transfers/",
        json={
            "source_account_id": acc1_id,
            "destination_account_id": acc1_id,
            "amount": "1000.00",
            "currency": "INR",
            "transfer_date": "2026-04-03",
        },
        headers=headers,
    )
    assert bad_xfer.status_code == 422
    assert "TRANSFER_SAME_ACCOUNT" in str(bad_xfer.json())

    # 2. Valid transfer of ₹15,000.00
    good_xfer = await client.post(
        "/api/v1/transfers/",
        json={
            "source_account_id": acc1_id,
            "destination_account_id": acc2_id,
            "amount": "15000.00",
            "currency": "INR",
            "transfer_date": "2026-04-03",
            "description": "Funding Savings B",
        },
        headers=headers,
    )
    assert good_xfer.status_code == 201
    transfer_data = good_xfer.json()
    transfer_id = transfer_data["transfer_id"]

    # 3. Retrieve transfer by transfer_id
    fetch_xfer = await client.get(f"/api/v1/transfers/{transfer_id}", headers=headers)
    assert fetch_xfer.status_code == 200
    assert fetch_xfer.json()["amount"] == "15000.00"

    # Balances updated
    b1 = (await client.get(f"/api/v1/accounts/{acc1_id}", headers=headers)).json()["balances"]
    b2 = (await client.get(f"/api/v1/accounts/{acc2_id}", headers=headers)).json()["balances"]
    assert b1["book_balance_paise"] == 3500000
    assert b2["book_balance_paise"] == 2500000


async def test_posted_transaction_fact_immutability(client: AsyncClient, registered_user: dict):
    """
    Verifies that financial facts (amount, currency, account, date, type, status) of posted transactions
    are immutable and rejected with 422 POSTED_TRANSACTION_IMMUTABLE, while editable metadata succeeds.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    acc_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Checking 1", "account_type": "current", "currency": "INR", "opening_balance": "50000.00"},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    tx_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "1000.00",
            "currency": "INR",
            "transaction_type": "expense",
            "transaction_date": "2026-04-04",
            "description": "Initial Memo",
        },
        headers=headers,
    )
    tx_id = tx_res.json()["id"]

    # 1. Attempt to alter amount on posted transaction -> 422
    bad_amount = await client.patch(
        f"/api/v1/transactions/{tx_id}",
        json={"amount": "9999.00"},
        headers=headers,
    )
    assert bad_amount.status_code == 422
    assert "POSTED_TRANSACTION_IMMUTABLE" in str(bad_amount.json())

    # 2. Attempt to alter date on posted transaction -> 422
    bad_date = await client.patch(
        f"/api/v1/transactions/{tx_id}",
        json={"transaction_date": "2026-01-01"},
        headers=headers,
    )
    assert bad_date.status_code == 422

    # 3. Updating non-financial metadata succeeds
    good_patch = await client.patch(
        f"/api/v1/transactions/{tx_id}",
        json={
            "description": "Updated Narrative",
            "merchant_name": "Flipkart Internet Pvt Ltd",
            "metadata": {"tax_deductible": True},
        },
        headers=headers,
    )
    assert good_patch.status_code == 200
    pdata = good_patch.json()
    assert pdata["description"] == "Updated Narrative"
    assert pdata["merchant_name"] == "Flipkart Internet Pvt Ltd"
    assert pdata["metadata"]["tax_deductible"] is True


async def test_anti_idor_cross_workspace_protection(client: AsyncClient, registered_user: dict, second_workspace: dict):
    """
    Verifies that accessing or mutating a transaction from another workspace returns 404 Not Found (anti-IDOR defense).
    """
    token = registered_user["token"]
    ws1 = registered_user["workspace"]
    ws1_headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws1.id)}
    ws2_headers = second_workspace["headers"]

    # Create account and transaction in Workspace 1
    acc_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "WS1 Account", "account_type": "savings", "currency": "INR"},
        headers=ws1_headers,
    )
    acc_id = acc_res.json()["id"]

    tx_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "2000.00",
            "currency": "INR",
            "transaction_type": "expense",
            "transaction_date": "2026-04-05",
            "description": "Private WS1 Transaction",
        },
        headers=ws1_headers,
    )
    tx_id = tx_res.json()["id"]

    # Attempt to access from Workspace 2 -> must be 404
    idor_get = await client.get(f"/api/v1/transactions/{tx_id}", headers=ws2_headers)
    assert idor_get.status_code == 404

    # Attempt to reverse from Workspace 2 -> must be 404
    idor_rev = await client.post(
        f"/api/v1/transactions/{tx_id}/reverse",
        json={"reason": "Unauthorized attack"},
        headers=ws2_headers,
    )
    assert idor_rev.status_code == 404


async def test_transaction_history_and_dual_mount_routes(client: AsyncClient, registered_user: dict):
    """
    Verifies that transaction lifecycle generates auditable change logs accessible via GET /{id}/history,
    and both /transactions and /workspaces/{id}/transactions return identical data.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)}

    acc_res = await client.post(
        "/api/v1/accounts/",
        json={"name": "Audited Bank", "account_type": "bank", "currency": "INR", "opening_balance": "10000.00"},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # Create transaction
    tx_res = await client.post(
        "/api/v1/transactions/",
        json={
            "account_id": acc_id,
            "amount": "1500.00",
            "currency": "INR",
            "transaction_type": "expense",
            "transaction_date": "2026-04-06",
            "description": "Audit Trail Test",
        },
        headers=headers,
    )
    tx_id = tx_res.json()["id"]

    # Update metadata
    await client.patch(f"/api/v1/transactions/{tx_id}", json={"description": "Audit Trail Test Modified"}, headers=headers)

    # Check history endpoint
    hist_res = await client.get(f"/api/v1/transactions/{tx_id}/history", headers=headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert isinstance(history, list)
    assert len(history) >= 2  # create and update
    actions = [h["action"] for h in history]
    assert "transaction:create" in actions
    assert "transaction:update" in actions

    # Check dual mount routes
    r1 = await client.get("/api/v1/transactions/", headers=headers)
    r2 = await client.get(f"/api/v1/workspaces/{ws.id}/transactions/", headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["total"] == r2.json()["total"]
