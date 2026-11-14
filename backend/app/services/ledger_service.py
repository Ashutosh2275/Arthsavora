"""
Arthsavora Double-Entry General Ledger Service Layer
Coordinates Chart of Accounts, accounting periods, journal posting workflows,
immutability protocols, transaction-to-ledger mappings, and trial balance calculations.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.accounting_types import (
    ACCOUNT_TYPE_TO_LEDGER_CODE,
    NORMAL_BALANCE_MAP,
    AccountType,
    JournalSourceType,
    JournalStatus,
    NormalBalance,
    PeriodStatus,
)
from app.domain.events import (
    DomainEventCollector,
    create_journal_created_event,
    create_journal_posted_event,
    create_journal_reversed_event,
    create_period_closed_event,
)
from app.domain.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
    ImmutableJournalError,
    PeriodClosedError,
    SystemAccountProtectedError,
    UnbalancedJournalError,
)
from app.infrastructure.database.models.accounting import (
    AccountingPeriod,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.ledger_repository import (
    AccountingPeriodRepository,
    JournalEntryRepository,
    LedgerAccountRepository,
)


class LedgerService:
    """Application service for the double-entry accounting engine and general ledger."""

    def __init__(self, session: AsyncSession, event_collector: Optional[DomainEventCollector] = None):
        self.session = session
        self.event_collector = event_collector or DomainEventCollector()
        self.account_repo = LedgerAccountRepository(session)
        self.period_repo = AccountingPeriodRepository(session)
        self.journal_repo = JournalEntryRepository(session)

    # ---------------------------------------------------------------------------
    # Chart of Accounts Management
    # ---------------------------------------------------------------------------

    async def ensure_chart_of_accounts(self, workspace_id: uuid.UUID) -> List[LedgerAccount]:
        """Ensures default Chart of Accounts is initialized for the workspace."""
        return await self.account_repo.seed_default_chart_of_accounts(workspace_id)

    async def list_ledger_accounts(
        self,
        workspace_id: uuid.UUID,
        is_active: Optional[bool] = None,
        account_type: Optional[str] = None,
    ) -> List[LedgerAccount]:
        """Lists all ledger accounts, seeding defaults if empty."""
        accounts = await self.account_repo.list_by_workspace(workspace_id, is_active, account_type)
        if not accounts:
            accounts = await self.account_repo.seed_default_chart_of_accounts(workspace_id)
        return accounts

    async def get_ledger_account(
        self,
        workspace_id: uuid.UUID,
        ledger_account_id: uuid.UUID,
    ) -> LedgerAccount:
        """Retrieves a single ledger account, raising EntityNotFoundError if missing."""
        account = await self.account_repo.get_by_id(workspace_id, ledger_account_id)
        if not account:
            raise EntityNotFoundError("LedgerAccount", ledger_account_id)
        return account

    async def create_ledger_account(
        self,
        workspace_id: uuid.UUID,
        code: str,
        name: str,
        account_type: str,
        normal_balance: Optional[str] = None,
        sub_type: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[uuid.UUID] = None,
        linked_account_id: Optional[uuid.UUID] = None,
    ) -> LedgerAccount:
        """Creates a custom ledger account with uniqueness and hierarchy validation."""
        # Check uniqueness of code in workspace
        existing = await self.account_repo.get_by_code(workspace_id, code)
        if existing:
            raise BusinessRuleViolationError(
                "DUPLICATE_LEDGER_CODE",
                f"A ledger account with code '{code}' already exists in this workspace.",
            )

        # Validate account type
        if account_type not in [t.value for t in AccountType]:
            raise BusinessRuleViolationError(
                "INVALID_ACCOUNT_TYPE",
                f"Invalid account type '{account_type}'. Must be one of {[t.value for t in AccountType]}.",
            )

        # Determine normal balance
        resolved_normal = normal_balance or NORMAL_BALANCE_MAP[AccountType(account_type)].value

        # Validate parent account if specified
        if parent_id:
            parent = await self.account_repo.get_by_id(workspace_id, parent_id)
            if not parent:
                raise EntityNotFoundError("LedgerAccount", parent_id)

        return await self.account_repo.create(
            workspace_id=workspace_id,
            code=code,
            name=name,
            account_type=account_type,
            normal_balance=resolved_normal,
            sub_type=sub_type,
            description=description,
            parent_id=parent_id,
            linked_account_id=linked_account_id,
            is_system=False,
        )

    async def update_ledger_account(
        self,
        workspace_id: uuid.UUID,
        ledger_account_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> LedgerAccount:
        """Updates metadata on a ledger account, protecting system critical accounts."""
        account = await self.get_ledger_account(workspace_id, ledger_account_id)

        if account.is_system and is_active is False:
            raise SystemAccountProtectedError(account.code, account.name)

        if name is not None:
            account.name = name
        if description is not None:
            account.description = description
        if is_active is not None:
            account.is_active = is_active

        await self.session.flush()
        return account

    # ---------------------------------------------------------------------------
    # Accounting Period Management
    # ---------------------------------------------------------------------------

    async def list_periods(
        self,
        workspace_id: uuid.UUID,
        fiscal_year: Optional[str] = None,
    ) -> List[AccountingPeriod]:
        """Lists accounting periods for the workspace."""
        return await self.period_repo.list_by_workspace(workspace_id, fiscal_year)

    async def create_period(
        self,
        workspace_id: uuid.UUID,
        fiscal_year: str,
        period_number: int,
        name: str,
        start_date: date,
        end_date: date,
    ) -> AccountingPeriod:
        """Creates an accounting period with date boundary validation."""
        if start_date > end_date:
            raise BusinessRuleViolationError("INVALID_PERIOD_DATES", "start_date cannot be after end_date.")

        return await self.period_repo.create(
            workspace_id=workspace_id,
            fiscal_year=fiscal_year,
            period_number=period_number,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status="open",
        )

    async def close_period(
        self,
        workspace_id: uuid.UUID,
        period_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> AccountingPeriod:
        """Closes an accounting period with audit logging."""
        period = await self.period_repo.get_by_id(workspace_id, period_id)
        if not period:
            raise EntityNotFoundError("AccountingPeriod", period_id)

        if period.status == "closed":
            return period

        closed = await self.period_repo.close_period(period, actor_id)

        # Audit Log
        audit = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="CLOSE_ACCOUNTING_PERIOD",
            entity_type="accounting_period",
            entity_id=period.id,
            before_state={"status": "open"},
            after_state={"status": "closed", "closed_at": closed.closed_at.isoformat() if closed.closed_at else None},
        )
        self.session.add(audit)
        await self.session.flush()

        self.event_collector.record(
            create_period_closed_event(
                workspace_id=workspace_id,
                period_id=period.id,
                fiscal_year=period.fiscal_year,
                period_number=period.period_number,
                period_name=period.name,
                actor_id=actor_id,
            )
        )
        return closed

    async def reopen_period(
        self,
        workspace_id: uuid.UUID,
        period_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> AccountingPeriod:
        """Reopens a closed accounting period."""
        period = await self.period_repo.get_by_id(workspace_id, period_id)
        if not period:
            raise EntityNotFoundError("AccountingPeriod", period_id)

        if period.status == "open":
            return period

        reopened = await self.period_repo.reopen_period(period)

        # Audit Log
        audit = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="REOPEN_ACCOUNTING_PERIOD",
            entity_type="accounting_period",
            entity_id=period.id,
            before_state={"status": "closed"},
            after_state={"status": "open"},
        )
        self.session.add(audit)
        await self.session.flush()
        return reopened

    # ---------------------------------------------------------------------------
    # Journal Entries & Balanced Posting Workflow
    # ---------------------------------------------------------------------------

    async def list_journals(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[JournalEntry], int]:
        """Lists journal entries with line details."""
        return await self.journal_repo.list_journals(
            workspace_id=workspace_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            source_type=source_type,
            limit=limit,
            offset=offset,
        )

    async def get_journal(
        self,
        workspace_id: uuid.UUID,
        journal_id: uuid.UUID,
    ) -> JournalEntry:
        """Retrieves a single journal entry with its lines."""
        entry = await self.journal_repo.get_by_id(workspace_id, journal_id)
        if not entry:
            raise EntityNotFoundError("JournalEntry", journal_id)
        return entry

    async def create_draft_journal(
        self,
        workspace_id: uuid.UUID,
        entry_number: str,
        entry_date: date,
        description: str,
        lines_data: List[Dict[str, Any]],
        source_type: str = "manual",
        source_id: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> JournalEntry:
        """Creates a draft journal entry."""
        if len(lines_data) < 2:
            raise BusinessRuleViolationError(
                "INSUFFICIENT_JOURNAL_LINES",
                "A journal entry requires at least two lines (one debit and one credit).",
            )

        # Ensure all ledger accounts exist and belong to workspace
        for line in lines_data:
            acct = await self.account_repo.get_by_id(workspace_id, line["ledger_account_id"])
            if not acct:
                raise EntityNotFoundError("LedgerAccount", line["ledger_account_id"])
            if not acct.is_active:
                raise BusinessRuleViolationError(
                    "INACTIVE_LEDGER_ACCOUNT",
                    f"Ledger account '{acct.code}' ({acct.name}) is inactive and cannot be used.",
                )

        # Associate accounting period if one exists for entry_date
        period = await self.period_repo.get_period_for_date(workspace_id, entry_date)
        period_id = period.id if period else None

        entry = await self.journal_repo.create_journal(
            workspace_id=workspace_id,
            entry_number=entry_number,
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            lines_data=lines_data,
            source_id=source_id,
            created_by=created_by,
            accounting_period_id=period_id,
            metadata_payload=metadata_payload,
            status="draft",
        )

        self.event_collector.record(
            create_journal_created_event(
                workspace_id=workspace_id,
                journal_id=entry.id,
                entry_number=entry.entry_number,
                source_type=source_type,
                actor_id=created_by,
            )
        )
        return entry

    async def post_journal_entry(
        self,
        workspace_id: uuid.UUID,
        journal_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[str] = None,
    ) -> JournalEntry:
        """
        Transitions a draft journal entry into immutable posted status.
        Enforces:
        1. Lock row against concurrent posting.
        2. Closed period verification.
        3. At least two lines.
        4. Line amounts strictly > 0.
        5. Exact Debit-Credit equality (Total Debits == Total Credits).
        6. Immutability transition.
        7. Audit trail.
        """
        # Step 1: Lock record
        entry = await self.journal_repo.get_by_id(workspace_id, journal_id, lock_for_update=True)
        if not entry:
            raise EntityNotFoundError("JournalEntry", journal_id)

        # Step 2: Immutability checks
        if entry.status == "posted":
            raise ImmutableJournalError(entry.entry_number, entry.status)
        if entry.status == "reversed":
            raise ImmutableJournalError(entry.entry_number, entry.status)

        # Step 3: Accounting period check
        if entry.accounting_period_id:
            period = await self.period_repo.get_by_id(workspace_id, entry.accounting_period_id)
            if period and period.status == "closed":
                raise PeriodClosedError(period.name, entry.entry_date)
        else:
            # Check if an accounting period covers this date and is closed
            active_period = await self.period_repo.get_period_for_date(workspace_id, entry.entry_date)
            if active_period and active_period.status == "closed":
                raise PeriodClosedError(active_period.name, entry.entry_date)
            if active_period:
                entry.accounting_period_id = active_period.id

        # Step 4: Line count and validation
        if len(entry.lines) < 2:
            raise BusinessRuleViolationError(
                "INSUFFICIENT_JOURNAL_LINES",
                "A journal entry requires at least two lines (one debit and one credit).",
            )

        total_debits = Decimal("0.0000")
        total_credits = Decimal("0.0000")
        total_debits_paise = 0
        total_credits_paise = 0

        for line in entry.lines:
            if line.amount <= Decimal("0.0000"):
                raise BusinessRuleViolationError(
                    "INVALID_LINE_AMOUNT",
                    f"Line {line.line_number}: Journal line amount must be strictly greater than zero.",
                )

            # Ensure amount_paise is populated
            if not line.amount_paise:
                line.amount_paise = int(round(line.amount * 100))

            if line.entry_type == "debit":
                total_debits += line.amount
                total_debits_paise += line.amount_paise
            elif line.entry_type == "credit":
                total_credits += line.amount
                total_credits_paise += line.amount_paise
            else:
                raise BusinessRuleViolationError(
                    "INVALID_ENTRY_TYPE",
                    f"Line {line.line_number}: Entry type must be 'debit' or 'credit'.",
                )

        # Step 5: Fundamental Accounting Equation Verification (Total Debits == Total Credits)
        debits_rounded = total_debits.quantize(Decimal("0.0001"))
        credits_rounded = total_credits.quantize(Decimal("0.0001"))

        if debits_rounded != credits_rounded or total_debits_paise != total_credits_paise:
            diff = abs(debits_rounded - credits_rounded)
            raise UnbalancedJournalError(debits_rounded, credits_rounded, diff)

        # Step 6: Atomic Posting
        now = datetime.now(timezone.utc)
        entry.status = "posted"
        entry.posting_date = now
        entry.posted_by_id = actor_id

        # Step 7: Audit Logging
        audit = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="POST_JOURNAL_ENTRY",
            entity_type="journal_entry",
            entity_id=entry.id,
            correlation_id=correlation_id,
            before_state={"status": "draft"},
            after_state={
                "status": "posted",
                "entry_number": entry.entry_number,
                "total_debits": str(debits_rounded),
                "total_credits": str(credits_rounded),
                "posting_date": now.isoformat(),
            },
        )
        self.session.add(audit)
        await self.session.flush()

        # Step 8: Domain Event
        self.event_collector.record(
            create_journal_posted_event(
                workspace_id=workspace_id,
                journal_id=entry.id,
                entry_number=entry.entry_number,
                total_amount_str=str(debits_rounded),
                currency=entry.lines[0].currency if entry.lines else "INR",
                actor_id=actor_id,
                correlation_id=correlation_id,
            )
        )
        return entry

    async def reverse_journal_entry(
        self,
        workspace_id: uuid.UUID,
        journal_id: uuid.UUID,
        reversal_number: str,
        reason: str,
        actor_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[str] = None,
    ) -> JournalEntry:
        """
        Executes a formal compensating reversal of a posted journal entry.
        Creates an inverted journal entry (debits become credits, credits become debits)
        and transitions the original entry status to 'reversed'.
        """
        original = await self.journal_repo.get_by_id(workspace_id, journal_id, lock_for_update=True)
        if not original:
            raise EntityNotFoundError("JournalEntry", journal_id)

        if original.status != "posted":
            raise BusinessRuleViolationError(
                "CANNOT_REVERSE_UNPOSTED",
                f"Only posted journal entries can be reversed. Current status: '{original.status}'.",
            )

        now = datetime.now(timezone.utc)

        # Create Reversal Header
        reversal_entry = JournalEntry(
            workspace_id=workspace_id,
            entry_number=reversal_number,
            entry_date=now.date(),
            posting_date=now,
            status="posted",
            description=f"REVERSAL of {original.entry_number}: {reason}",
            source_type="reversal",
            source_id=original.id,
            reversal_of_entry_id=original.id,
            created_by=actor_id,
            posted_by_id=actor_id,
            accounting_period_id=original.accounting_period_id,
            metadata_payload={"original_entry_id": str(original.id), "reversal_reason": reason},
        )
        self.session.add(reversal_entry)
        await self.session.flush()

        # Invert Lines
        for idx, orig_line in enumerate(original.lines, start=1):
            inverted_type = "credit" if orig_line.entry_type == "debit" else "debit"
            reversal_line = JournalLine(
                journal_entry_id=reversal_entry.id,
                ledger_account_id=orig_line.ledger_account_id,
                line_number=idx,
                entry_type=inverted_type,
                amount=orig_line.amount,
                amount_paise=orig_line.amount_paise or int(round(orig_line.amount * 100)),
                currency=orig_line.currency,
                description=f"Reversal of line {orig_line.line_number}",
                financial_account_id=orig_line.financial_account_id,
            )
            self.session.add(reversal_line)

        # Update original status
        original.status = "reversed"
        original.reversal_reason = reason

        # Audit Log
        audit = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="REVERSE_JOURNAL_ENTRY",
            entity_type="journal_entry",
            entity_id=reversal_entry.id,
            correlation_id=correlation_id,
            before_state={"original_id": str(original.id), "status": "posted"},
            after_state={
                "reversal_id": str(reversal_entry.id),
                "reversal_number": reversal_number,
                "reason": reason,
            },
        )
        self.session.add(audit)
        await self.session.flush()

        self.event_collector.record(
            create_journal_reversed_event(
                workspace_id=workspace_id,
                original_journal_id=original.id,
                reversal_journal_id=reversal_entry.id,
                reversal_number=reversal_number,
                reason=reason,
                actor_id=actor_id,
                correlation_id=correlation_id,
            )
        )
        return reversal_entry

    # ---------------------------------------------------------------------------
    # Transaction to Ledger Integration
    # ---------------------------------------------------------------------------

    async def post_transaction_to_ledger(
        self,
        workspace_id: uuid.UUID,
        transaction: Transaction,
        actor_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[str] = None,
    ) -> JournalEntry:
        """
        Translates a financial transaction into an authoritative double-entry journal entry.
        Enforces appropriate accounting debit and credit classifications per transaction type.
        """
        await self.ensure_chart_of_accounts(workspace_id)

        tx_type = transaction.transaction_type.lower()
        amount_dec = transaction.amount
        amount_paise = transaction.amount_paise

        # Resolve ledger account for the transaction's financial account
        account_ledger_code = "1021"  # Default Primary Operating Bank
        if transaction.account:
            account_ledger_code = ACCOUNT_TYPE_TO_LEDGER_CODE.get(transaction.account.account_type, "1021")

        account_ledger = await self.account_repo.get_by_code(workspace_id, account_ledger_code)
        if not account_ledger:
            account_ledger = (await self.account_repo.list_by_workspace(workspace_id, account_type="asset"))[0]

        lines_data: List[Dict[str, Any]] = []

        if tx_type == "income":
            # Debit: Bank/Cash, Credit: Operating Revenue
            revenue_ledger = await self.account_repo.get_by_code(workspace_id, "4020") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": account_ledger.id,
                    "entry_type": "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": transaction.description,
                },
                {
                    "ledger_account_id": revenue_ledger.id,
                    "entry_type": "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": transaction.description,
                },
            ]

        elif tx_type == "expense":
            # Debit: Expense, Credit: Bank/Cash
            expense_ledger = await self.account_repo.get_by_code(workspace_id, "5000") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": expense_ledger.id,
                    "entry_type": "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": transaction.description,
                },
                {
                    "ledger_account_id": account_ledger.id,
                    "entry_type": "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": transaction.description,
                },
            ]

        elif tx_type in ("transfer", "transfer_out", "transfer_in"):
            # Internal transfers: Debit Destination, Credit Source
            # For a paired transfer, we map both sides cleanly
            dest_ledger = await self.account_repo.get_by_code(workspace_id, "1022") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": dest_ledger.id,
                    "entry_type": "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": f"Transfer leg: {transaction.description}",
                },
                {
                    "ledger_account_id": account_ledger.id,
                    "entry_type": "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": f"Transfer leg: {transaction.description}",
                },
            ]

        elif tx_type == "purchase":
            # Credit Card Purchase: Debit Expense, Credit Credit Card Payable (2010)
            expense_ledger = await self.account_repo.get_by_code(workspace_id, "5000") or account_ledger
            cc_payable_ledger = await self.account_repo.get_by_code(workspace_id, "2010") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": expense_ledger.id,
                    "entry_type": "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": transaction.description,
                },
                {
                    "ledger_account_id": cc_payable_ledger.id,
                    "entry_type": "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": transaction.description,
                },
            ]

        elif tx_type == "payment":
            # Credit Card Payment: Debit Credit Card Payable (2010), Credit Bank (1021)
            cc_payable_ledger = await self.account_repo.get_by_code(workspace_id, "2010") or account_ledger
            bank_ledger = await self.account_repo.get_by_code(workspace_id, "1021") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": cc_payable_ledger.id,
                    "entry_type": "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": "Credit card liability discharge",
                },
                {
                    "ledger_account_id": bank_ledger.id,
                    "entry_type": "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": "Credit card bill payment",
                },
            ]

        elif tx_type == "opening_balance":
            # Opening Balance: Debit Asset (or Credit Liability), Credit Opening Balance Equity (3030)
            equity_ledger = await self.account_repo.get_by_code(workspace_id, "3030") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": account_ledger.id,
                    "entry_type": "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": "Opening account balance",
                },
                {
                    "ledger_account_id": equity_ledger.id,
                    "entry_type": "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": "Opening Balance Equity offset",
                },
            ]

        elif tx_type == "refund":
            # Refund: Debit Bank/Cash, Credit Expense (Reimbursement)
            expense_ledger = await self.account_repo.get_by_code(workspace_id, "5000") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": account_ledger.id,
                    "entry_type": "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": f"Refund: {transaction.description}",
                },
                {
                    "ledger_account_id": expense_ledger.id,
                    "entry_type": "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": f"Refund reimbursement: {transaction.description}",
                },
            ]

        else:
            # General fallback: Debit Expense or Inflow, Credit Contra
            contra_ledger = await self.account_repo.get_by_code(workspace_id, "5990") or account_ledger
            lines_data = [
                {
                    "ledger_account_id": account_ledger.id,
                    "entry_type": "debit" if transaction.direction == "inflow" else "credit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "financial_account_id": transaction.account_id,
                    "description": transaction.description,
                },
                {
                    "ledger_account_id": contra_ledger.id,
                    "entry_type": "credit" if transaction.direction == "inflow" else "debit",
                    "amount": amount_dec,
                    "amount_paise": amount_paise,
                    "description": transaction.description,
                },
            ]

        # Generate unique entry number
        entry_number = f"JE-TX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Create draft journal
        draft_journal = await self.create_draft_journal(
            workspace_id=workspace_id,
            entry_number=entry_number,
            entry_date=transaction.transaction_date.date() if isinstance(transaction.transaction_date, datetime) else transaction.transaction_date,
            description=f"Ledger posting for TX: {transaction.description}",
            lines_data=lines_data,
            source_type=JournalSourceType.TRANSACTION.value,
            source_id=transaction.id,
            created_by=actor_id,
            metadata_payload={"transaction_id": str(transaction.id), "transaction_type": transaction.transaction_type},
        )

        # Immediately post to maintain ledger synchronization
        posted_journal = await self.post_journal_entry(
            workspace_id=workspace_id,
            journal_id=draft_journal.id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )
        return posted_journal

    # ---------------------------------------------------------------------------
    # Balances & Trial Balance
    # ---------------------------------------------------------------------------

    async def get_account_balance(
        self,
        workspace_id: uuid.UUID,
        ledger_account_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Derives authoritative account balance from posted ledger entries."""
        return await self.journal_repo.get_account_balance(workspace_id, ledger_account_id, as_of_date)

    async def get_trial_balance(
        self,
        workspace_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Calculates and verifies the complete Trial Balance."""
        await self.ensure_chart_of_accounts(workspace_id)
        return await self.journal_repo.get_trial_balance(workspace_id, as_of_date)
