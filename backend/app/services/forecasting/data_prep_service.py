"""
Arthsavora Data Preparation & Eligibility Service
Extracts confirmed posted transactions, filters transfers and credit card repayments,
derives verified starting balances, and aggregates time-series for forecasting.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.forecasting import (
    DataEligibilityAssessment,
    TimeSeriesPoint,
    assess_data_eligibility,
)
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.transaction import Transaction


class DataPreparationService:
    """Extracts, cleans, and structures historical financial data for forecasting models."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_starting_balance(self, workspace_id: uuid.UUID) -> int:
        """
        Derives the authoritative starting cash balance across liquid accounts
        (savings, checking/current, cash, digital wallet, salary).
        Excludes credit card liabilities and loan principal.
        """
        stmt = (
            select(func.coalesce(func.sum(Account.current_book_balance_paise), 0))
            .where(
                Account.workspace_id == workspace_id,
                Account.status.in_(["active", "inactive"]),
                Account.is_deleted == False,
                Account.account_type.in_(["savings", "current", "cash", "salary", "digital_wallet", "petty_cash"]),
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def extract_daily_series(
        self,
        workspace_id: uuid.UUID,
        lookback_days: int = 90,
        end_date: Optional[date] = None,
    ) -> Tuple[List[TimeSeriesPoint], List[TimeSeriesPoint], date, date]:
        """
        Extracts daily aggregated posted income and expense series.
        Strictly excludes internal transfers, credit-card payments, and pending holds.
        Nets contra-expense refunds against daily outflows.
        """
        end_dt = end_date or date.today()
        start_dt = end_dt - timedelta(days=lookback_days)

        # Outflow query (excluding transfers & card repayments)
        outflow_stmt = (
            select(
                Transaction.transaction_date,
                func.sum(Transaction.amount_paise).label("total_paise"),
            )
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.status == "posted",
                Transaction.is_deleted == False,
                Transaction.transaction_date >= start_dt,
                Transaction.transaction_date <= end_dt,
                Transaction.direction == "outflow",
                Transaction.transfer_id.is_(None),
                Transaction.transaction_type.notin_(["transfer", "credit_card_payment", "loan_repayment"]),
            )
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date.asc())
        )
        outflow_res = await self.db.execute(outflow_stmt)
        outflow_map = {row[0]: int(row[1]) for row in outflow_res.all()}

        # Refund query to net against expense outflows
        refund_stmt = (
            select(
                Transaction.transaction_date,
                func.sum(Transaction.amount_paise).label("total_paise"),
            )
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.status == "posted",
                Transaction.is_deleted == False,
                Transaction.transaction_date >= start_dt,
                Transaction.transaction_date <= end_dt,
                Transaction.transaction_type.in_(["refund", "credit_card_refund"]),
            )
            .group_by(Transaction.transaction_date)
        )
        refund_res = await self.db.execute(refund_stmt)
        for row in refund_res.all():
            r_dt, r_amt = row[0], int(row[1])
            if r_dt in outflow_map:
                outflow_map[r_dt] = max(0, outflow_map[r_dt] - r_amt)

        # Inflow query (excluding transfers & refunds)
        inflow_stmt = (
            select(
                Transaction.transaction_date,
                func.sum(Transaction.amount_paise).label("total_paise"),
            )
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.status == "posted",
                Transaction.is_deleted == False,
                Transaction.transaction_date >= start_dt,
                Transaction.transaction_date <= end_dt,
                Transaction.direction == "inflow",
                Transaction.transfer_id.is_(None),
                Transaction.transaction_type.notin_(["transfer", "refund", "credit_card_refund"]),
            )
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date.asc())
        )
        inflow_res = await self.db.execute(inflow_stmt)
        inflow_map = {row[0]: int(row[1]) for row in inflow_res.all()}

        # Construct contiguous daily series
        daily_inflows: List[TimeSeriesPoint] = []
        daily_outflows: List[TimeSeriesPoint] = []

        curr_dt = start_dt
        while curr_dt <= end_dt:
            daily_inflows.append(TimeSeriesPoint(date=curr_dt, amount_paise=inflow_map.get(curr_dt, 0)))
            daily_outflows.append(TimeSeriesPoint(date=curr_dt, amount_paise=outflow_map.get(curr_dt, 0)))
            curr_dt += timedelta(days=1)

        return daily_inflows, daily_outflows, start_dt, end_dt

    async def extract_category_spending(
        self,
        workspace_id: uuid.UUID,
        lookback_days: int = 90,
        end_date: Optional[date] = None,
    ) -> Dict[Optional[uuid.UUID], List[TimeSeriesPoint]]:
        """Extracts daily spending time-series broken down by category."""
        end_dt = end_date or date.today()
        start_dt = end_dt - timedelta(days=lookback_days)

        stmt = (
            select(
                Transaction.category_id,
                Transaction.transaction_date,
                func.sum(Transaction.amount_paise).label("total_paise"),
            )
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.status == "posted",
                Transaction.is_deleted == False,
                Transaction.transaction_date >= start_dt,
                Transaction.transaction_date <= end_dt,
                Transaction.direction == "outflow",
                Transaction.transfer_id.is_(None),
                Transaction.transaction_type.notin_(["transfer", "credit_card_payment", "loan_repayment"]),
            )
            .group_by(Transaction.category_id, Transaction.transaction_date)
            .order_by(Transaction.transaction_date.asc())
        )
        res = await self.db.execute(stmt)

        cat_series: Dict[Optional[uuid.UUID], List[TimeSeriesPoint]] = {}
        for row in res.all():
            cat_id, dt, amt = row[0], row[1], int(row[2])
            if cat_id not in cat_series:
                cat_series[cat_id] = []
            cat_series[cat_id].append(TimeSeriesPoint(date=dt, amount_paise=amt))

        return cat_series
