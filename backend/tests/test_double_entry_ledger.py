"""
Arthsavora Comprehensive Double-Entry Ledger & Accounting Engine Tests
Tests PostgreSQL database-level triggers, debit-credit equality invariants,
Chart of Accounts seeding, accounting periods, immutability, reversals,
transaction-to-ledger mapping, and trial balance balance verification.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.exceptions import (
    ConflictException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.domain.accounting_types import AccountType, NormalBalance
from app.domain.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
    ImmutableJournalError,
    PeriodClosedError,
    UnbalancedJournalError,
)
from app.infrastructure.database.models import (
    Account,
    AccountingPeriod,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    Transaction,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.infrastructure.database.ledger import (
    post_journal_entry as legacy_post,
    reverse_journal_entry as legacy_reverse,
    validate_journal_balanced,
)
from app.services.ledger_service import LedgerService


@pytest.fixture
async def accounting_setup(db_session: AsyncSession):
    """Sets up an authoritative business workspace with users and seeded COA."""
    user = User(email=f"cfo_{uuid.uuid4().hex[:8]}@example.com", full_name="Chief Financial Officer")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(
        name="FinTech Corp India",
        slug=f"fintech-{uuid.uuid4().hex[:6]}",
        type="business",
        owner_id=user.id,
    )
    db_session.add(ws)
    await db_session.flush()

    # Add owner membership
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    db_session.add(member)
    await db_session.flush()

    service = LedgerService(db_session)
    accounts = await service.ensure_chart_of_accounts(ws.id)
    await db_session.commit()

    return {
        "user": user,
        "workspace": ws,
        "service": service,
        "accounts": accounts,
    }


# ===========================================================================
# 1. Chart of Accounts Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_chart_of_accounts_seeding_and_hierarchy(db_session: AsyncSession, accounting_setup):
    """Verifies standard Indian FinTech COA is seeded with parent-child relationships and system flags."""
    ws = accounting_setup["workspace"]
    service = LedgerService(db_session)

    accounts = await service.list_ledger_accounts(ws.id)
    assert len(accounts) >= 25

    # Check key system accounts
    codes = {a.code: a for a in accounts}
    assert "1010" in codes  # Cash
    assert "1021" in codes  # Bank
    assert "2010" in codes  # Credit Card Payable
    assert "3020" in codes  # Retained Earnings
    assert "3030" in codes  # Opening Balance Equity
    assert codes["3020"].is_system is True
    assert codes["3030"].is_system is True

    # Check parent-child hierarchy
    assert codes["1011"].parent_id is not None
    assert codes["1011"].parent_id == codes["1010"].id


@pytest.mark.asyncio
async def test_create_custom_ledger_account(db_session: AsyncSession, accounting_setup):
    """Allows creating custom ledger accounts within the workspace."""
    ws = accounting_setup["workspace"]
    service = LedgerService(db_session)

    custom = await service.create_ledger_account(
        workspace_id=ws.id,
        code="5085",
        name="Audit & Compliance Retainer",
        account_type="expense",
        normal_balance="debit",
        description="Statutory external auditing fees",
    )
    await db_session.commit()

    assert custom.id is not None
    assert custom.code == "5085"
    assert custom.is_system is False

    # Duplicate code rejection
    with pytest.raises(BusinessRuleViolationError):
        await service.create_ledger_account(
            workspace_id=ws.id,
            code="5085",
            name="Duplicate Code",
            account_type="expense",
        )


# ===========================================================================
# 2. Balanced Posting & Fundamental Accounting Invariant Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_balanced_journal_posting_workflow(db_session: AsyncSession, accounting_setup):
    """Verifies that a balanced draft entry transitions to posted and sets posting attribution."""
    ws = accounting_setup["workspace"]
    user = accounting_setup["user"]
    service = LedgerService(db_session)

    bank = await service.account_repo.get_by_code(ws.id, "1021")
    revenue = await service.account_repo.get_by_code(ws.id, "4020")

    draft = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"JE-TEST-{uuid.uuid4().hex[:6].upper()}",
        entry_date=date.today(),
        description="SaaS Subscription Enterprise Revenue",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("125000.0000")},
            {"ledger_account_id": revenue.id, "entry_type": "credit", "amount": Decimal("125000.0000")},
        ],
        created_by=user.id,
    )
    await db_session.commit()

    assert draft.status == "draft"

    # Post Entry
    posted = await service.post_journal_entry(
        workspace_id=ws.id,
        journal_id=draft.id,
        actor_id=user.id,
        correlation_id="req-test-1234",
    )
    await db_session.commit()

    assert posted.status == "posted"
    assert posted.posting_date is not None
    assert posted.posted_by_id == user.id

    # Verify duplicate posting raises ImmutableJournalError
    with pytest.raises(ImmutableJournalError):
        await service.post_journal_entry(ws.id, draft.id, actor_id=user.id)


@pytest.mark.asyncio
async def test_unbalanced_journal_rejected_by_service(db_session: AsyncSession, accounting_setup):
    """Rejects journal posting if Total Debits != Total Credits."""
    ws = accounting_setup["workspace"]
    user = accounting_setup["user"]
    service = LedgerService(db_session)

    bank = await service.account_repo.get_by_code(ws.id, "1021")
    revenue = await service.account_repo.get_by_code(ws.id, "4020")

    draft = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"JE-UNBAL-{uuid.uuid4().hex[:6].upper()}",
        entry_date=date.today(),
        description="Unbalanced Attempt",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("10000.0000")},
            {"ledger_account_id": revenue.id, "entry_type": "credit", "amount": Decimal("9500.0000")},
        ],
        created_by=user.id,
    )
    await db_session.commit()

    with pytest.raises(UnbalancedJournalError) as exc_info:
        await service.post_journal_entry(ws.id, draft.id, actor_id=user.id)

    assert "Difference: 500.0000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_database_trigger_enforces_balanced_posting(db_session: AsyncSession, accounting_setup):
    """
    Verifies that even if application logic were completely bypassed,
    the PostgreSQL deferred constraint trigger 'trg_journal_balanced_deferred'
    aborts the commit with error code P0001!
    """
    ws = accounting_setup["workspace"]
    service = LedgerService(db_session)
    bank = await service.account_repo.get_by_code(ws.id, "1021")
    revenue = await service.account_repo.get_by_code(ws.id, "4020")

    # Manually insert unbalanced lines directly into database with status = 'posted'
    raw_entry = JournalEntry(
        workspace_id=ws.id,
        entry_number=f"RAW-UNBAL-{uuid.uuid4().hex[:6].upper()}",
        entry_date=date.today(),
        description="Direct SQL Bypass Attempt",
        source_type="system",
        status="posted",
    )
    db_session.add(raw_entry)
    await db_session.flush()

    line1 = JournalLine(
        journal_entry_id=raw_entry.id,
        ledger_account_id=bank.id,
        line_number=1,
        entry_type="debit",
        amount=Decimal("50000.0000"),
    )
    line2 = JournalLine(
        journal_entry_id=raw_entry.id,
        ledger_account_id=revenue.id,
        line_number=2,
        entry_type="credit",
        amount=Decimal("49000.0000"),  # ₹1,000 difference!
    )
    db_session.add_all([line1, line2])

    with pytest.raises(DBAPIError) as exc_info:
        await db_session.commit()

    assert "P0001" in str(exc_info.value) or "Unbalanced posted journal entry" in str(exc_info.value)
    await db_session.rollback()


@pytest.mark.asyncio
async def test_database_trigger_prevents_posted_line_mutation(db_session: AsyncSession, accounting_setup):
    """
    Verifies that the PostgreSQL trigger 'trg_prevent_posted_line_mutation'
    rejects direct SQL UPDATE or DELETE on lines belonging to a posted entry.
    """
    ws = accounting_setup["workspace"]
    user = accounting_setup["user"]
    service = LedgerService(db_session)

    bank = await service.account_repo.get_by_code(ws.id, "1021")
    revenue = await service.account_repo.get_by_code(ws.id, "4020")

    draft = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"IMMUT-TEST-{uuid.uuid4().hex[:6].upper()}",
        entry_date=date.today(),
        description="Immutable Test Entry",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("10000.0000")},
            {"ledger_account_id": revenue.id, "entry_type": "credit", "amount": Decimal("10000.0000")},
        ],
        created_by=user.id,
    )
    await service.post_journal_entry(ws.id, draft.id, actor_id=user.id)
    await db_session.commit()

    # Attempt to modify a line of the posted entry directly
    stmt = select(JournalLine).where(JournalLine.journal_entry_id == draft.id).limit(1)
    line = (await db_session.execute(stmt)).scalar_one()

    line.amount = Decimal("99999.0000")
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.flush()

    assert "P0002" in str(exc_info.value) or "Cannot modify or delete journal lines" in str(exc_info.value)
    await db_session.rollback()


# ===========================================================================
# 3. Accounting Periods & Closed Period Enforcement
# ===========================================================================

@pytest.mark.asyncio
async def test_closed_period_prevents_posting(db_session: AsyncSession, accounting_setup):
    """Verifies that postings dated in closed accounting periods are rejected."""
    ws = accounting_setup["workspace"]
    user = accounting_setup["user"]
    service = LedgerService(db_session)

    # Create a historical period and close it
    period = await service.create_period(
        workspace_id=ws.id,
        fiscal_year="2026-2027",
        period_number=1,
        name="April 2026",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )
    await service.close_period(ws.id, period.id, user.id)
    await db_session.commit()

    bank = await service.account_repo.get_by_code(ws.id, "1021")
    revenue = await service.account_repo.get_by_code(ws.id, "4020")

    draft = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"JE-CLOSED-{uuid.uuid4().hex[:6].upper()}",
        entry_date=date(2026, 4, 15),  # Falls inside closed period!
        description="Historical Revenue Attempt",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("50000.0000")},
            {"ledger_account_id": revenue.id, "entry_type": "credit", "amount": Decimal("50000.0000")},
        ],
        created_by=user.id,
    )
    await db_session.commit()

    with pytest.raises(PeriodClosedError) as exc_info:
        await service.post_journal_entry(ws.id, draft.id, actor_id=user.id)

    assert "April 2026" in str(exc_info.value)

    # Reopen period permits posting
    await service.reopen_period(ws.id, period.id, user.id)
    await db_session.commit()

    posted = await service.post_journal_entry(ws.id, draft.id, actor_id=user.id)
    assert posted.status == "posted"


# ===========================================================================
# 4. Compensating Reversal Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_compensating_reversal_workflow(db_session: AsyncSession, accounting_setup):
    """Verifies that a posted entry is reversed with inverted lines and reference linkage."""
    ws = accounting_setup["workspace"]
    user = accounting_setup["user"]
    service = LedgerService(db_session)

    bank = await service.account_repo.get_by_code(ws.id, "1021")
    expense = await service.account_repo.get_by_code(ws.id, "5010")

    draft = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"JE-RENT-{uuid.uuid4().hex[:6].upper()}",
        entry_date=date.today(),
        description="Monthly Office Rent",
        lines_data=[
            {"ledger_account_id": expense.id, "entry_type": "debit", "amount": Decimal("40000.0000")},
            {"ledger_account_id": bank.id, "entry_type": "credit", "amount": Decimal("40000.0000")},
        ],
        created_by=user.id,
    )
    posted = await service.post_journal_entry(ws.id, draft.id, actor_id=user.id)
    await db_session.commit()

    # Execute reversal
    reversal = await service.reverse_journal_entry(
        workspace_id=ws.id,
        journal_id=posted.id,
        reversal_number=f"REV-RENT-{uuid.uuid4().hex[:6].upper()}",
        reason="Erroneous rent debit refunded by landlord",
        actor_id=user.id,
    )
    await db_session.commit()

    assert reversal.status == "posted"
    assert reversal.reversal_of_entry_id == posted.id
    assert posted.status == "reversed"
    assert posted.reversal_reason is not None

    # Verify reversed lines are exact inverted mirror
    reversal_loaded = await service.journal_repo.get_by_id(ws.id, reversal.id)
    assert reversal_loaded is not None
    rev_lines = reversal_loaded.lines
    assert len(rev_lines) == 2
    expense_rev = next(l for l in rev_lines if l.ledger_account_id == expense.id)
    bank_rev = next(l for l in rev_lines if l.ledger_account_id == bank.id)

    assert expense_rev.entry_type == "credit"
    assert bank_rev.entry_type == "debit"
    assert expense_rev.amount == Decimal("40000.0000")
    assert bank_rev.amount == Decimal("40000.0000")


# ===========================================================================
# 5. Transaction-to-Ledger Mapping Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_transaction_to_ledger_mappings(db_session: AsyncSession, accounting_setup):
    """Tests all standard transaction mappings to general ledger journal entries."""
    ws = accounting_setup["workspace"]
    user = accounting_setup["user"]
    service = LedgerService(db_session)

    # 1. Operational Bank Account
    bank_acct = Account(
        workspace_id=ws.id,
        name="HDFC Current",
        account_type="current",
        currency="INR",
    )
    # 2. Credit Card Account
    cc_acct = Account(
        workspace_id=ws.id,
        name="ICICI Sapphiro",
        account_type="credit_card",
        currency="INR",
    )
    db_session.add_all([bank_acct, cc_acct])
    await db_session.flush()

    # Case A: Income Transaction
    income_tx = Transaction(
        workspace_id=ws.id,
        account_id=bank_acct.id,
        transaction_type="income",
        direction="inflow",
        amount=Decimal("50000.0000"),
        amount_paise=5000000,
        currency="INR",
        transaction_date=datetime.now(timezone.utc),
        description="Client Retainer Invoice #101",
    )
    db_session.add(income_tx)
    await db_session.flush()

    je_income = await service.post_transaction_to_ledger(ws.id, income_tx, actor_id=user.id)
    assert je_income.status == "posted"
    assert je_income.source_type == "transaction"
    assert je_income.source_id == income_tx.id

    # Case B: Credit Card Purchase (Debit Expense, Credit CC Payable)
    cc_purchase_tx = Transaction(
        workspace_id=ws.id,
        account_id=cc_acct.id,
        transaction_type="purchase",
        direction="outflow",
        amount=Decimal("8500.0000"),
        amount_paise=850000,
        currency="INR",
        transaction_date=datetime.now(timezone.utc),
        description="Office Monitor Dell",
    )
    db_session.add(cc_purchase_tx)
    await db_session.flush()

    je_purchase = await service.post_transaction_to_ledger(ws.id, cc_purchase_tx, actor_id=user.id)
    assert je_purchase.status == "posted"

    # Case C: Credit Card Bill Payment (Debit CC Payable, Credit Bank - Zero Expense Double Counting!)
    cc_payment_tx = Transaction(
        workspace_id=ws.id,
        account_id=bank_acct.id,
        transaction_type="payment",
        direction="inflow",
        amount=Decimal("8500.0000"),
        amount_paise=850000,
        currency="INR",
        transaction_date=datetime.now(timezone.utc),
        description="Settlement of CC Statement",
    )
    db_session.add(cc_payment_tx)
    await db_session.flush()

    je_payment = await service.post_transaction_to_ledger(ws.id, cc_payment_tx, actor_id=user.id)
    assert je_payment.status == "posted"

    # Case D: Opening Balance (Debit Asset, Credit Opening Balance Equity)
    opening_tx = Transaction(
        workspace_id=ws.id,
        account_id=bank_acct.id,
        transaction_type="opening_balance",
        direction="inflow",
        amount=Decimal("200000.0000"),
        amount_paise=20000000,
        currency="INR",
        transaction_date=datetime.now(timezone.utc),
        description="Initial Bank Balance",
    )
    db_session.add(opening_tx)
    await db_session.flush()

    je_opening = await service.post_transaction_to_ledger(ws.id, opening_tx, actor_id=user.id)
    assert je_opening.status == "posted"


# ===========================================================================
# 6. Trial Balance & Derived Balance Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_trial_balance_equality_invariant(db_session: AsyncSession, accounting_setup):
    """
    Verifies that the Trial Balance report aggregates all posted ledger activity
    and rigorously proves Total Debits == Total Credits with zero discrepancy.
    """
    ws = accounting_setup["workspace"]
    user = accounting_setup["user"]
    service = LedgerService(db_session)

    bank = await service.account_repo.get_by_code(ws.id, "1021")
    equity = await service.account_repo.get_by_code(ws.id, "3030")
    revenue = await service.account_repo.get_by_code(ws.id, "4020")
    rent = await service.account_repo.get_by_code(ws.id, "5010")
    utilities = await service.account_repo.get_by_code(ws.id, "5030")

    # Entry 1: Opening capital ₹5,00,000 (Debit Bank, Credit Equity)
    je1 = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"TB-01-{uuid.uuid4().hex[:6]}",
        entry_date=date.today(),
        description="Opening Capital Deposit",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("500000.0000")},
            {"ledger_account_id": equity.id, "entry_type": "credit", "amount": Decimal("500000.0000")},
        ],
        created_by=user.id,
    )
    await service.post_journal_entry(ws.id, je1.id, actor_id=user.id)

    # Entry 2: Customer Revenue ₹1,50,000 (Debit Bank, Credit Revenue)
    je2 = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"TB-02-{uuid.uuid4().hex[:6]}",
        entry_date=date.today(),
        description="Customer Payment Received",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("150000.0000")},
            {"ledger_account_id": revenue.id, "entry_type": "credit", "amount": Decimal("150000.0000")},
        ],
        created_by=user.id,
    )
    await service.post_journal_entry(ws.id, je2.id, actor_id=user.id)

    # Entry 3: Expenses ₹60,000 Rent + ₹15,000 Utilities (Debit Expenses, Credit Bank)
    je3 = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"TB-03-{uuid.uuid4().hex[:6]}",
        entry_date=date.today(),
        description="Office Rent & Electricity Payment",
        lines_data=[
            {"ledger_account_id": rent.id, "entry_type": "debit", "amount": Decimal("60000.0000")},
            {"ledger_account_id": utilities.id, "entry_type": "debit", "amount": Decimal("15000.0000")},
            {"ledger_account_id": bank.id, "entry_type": "credit", "amount": Decimal("75000.0000")},
        ],
        created_by=user.id,
    )
    await service.post_journal_entry(ws.id, je3.id, actor_id=user.id)
    await db_session.commit()

    # Verify Trial Balance
    tb = await service.get_trial_balance(ws.id)

    assert tb["is_balanced"] is True
    assert tb["difference"] == Decimal("0.0000")
    assert tb["difference_paise"] == 0

    # Total debits = Total credits
    # Bank net debit = 500k + 150k - 75k = 575k
    # Rent debit = 60k
    # Utilities debit = 15k
    # Total TB Debits = 575k + 60k + 15k = 650,000.0000
    # Equity credit = 500k
    # Revenue credit = 150k
    # Total TB Credits = 500k + 150k = 650,000.0000
    assert tb["total_debits"] == Decimal("650000.0000")
    assert tb["total_credits"] == Decimal("650000.0000")
    assert tb["total_debits_paise"] == 65000000
    assert tb["total_credits_paise"] == 65000000

    # Test Derived Account Balance
    bank_balance = await service.get_account_balance(ws.id, bank.id)
    assert bank_balance["net_balance"] == Decimal("575000.0000")
    assert bank_balance["net_balance_paise"] == 57500000
