"""
Arthsavora Financial Account Application Service
Orchestrates account creation, workspace isolation verification, and domain event emission.
"""

from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ValidationException
from app.core.permissions import WorkspaceContext
from app.domain.events import create_account_created_event
from app.domain.exceptions import DomainError
from app.domain.money import Money
from app.infrastructure.database.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreateRequest


class AccountService:
    """Service orchestrating financial account domain logic and persistence."""

    @staticmethod
    async def list_accounts(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_type: Optional[str] = None,
    ) -> List[Account]:
        """Lists active accounts strictly within the caller's workspace context."""
        repo = AccountRepository(session)
        return await repo.list_by_workspace(
            workspace_id=workspace_context.workspace.id,
            account_type=account_type,
        )

    @staticmethod
    async def get_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
    ) -> Account:
        """
        Retrieves a single account by ID.
        Returns 404 if the account belongs to another workspace (anti-IDOR defense).
        """
        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(
            entity_id=account_id,
            workspace_id=workspace_context.workspace.id,
        )
        if not account:
            raise NotFoundException(message="Account not found.")
        return account

    @staticmethod
    async def create_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        data: AccountCreateRequest,
    ) -> Account:
        """Provisions a new financial account and emits account.created domain event."""
        # 1. Validate currency code using Money value object
        try:
            Money.from_amount("0", currency=data.currency)
        except DomainError as err:
            raise ValidationException(message=str(err), code="INVALID_CURRENCY")

        # 2. Persist account through repository
        repo = AccountRepository(session)
        account = repo.create(
            workspace_id=workspace_context.workspace.id,
            name=data.name,
            account_type=data.account_type,
            currency=data.currency,
            institution_name=data.institution_name,
            masked_identifier=data.masked_identifier,
        )
        await repo.flush()

        # 3. Emit Domain Event
        event = create_account_created_event(
            workspace_id=workspace_context.workspace.id,
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            currency=account.currency,
            actor_id=workspace_context.current_user.id,
        )

        await session.commit()
        await repo.refresh(account)
        return account
