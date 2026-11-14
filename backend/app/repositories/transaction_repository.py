"""
Arthsavora Transaction Repository
Data access layer for operational financial transactions.
Supports idempotent deduplication via external_transaction_id,
transfer pairing, refund summation, date-range filtering, and strictly workspace-scoped pagination.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
import uuid
from sqlalchemy import func, select, or_
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
            Transaction.external_transaction_id == external_id.strip(),
            Transaction.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_transfer_id(
        self,
        workspace_id: uuid.UUID,
        transfer_id: uuid.UUID,
    ) -> List[Transaction]:
        """Retrieves both legs of a paired transfer within the authorized workspace."""
        stmt = (
            select(Transaction)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.transfer_id == transfer_id,
                Transaction.is_deleted == False,
            )
            .order_by(Transaction.direction.desc())  # outflow first, then inflow
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_refunds_for_transaction(
        self,
        workspace_id: uuid.UUID,
        original_transaction_id: uuid.UUID,
    ) -> List[Transaction]:
        """
        Retrieves all valid (non-cancelled, non-failed) refund transactions
        originating from the specified parent transaction.
        """
        stmt = select(Transaction).where(
            Transaction.workspace_id == workspace_id,
            Transaction.original_transaction_id == original_transaction_id,
            Transaction.transaction_type.in_(["refund", "credit_card_refund"]),
            Transaction.status.in_(["posted", "pending"]),
            Transaction.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_transactions_paginated(
        self,
        workspace_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        account_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        transaction_type: Optional[str] = None,
        direction: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount_paise: Optional[int] = None,
        max_amount_paise: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Transaction], int]:
        """
        Retrieves a paginated list of transactions with comprehensive multi-criteria filtering,
        along with the total matching count.
        """
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        filters = [
            Transaction.workspace_id == workspace_id,
            Transaction.is_deleted == False,
        ]

        if account_id:
            filters.append(Transaction.account_id == account_id)
        if category_id:
            filters.append(Transaction.category_id == category_id)
        if status:
            filters.append(Transaction.status == status.lower().strip())
        if transaction_type:
            filters.append(Transaction.transaction_type == transaction_type.lower().strip())
        if direction:
            filters.append(Transaction.direction == direction.lower().strip())
        if start_date:
            filters.append(Transaction.transaction_date >= start_date)
        if end_date:
            filters.append(Transaction.transaction_date <= end_date)
        if min_amount_paise is not None:
            filters.append(Transaction.amount_paise >= min_amount_paise)
        if max_amount_paise is not None:
            filters.append(Transaction.amount_paise <= max_amount_paise)
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Transaction.description.ilike(search_term),
                    Transaction.merchant_name.ilike(search_term),
                )
            )

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
        amount_paise: Optional[int] = None,
        direction: Optional[str] = None,
        settlement_date: Optional[date] = None,
        merchant_name: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        status: str = "posted",
        source_type: str = "manual",
        source_reference: Optional[str] = None,
        external_transaction_id: Optional[str] = None,
        related_transaction_id: Optional[uuid.UUID] = None,
        original_transaction_id: Optional[uuid.UUID] = None,
        transfer_id: Optional[uuid.UUID] = None,
        created_by_id: Optional[uuid.UUID] = None,
        reversal_reason: Optional[str] = None,
        is_ai_predicted: bool = False,
        ai_confidence: Optional[float] = None,
        source_provenance: Optional[Dict[str, Any]] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        """Schedules creation of an operational transaction entity."""
        from app.domain.transaction_types import resolve_transaction_direction

        calculated_paise = amount_paise if amount_paise is not None else int(round(Decimal(str(amount)) * 100))
        resolved_dir = direction or resolve_transaction_direction(transaction_type)

        tx = Transaction(
            workspace_id=workspace_id,
            account_id=account_id,
            amount=amount,
            amount_paise=calculated_paise,
            currency=currency.upper().strip(),
            transaction_type=transaction_type.lower().strip(),
            direction=resolved_dir.lower().strip(),
            transaction_date=transaction_date,
            settlement_date=settlement_date,
            description=description.strip(),
            merchant_name=merchant_name.strip() if merchant_name else None,
            category_id=category_id,
            status=status.lower().strip(),
            source_type=source_type.lower().strip() if source_type else "manual",
            source_reference=source_reference.strip() if source_reference else None,
            external_transaction_id=external_transaction_id.strip() if external_transaction_id else None,
            related_transaction_id=related_transaction_id,
            original_transaction_id=original_transaction_id,
            transfer_id=transfer_id,
            created_by_id=created_by_id,
            reversal_reason=reversal_reason.strip() if reversal_reason else None,
            is_ai_predicted=is_ai_predicted,
            ai_confidence=Decimal(str(ai_confidence)) if ai_confidence is not None else None,
            source_provenance=source_provenance or {},
            metadata_payload=metadata_payload or {},
        )
        self.session.add(tx)
        return tx
