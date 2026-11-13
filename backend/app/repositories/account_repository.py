"""
Arthsavora Financial Account Repository
Data access layer for bank, cash, credit card, and wallet accounts.
Strictly scoped by workspace_id to guarantee tenant isolation.
"""

from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.account import Account
from app.repositories.workspace_scoped import WorkspaceScopedRepository


class AccountRepository(WorkspaceScopedRepository[Account]):
    """Repository handling financial Account persistence operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Account)

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        account_type: Optional[str] = None,
    ) -> List[Account]:
        """Retrieves all active accounts for a workspace, optionally filtered by type."""
        stmt = select(Account).where(
            Account.workspace_id == workspace_id,
            Account.status == "active",
        )
        if account_type:
            stmt = stmt.where(Account.account_type == account_type)
        stmt = stmt.order_by(Account.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        account_type: str,
        currency: str = "INR",
        institution_name: Optional[str] = None,
        masked_identifier: Optional[str] = None,
    ) -> Account:
        """Schedules creation of a new financial account."""
        account = Account(
            workspace_id=workspace_id,
            name=name.strip(),
            account_type=account_type.lower().strip(),
            currency=currency.upper().strip(),
            institution_name=institution_name.strip() if institution_name else None,
            masked_identifier=masked_identifier.strip() if masked_identifier else None,
            status="active",
        )
        self.session.add(account)
        return account
