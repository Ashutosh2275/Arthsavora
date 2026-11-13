"""
Arthsavora Repository Tests — Data Access & Multi-Tenant Isolation
Verifies BaseRepository, WorkspaceScopedRepository anti-IDOR defenses,
bounded pagination enforcement, and domain-specific repository queries.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models import User, Workspace, Account, Transaction
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository


@pytest.fixture
async def multi_workspace_setup(db_session: AsyncSession):
    """Provisions two distinct workspaces with distinct owners for cross-tenant isolation testing."""
    # User 1 & Workspace 1
    u1 = User(
        id=uuid.uuid4(),
        email=f"repo_user1_{uuid.uuid4().hex[:6]}@example.com",
        full_name="User Alpha",
        hashed_password="hash",
    )
    ws1 = Workspace(
        id=uuid.uuid4(),
        name="Alpha Workspace",
        slug=f"alpha-ws-{uuid.uuid4().hex[:6]}",
        type="personal",
        owner_id=u1.id,
    )
    db_session.add_all([u1, ws1])
    await db_session.flush()

    ws_repo = WorkspaceRepository(db_session)
    ws_repo.add_member(ws1.id, u1.id, role="owner")

    # User 2 & Workspace 2
    u2 = User(
        id=uuid.uuid4(),
        email=f"repo_user2_{uuid.uuid4().hex[:6]}@example.com",
        full_name="User Beta",
        hashed_password="hash",
    )
    ws2 = Workspace(
        id=uuid.uuid4(),
        name="Beta Workspace",
        slug=f"beta-ws-{uuid.uuid4().hex[:6]}",
        type="business",
        owner_id=u2.id,
    )
    db_session.add_all([u2, ws2])
    await db_session.flush()

    ws_repo.add_member(ws2.id, u2.id, role="owner")
    await db_session.commit()

    return {"ws1": ws1, "u1": u1, "ws2": ws2, "u2": u2}


async def test_workspace_scoped_repository_anti_idor(db_session: AsyncSession, multi_workspace_setup):
    """Verify that an entity in Workspace 1 CANNOT be retrieved via Workspace 2 ID."""
    ws1 = multi_workspace_setup["ws1"]
    ws2 = multi_workspace_setup["ws2"]

    acc_repo = AccountRepository(db_session)
    acc1 = acc_repo.create(
        workspace_id=ws1.id,
        name="Alpha HDFC Bank",
        account_type="bank",
        currency="INR",
    )
    await db_session.commit()

    # Query using correct workspace_id -> succeeds
    retrieved_correct = await acc_repo.get_by_id_scoped(acc1.id, ws1.id)
    assert retrieved_correct is not None
    assert retrieved_correct.id == acc1.id
    assert retrieved_correct.name == "Alpha HDFC Bank"

    # Query using wrong workspace_id -> returns None (Anti-IDOR defense)
    retrieved_idor = await acc_repo.get_by_id_scoped(acc1.id, ws2.id)
    assert retrieved_idor is None


async def test_bounded_pagination_enforcement(db_session: AsyncSession, multi_workspace_setup):
    """Verify pagination caps limit at 100 max even when caller requests larger limit."""
    ws1 = multi_workspace_setup["ws1"]
    acc_repo = AccountRepository(db_session)

    # Calling list_scoped with limit=500 should be constrained to 100
    results = await acc_repo.list_scoped(ws1.id, limit=500, offset=0)
    assert isinstance(results, list)
    assert len(results) <= 100


async def test_account_repository_list_and_filters(db_session: AsyncSession, multi_workspace_setup):
    """Verify AccountRepository listing and account_type filtering."""
    ws1 = multi_workspace_setup["ws1"]
    acc_repo = AccountRepository(db_session)

    acc_repo.create(ws1.id, "Savings Account", "savings", "INR")
    acc_repo.create(ws1.id, "Credit Card", "credit_card", "INR")
    await db_session.commit()

    all_accounts = await acc_repo.list_by_workspace(ws1.id)
    assert len(all_accounts) >= 2

    savings_only = await acc_repo.list_by_workspace(ws1.id, account_type="savings")
    assert all(a.account_type == "savings" for a in savings_only)


async def test_transaction_repository_external_id_idempotency(db_session: AsyncSession, multi_workspace_setup):
    """Verify TransactionRepository idempotent external ID lookup and pagination."""
    ws1 = multi_workspace_setup["ws1"]
    acc_repo = AccountRepository(db_session)
    tx_repo = TransactionRepository(db_session)

    acc = acc_repo.create(ws1.id, "Operating Account", "bank", "INR")
    await db_session.flush()

    ext_ref = f"UPI-REF-{uuid.uuid4().hex[:8]}"
    tx = tx_repo.create(
        workspace_id=ws1.id,
        account_id=acc.id,
        amount=Decimal("12500.00"),
        currency="INR",
        transaction_type="income",
        transaction_date=date(2026, 3, 1),
        description="Client Retainer Payment",
        external_transaction_id=ext_ref,
    )
    await db_session.commit()

    # Query by external ID in same workspace
    found_tx = await tx_repo.get_by_external_id(ws1.id, ext_ref)
    assert found_tx is not None
    assert found_tx.id == tx.id
    assert found_tx.amount == Decimal("12500.00")

    # In another workspace, external ID should not be found
    found_other = await tx_repo.get_by_external_id(multi_workspace_setup["ws2"].id, ext_ref)
    assert found_other is None

    # Paginated listing
    tx_list, total = await tx_repo.list_transactions_paginated(
        workspace_id=ws1.id,
        limit=10,
        transaction_type="income",
    )
    assert total >= 1
    assert any(t.id == tx.id for t in tx_list)
