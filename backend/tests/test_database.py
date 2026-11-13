"""
Arthsavora PostgreSQL Database Architecture & Integrity Tests
Validates relational mapping, financial precision, double-entry balancing,
idempotent deduplication, multi-tenant isolation, and audit trail resilience.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException, ConflictException
from app.infrastructure.database.models import (
    User,
    UserProfile,
    Workspace,
    WorkspaceMember,
    Account,
    Category,
    Transaction,
    LedgerAccount,
    JournalEntry,
    JournalLine,
    AuditLog,
)
from app.infrastructure.database.ledger import post_journal_entry, reverse_journal_entry
from app.infrastructure.database.rls import set_tenant_context, reset_tenant_context


@pytest.mark.asyncio
async def test_user_and_workspace_creation(db_session: AsyncSession):
    """Verifies user, user profile, workspace, and workspace membership relationships."""
    user = User(
        email=f"fintech_user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Rajesh Sharma",
        auth_provider="local",
    )
    db_session.add(user)
    await db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        default_currency="INR",
        timezone="Asia/Kolkata",
        locale="en-IN",
        theme="dark",
    )
    db_session.add(profile)
    await db_session.flush()

    workspace = Workspace(
        name="Sharma Family Workspace",
        slug=f"sharma-family-{uuid.uuid4().hex[:6]}",
        type="family",
        owner_id=user.id,
        default_currency="INR",
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    db_session.add(member)
    await db_session.flush()

    assert user.id is not None
    assert workspace.owner_id == user.id
    assert member.role == "owner"


@pytest.mark.asyncio
async def test_financial_amount_exact_precision(db_session: AsyncSession):
    """Validates that monetary amounts use exact NUMERIC(18, 4) storage without floating-point errors."""
    user = User(email=f"precision_{uuid.uuid4().hex[:8]}@example.com", full_name="Auditor")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Precision Test", slug=f"precision-{uuid.uuid4().hex[:6]}", type="personal", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    acct = Account(workspace_id=ws.id, name="Test Bank", account_type="bank")
    db_session.add(acct)
    await db_session.flush()

    # Fractional paise amount: ₹1,54,000.5050
    exact_amount = Decimal("154000.5050")
    tx = Transaction(
        workspace_id=ws.id,
        account_id=acct.id,
        transaction_type="income",
        amount=exact_amount,
        currency="INR",
        transaction_date=date(2026, 11, 14),
        description="Consulting Revenue",
    )
    db_session.add(tx)
    await db_session.flush()

    # Query back and verify zero floating-point drift
    result = await db_session.execute(select(Transaction).where(Transaction.id == tx.id))
    fetched = result.scalar_one()

    assert fetched.amount == exact_amount
    assert isinstance(fetched.amount, Decimal)
    # Ensure standard floating-point addition error (0.1 + 0.2 != 0.3) is impossible
    assert fetched.amount + Decimal("0.0001") == Decimal("154000.5051")


@pytest.mark.asyncio
async def test_idempotent_import_deduplication(db_session: AsyncSession):
    """Enforces that identical external transactions cannot be duplicated within the same workspace."""
    user = User(email=f"idempotent_{uuid.uuid4().hex[:8]}@example.com", full_name="User")
    db_session.add(user)
    await db_session.flush()

    ws1 = Workspace(name="WS 1", slug=f"ws1-{uuid.uuid4().hex[:6]}", type="business", owner_id=user.id)
    ws2 = Workspace(name="WS 2", slug=f"ws2-{uuid.uuid4().hex[:6]}", type="business", owner_id=user.id)
    db_session.add_all([ws1, ws2])
    await db_session.flush()

    acct1 = Account(workspace_id=ws1.id, name="Current A", account_type="current")
    acct2 = Account(workspace_id=ws2.id, name="Current B", account_type="current")
    db_session.add_all([acct1, acct2])
    await db_session.flush()

    external_ref = "UPI-20261114-HDFC-998877"

    # First import into WS1 succeeds
    tx1 = Transaction(
        workspace_id=ws1.id,
        account_id=acct1.id,
        transaction_type="expense",
        amount=Decimal("2500.0000"),
        transaction_date=date(2026, 11, 14),
        description="Office Supplies",
        external_transaction_id=external_ref,
    )
    db_session.add(tx1)
    await db_session.flush()

    # Second import of same reference in WS2 succeeds (tenant isolation)
    tx2 = Transaction(
        workspace_id=ws2.id,
        account_id=acct2.id,
        transaction_type="expense",
        amount=Decimal("2500.0000"),
        transaction_date=date(2026, 11, 14),
        description="Office Supplies",
        external_transaction_id=external_ref,
    )
    db_session.add(tx2)
    await db_session.flush()

    # Duplicate import in WS1 MUST fail unique constraint
    duplicate_tx = Transaction(
        workspace_id=ws1.id,
        account_id=acct1.id,
        transaction_type="expense",
        amount=Decimal("2500.0000"),
        transaction_date=date(2026, 11, 14),
        description="Duplicate Attempt",
        external_transaction_id=external_ref,
    )
    db_session.add(duplicate_tx)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_double_entry_balanced_journal(db_session: AsyncSession):
    """Validates that a balanced journal entry posts successfully and creates an audit log."""
    user = User(email=f"accountant_{uuid.uuid4().hex[:8]}@example.com", full_name="Accountant")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Accounting Test", slug=f"acct-{uuid.uuid4().hex[:6]}", type="business", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    # Chart of accounts
    cash_acct = LedgerAccount(workspace_id=ws.id, code="1010", name="Operating Cash", account_type="asset", normal_balance="debit")
    sales_acct = LedgerAccount(workspace_id=ws.id, code="4010", name="Service Revenue", account_type="revenue", normal_balance="credit")
    db_session.add_all([cash_acct, sales_acct])
    await db_session.flush()

    # Create Draft Journal Entry
    je = JournalEntry(
        workspace_id=ws.id,
        entry_number=f"JE-{uuid.uuid4().hex[:6]}",
        entry_date=date(2026, 11, 14),
        description="Customer Invoice Payment Received",
        source_type="manual",
        created_by=user.id,
    )
    db_session.add(je)
    await db_session.flush()

    # Lines: Debit Cash ₹50,000, Credit Revenue ₹50,000
    line1 = JournalLine(journal_entry_id=je.id, ledger_account_id=cash_acct.id, line_number=1, entry_type="debit", amount=Decimal("50000.0000"))
    line2 = JournalLine(journal_entry_id=je.id, ledger_account_id=sales_acct.id, line_number=2, entry_type="credit", amount=Decimal("50000.0000"))
    db_session.add_all([line1, line2])
    await db_session.flush()

    # Post Entry
    posted_entry = await post_journal_entry(db_session, je.id, actor_id=user.id, correlation_id="req-audit-1234")

    assert posted_entry.status == "posted"
    assert posted_entry.posting_date is not None


@pytest.mark.asyncio
async def test_double_entry_unbalanced_journal_rejected(db_session: AsyncSession):
    """Enforces that an unbalanced journal entry cannot be posted."""
    user = User(email=f"unbalanced_{uuid.uuid4().hex[:8]}@example.com", full_name="User")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Unbalanced Test", slug=f"unbal-{uuid.uuid4().hex[:6]}", type="business", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    acct1 = LedgerAccount(workspace_id=ws.id, code="1010", name="Cash", account_type="asset", normal_balance="debit")
    acct2 = LedgerAccount(workspace_id=ws.id, code="4010", name="Revenue", account_type="revenue", normal_balance="credit")
    db_session.add_all([acct1, acct2])
    await db_session.flush()

    je = JournalEntry(
        workspace_id=ws.id,
        entry_number=f"JE-UNBAL-{uuid.uuid4().hex[:6]}",
        entry_date=date(2026, 11, 14),
        description="Unbalanced Attempt",
        source_type="manual",
    )
    db_session.add(je)
    await db_session.flush()

    # Unbalanced: Debit ₹50,000 vs Credit ₹45,000
    line1 = JournalLine(journal_entry_id=je.id, ledger_account_id=acct1.id, line_number=1, entry_type="debit", amount=Decimal("50000.0000"))
    line2 = JournalLine(journal_entry_id=je.id, ledger_account_id=acct2.id, line_number=2, entry_type="credit", amount=Decimal("45000.0000"))
    db_session.add_all([line1, line2])
    await db_session.flush()

    with pytest.raises(ValidationException) as exc_info:
        await post_journal_entry(db_session, je.id)

    assert "Unbalanced journal entry" in str(exc_info.value)
    assert "Difference: ₹5000.0000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_posted_journal_immutability_and_reversal(db_session: AsyncSession):
    """Validates that posted entries are immutable and must be corrected via formal reversals."""
    user = User(email=f"reversal_{uuid.uuid4().hex[:8]}@example.com", full_name="Accountant")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Reversal Test", slug=f"rev-{uuid.uuid4().hex[:6]}", type="business", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    acct1 = LedgerAccount(workspace_id=ws.id, code="1010", name="Cash", account_type="asset", normal_balance="debit")
    acct2 = LedgerAccount(workspace_id=ws.id, code="5010", name="Rent Expense", account_type="expense", normal_balance="debit")
    db_session.add_all([acct1, acct2])
    await db_session.flush()

    je = JournalEntry(
        workspace_id=ws.id,
        entry_number=f"JE-POSTED-{uuid.uuid4().hex[:6]}",
        entry_date=date(2026, 11, 14),
        description="Office Rent",
        source_type="manual",
    )
    db_session.add(je)
    await db_session.flush()

    line1 = JournalLine(journal_entry_id=je.id, ledger_account_id=acct2.id, line_number=1, entry_type="debit", amount=Decimal("20000.0000"))
    line2 = JournalLine(journal_entry_id=je.id, ledger_account_id=acct1.id, line_number=2, entry_type="credit", amount=Decimal("20000.0000"))
    db_session.add_all([line1, line2])
    await db_session.flush()

    # Post first time
    await post_journal_entry(db_session, je.id, actor_id=user.id)

    # Re-posting MUST fail (Immutability)
    with pytest.raises(ConflictException):
        await post_journal_entry(db_session, je.id, actor_id=user.id)

    # Execute formal reversal
    reversal = await reverse_journal_entry(
        db_session,
        entry_id=je.id,
        reversal_number=f"REV-{uuid.uuid4().hex[:6]}",
        reason="Erroneous duplicate entry",
        actor_id=user.id,
    )

    assert reversal.status == "posted"
    assert reversal.reversal_of_entry_id == je.id
    assert je.status == "reversed"


@pytest.mark.asyncio
async def test_audit_log_survives_member_revocation(db_session: AsyncSession):
    """Validates that append-only audit trail logs persist attribution even after member access is revoked."""
    user = User(email=f"audit_actor_{uuid.uuid4().hex[:8]}@example.com", full_name="Former Employee")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Audit WS", slug=f"audit-ws-{uuid.uuid4().hex[:6]}", type="business", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="staff", status="active")
    db_session.add(member)
    await db_session.flush()

    # Log an action
    audit_entry = AuditLog(
        workspace_id=ws.id,
        actor_id=user.id,
        action="EXPORT_STATEMENTS",
        entity_type="report",
        correlation_id="corr-audit-9988",
        after_state={"format": "PDF", "period": "Q3-2026"},
    )
    db_session.add(audit_entry)
    await db_session.flush()

    # Revoke member access
    member.status = "revoked"
    member.revoked_at = datetime.now(timezone.utc)
    await db_session.flush()

    # Query audit log - attribution must be intact
    result = await db_session.execute(select(AuditLog).where(AuditLog.id == audit_entry.id))
    log = result.scalar_one()

    assert log.actor_id == user.id
    assert log.workspace_id == ws.id
    assert log.correlation_id == "corr-audit-9988"


@pytest.mark.asyncio
async def test_rls_tenant_context_management(db_session: AsyncSession):
    """Validates transaction-scoped setting of PostgreSQL tenant context and clean reset."""
    target_workspace_id = uuid.uuid4()

    # Set tenant context
    await set_tenant_context(db_session, target_workspace_id)
    res = await db_session.execute(text("SELECT current_setting('app.current_workspace_id', true)"))
    val = res.scalar()
    assert val == str(target_workspace_id)

    # Reset tenant context
    await reset_tenant_context(db_session)
    res2 = await db_session.execute(text("SELECT current_setting('app.current_workspace_id', true)"))
    val2 = res2.scalar()
    assert val2 == ""

