"""
Arthsavora Transaction Repository
Data access layer for operational financial transactions.
Supports idempotent deduplication via external_transaction_id,
date-range filtering, and strictly workspace-scoped pagination.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.workspace_scoped import WorkspaceScopedRepository


class TransactionRepository(WorkspaceScopedRepository[Transaction]):
    """Repository handling operational Transaction persistence operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Transaction)

    async def get_by_external_id(
        self,
        workspace_id: uuid.UUID,
        external_id: str,
    ) -> Optional[Transaction]:
        """
        Idempotent lookup: Finds an existing transaction by external reference
        within the workspace boundary (e.g. Bank statement or UPI reference).
        """
        stmt = select(Transaction).where(
            Transaction.workspace_id == workspace_id,
            Transaction.external_transaction_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_transactions_paginated(
        self,
        workspace_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        account_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
    ) -> Tuple[List[Transaction], int]:
        """
        Retrieves a paginated list of transactions with optional filtering,
        along with the total matching count.
        """
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        # Base filter condition
        filters = [Transaction.workspace_id == workspace_id]
        if account_id:
            filters.append(Transaction.account_id == account_id)
        if start_date:
            filters.append(Transaction.transaction_date >= start_date)
        if end_date:
            filters.append(Transaction.transaction_date <= end_date)
        if transaction_type:
            filters.append(Transaction.transaction_type == transaction_type)

        # Count total
        count_stmt = select(func.count()).select_from(Transaction).where(*filters)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Query records
        items_stmt = (
            select(Transaction)
            .where(*filters)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(safe_limit)
            .offset(safe_offset)
        )
        items_result = await self.session.execute(items_stmt)
        items = list(items_result.scalars().all())

        return items, total

    def create(
        self,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        transaction_type: str,
        transaction_date: date,
        description: str,
        merchant_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        external_transaction_id: Optional[str] = None,
        is_ai_predicted: bool = False,
        ai_confidence: Optional[float] = None,
    ) -> Transaction:
        """Schedules creation of an operational transaction."""
        tx = Transaction(
            workspace_id=workspace_id,
            account_id=account_id,
            amount=amount,
            currency=currency.upper().strip(),
            transaction_type=transaction_type.lower().strip(),
            transaction_date=transaction_date,
            description=description.strip(),
            merchant_name=merchant_name.strip() if merchant_name else None,
            category_id=category_id,
            external_transaction_id=external_transaction_id.strip() if external_transaction_id else None,
            is_ai_predicted=is_ai_predicted,
            ai_confidence=ai_confidence,
            status="cleared",
        )
        self.session.add(tx)
        return tx
