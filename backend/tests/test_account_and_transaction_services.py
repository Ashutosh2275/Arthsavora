"""
Arthsavora Service Layer Tests — Account and Transaction Application Services
Verifies domain logic orchestration, Money validation, idempotent deduplication,
anti-IDOR defenses, and workspace-scoped data isolation.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ValidationException
from app.core.permissions import WorkspaceContext
from app.infrastructure.database.models import User, Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.account import AccountCreateRequest
from app.schemas.transaction import TransactionCreateRequest
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService


@pytest.fixture
async def workspace_context_fixture(db_session: AsyncSession) -> WorkspaceContext:
    """Creates a complete WorkspaceContext with owner membership for service testing."""
    u = User(
        id=uuid.uuid4(),
        email=f"svc_user_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Service Test User",
        hashed_password="hash",
    )
    ws = Workspace(
        id=uuid.uuid4(),
        name="Finance Services Workspace",
        slug=f"svc-ws-{uuid.uuid4().hex[:6]}",
        type="business",
        owner_id=u.id,
    )
    db_session.add_all([u, ws])
    await db_session.flush()

    mem = WorkspaceMember(
        workspace_id=ws.id,
        user_id=u.id,
        role=WorkspaceRole.OWNER.value,
        status="active",
    )
    db_session.add(mem)
    await db_session.commit()

    return WorkspaceContext(
        workspace=ws,
        membership=mem,
        current_user=u,
        role=WorkspaceRole.OWNER,
    )


async def test_account_service_create_and_list(db_session: AsyncSession, workspace_context_fixture: WorkspaceContext):
    """Verify AccountService provisions account and lists strictly within workspace."""
    ctx = workspace_context_fixture

    req = AccountCreateRequest(
        name="Axis Salary Account",
        account_type="savings",
        currency="INR",
        institution_name="Axis Bank",
        masked_identifier="XX9901",
    )

    account = await AccountService.create_account(db_session, ctx, req)
    assert account is not None
    assert account.id is not None
    assert account.name == "Axis Salary Account"
    assert account.currency == "INR"
    assert account.workspace_id == ctx.workspace.id

    # List accounts
    accounts = await AccountService.list_accounts(db_session, ctx)
    assert len(accounts) >= 1
    assert any(a.id == account.id for a in accounts)


async def test_account_service_invalid_currency_rejected(db_session: AsyncSession, workspace_context_fixture: WorkspaceContext):
    """Verify AccountService rejects invalid ISO 4217 currency."""
    ctx = workspace_context_fixture
    req = AccountCreateRequest(
        name="Bad Currency Account",
        account_type="savings",
        currency="ZZZ",
    )
    with pytest.raises(ValidationException):
        await AccountService.create_account(db_session, ctx, req)


async def test_account_service_anti_idor_get(db_session: AsyncSession, workspace_context_fixture: WorkspaceContext):
    """Verify get_account raises NotFoundException when account belongs to another workspace."""
    ctx = workspace_context_fixture

    # Account created in ctx workspace
    req = AccountCreateRequest(name="HDFC Current", account_type="current", currency="INR")
    account = await AccountService.create_account(db_session, ctx, req)

    # Another workspace context
    other_ws = Workspace(
        id=uuid.uuid4(),
        name="Other Workspace",
        slug=f"other-{uuid.uuid4().hex[:6]}",
        type="personal",
        owner_id=ctx.current_user.id,
    )
    db_session.add(other_ws)
    await db_session.flush()
    other_mem = WorkspaceMember(
        workspace_id=other_ws.id,
        user_id=ctx.current_user.id,
        role=WorkspaceRole.OWNER.value,
    )
    db_session.add(other_mem)
    await db_session.commit()

    other_ctx = WorkspaceContext(
        workspace=other_ws,
        membership=other_mem,
        current_user=ctx.current_user,
        role=WorkspaceRole.OWNER,
    )

    # Calling get_account with other_ctx must raise NotFoundException (Anti-IDOR)
    with pytest.raises(NotFoundException):
        await AccountService.get_account(db_session, other_ctx, account.id)


async def test_transaction_service_intake_and_idempotency(db_session: AsyncSession, workspace_context_fixture: WorkspaceContext):
    """Verify TransactionService intake, Money validation, and idempotent deduplication."""
    ctx = workspace_context_fixture

    # 1. Setup account
    acc_req = AccountCreateRequest(name="Federal Business", account_type="current", currency="INR")
    account = await AccountService.create_account(db_session, ctx, acc_req)

    # 2. Intake transaction
    ext_id = f"EXT-TX-{uuid.uuid4().hex[:8]}"
    tx_req = TransactionCreateRequest(
        account_id=account.id,
        amount=Decimal("45000.50"),
        currency="INR",
        transaction_type="income",
        transaction_date=date(2026, 3, 15),
        description="Software Consulting Invoice #1024",
        external_transaction_id=ext_id,
    )

    tx1, is_new1 = await TransactionService.intake_transaction(db_session, ctx, tx_req)
    assert is_new1 is True
    assert tx1.id is not None
    assert tx1.amount == Decimal("45000.5000")
    assert tx1.currency == "INR"

    # 3. Duplicate intake with identical external_transaction_id -> Idempotency
    tx2, is_new2 = await TransactionService.intake_transaction(db_session, ctx, tx_req)
    assert is_new2 is False
    assert tx2.id == tx1.id  # Same transaction returned without duplication

    # 4. Zero amount rejection
    zero_req = TransactionCreateRequest(
        account_id=account.id,
        amount=Decimal("0.00"),
        currency="INR",
        transaction_type="expense",
        transaction_date=date(2026, 3, 15),
        description="Zero test",
    )
    with pytest.raises(ValidationException):
        await TransactionService.intake_transaction(db_session, ctx, zero_req)


async def test_transaction_service_list_paginated(db_session: AsyncSession, workspace_context_fixture: WorkspaceContext):
    """Verify TransactionService list_transactions returns paginated records with total count."""
    ctx = workspace_context_fixture
    acc_req = AccountCreateRequest(name="Petty Cash", account_type="cash", currency="INR")
    account = await AccountService.create_account(db_session, ctx, acc_req)

    tx_req = TransactionCreateRequest(
        account_id=account.id,
        amount=Decimal("500.00"),
        currency="INR",
        transaction_type="expense",
        transaction_date=date(2026, 3, 10),
        description="Office stationary",
    )
    await TransactionService.intake_transaction(db_session, ctx, tx_req)

    items, total = await TransactionService.list_transactions(
        db_session,
        ctx,
        limit=10,
        offset=0,
        transaction_type="expense",
    )
    assert total >= 1
    assert any(t.account_id == account.id for t in items)
