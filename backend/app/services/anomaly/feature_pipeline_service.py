"""
Arthsavora Financial Feature Pipeline Service
Controlled feature extraction, historical baselines, and vector transformation
for statistical and machine learning anomaly detection.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.anomaly import CandidateTransactionVO, extract_ml_feature_vector
from app.infrastructure.database.models.transaction import Transaction
from app.infrastructure.database.models.recurring import RecurringDefinition, RecurringOccurrence


class FeaturePipelineService:
    """Extracts historical financial metrics and feature vectors with zero future lookahead."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_candidate_transaction(
        self,
        transaction_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[CandidateTransactionVO]:
        """Loads transaction with eager relations and converts to domain CandidateTransactionVO."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.category),
            )
            .where(
                Transaction.id == transaction_id,
                Transaction.workspace_id == workspace_id,
                Transaction.is_deleted == False,
            )
        )
        res = await self.db.execute(stmt)
        tx = res.scalar_one_or_none()
        if not tx:
            return None

        merchant_name = tx.merchant_name
        category_name = tx.category.name if tx.category else None

        return CandidateTransactionVO(
            id=tx.id,
            workspace_id=tx.workspace_id,
            amount_paise=tx.amount_paise,
            currency=tx.currency,
            direction=tx.direction,
            transaction_date=tx.transaction_date,
            created_at=tx.created_at,
            description=tx.description or "",
            account_id=tx.account_id,
            category_id=tx.category_id,
            merchant_id=getattr(tx, "merchant_id", None),
            merchant_name=merchant_name,
            category_name=category_name,
            transaction_type=tx.transaction_type,
            status=tx.status,
            transfer_id=tx.transfer_id,
        )

    async def get_recent_transactions(
        self,
        workspace_id: uuid.UUID,
        as_of_datetime: datetime,
        lookback_hours: int = 48,
    ) -> List[CandidateTransactionVO]:
        """Fetches recent workspace transactions for frequency and duplicate candidate checks."""
        start_time = as_of_datetime - timedelta(hours=lookback_hours)
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.category),
            )
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.is_deleted == False,
                Transaction.created_at >= start_time,
                Transaction.created_at <= as_of_datetime,
            )
            .order_by(Transaction.created_at.desc())
        )
        res = await self.db.execute(stmt)
        txs = res.scalars().all()

        return [
            CandidateTransactionVO(
                id=t.id,
                workspace_id=t.workspace_id,
                amount_paise=t.amount_paise,
                currency=t.currency,
                direction=t.direction,
                transaction_date=t.transaction_date,
                created_at=t.created_at,
                description=t.description or "",
                account_id=t.account_id,
                category_id=t.category_id,
                merchant_id=getattr(t, "merchant_id", None),
                merchant_name=t.merchant_name,
                category_name=t.category.name if t.category else None,
                transaction_type=t.transaction_type,
                status=t.status,
                transfer_id=t.transfer_id,
            )
            for t in txs
        ]

    async def get_merchant_historical_amounts(
        self,
        workspace_id: uuid.UUID,
        merchant_id: Optional[uuid.UUID],
        merchant_name: Optional[str],
        exclude_transaction_id: uuid.UUID,
        lookback_days: int = 180,
    ) -> List[int]:
        """Fetches historical payment amounts for a specific merchant."""
        if not merchant_name:
            return []

        conditions = [
            Transaction.workspace_id == workspace_id,
            Transaction.id != exclude_transaction_id,
            Transaction.is_deleted == False,
            Transaction.status == "posted",
            Transaction.direction == "outflow",
            or_(
                Transaction.merchant_name.ilike(f"%{merchant_name}%"),
                Transaction.description.ilike(f"%{merchant_name}%"),
            ),
        ]

        stmt = (
            select(Transaction.amount_paise)
            .where(*conditions)
            .order_by(Transaction.transaction_date.desc())
            .limit(100)
        )
        res = await self.db.execute(stmt)
        return [int(r[0]) for r in res.all()]

    async def get_category_metrics(
        self,
        workspace_id: uuid.UUID,
        category_id: Optional[uuid.UUID],
        target_date: date,
    ) -> Tuple[List[int], int]:
        """
        Computes 90-day daily spending history and current calendar month spend for a category.
        """
        if not category_id:
            return [], 0

        # Current month total
        month_start = target_date.replace(day=1)
        cur_month_stmt = (
            select(func.coalesce(func.sum(Transaction.amount_paise), 0))
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.category_id == category_id,
                Transaction.is_deleted == False,
                Transaction.status == "posted",
                Transaction.direction == "outflow",
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date <= target_date,
            )
        )
        cur_month_res = await self.db.execute(cur_month_stmt)
        cur_month_total = int(cur_month_res.scalar() or 0)

        # 90-day daily history
        hist_start = target_date - timedelta(days=90)
        hist_stmt = (
            select(
                Transaction.transaction_date,
                func.sum(Transaction.amount_paise),
            )
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.category_id == category_id,
                Transaction.is_deleted == False,
                Transaction.status == "posted",
                Transaction.direction == "outflow",
                Transaction.transaction_date >= hist_start,
                Transaction.transaction_date < month_start,
            )
            .group_by(Transaction.transaction_date)
        )
        hist_res = await self.db.execute(hist_stmt)
        daily_amounts = [int(r[1]) for r in hist_res.all()]

        return daily_amounts, cur_month_total

    async def get_recurring_commitment_context(
        self,
        workspace_id: uuid.UUID,
        tx: CandidateTransactionVO,
    ) -> Optional[Dict[str, Any]]:
        """Checks if transaction matches an active or cancelled recurring definition."""
        if not tx.merchant_name and not tx.description:
            return None

        # Look for matching recurring definitions by name
        stmt = (
            select(RecurringDefinition)
            .where(
                RecurringDefinition.workspace_id == workspace_id,
                RecurringDefinition.is_deleted == False,
            )
        )
        res = await self.db.execute(stmt)
        defs = res.scalars().all()

        target_name = (tx.merchant_name or tx.description).lower()
        for d in defs:
            if d.name.lower() in target_name or target_name in d.name.lower():
                return {
                    "is_recurring": True,
                    "definition_id": d.id,
                    "name": d.name,
                    "expected_amount_paise": d.expected_amount_paise,
                    "status": d.status,
                    "frequency": d.frequency,
                }
        return None

    async def extract_ml_training_matrix(
        self,
        workspace_id: uuid.UUID,
        lookback_days: int = 90,
    ) -> List[List[float]]:
        """Extracts multivariate numerical feature vectors across historical transactions."""
        start_date = date.today() - timedelta(days=lookback_days)
        stmt = (
            select(Transaction)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.is_deleted == False,
                Transaction.status == "posted",
                Transaction.direction == "outflow",
                Transaction.transaction_date >= start_date,
            )
            .order_by(Transaction.created_at.asc())
            .limit(250)
        )
        res = await self.db.execute(stmt)
        txs = res.scalars().all()

        if len(txs) < 10:
            return []

        matrix: List[List[float]] = []
        prev_dt: Optional[datetime] = None

        for t in txs:
            diff_hrs = (t.created_at - prev_dt).total_seconds() / 3600.0 if prev_dt else 24.0
            prev_dt = t.created_at

            c_vo = CandidateTransactionVO(
                id=t.id,
                workspace_id=t.workspace_id,
                amount_paise=t.amount_paise,
                currency=t.currency,
                direction=t.direction,
                transaction_date=t.transaction_date,
                created_at=t.created_at,
                description=t.description or "",
                account_id=t.account_id,
                category_id=t.category_id,
                merchant_id=getattr(t, "merchant_id", None),
                merchant_name=t.merchant_name,
            )
            vec = extract_ml_feature_vector(c_vo, time_since_last_tx_hours=diff_hrs)
            matrix.append(vec)

        return matrix
