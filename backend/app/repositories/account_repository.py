"""
Arthsavora Financial Account Repository
Data access layer for bank, cash, credit card, and wallet accounts.
Strictly scoped by workspace_id to guarantee tenant isolation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.account import Account, AccountBalanceSnapshot
from app.repositories.workspace_scoped import WorkspaceScopedRepository


class AccountRepository(WorkspaceScopedRepository[Account]):
    """Repository handling financial Account and Balance Snapshot persistence operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Account)

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        account_type: Optional[str] = None,
        status: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Account]:
        """
        Retrieves accounts for a workspace with bounded pagination and filtering.
        Defaults to active accounts unless status or include_archived is specified.
        """
        stmt = select(Account).where(
            Account.workspace_id == workspace_id,
            Account.is_deleted == False,
        )
        if status:
            stmt = stmt.where(Account.status == status.lower().strip())
        elif not include_archived:
            stmt = stmt.where(Account.status.in_(["active", "inactive"]))

        if account_type:
            stmt = stmt.where(Account.account_type == account_type.lower().strip())

        bounded_limit = min(max(limit, 1), 100)
        stmt = stmt.order_by(Account.created_at.desc()).offset(offset).limit(bounded_limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        account_type: Optional[str] = None,
        status: Optional[str] = None,
        include_archived: bool = False,
    ) -> int:
        """Counts total accounts in a workspace matching filters."""
        stmt = select(func.count(Account.id)).where(
            Account.workspace_id == workspace_id,
            Account.is_deleted == False,
        )
        if status:
            stmt = stmt.where(Account.status == status.lower().strip())
        elif not include_archived:
            stmt = stmt.where(Account.status.in_(["active", "inactive"]))

        if account_type:
            stmt = stmt.where(Account.account_type == account_type.lower().strip())

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_provider_account_id(
        self,
        workspace_id: uuid.UUID,
        provider_name: str,
        provider_account_id: str,
    ) -> Optional[Account]:
        """Checks for existing linked account under provider name and external ID."""
        stmt = select(Account).where(
            Account.workspace_id == workspace_id,
            Account.provider_name == provider_name.strip(),
            Account.provider_account_id == provider_account_id.strip(),
            Account.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        account_type: str,
        currency: str = "INR",
        account_subtype: Optional[str] = None,
        description: Optional[str] = None,
        institution_name: Optional[str] = None,
        masked_identifier: Optional[str] = None,
        opening_date: Optional[date] = None,
        created_by_id: Optional[uuid.UUID] = None,
        opening_balance_paise: int = 0,
        opening_balance_date: Optional[date] = None,
        opening_balance_source: Optional[str] = "manual",
        credit_limit_paise: Optional[int] = None,
        statement_balance_paise: Optional[int] = None,
        minimum_due_paise: Optional[int] = None,
        due_date: Optional[date] = None,
        initial_liability_paise: Optional[int] = None,
        original_principal_paise: Optional[int] = None,
        interest_rate: Optional[Decimal] = None,
        repayment_amount_paise: Optional[int] = None,
        loan_due_date: Optional[date] = None,
        provider_name: Optional[str] = None,
        provider_account_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        source_metadata: Optional[dict] = None,
    ) -> Account:
        """Schedules creation of a normalized financial account."""
        # For liability accounts (credit card / loan), set outstanding liability
        outstanding_liability_val = initial_liability_paise
        if outstanding_liability_val is None and original_principal_paise:
            outstanding_liability_val = original_principal_paise

        # Initial book balance equals opening balance (or 0 for credit cards)
        book_balance_val = opening_balance_paise

        # Available balance for credit card is credit_limit - liability (if limit provided)
        available_val = None
        if account_type == "credit_card" and credit_limit_paise is not None:
            available_val = max(0, credit_limit_paise - (outstanding_liability_val or 0))
        elif account_type in ["savings", "current", "salary", "cash", "petty_cash", "digital_wallet"]:
            available_val = book_balance_val

        effective_due_date = due_date or loan_due_date

        account = Account(
            workspace_id=workspace_id,
            name=name.strip(),
            account_type=account_type.lower().strip(),
            account_subtype=account_subtype.lower().strip() if account_subtype else None,
            description=description.strip() if description else None,
            currency=currency.upper().strip(),
            institution_name=institution_name.strip() if institution_name else None,
            masked_identifier=masked_identifier.strip() if masked_identifier else None,
            status="active",
            opening_date=opening_date or date.today(),
            created_by_id=created_by_id,
            opening_balance_paise=opening_balance_paise,
            opening_balance_date=opening_balance_date or opening_date or date.today(),
            opening_balance_source=opening_balance_source or "manual",
            current_book_balance_paise=book_balance_val,
            available_balance_paise=available_val,
            outstanding_liability_paise=outstanding_liability_val,
            pending_amount_paise=0,
            credit_limit_paise=credit_limit_paise,
            statement_balance_paise=statement_balance_paise,
            minimum_due_paise=minimum_due_paise,
            due_date=effective_due_date,
            interest_rate=interest_rate,
            repayment_amount_paise=repayment_amount_paise,
            provider_name=provider_name.strip() if provider_name else None,
            provider_account_id=provider_account_id.strip() if provider_account_id else None,
            connection_id=connection_id.strip() if connection_id else None,
            source_metadata=source_metadata or {},
        )
        self.session.add(account)
        return account

    def create_snapshot(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        balance_type: str,
        balance_amount: Decimal,
        balance_paise: int,
        currency: str,
        effective_at: datetime,
        source: str = "manual",
        source_reference: Optional[str] = None,
        reconciliation_status: str = "unreconciled",
        created_by_id: Optional[uuid.UUID] = None,
    ) -> AccountBalanceSnapshot:
        """Schedules creation of an immutable point-in-time balance snapshot."""
        snapshot = AccountBalanceSnapshot(
            account_id=account_id,
            workspace_id=workspace_id,
            balance_type=balance_type.lower().strip(),
            balance_amount=balance_amount,
            balance_paise=balance_paise,
            currency=currency.upper().strip(),
            effective_at=effective_at,
            source=source.lower().strip(),
            source_reference=source_reference.strip() if source_reference else None,
            reconciliation_status=reconciliation_status.lower().strip(),
            created_by_id=created_by_id,
        )
        self.session.add(snapshot)
        return snapshot

    async def list_snapshots(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        balance_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AccountBalanceSnapshot]:
        """Retrieves point-in-time balance snapshots for an account in reverse chronological order."""
        stmt = select(AccountBalanceSnapshot).where(
            AccountBalanceSnapshot.account_id == account_id,
            AccountBalanceSnapshot.workspace_id == workspace_id,
        )
        if balance_type:
            stmt = stmt.where(AccountBalanceSnapshot.balance_type == balance_type.lower().strip())

        bounded_limit = min(max(limit, 1), 100)
        stmt = stmt.order_by(AccountBalanceSnapshot.effective_at.desc()).offset(offset).limit(bounded_limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_snapshots(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        balance_type: Optional[str] = None,
    ) -> int:
        """Counts total snapshots for an account matching filters."""
        stmt = select(func.count(AccountBalanceSnapshot.id)).where(
            AccountBalanceSnapshot.account_id == account_id,
            AccountBalanceSnapshot.workspace_id == workspace_id,
        )
        if balance_type:
            stmt = stmt.where(AccountBalanceSnapshot.balance_type == balance_type.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one()
