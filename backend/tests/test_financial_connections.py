"""
Arthsavora Financial Connection, Account Aggregation & Normalization Test Suite
Tests pure domain logic, ReBIT AA provider registry, Mock Sandbox adapter,
end-to-end connection lifecycle, deduplication, balance reconciliation, API permissions,
and AI assistant tool integration.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.financial_connection import (
    AccountLinkStatus,
    ConnectionHealthStatus,
    ConnectionStatus,
    ConsentStatus,
    ReconciliationStatus,
    calculate_reconciliation_variance,
    compute_connection_health,
    evaluate_consent_validity,
    mask_account_identifier,
    normalize_transaction_direction,
)
from app.infrastructure.database.models import (
    Account,
    AccountBalanceSnapshot,
    ExternalAccountReference,
    FinancialConnection,
    FinancialConsent,
    FinancialProvider,
    ReconciliationRecord,
    SyncCheckpoint,
    SyncJob,
    Transaction,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceType,
)
from app.domain.assistant import ToolCallVO
from app.services.assistant.tool_executor import ToolExecutor
from app.services.financial_connection_service import FinancialConnectionService
from app.services.financial_providers.mock_sandbox_adapter import MockSandboxAdapter
from app.services.financial_providers.registry import FinancialProviderRegistry
from app.core.security import create_access_token, get_password_hash
from app.main import app


# -----------------------------------------------------------------------------
# 1. Pure Domain Logic Tests
# -----------------------------------------------------------------------------
def test_pure_domain_account_masking():
    """Verifies that account numbers are properly masked for privacy."""
    assert mask_account_identifier("123456789012") == "••••9012"
    assert mask_account_identifier("4289") == "••••4289"
    assert mask_account_identifier("12") == "••••12"
    assert mask_account_identifier("") == "••••"
    assert mask_account_identifier(None) == "••••"


def test_pure_domain_normalize_direction():
    """Verifies direction normalization and positive paise representation."""
    dir1, amt1 = normalize_transaction_direction(raw_direction="CR", amount_paise=50000)
    assert dir1 == "inflow"
    assert amt1 == 50000

    dir2, amt2 = normalize_transaction_direction(raw_direction="DEBIT", amount_paise=-12500)
    assert dir2 == "outflow"
    assert amt2 == 12500

    dir3, amt3 = normalize_transaction_direction(raw_type="deposit", amount_paise=30000)
    assert dir3 == "inflow"
    assert amt3 == 30000

    dir4, amt4 = normalize_transaction_direction(amount_paise=-45000)
    assert dir4 == "outflow"
    assert amt4 == 45000


def test_pure_domain_reconciliation_variance():
    """Verifies deterministic reconciliation calculations and explanations."""
    # Case 1: Perfectly matched
    rec1 = calculate_reconciliation_variance(
        provider_reported_balance_paise=25000000,
        calculated_book_balance_paise=25000000,
        unmatched_transactions_count=0,
    )
    assert rec1.status == ReconciliationStatus.MATCHED
    assert rec1.difference_paise == 0
    assert "perfectly reconciled" in rec1.explanation

    # Case 2: Balance variance with unmatched items
    rec2 = calculate_reconciliation_variance(
        provider_reported_balance_paise=25000000,
        calculated_book_balance_paise=24500000,
        unmatched_transactions_count=2,
    )
    assert rec2.status == ReconciliationStatus.REQUIRES_REVIEW
    assert rec2.difference_paise == 500000  # ₹5,000.00
    assert "₹5,000.00" in rec2.explanation


def test_pure_domain_connection_health():
    """Verifies operational health indicator states."""
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(days=1)
    future_time = now + timedelta(days=90)

    # Healthy
    h1 = compute_connection_health(
        connection_status=ConnectionStatus.ACTIVE,
        last_successful_sync_at=now - timedelta(hours=2),
        consent_expiry=future_time,
        sync_failure_count=0,
    )
    assert h1 == ConnectionHealthStatus.HEALTHY

    # Needs Auth
    h2 = compute_connection_health(
        connection_status=ConnectionStatus.INITIATED,
        last_successful_sync_at=None,
        consent_expiry=future_time,
    )
    assert h2 == ConnectionHealthStatus.NEEDS_AUTHORIZATION

    # Consent Expired
    h3 = compute_connection_health(
        connection_status=ConnectionStatus.ACTIVE,
        last_successful_sync_at=now - timedelta(days=1),
        consent_expiry=expired_time,
    )
    assert h3 == ConnectionHealthStatus.CONNECTION_EXPIRED

    # Provider Error / Failures
    h4 = compute_connection_health(
        connection_status=ConnectionStatus.FAILED,
        last_successful_sync_at=None,
        consent_expiry=future_time,
        sync_failure_count=3,
    )
    assert h4 == ConnectionHealthStatus.PROVIDER_UNAVAILABLE


def test_pure_domain_consent_validity():
    """Verifies consent temporal window validation and revocation."""
    now = datetime.now(timezone.utc)
    valid_from = now - timedelta(days=10)
    valid_to = now + timedelta(days=170)

    # Valid
    assert evaluate_consent_validity(ConsentStatus.ACTIVE, valid_from, valid_to, None, now) is True

    # Revoked
    assert evaluate_consent_validity(ConsentStatus.ACTIVE, valid_from, valid_to, now - timedelta(hours=1), now) is False

    # Pending approval
    assert evaluate_consent_validity(ConsentStatus.PENDING_USER_APPROVAL, valid_from, valid_to, None, now) is False


# -----------------------------------------------------------------------------
# 2. Provider Registry & Adapter Tests
# -----------------------------------------------------------------------------
def test_provider_registry():
    """Verifies provider catalog and adapter resolution."""
    catalog = FinancialProviderRegistry.get_catalog()
    assert len(catalog) >= 4

    setu = FinancialProviderRegistry.get_provider_definition("SETU_AA")
    assert setu is not None
    assert setu["country"] == "IN"
    assert setu["auth_method"] == "consent_handle"

    adapter = FinancialProviderRegistry.get_adapter("MOCK_SANDBOX_AA")
    assert isinstance(adapter, MockSandboxAdapter)
    assert adapter.provider_code == "MOCK_SANDBOX_AA"


@pytest.mark.asyncio
async def test_mock_sandbox_adapter_flow():
    """Verifies mock adapter consent, discovery, transaction, and balance feeds."""
    adapter = MockSandboxAdapter()
    ws_id = uuid.uuid4()
    u_id = uuid.uuid4()

    # 1. Initiate Consent
    consent = await adapter.initiate_consent(
        workspace_id=ws_id,
        user_id=u_id,
        institution_id="HDFC",
        purpose="Testing",
        data_categories=["TRANSACTIONS", "BALANCES"],
        account_types=["savings", "current"],
    )
    handle = consent["provider_consent_handle"]
    assert handle.startswith("MOCK_CONSENT_")
    assert "https://" in consent["authorization_url"]

    # 2. Check Consent Status
    status = await adapter.check_consent_status(handle)
    assert status["status"] == "active"

    # 3. Discover Accounts
    accounts = await adapter.discover_accounts(handle, "HDFC")
    assert len(accounts) == 2
    assert accounts[0].institution_name == "HDFC Bank Ltd"
    assert accounts[0].currency == "INR"
    assert accounts[0].current_balance_paise == 25400000

    # 4. Fetch Transactions
    today = date.today()
    txs, next_cursor = await adapter.fetch_transactions(
        provider_consent_handle=handle,
        provider_account_id=accounts[0].provider_account_id,
        from_date=today - timedelta(days=30),
        to_date=today,
    )
    assert len(txs) == 3
    assert txs[0].amount_paise == 5000000
    assert txs[0].direction == "inflow"

    # 5. Fetch Balances
    balances = await adapter.fetch_balances(handle, [accounts[0].provider_account_id])
    assert accounts[0].provider_account_id in balances
    assert balances[accounts[0].provider_account_id]["current_balance_paise"] == 25400000


# -----------------------------------------------------------------------------
# 3. Service Lifecycle & End-to-End Persistence Tests
# -----------------------------------------------------------------------------
@pytest.fixture
async def conn_test_context(db_session: AsyncSession):
    """Sets up a test user, workspace, and seeded providers for connection testing."""
    user = User(
        id=uuid.uuid4(),
        email=f"conn_user_{uuid.uuid4().hex[:6]}@arthsavora.in",
        full_name="Financial Connectivity Tester",
        hashed_password=get_password_hash("Password123!"),
        auth_provider="local",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)

    workspace = Workspace(
        id=uuid.uuid4(),
        name="Connectivity Sandbox Workspace",
        slug=f"conn-ws-{uuid.uuid4().hex[:6]}",
        type=WorkspaceType.PERSONAL.value,
        owner_id=user.id,
        default_currency="INR",
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER.value,
    )
    db_session.add(member)
    await db_session.commit()

    service = FinancialConnectionService(db_session)
    await service.repo.ensure_provider_catalog_seeded()
    await db_session.commit()

    return {"user": user, "workspace": workspace, "service": service, "session": db_session}


@pytest.mark.asyncio
async def test_financial_connection_full_lifecycle(conn_test_context):
    """
    Tests complete connection lifecycle:
    initiate -> authorize -> discover accounts -> link account -> sync -> reconcile -> revoke -> disconnect.
    """
    user = conn_test_context["user"]
    ws = conn_test_context["workspace"]
    service: FinancialConnectionService = conn_test_context["service"]
    session: AsyncSession = conn_test_context["session"]

    # 1. Initiate Connection
    connection, consent = await service.initiate_connection(
        workspace_id=ws.id,
        user_id=user.id,
        provider_code="MOCK_SANDBOX_AA",
        institution_id="HDFC",
        institution_name="HDFC Bank Ltd",
    )
    assert connection.status == ConnectionStatus.INITIATED.value
    assert consent.status == ConsentStatus.INITIATED.value

    # 2. Authorize Connection (also triggers auto-discovery)
    conn_auth = await service.authorize_connection(
        connection_id=connection.id,
        workspace_id=ws.id,
        user_id=user.id,
    )
    assert conn_auth.status == ConnectionStatus.ACTIVE.value
    assert conn_auth.health_status == ConnectionHealthStatus.HEALTHY.value

    # 3. Verify Discovered Accounts
    discovered = await service.repo.list_account_references(connection.id)
    assert len(discovered) == 2
    target_ref = discovered[0]
    assert target_ref.status == AccountLinkStatus.DISCOVERED.value

    # 4. Link Account (Create New Internal Account)
    linked_ref = await service.link_account(
        connection_id=connection.id,
        external_ref_id=target_ref.id,
        workspace_id=ws.id,
        user_id=user.id,
        create_new=True,
        account_name="Primary HDFC Savings Feed",
    )
    assert linked_ref.status == AccountLinkStatus.LINKED.value
    assert linked_ref.account_id is not None

    # Verify Account in Database
    acc_stmt = select(Account).where(Account.id == linked_ref.account_id)
    account = (await session.execute(acc_stmt)).scalar_one()
    assert account.connection_status == "connected"
    assert account.provider_name == "MOCK_SANDBOX_AA"
    assert account.provider_reported_balance_paise == 25400000

    # 5. Execute Data Synchronization
    sync_job = await service.sync_connection(
        connection_id=connection.id,
        workspace_id=ws.id,
        user_id=user.id,
        job_type="manual_sync",
    )
    assert sync_job.status == "completed"
    assert sync_job.records_retrieved == 3
    assert sync_job.records_imported == 3
    assert sync_job.duplicates_detected == 0

    # Verify Transactions in Database
    tx_stmt = select(Transaction).where(
        Transaction.workspace_id == ws.id,
        Transaction.account_id == account.id,
    )
    transactions = (await session.execute(tx_stmt)).scalars().all()
    assert len(transactions) == 3

    # 6. Idempotency Test: Run sync a second time
    sync_job_2 = await service.sync_connection(
        connection_id=connection.id,
        workspace_id=ws.id,
        user_id=user.id,
    )
    assert sync_job_2.records_imported == 0
    assert sync_job_2.duplicates_detected == 3

    # Verify no duplicate transactions were added
    txs_after = (await session.execute(tx_stmt)).scalars().all()
    assert len(txs_after) == 3

    # 7. Verify Reconciliation Records
    rec_records = await service.get_reconciliation_records(ws.id, connection_id=connection.id)
    assert len(rec_records) >= 1
    assert rec_records[0].provider_reported_balance_paise == 25400000

    # 8. Revoke Consent
    revoked_conn = await service.revoke_consent(
        connection_id=connection.id,
        workspace_id=ws.id,
        user_id=user.id,
        reason="User testing revocation",
    )
    assert revoked_conn.status == ConnectionStatus.REVOKED.value

    # Verify sync fails when consent revoked
    with pytest.raises(Exception):
        await service.sync_connection(connection.id, ws.id, user.id)

    # 9. Disconnect Connection
    success = await service.disconnect_connection(connection.id, ws.id, user.id)
    assert success is True

    # Verify account connection status is updated to disconnected
    refreshed_acc = (await session.execute(acc_stmt)).scalar_one()
    assert refreshed_acc.connection_status == "disconnected"


# -----------------------------------------------------------------------------
# 4. REST API & RBAC Security Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_financial_connections_api_and_rbac(conn_test_context, client):
    """Tests FastAPI financial connection endpoints with authentication and permission checks."""
    user = conn_test_context["user"]
    ws = conn_test_context["workspace"]
    service = conn_test_context["service"]

    token = create_access_token(subject=str(user.id), email=user.email)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": str(ws.id),
    }

    # 1. GET /api/v1/financial-providers
    resp_prov = await client.get("/api/v1/financial-providers", headers=headers)
    assert resp_prov.status_code == 200
    providers = resp_prov.json()
    assert len(providers) >= 4

    # 2. POST /api/v1/financial-connections
    init_payload = {
        "provider_code": "MOCK_SANDBOX_AA",
        "institution_id": "SBI",
        "institution_name": "State Bank of India",
        "purpose": "Automated Bookkeeping",
        "valid_days": 180,
    }
    resp_init = await client.post("/api/v1/financial-connections", json=init_payload, headers=headers)
    assert resp_init.status_code == 201
    conn_data = resp_init.json()
    conn_id = conn_data["id"]
    assert conn_data["institution_id"] == "SBI"
    assert conn_data["status"] == "initiated"

    # 3. POST /api/v1/financial-connections/{id}/authorize
    resp_auth = await client.post(f"/api/v1/financial-connections/{conn_id}/authorize", headers=headers)
    assert resp_auth.status_code == 200
    auth_data = resp_auth.json()
    assert auth_data["status"] == "active"
    assert auth_data["health_status"] == "healthy"

    # 4. GET /api/v1/financial-connections/{id}/accounts
    resp_acc = await client.get(f"/api/v1/financial-connections/{conn_id}/accounts", headers=headers)
    assert resp_acc.status_code == 200
    discovered = resp_acc.json()
    assert len(discovered) == 2
    ref_id = discovered[0]["id"]

    # 5. POST /api/v1/financial-connections/{id}/accounts/{ref_id}/link
    resp_link = await client.post(
        f"/api/v1/financial-connections/{conn_id}/accounts/{ref_id}/link",
        json={"create_new": True, "account_name": "SBI Test Account"},
        headers=headers,
    )
    assert resp_link.status_code == 200
    assert resp_link.json()["status"] == "linked"

    # 6. POST /api/v1/financial-connections/{id}/sync
    resp_sync = await client.post(f"/api/v1/financial-connections/{conn_id}/sync", headers=headers)
    assert resp_sync.status_code == 200
    sync_data = resp_sync.json()
    assert sync_data["status"] == "completed"
    assert sync_data["records_imported"] == 3

    # 7. GET /api/v1/financial-connections/{id}/reconciliation
    resp_rec = await client.get(f"/api/v1/financial-connections/{conn_id}/reconciliation", headers=headers)
    assert resp_rec.status_code == 200
    recs = resp_rec.json()
    assert len(recs) >= 1

    # 8. DELETE /api/v1/financial-connections/{id}
    resp_del = await client.delete(f"/api/v1/financial-connections/{conn_id}", headers=headers)
    assert resp_del.status_code == 204


# -----------------------------------------------------------------------------
# 5. AI Assistant Tools Integration Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ai_assistant_connection_tools(conn_test_context):
    """Verifies that AI assistant connection tools query live connections and reconciliation data."""
    user = conn_test_context["user"]
    ws = conn_test_context["workspace"]
    service = conn_test_context["service"]
    session = conn_test_context["session"]

    # Create and authorize a connection with a linked account
    conn, _ = await service.initiate_connection(
        workspace_id=ws.id,
        user_id=user.id,
        provider_code="MOCK_SANDBOX_AA",
        institution_id="ICICI",
        institution_name="ICICI Bank Ltd",
    )
    await service.authorize_connection(conn.id, ws.id, user.id)
    discovered = await service.repo.list_account_references(conn.id)
    await service.link_account(conn.id, discovered[0].id, ws.id, user.id, create_new=True)
    await service.sync_connection(conn.id, ws.id, user.id)

    executor = ToolExecutor(session)
    user_perms = {
        "connections:view",
        "connections:manage",
        "connections:sync",
    }

    # Tool 1: get_connected_accounts_overview
    tc1 = ToolCallVO(call_id="call_c1", tool_name="get_connected_accounts_overview", arguments={})
    res1 = await executor.execute_tool(tc1, ws.id, user_perms, user_id=user.id)
    assert res1.success is True
    assert res1.data["total_connected_accounts"] >= 1
    assert res1.data["accounts"][0]["institution_name"] == "ICICI Bank Ltd"

    # Tool 2: get_connection_sync_health
    tc2 = ToolCallVO(call_id="call_c2", tool_name="get_connection_sync_health", arguments={})
    res2 = await executor.execute_tool(tc2, ws.id, user_perms, user_id=user.id)
    assert res2.success is True
    assert res2.data["connection_count"] >= 1
    assert res2.data["connections"][0]["health_status"] == "healthy"

    # Tool 3: get_account_reconciliation_summary
    tc3 = ToolCallVO(call_id="call_c3", tool_name="get_account_reconciliation_summary", arguments={})
    res3 = await executor.execute_tool(tc3, ws.id, user_perms, user_id=user.id)
    assert res3.success is True
    assert res3.data["total_records"] >= 1
