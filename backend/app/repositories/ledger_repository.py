"""
Arthsavora Double-Entry Ledger Repository Layer
Provides transactional persistence, locking, COA hierarchy traversal,
accounting period lifecycle management, and balance aggregations.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.accounting_types import (
    DEFAULT_CHART_OF_ACCOUNTS,
    NORMAL_BALANCE_MAP,
    AccountType,
    JournalSourceType,
    JournalStatus,
    NormalBalance,
    PeriodStatus,
    TemplateAccount,
)
from app.domain.exceptions import (
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


class LedgerAccountRepository:
    """Repository managing Chart of Accounts ledger entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        is_active: Optional[bool] = None,
        account_type: Optional[str] = None,
    ) -> List[LedgerAccount]:
        """Lists ledger accounts for a workspace ordered by code."""
        stmt = select(LedgerAccount).where(LedgerAccount.workspace_id == workspace_id)
        if is_active is not None:
            stmt = stmt.where(LedgerAccount.is_active == is_active)
        if account_type is not None:
            stmt = stmt.where(LedgerAccount.account_type == account_type)
        stmt = stmt.order_by(LedgerAccount.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        workspace_id: uuid.UUID,
        ledger_account_id: uuid.UUID,
    ) -> Optional[LedgerAccount]:
        """Fetches a ledger account within workspace boundary (Anti-IDOR)."""
        stmt = select(LedgerAccount).where(
            LedgerAccount.id == ledger_account_id,
            LedgerAccount.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(
        self,
        workspace_id: uuid.UUID,
        code: str,
    ) -> Optional[LedgerAccount]:
        """Fetches a ledger account by its unique code within the workspace."""
        stmt = select(LedgerAccount).where(
            LedgerAccount.workspace_id == workspace_id,
            LedgerAccount.code == code,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        workspace_id: uuid.UUID,
        code: str,
        name: str,
        account_type: str,
        normal_balance: str,
        sub_type: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[uuid.UUID] = None,
        linked_account_id: Optional[uuid.UUID] = None,
        is_system: bool = False,
    ) -> LedgerAccount:
        """Creates a new ledger account."""
        account = LedgerAccount(
            workspace_id=workspace_id,
            code=code,
            name=name,
            account_type=account_type,
            normal_balance=normal_balance,
            sub_type=sub_type,
            description=description,
            parent_id=parent_id,
            linked_account_id=linked_account_id,
            is_system=is_system,
            is_active=True,
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def seed_default_chart_of_accounts(
        self,
        workspace_id: uuid.UUID,
    ) -> List[LedgerAccount]:
        """
        Seeds standard Indian FinTech Chart of Accounts if workspace has none.
        Handles parent-child hierarchy in two passes.
        """
        existing = await self.list_by_workspace(workspace_id)
        if existing:
            return existing

        created_by_code: Dict[str, LedgerAccount] = {}

        # Pass 1: Create all accounts without parent links
        for tpl in DEFAULT_CHART_OF_ACCOUNTS:
            acct = LedgerAccount(
                workspace_id=workspace_id,
                code=tpl.code,
                name=tpl.name,
                account_type=tpl.account_type.value,
                normal_balance=tpl.normal_balance.value,
                sub_type=tpl.sub_type,
                description=tpl.description,
                is_system=tpl.is_system,
                is_active=True,
            )
            self.session.add(acct)
            created_by_code[tpl.code] = acct

        await self.session.flush()

        # Pass 2: Establish parent-child foreign key relationships
        for tpl in DEFAULT_CHART_OF_ACCOUNTS:
            if tpl.parent_code and tpl.parent_code in created_by_code:
                child = created_by_code[tpl.code]
                parent = created_by_code[tpl.parent_code]
                child.parent_id = parent.id

        await self.session.flush()
        return list(created_by_code.values())


class AccountingPeriodRepository:
    """Repository managing Fiscal Years and Accounting Periods."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        fiscal_year: Optional[str] = None,
    ) -> List[AccountingPeriod]:
        """Lists accounting periods for a workspace."""
        stmt = select(AccountingPeriod).where(AccountingPeriod.workspace_id == workspace_id)
        if fiscal_year:
            stmt = stmt.where(AccountingPeriod.fiscal_year == fiscal_year)
        stmt = stmt.order_by(AccountingPeriod.period_number)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        workspace_id: uuid.UUID,
        period_id: uuid.UUID,
    ) -> Optional[AccountingPeriod]:
        """Fetches an accounting period by ID."""
        stmt = select(AccountingPeriod).where(
            AccountingPeriod.id == period_id,
            AccountingPeriod.workspace_id == workspace_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_period_for_date(
        self,
        workspace_id: uuid.UUID,
        target_date: date,
    ) -> Optional[AccountingPeriod]:
        """Finds the active accounting period enclosing the given calendar date."""
        stmt = select(AccountingPeriod).where(
            AccountingPeriod.workspace_id == workspace_id,
            AccountingPeriod.start_date <= target_date,
            AccountingPeriod.end_date >= target_date,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        workspace_id: uuid.UUID,
        fiscal_year: str,
        period_number: int,
        name: str,
        start_date: date,
        end_date: date,
        status: str = "open",
    ) -> AccountingPeriod:
        """Creates an accounting period."""
        period = AccountingPeriod(
            workspace_id=workspace_id,
            fiscal_year=fiscal_year,
            period_number=period_number,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        self.session.add(period)
        await self.session.flush()
        return period

    async def close_period(
        self,
        period: AccountingPeriod,
        closed_by_id: uuid.UUID,
    ) -> AccountingPeriod:
        """Closes an accounting period."""
        period.status = "closed"
        period.closed_at = datetime.now(timezone.utc)
        period.closed_by_id = closed_by_id
        await self.session.flush()
        return period

    async def reopen_period(
        self,
        period: AccountingPeriod,
    ) -> AccountingPeriod:
        """Reopens a closed accounting period."""
        period.status = "open"
        period.closed_at = None
        period.closed_by_id = None
        await self.session.flush()
        return period


class JournalEntryRepository:
    """Repository managing double-entry journal headers and balanced line items."""

    def __init__(self, session: AsyncSession):
        self.session = session

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
        """Lists journals with lines and returns (items, total_count)."""
        base_stmt = select(JournalEntry).where(JournalEntry.workspace_id == workspace_id)
        count_stmt = select(func.count()).select_from(JournalEntry).where(JournalEntry.workspace_id == workspace_id)

        if status:
            base_stmt = base_stmt.where(JournalEntry.status == status)
            count_stmt = count_stmt.where(JournalEntry.status == status)
        if start_date:
            base_stmt = base_stmt.where(JournalEntry.entry_date >= start_date)
            count_stmt = count_stmt.where(JournalEntry.entry_date >= start_date)
        if end_date:
            base_stmt = base_stmt.where(JournalEntry.entry_date <= end_date)
            count_stmt = count_stmt.where(JournalEntry.entry_date <= end_date)
        if source_type:
            base_stmt = base_stmt.where(JournalEntry.source_type == source_type)
            count_stmt = count_stmt.where(JournalEntry.source_type == source_type)

        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            base_stmt
            .options(
                selectinload(JournalEntry.lines).selectinload(JournalLine.ledger_account),
                selectinload(JournalEntry.accounting_period),
            )
            .order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    async def get_by_id(
        self,
        workspace_id: uuid.UUID,
        journal_id: uuid.UUID,
        lock_for_update: bool = False,
    ) -> Optional[JournalEntry]:
        """Fetches a journal entry with all line items and ledger accounts."""
        stmt = (
            select(JournalEntry)
            .where(
                JournalEntry.id == journal_id,
                JournalEntry.workspace_id == workspace_id,
            )
            .options(
                selectinload(JournalEntry.lines).selectinload(JournalLine.ledger_account),
                selectinload(JournalEntry.accounting_period),
            )
        )
        if lock_for_update:
            stmt = stmt.with_for_update()

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_journal(
        self,
        workspace_id: uuid.UUID,
        entry_number: str,
        entry_date: date,
        description: str,
        source_type: str,
        lines_data: List[Dict[str, Any]],
        source_id: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None,
        accounting_period_id: Optional[uuid.UUID] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
        status: str = "draft",
    ) -> JournalEntry:
        """Creates a journal entry header and its lines atomically."""
        entry = JournalEntry(
            workspace_id=workspace_id,
            entry_number=entry_number,
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            source_id=source_id,
            created_by=created_by,
            accounting_period_id=accounting_period_id,
            metadata_payload=metadata_payload or {},
            status=status,
            posting_date=datetime.now(timezone.utc) if status == "posted" else None,
        )
        self.session.add(entry)
        await self.session.flush()

        for idx, line_dict in enumerate(lines_data, start=1):
            amount_dec = Decimal(str(line_dict["amount"]))
            amount_paise = line_dict.get("amount_paise") or int(round(amount_dec * 100))
            line = JournalLine(
                journal_entry_id=entry.id,
                ledger_account_id=line_dict["ledger_account_id"],
                line_number=idx,
                entry_type=line_dict["entry_type"],
                amount=amount_dec,
                amount_paise=amount_paise,
                currency=line_dict.get("currency", "INR"),
                description=line_dict.get("description"),
                financial_account_id=line_dict.get("financial_account_id"),
                counterparty_name=line_dict.get("counterparty_name"),
                source_metadata=line_dict.get("source_metadata", {}),
            )
            self.session.add(line)

        await self.session.flush()
        return entry

    async def get_account_balance(
        self,
        workspace_id: uuid.UUID,
        ledger_account_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Derives the authoritative ledger balance for an account from posted journal lines.
        Returns debits, credits, net balance in Decimal and integer paise.
        """
        # Fetch account to check normal balance
        acct_stmt = select(LedgerAccount).where(
            LedgerAccount.id == ledger_account_id,
            LedgerAccount.workspace_id == workspace_id,
        )
        acct_res = await self.session.execute(acct_stmt)
        acct = acct_res.scalar_one_or_none()
        if not acct:
            raise EntityNotFoundError("LedgerAccount", ledger_account_id)

        # Sum posted debits and credits
        query = (
            select(
                JournalLine.entry_type,
                func.coalesce(func.sum(JournalLine.amount), Decimal("0.0000")),
                func.coalesce(func.sum(JournalLine.amount_paise), 0),
            )
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalEntry.workspace_id == workspace_id,
                JournalEntry.status == "posted",
                JournalLine.ledger_account_id == ledger_account_id,
            )
        )
        if as_of_date:
            query = query.where(JournalEntry.entry_date <= as_of_date)

        query = query.group_by(JournalLine.entry_type)
        res = await self.session.execute(query)

        debit_dec = Decimal("0.0000")
        credit_dec = Decimal("0.0000")
        debit_paise = 0
        credit_paise = 0

        for row in res.fetchall():
            etype, amt, paise = row
            if etype == "debit":
                debit_dec = Decimal(str(amt))
                debit_paise = int(paise)
            elif etype == "credit":
                credit_dec = Decimal(str(amt))
                credit_paise = int(paise)

        # Apply normal balance orientation
        if acct.normal_balance == "debit":
            net_balance_dec = debit_dec - credit_dec
            net_balance_paise = debit_paise - credit_paise
        else:
            net_balance_dec = credit_dec - debit_dec
            net_balance_paise = credit_paise - debit_paise

        return {
            "account_id": str(acct.id),
            "code": acct.code,
            "name": acct.name,
            "account_type": acct.account_type,
            "normal_balance": acct.normal_balance,
            "total_debits": debit_dec,
            "total_credits": credit_dec,
            "total_debits_paise": debit_paise,
            "total_credits_paise": credit_paise,
            "net_balance": net_balance_dec,
            "net_balance_paise": net_balance_paise,
        }

    async def get_trial_balance(
        self,
        workspace_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Calculates the complete Trial Balance across all ledger accounts in the workspace.
        Enforces and verifies: Total Debits == Total Credits across the entire general ledger.
        """
        # Fetch all active accounts
        accts_stmt = (
            select(LedgerAccount)
            .where(LedgerAccount.workspace_id == workspace_id)
            .order_by(LedgerAccount.code)
        )
        accts_res = await self.session.execute(accts_stmt)
        accounts = list(accts_res.scalars().all())

        # Aggregate sums by account and entry_type
        agg_query = (
            select(
                JournalLine.ledger_account_id,
                JournalLine.entry_type,
                func.coalesce(func.sum(JournalLine.amount), Decimal("0.0000")),
                func.coalesce(func.sum(JournalLine.amount_paise), 0),
            )
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalEntry.workspace_id == workspace_id,
                JournalEntry.status == "posted",
            )
        )
        if as_of_date:
            agg_query = agg_query.where(JournalEntry.entry_date <= as_of_date)

        agg_query = agg_query.group_by(JournalLine.ledger_account_id, JournalLine.entry_type)
        agg_res = await self.session.execute(agg_query)

        debits_by_acct: Dict[uuid.UUID, Decimal] = {}
        credits_by_acct: Dict[uuid.UUID, Decimal] = {}
        debits_paise_by_acct: Dict[uuid.UUID, int] = {}
        credits_paise_by_acct: Dict[uuid.UUID, int] = {}

        for row in agg_res.fetchall():
            acct_id, etype, amt, paise = row
            if etype == "debit":
                debits_by_acct[acct_id] = Decimal(str(amt))
                debits_paise_by_acct[acct_id] = int(paise)
            elif etype == "credit":
                credits_by_acct[acct_id] = Decimal(str(amt))
                credits_paise_by_acct[acct_id] = int(paise)

        entries = []
        grand_total_debits = Decimal("0.0000")
        grand_total_credits = Decimal("0.0000")
        grand_total_debits_paise = 0
        grand_total_credits_paise = 0

        for acct in accounts:
            debit = debits_by_acct.get(acct.id, Decimal("0.0000"))
            credit = credits_by_acct.get(acct.id, Decimal("0.0000"))
            debit_p = debits_paise_by_acct.get(acct.id, 0)
            credit_p = credits_paise_by_acct.get(acct.id, 0)

            # In trial balance: net balance is placed in debit column or credit column
            if acct.normal_balance == "debit":
                net = debit - credit
                net_p = debit_p - credit_p
                tb_debit = net if net > 0 else Decimal("0.0000")
                tb_credit = -net if net < 0 else Decimal("0.0000")
                tb_debit_p = net_p if net_p > 0 else 0
                tb_credit_p = -net_p if net_p < 0 else 0
            else:
                net = credit - debit
                net_p = credit_p - debit_p
                tb_credit = net if net > 0 else Decimal("0.0000")
                tb_debit = -net if net < 0 else Decimal("0.0000")
                tb_credit_p = net_p if net_p > 0 else 0
                tb_debit_p = -net_p if net_p < 0 else 0

            # Only include accounts that have activity or non-zero balances
            if debit > 0 or credit > 0:
                entries.append({
                    "account_id": str(acct.id),
                    "code": acct.code,
                    "name": acct.name,
                    "account_type": acct.account_type,
                    "normal_balance": acct.normal_balance,
                    "debit_balance": tb_debit,
                    "credit_balance": tb_credit,
                    "debit_balance_paise": tb_debit_p,
                    "credit_balance_paise": tb_credit_p,
                })
                grand_total_debits += tb_debit
                grand_total_credits += tb_credit
                grand_total_debits_paise += tb_debit_p
                grand_total_credits_paise += tb_credit_p

        is_balanced = (grand_total_debits == grand_total_credits) and (grand_total_debits_paise == grand_total_credits_paise)

        return {
            "as_of_date": as_of_date.isoformat() if as_of_date else date.today().isoformat(),
            "is_balanced": is_balanced,
            "total_debits": grand_total_debits,
            "total_credits": grand_total_credits,
            "total_debits_paise": grand_total_debits_paise,
            "total_credits_paise": grand_total_credits_paise,
            "difference": abs(grand_total_debits - grand_total_credits),
            "difference_paise": abs(grand_total_debits_paise - grand_total_credits_paise),
            "entries": entries,
        }
