"""
Arthsavora Financial Analytics Repository
High-performance PostgreSQL aggregation queries for financial dashboards,
cash-flow forecasting foundations, category/merchant intelligence, and balance sheets.
Enforces multi-tenant isolation, exact integer minor units (paise), transfer exclusions,
and anti-IDOR security.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import BigInteger, DateTime, Integer, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.transaction import Transaction
from app.domain.analytics import (
    PeriodGrouping,
    calculate_percentage_delta,
    calculate_savings_rate,
    evaluate_sentiment,
    get_previous_period_bounds,
)

# Standard classification sets for double-entry financial integrity
INCOME_TRANSACTION_TYPES = (
    "income",
    "deposit",
    "dividend",
    "interest_income",
)

EXPENSE_TRANSACTION_TYPES = (
    "expense",
    "withdrawal",
    "bank_fee",
    "tax",
    "credit_card_purchase",
    "credit_card_fee",
    "credit_card_interest",
    "loan_interest_payment",
    "loan_fee",
    "investment_fee",
    "cash_transaction",
)

REFUND_TRANSACTION_TYPES = (
    "refund",
    "credit_card_refund",
)

EXCLUDED_TRANSFER_TYPES = (
    "transfer",
    "credit_card_payment",
    "loan_disbursal",
    "loan_principal_repayment",
    "investment_contribution",
    "investment_withdrawal",
    "adjustment",
    "reversal",
)

LIABILITY_ACCOUNT_TYPES = (
    "credit_card",
    "loan",
    "business_credit_card",
    "loan_account",
)


class AnalyticsRepository:
    """Repository handling all server-side SQL aggregation for financial analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_financial_overview(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Executes a single PostgreSQL aggregation query computing:
        - Gross income, refunds, gross expense, net expense, net cash flow
        - Transaction counts
        - Excluded transfer count/amount
        - Excluded pending count/amount
        - Uncategorized count/amount
        """
        # Base filter for workspace and date range
        base_conditions = [
            Transaction.workspace_id == workspace_id,
            Transaction.is_deleted == False,
            Transaction.currency == currency,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        ]
        if account_id:
            base_conditions.append(Transaction.account_id == account_id)

        # SQL Case expressions for server-side aggregation
        is_posted = Transaction.status == "posted"
        is_pending = Transaction.status == "pending"
        is_not_transfer = (
            Transaction.transfer_id.is_(None)
            & (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES))
        )

        income_condition = (
            is_posted
            & is_not_transfer
            & (
                Transaction.transaction_type.in_(INCOME_TRANSACTION_TYPES)
                | ((Transaction.direction == "inflow") & (~Transaction.transaction_type.in_(REFUND_TRANSACTION_TYPES)))
            )
        )

        expense_condition = (
            is_posted
            & is_not_transfer
            & (
                Transaction.transaction_type.in_(EXPENSE_TRANSACTION_TYPES)
                | ((Transaction.direction == "outflow") & (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)))
            )
        )

        refund_condition = (
            is_posted
            & is_not_transfer
            & Transaction.transaction_type.in_(REFUND_TRANSACTION_TYPES)
        )

        transfer_condition = is_posted & (
            Transaction.transfer_id.is_not(None)
            | Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)
        )

        uncategorized_condition = (
            is_posted
            & is_not_transfer
            & Transaction.category_id.is_(None)
            & (expense_condition | income_condition)
        )

        stmt = select(
            # Total Income
            func.coalesce(
                func.sum(case((income_condition, Transaction.amount_paise), else_=0)),
                0,
            ).label("gross_income_paise"),
            # Total Refunds (contra-expense / inflow)
            func.coalesce(
                func.sum(case((refund_condition, Transaction.amount_paise), else_=0)),
                0,
            ).label("refunds_paise"),
            # Gross Expenses
            func.coalesce(
                func.sum(case((expense_condition, Transaction.amount_paise), else_=0)),
                0,
            ).label("gross_expenses_paise"),
            # Posted Operational Transaction Count
            func.coalesce(
                func.sum(case(((income_condition | expense_condition | refund_condition), 1), else_=0)),
                0,
            ).label("transaction_count"),
            # Excluded Transfers (Count & Volume)
            func.coalesce(
                func.sum(case((transfer_condition, 1), else_=0)),
                0,
            ).label("excluded_transfers_count"),
            func.coalesce(
                func.sum(case((transfer_condition, Transaction.amount_paise), else_=0)),
                0,
            ).label("excluded_transfers_amount_paise"),
            # Excluded Pending Transactions (Count & Volume)
            func.coalesce(
                func.sum(case((is_pending, 1), else_=0)),
                0,
            ).label("excluded_pending_count"),
            func.coalesce(
                func.sum(case((is_pending, Transaction.amount_paise), else_=0)),
                0,
            ).label("excluded_pending_amount_paise"),
            # Uncategorized Transactions (Count & Volume)
            func.coalesce(
                func.sum(case((uncategorized_condition, 1), else_=0)),
                0,
            ).label("uncategorized_count"),
            func.coalesce(
                func.sum(case((uncategorized_condition, Transaction.amount_paise), else_=0)),
                0,
            ).label("uncategorized_amount_paise"),
        ).where(*base_conditions)

        result = (await self.session.execute(stmt)).one()

        gross_income_paise = int(result.gross_income_paise)
        refunds_paise = int(result.refunds_paise)
        gross_expenses_paise = int(result.gross_expenses_paise)

        # Net expenses = gross expenses - refunds (refunds directly offset spending)
        net_expenses_paise = max(0, gross_expenses_paise - refunds_paise)
        total_income_paise = gross_income_paise
        net_cash_flow_paise = total_income_paise - net_expenses_paise
        savings_rate_percentage = calculate_savings_rate(total_income_paise, net_expenses_paise)

        # Average daily spend calculation
        days_in_period = max(1, (end_date - start_date).days + 1)
        avg_daily_spend_paise = int(net_expenses_paise // days_in_period)

        return {
            "workspace_id": workspace_id,
            "currency": currency,
            "start_date": start_date,
            "end_date": end_date,
            "total_income_paise": total_income_paise,
            "total_income": Decimal(total_income_paise) / Decimal(100),
            "gross_expenses_paise": gross_expenses_paise,
            "refunds_paise": refunds_paise,
            "total_expenses_paise": net_expenses_paise,
            "total_expenses": Decimal(net_expenses_paise) / Decimal(100),
            "net_cash_flow_paise": net_cash_flow_paise,
            "net_cash_flow": Decimal(net_cash_flow_paise) / Decimal(100),
            "savings_paise": net_cash_flow_paise,
            "savings": Decimal(net_cash_flow_paise) / Decimal(100),
            "savings_rate_percentage": savings_rate_percentage,
            "transaction_count": int(result.transaction_count),
            "average_daily_spend_paise": avg_daily_spend_paise,
            "average_daily_spend": Decimal(avg_daily_spend_paise) / Decimal(100),
            "days_in_period": days_in_period,
            "data_quality": {
                "uncategorized_count": int(result.uncategorized_count),
                "uncategorized_amount_paise": int(result.uncategorized_amount_paise),
                "uncategorized_amount": Decimal(int(result.uncategorized_amount_paise)) / Decimal(100),
                "excluded_transfers_count": int(result.excluded_transfers_count),
                "excluded_transfers_amount_paise": int(result.excluded_transfers_amount_paise),
                "excluded_transfers_amount": Decimal(int(result.excluded_transfers_amount_paise)) / Decimal(100),
                "excluded_pending_count": int(result.excluded_pending_count),
                "excluded_pending_amount_paise": int(result.excluded_pending_amount_paise),
                "excluded_pending_amount": Decimal(int(result.excluded_pending_amount_paise)) / Decimal(100),
            },
        }

    async def get_cash_flow_trends(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        grouping: PeriodGrouping = PeriodGrouping.MONTH,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Groups cash-flow into time intervals (day, week, month, quarter, financial_year).
        Uses PostgreSQL date_trunc for server-side temporal partitioning.
        """
        # Determine PostgreSQL date_trunc interval
        trunc_interval_map = {
            PeriodGrouping.DAY: "day",
            PeriodGrouping.WEEK: "week",
            PeriodGrouping.MONTH: "month",
            PeriodGrouping.QUARTER: "quarter",
            PeriodGrouping.FINANCIAL_YEAR: "year",
        }
        interval_str = trunc_interval_map.get(grouping, "month")

        base_conditions = [
            Transaction.workspace_id == workspace_id,
            Transaction.is_deleted == False,
            Transaction.currency == currency,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == "posted",
            Transaction.transfer_id.is_(None),
            (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)),
        ]
        if account_id:
            base_conditions.append(Transaction.account_id == account_id)

        income_condition = (
            Transaction.transaction_type.in_(INCOME_TRANSACTION_TYPES)
            | ((Transaction.direction == "inflow") & (~Transaction.transaction_type.in_(REFUND_TRANSACTION_TYPES)))
        )

        expense_condition = (
            Transaction.transaction_type.in_(EXPENSE_TRANSACTION_TYPES)
            | ((Transaction.direction == "outflow") & (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)))
        )

        refund_condition = Transaction.transaction_type.in_(REFUND_TRANSACTION_TYPES)

        # Truncate transaction date to interval
        period_bucket = func.date_trunc(interval_str, cast(Transaction.transaction_date, DateTime)).label("bucket")

        stmt = (
            select(
                period_bucket,
                func.coalesce(
                    func.sum(case((income_condition, Transaction.amount_paise), else_=0)),
                    0,
                ).label("income_paise"),
                func.coalesce(
                    func.sum(case((expense_condition, Transaction.amount_paise), else_=0)),
                    0,
                ).label("gross_expense_paise"),
                func.coalesce(
                    func.sum(case((refund_condition, Transaction.amount_paise), else_=0)),
                    0,
                ).label("refunds_paise"),
                func.count(Transaction.id).label("tx_count"),
            )
            .where(*base_conditions)
            .group_by(period_bucket)
            .order_by(period_bucket.asc())
        )

        rows = (await self.session.execute(stmt)).all()

        cumulative_cash_flow_paise = 0
        trend_points: List[Dict[str, Any]] = []

        for row in rows:
            bucket_dt: datetime = row.bucket
            bucket_date = bucket_dt.date() if isinstance(bucket_dt, datetime) else bucket_dt

            income_paise = int(row.income_paise)
            gross_expense_paise = int(row.gross_expense_paise)
            refunds_paise = int(row.refunds_paise)
            net_expense_paise = max(0, gross_expense_paise - refunds_paise)
            net_flow_paise = income_paise - net_expense_paise
            cumulative_cash_flow_paise += net_flow_paise

            # Construct human-friendly label
            if grouping == PeriodGrouping.DAY:
                label = bucket_date.strftime("%d %b %Y")
            elif grouping == PeriodGrouping.WEEK:
                label = f"W{bucket_date.isocalendar()[1]} {bucket_date.year}"
            elif grouping == PeriodGrouping.MONTH:
                label = bucket_date.strftime("%b %Y")
            elif grouping == PeriodGrouping.QUARTER:
                quarter = (bucket_date.month - 1) // 3 + 1
                label = f"Q{quarter} {bucket_date.year}"
            elif grouping == PeriodGrouping.FINANCIAL_YEAR:
                fy_start_yr = bucket_date.year if bucket_date.month >= 4 else bucket_date.year - 1
                label = f"FY {fy_start_yr}-{(fy_start_yr + 1) % 100:02d}"
            else:
                label = str(bucket_date)

            trend_points.append({
                "period_start": bucket_date.isoformat(),
                "period_label": label,
                "income_paise": income_paise,
                "income": Decimal(income_paise) / Decimal(100),
                "expenses_paise": net_expense_paise,
                "expenses": Decimal(net_expense_paise) / Decimal(100),
                "net_cash_flow_paise": net_flow_paise,
                "net_cash_flow": Decimal(net_flow_paise) / Decimal(100),
                "cumulative_cash_flow_paise": cumulative_cash_flow_paise,
                "cumulative_cash_flow": Decimal(cumulative_cash_flow_paise) / Decimal(100),
                "transaction_count": int(row.tx_count),
            })

        return trend_points

    async def get_category_spending(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        direction: str = "outflow",
        limit: int = 10,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates category spending with exact percentages, transaction counts,
        and graceful handling for uncategorized transactions.
        """
        safe_limit = max(1, min(limit, 50))

        base_conditions = [
            Transaction.workspace_id == workspace_id,
            Transaction.is_deleted == False,
            Transaction.currency == currency,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == "posted",
            Transaction.transfer_id.is_(None),
            (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)),
        ]
        if account_id:
            base_conditions.append(Transaction.account_id == account_id)

        if direction == "outflow":
            base_conditions.append(
                Transaction.transaction_type.in_(EXPENSE_TRANSACTION_TYPES)
                | ((Transaction.direction == "outflow") & (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)))
            )
        else:
            base_conditions.append(
                Transaction.transaction_type.in_(INCOME_TRANSACTION_TYPES)
                | ((Transaction.direction == "inflow") & (~Transaction.transaction_type.in_(REFUND_TRANSACTION_TYPES)))
            )

        # 1. Total spend across all categories in period
        total_stmt = select(
            func.coalesce(func.sum(Transaction.amount_paise), 0).label("total_paise")
        ).where(*base_conditions)
        total_spend_paise = int((await self.session.execute(total_stmt)).scalar() or 0)

        # 2. Group by category
        group_stmt = (
            select(
                Transaction.category_id,
                Category.name.label("category_name"),
                Category.slug.label("category_slug"),
                Category.icon.label("category_icon"),
                Category.color.label("category_color"),
                Category.is_system.label("is_system"),
                func.sum(Transaction.amount_paise).label("cat_amount_paise"),
                func.count(Transaction.id).label("tx_count"),
            )
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(*base_conditions)
            .group_by(
                Transaction.category_id,
                Category.name,
                Category.slug,
                Category.icon,
                Category.color,
                Category.is_system,
            )
            .order_by(func.sum(Transaction.amount_paise).desc())
            .limit(safe_limit)
        )

        rows = (await self.session.execute(group_stmt)).all()

        categories_list = []
        for r in rows:
            cat_paise = int(r.cat_amount_paise)
            pct = round((cat_paise / total_spend_paise) * 100.0, 2) if total_spend_paise > 0 else 0.0

            is_uncategorized = r.category_id is None
            cat_name = "Uncategorized" if is_uncategorized else (r.category_name or "Unknown")
            cat_slug = "uncategorized" if is_uncategorized else (r.category_slug or "unknown")
            cat_icon = "help-circle" if is_uncategorized else (r.category_icon or "tag")
            cat_color = "#94a3b8" if is_uncategorized else (r.category_color or "#6366f1")

            categories_list.append({
                "category_id": r.category_id,
                "category_name": cat_name,
                "category_slug": cat_slug,
                "icon": cat_icon,
                "color": cat_color,
                "is_system": bool(r.is_system) if not is_uncategorized else False,
                "is_uncategorized": is_uncategorized,
                "total_amount_paise": cat_paise,
                "total_amount": Decimal(cat_paise) / Decimal(100),
                "percentage_of_total": pct,
                "transaction_count": int(r.tx_count),
            })

        return {
            "direction": direction,
            "currency": currency,
            "total_spend_paise": total_spend_paise,
            "total_spend": Decimal(total_spend_paise) / Decimal(100),
            "categories": categories_list,
        }

    async def get_merchant_spending(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        limit: int = 10,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Ranks top merchants by expenditure, calculating transaction frequency,
        average ticket size, and percentage of overall spend.
        """
        safe_limit = max(1, min(limit, 50))

        base_conditions = [
            Transaction.workspace_id == workspace_id,
            Transaction.is_deleted == False,
            Transaction.currency == currency,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == "posted",
            Transaction.transfer_id.is_(None),
            (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)),
            (
                Transaction.transaction_type.in_(EXPENSE_TRANSACTION_TYPES)
                | ((Transaction.direction == "outflow") & (~Transaction.transaction_type.in_(EXCLUDED_TRANSFER_TYPES)))
            ),
        ]
        if account_id:
            base_conditions.append(Transaction.account_id == account_id)

        # Total spend across all merchants
        total_stmt = select(
            func.coalesce(func.sum(Transaction.amount_paise), 0)
        ).where(*base_conditions)
        total_spend_paise = int((await self.session.execute(total_stmt)).scalar() or 0)

        merchant_expr = func.coalesce(
            func.nullif(func.trim(Transaction.merchant_name), ""),
            "Other / Unspecified",
        ).label("merchant_label")

        stmt = (
            select(
                merchant_expr,
                func.sum(Transaction.amount_paise).label("merchant_paise"),
                func.count(Transaction.id).label("tx_count"),
                func.max(Transaction.transaction_date).label("last_date"),
            )
            .where(*base_conditions)
            .group_by(merchant_expr)
            .order_by(func.sum(Transaction.amount_paise).desc())
            .limit(safe_limit)
        )

        rows = (await self.session.execute(stmt)).all()

        merchants_list = []
        for r in rows:
            m_paise = int(r.merchant_paise)
            tx_count = int(r.tx_count)
            avg_ticket_paise = int(m_paise // max(1, tx_count))
            pct = round((m_paise / total_spend_paise) * 100.0, 2) if total_spend_paise > 0 else 0.0

            merchants_list.append({
                "merchant_name": r.merchant_label,
                "total_amount_paise": m_paise,
                "total_amount": Decimal(m_paise) / Decimal(100),
                "percentage_of_total": pct,
                "transaction_count": tx_count,
                "average_ticket_paise": avg_ticket_paise,
                "average_ticket": Decimal(avg_ticket_paise) / Decimal(100),
                "last_transaction_date": r.last_date.isoformat() if r.last_date else None,
            })

        return {
            "currency": currency,
            "total_spend_paise": total_spend_paise,
            "total_spend": Decimal(total_spend_paise) / Decimal(100),
            "merchants": merchants_list,
        }

    async def get_account_balances_and_net_worth(
        self,
        workspace_id: uuid.UUID,
        currency: str = "INR",
    ) -> Dict[str, Any]:
        """
        Derives current balance sheet position from active accounts:
        - Asset accounts (Savings, Current, Cash, Wallet, Investment)
        - Liability accounts (Credit Card, Loan, Loan Account)
        - Net Worth = Total Assets - Total Liabilities
        """
        stmt = (
            select(Account)
            .where(
                Account.workspace_id == workspace_id,
                Account.is_deleted == False,
                Account.currency == currency,
                Account.status == "active",
            )
            .order_by(Account.account_type.asc(), Account.name.asc())
        )
        accounts = list((await self.session.execute(stmt)).scalars().all())

        total_assets_paise = 0
        total_liabilities_paise = 0

        asset_accounts = []
        liability_accounts = []

        for acc in accounts:
            acc_type_lower = acc.account_type.lower()
            if acc_type_lower in LIABILITY_ACCOUNT_TYPES:
                # Liability balance: outstanding_liability_paise or abs(current_book_balance_paise)
                liability_val = (
                    acc.outstanding_liability_paise
                    if acc.outstanding_liability_paise is not None
                    else abs(acc.current_book_balance_paise)
                )
                total_liabilities_paise += liability_val

                liability_accounts.append({
                    "id": acc.id,
                    "name": acc.name,
                    "account_type": acc.account_type,
                    "institution_name": acc.institution_name,
                    "masked_identifier": acc.masked_identifier,
                    "outstanding_liability_paise": liability_val,
                    "outstanding_liability": Decimal(liability_val) / Decimal(100),
                    "credit_limit_paise": acc.credit_limit_paise,
                    "credit_limit": Decimal(acc.credit_limit_paise) / Decimal(100) if acc.credit_limit_paise else None,
                    "due_date": acc.due_date.isoformat() if acc.due_date else None,
                })
            else:
                # Asset account: current_book_balance_paise
                asset_val = acc.current_book_balance_paise
                total_assets_paise += asset_val

                asset_accounts.append({
                    "id": acc.id,
                    "name": acc.name,
                    "account_type": acc.account_type,
                    "institution_name": acc.institution_name,
                    "masked_identifier": acc.masked_identifier,
                    "current_book_balance_paise": asset_val,
                    "current_book_balance": Decimal(asset_val) / Decimal(100),
                })

        net_worth_paise = total_assets_paise - total_liabilities_paise

        return {
            "workspace_id": workspace_id,
            "currency": currency,
            "as_of_date": date.today().isoformat(),
            "total_assets_paise": total_assets_paise,
            "total_assets": Decimal(total_assets_paise) / Decimal(100),
            "total_liabilities_paise": total_liabilities_paise,
            "total_liabilities": Decimal(total_liabilities_paise) / Decimal(100),
            "net_worth_paise": net_worth_paise,
            "net_worth": Decimal(net_worth_paise) / Decimal(100),
            "asset_accounts": asset_accounts,
            "liability_accounts": liability_accounts,
        }

    async def get_period_comparison(
        self,
        workspace_id: uuid.UUID,
        current_start: date,
        current_end: date,
        previous_start: Optional[date] = None,
        previous_end: Optional[date] = None,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Compares current period financial performance against an automatically computed
        or explicitly provided previous period.
        Calculates absolute deltas, percentage changes, and financial sentiments.
        """
        if not previous_start or not previous_end:
            previous_start, previous_end = get_previous_period_bounds(current_start, current_end)

        current_overview = await self.get_financial_overview(
            workspace_id=workspace_id,
            start_date=current_start,
            end_date=current_end,
            currency=currency,
            account_id=account_id,
        )

        previous_overview = await self.get_financial_overview(
            workspace_id=workspace_id,
            start_date=previous_start,
            end_date=previous_end,
            currency=currency,
            account_id=account_id,
        )

        # Delta calculations
        income_delta_paise = current_overview["total_income_paise"] - previous_overview["total_income_paise"]
        income_pct_delta = calculate_percentage_delta(
            current_overview["total_income_paise"],
            previous_overview["total_income_paise"],
        )
        income_sentiment = evaluate_sentiment("income", income_delta_paise)

        expense_delta_paise = current_overview["total_expenses_paise"] - previous_overview["total_expenses_paise"]
        expense_pct_delta = calculate_percentage_delta(
            current_overview["total_expenses_paise"],
            previous_overview["total_expenses_paise"],
        )
        expense_sentiment = evaluate_sentiment("expenses", expense_delta_paise)

        net_flow_delta_paise = current_overview["net_cash_flow_paise"] - previous_overview["net_cash_flow_paise"]
        net_flow_pct_delta = calculate_percentage_delta(
            current_overview["net_cash_flow_paise"],
            previous_overview["net_cash_flow_paise"],
        )
        net_flow_sentiment = evaluate_sentiment("net_cash_flow", net_flow_delta_paise)

        savings_rate_delta_pct = round(
            current_overview["savings_rate_percentage"] - previous_overview["savings_rate_percentage"],
            2,
        )
        savings_rate_sentiment = evaluate_sentiment("savings", savings_rate_delta_pct)

        return {
            "currency": currency,
            "current_period": {
                "start_date": current_start.isoformat(),
                "end_date": current_end.isoformat(),
                "income_paise": current_overview["total_income_paise"],
                "income": current_overview["total_income"],
                "expenses_paise": current_overview["total_expenses_paise"],
                "expenses": current_overview["total_expenses"],
                "net_cash_flow_paise": current_overview["net_cash_flow_paise"],
                "net_cash_flow": current_overview["net_cash_flow"],
                "savings_rate_percentage": current_overview["savings_rate_percentage"],
            },
            "previous_period": {
                "start_date": previous_start.isoformat(),
                "end_date": previous_end.isoformat(),
                "income_paise": previous_overview["total_income_paise"],
                "income": previous_overview["total_income"],
                "expenses_paise": previous_overview["total_expenses_paise"],
                "expenses": previous_overview["total_expenses"],
                "net_cash_flow_paise": previous_overview["net_cash_flow_paise"],
                "net_cash_flow": previous_overview["net_cash_flow"],
                "savings_rate_percentage": previous_overview["savings_rate_percentage"],
            },
            "deltas": {
                "income_delta_paise": income_delta_paise,
                "income_delta": Decimal(income_delta_paise) / Decimal(100),
                "income_percentage_delta": income_pct_delta,
                "income_sentiment": income_sentiment.value,
                "expenses_delta_paise": expense_delta_paise,
                "expenses_delta": Decimal(expense_delta_paise) / Decimal(100),
                "expenses_percentage_delta": expense_pct_delta,
                "expenses_sentiment": expense_sentiment.value,
                "net_cash_flow_delta_paise": net_flow_delta_paise,
                "net_cash_flow_delta": Decimal(net_flow_delta_paise) / Decimal(100),
                "net_cash_flow_percentage_delta": net_flow_pct_delta,
                "net_cash_flow_sentiment": net_flow_sentiment.value,
                "savings_rate_delta_percentage": savings_rate_delta_pct,
                "savings_rate_sentiment": savings_rate_sentiment.value,
            },
        }
