"""
Arthsavora Transaction Application Service
Orchestrates operational transaction intake, Money value object validation,
idempotent deduplication via external references, and domain event emission.
"""

from datetime import date
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ValidationException
from app.core.permissions import WorkspaceContext
from app.domain.events import create_transaction_created_event
from app.domain.exceptions import DomainError
from app.domain.money import Money
from app.domain.rules import validate_ai_prediction_invariants
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreateRequest


class TransactionService:
    """Service orchestrating operational transaction intake and queries."""

    @staticmethod
    async def list_transactions(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        limit: int = 20,
        offset: int = 0,
        account_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
    ) -> Tuple[List[Transaction], int]:
        """Retrieves paginated transactions with strict workspace scoping."""
        repo = TransactionRepository(session)
        return await repo.list_transactions_paginated(
            workspace_id=workspace_context.workspace.id,
            limit=limit,
            offset=offset,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
        )

    @staticmethod
    async def intake_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        data: TransactionCreateRequest,
    ) -> Tuple[Transaction, bool]:
        """
        Processes an incoming transaction:
        1. Verifies target account belongs to the caller's workspace.
        2. Validates amount and currency using the Money value object.
        3. Enforces AI prediction transparency rules.
        4. Detects duplicates via external_transaction_id (idempotency).
        5. Persists and emits transaction.created domain event.
        Returns (transaction, is_new).
        """
        ws_id = workspace_context.workspace.id

        # 1. Verify target account ownership
        account_repo = AccountRepository(session)
        account = await account_repo.get_by_id_scoped(
            entity_id=data.account_id,
            workspace_id=ws_id,
        )
        if not account:
            raise NotFoundException(message="Target account not found in current workspace.")

        # 2. Financial validation via Money Value Object
        try:
            money = Money.from_amount(data.amount, currency=data.currency)
        except DomainError as err:
            raise ValidationException(message=str(err), code="INVALID_FINANCIAL_AMOUNT")

        if money.is_zero:
            raise ValidationException(
                message="Transaction amount cannot be zero.",
                code="ZERO_AMOUNT_PROHIBITED",
            )

        # 3. AI prediction invariant verification
        if data.is_ai_predicted:
            validate_ai_prediction_invariants(data.is_ai_predicted, data.ai_confidence)

        # 4. Idempotency Check (Deduplication)
        tx_repo = TransactionRepository(session)
        if data.external_transaction_id:
            existing = await tx_repo.get_by_external_id(
                workspace_id=ws_id,
                external_id=data.external_transaction_id,
            )
            if existing:
                # Return existing transaction without duplicate insertion
                return existing, False

        # 5. Persist Transaction
        tx = tx_repo.create(
            workspace_id=ws_id,
            account_id=data.account_id,
            amount=money.amount,
            currency=money.currency,
            transaction_type=data.transaction_type,
            transaction_date=data.transaction_date,
            description=data.description,
            merchant_name=data.merchant_name,
            category_id=data.category_id,
            external_transaction_id=data.external_transaction_id,
            is_ai_predicted=data.is_ai_predicted,
            ai_confidence=data.ai_confidence,
        )
        await tx_repo.flush()

        # 6. Emit Domain Event
        event = create_transaction_created_event(
            workspace_id=ws_id,
            transaction_id=tx.id,
            account_id=tx.account_id,
            amount_str=str(money.display_amount),
            currency=money.currency,
            transaction_type=tx.transaction_type,
            actor_id=workspace_context.current_user.id,
        )

        await session.commit()
        await tx_repo.refresh(tx)
        return tx, True
