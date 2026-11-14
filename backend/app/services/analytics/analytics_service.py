"""
Arthsavora Financial Analytics Application Service
Orchestrates analytical queries, validates date ranges, ensures multi-currency safety,
formats CSV export data with formula-injection sanitization, and verifies workspace security boundaries.
"""

import csv
from datetime import date
from decimal import Decimal
import io
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.analytics import (
    PeriodGrouping,
    ReportType,
    get_financial_year_bounds,
    get_month_bounds,
    get_quarter_bounds,
    sanitize_csv_cell,
)
from app.domain.exceptions import BusinessRuleViolationError
from app.repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:
    """Service layer orchestrating financial metrics, insights, and report generation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AnalyticsRepository(session)

    def _validate_date_range(self, start_date: date, end_date: date) -> None:
        """Validates that date ranges are chronologically ordered and bounded."""
        if start_date > end_date:
            raise BusinessRuleViolationError(
                rule_name="INVALID_DATE_RANGE",
                message=f"Start date ({start_date}) cannot be after end date ({end_date}).",
            )
        # Limit maximum analytical span to 10 years to prevent resource exhaustion
        if (end_date - start_date).days > 3650:
            raise BusinessRuleViolationError(
                rule_name="DATE_RANGE_EXCEEDED",
                message="Analytics query span cannot exceed 10 years (3650 days).",
            )

    def _validate_currency(self, currency: str) -> str:
        """Normalizes and validates ISO currency code."""
        curr = currency.strip().upper()
        if len(curr) != 3 or not curr.isalpha():
            raise BusinessRuleViolationError(
                rule_name="INVALID_CURRENCY",
                message=f"Currency '{currency}' must be a valid 3-letter ISO code (e.g. INR, USD, EUR).",
            )
        return curr

    async def get_overview(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Retrieves authoritative summary KPIs for a workspace and date window."""
        self._validate_date_range(start_date, end_date)
        valid_currency = self._validate_currency(currency)

        return await self.repository.get_financial_overview(
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            currency=valid_currency,
            account_id=account_id,
        )

    async def get_cash_flow_trends(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        grouping: PeriodGrouping = PeriodGrouping.MONTH,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves bucketed cash-flow time series for trend visualization."""
        self._validate_date_range(start_date, end_date)
        valid_currency = self._validate_currency(currency)

        return await self.repository.get_cash_flow_trends(
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            grouping=grouping,
            currency=valid_currency,
            account_id=account_id,
        )

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
        """Retrieves categorized spending breakdown and proportions."""
        self._validate_date_range(start_date, end_date)
        valid_currency = self._validate_currency(currency)

        valid_direction = direction.lower().strip()
        if valid_direction not in ("inflow", "outflow"):
            raise BusinessRuleViolationError(
                rule_name="INVALID_DIRECTION",
                message="Category spending direction must be either 'inflow' or 'outflow'.",
            )

        return await self.repository.get_category_spending(
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            direction=valid_direction,
            limit=limit,
            currency=valid_currency,
            account_id=account_id,
        )

    async def get_merchant_spending(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        limit: int = 10,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Retrieves top merchant rankings and metrics."""
        self._validate_date_range(start_date, end_date)
        valid_currency = self._validate_currency(currency)

        return await self.repository.get_merchant_spending(
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            currency=valid_currency,
            account_id=account_id,
        )

    async def get_net_worth(
        self,
        workspace_id: uuid.UUID,
        currency: str = "INR",
    ) -> Dict[str, Any]:
        """Calculates current net worth and account asset/liability breakdown."""
        valid_currency = self._validate_currency(currency)
        return await self.repository.get_account_balances_and_net_worth(
            workspace_id=workspace_id,
            currency=valid_currency,
        )

    async def get_comparison(
        self,
        workspace_id: uuid.UUID,
        current_start: date,
        current_end: date,
        previous_start: Optional[date] = None,
        previous_end: Optional[date] = None,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Calculates period-over-period comparative metrics and delta sentiments."""
        self._validate_date_range(current_start, current_end)
        if previous_start and previous_end:
            self._validate_date_range(previous_start, previous_end)

        valid_currency = self._validate_currency(currency)

        return await self.repository.get_period_comparison(
            workspace_id=workspace_id,
            current_start=current_start,
            current_end=current_end,
            previous_start=previous_start,
            previous_end=previous_end,
            currency=valid_currency,
            account_id=account_id,
        )

    async def export_analytics_csv(
        self,
        workspace_id: uuid.UUID,
        report_type: ReportType,
        start_date: date,
        end_date: date,
        currency: str = "INR",
        account_id: Optional[uuid.UUID] = None,
    ) -> str:
        """
        Generates a sanitized CSV string for analytical reports.
        Applies formula injection protection to all string outputs.
        """
        self._validate_date_range(start_date, end_date)
        valid_currency = self._validate_currency(currency)

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        if report_type == ReportType.OVERVIEW:
            data = await self.get_overview(
                workspace_id=workspace_id,
                start_date=start_date,
                end_date=end_date,
                currency=valid_currency,
                account_id=account_id,
            )
            writer.writerow(["Arthsavora Financial Analytics Summary"])
            writer.writerow(["Workspace ID", sanitize_csv_cell(str(workspace_id))])
            writer.writerow(["Period", f"{start_date} to {end_date}"])
            writer.writerow(["Currency", valid_currency])
            writer.writerow([])
            writer.writerow(["Metric", "Amount (Major)", "Amount (Paise)"])
            writer.writerow(["Total Income", str(data["total_income"]), data["total_income_paise"]])
            writer.writerow(["Gross Expenses", str(Decimal(data["gross_expenses_paise"]) / Decimal(100)), data["gross_expenses_paise"]])
            writer.writerow(["Refunds & Cashbacks", str(Decimal(data["refunds_paise"]) / Decimal(100)), data["refunds_paise"]])
            writer.writerow(["Net Operating Expenses", str(data["total_expenses"]), data["total_expenses_paise"]])
            writer.writerow(["Net Cash Flow", str(data["net_cash_flow"]), data["net_cash_flow_paise"]])
            writer.writerow(["Savings Rate (%)", f"{data['savings_rate_percentage']}%", ""])
            writer.writerow(["Average Daily Spend", str(data["average_daily_spend"]), data["average_daily_spend_paise"]])
            writer.writerow(["Transaction Count", data["transaction_count"], ""])
            writer.writerow([])
            writer.writerow(["Data Quality Indicators", "Value", "Amount (Paise)"])
            dq = data["data_quality"]
            writer.writerow(["Uncategorized Transactions", dq["uncategorized_count"], dq["uncategorized_amount_paise"]])
            writer.writerow(["Excluded Transfers", dq["excluded_transfers_count"], dq["excluded_transfers_amount_paise"]])
            writer.writerow(["Excluded Pending Transactions", dq["excluded_pending_count"], dq["excluded_pending_amount_paise"]])

        elif report_type == ReportType.CASH_FLOW:
            trends = await self.get_cash_flow_trends(
                workspace_id=workspace_id,
                start_date=start_date,
                end_date=end_date,
                grouping=PeriodGrouping.MONTH,
                currency=valid_currency,
                account_id=account_id,
            )
            writer.writerow(["Period Start", "Period Label", "Income", "Expenses", "Net Cash Flow", "Cumulative Cash Flow", "Transactions"])
            for pt in trends:
                writer.writerow([
                    sanitize_csv_cell(pt["period_start"]),
                    sanitize_csv_cell(pt["period_label"]),
                    str(pt["income"]),
                    str(pt["expenses"]),
                    str(pt["net_cash_flow"]),
                    str(pt["cumulative_cash_flow"]),
                    pt["transaction_count"],
                ])

        elif report_type == ReportType.CATEGORIES:
            cat_data = await self.get_category_spending(
                workspace_id=workspace_id,
                start_date=start_date,
                end_date=end_date,
                direction="outflow",
                limit=50,
                currency=valid_currency,
                account_id=account_id,
            )
            writer.writerow(["Category Name", "Category Slug", "Spend Amount", "Amount (Paise)", "Percentage of Total (%)", "Transactions"])
            for cat in cat_data["categories"]:
                writer.writerow([
                    sanitize_csv_cell(cat["category_name"]),
                    sanitize_csv_cell(cat["category_slug"]),
                    str(cat["total_amount"]),
                    cat["total_amount_paise"],
                    f"{cat['percentage_of_total']}%",
                    cat["transaction_count"],
                ])

        elif report_type == ReportType.MERCHANTS:
            merchant_data = await self.get_merchant_spending(
                workspace_id=workspace_id,
                start_date=start_date,
                end_date=end_date,
                limit=50,
                currency=valid_currency,
                account_id=account_id,
            )
            writer.writerow(["Merchant Name", "Spend Amount", "Amount (Paise)", "Percentage of Total (%)", "Transactions", "Average Ticket", "Last Date"])
            for m in merchant_data["merchants"]:
                writer.writerow([
                    sanitize_csv_cell(m["merchant_name"]),
                    str(m["total_amount"]),
                    m["total_amount_paise"],
                    f"{m['percentage_of_total']}%",
                    m["transaction_count"],
                    str(m["average_ticket"]),
                    sanitize_csv_cell(m["last_transaction_date"]),
                ])

        elif report_type == ReportType.NET_WORTH:
            nw_data = await self.get_net_worth(workspace_id=workspace_id, currency=valid_currency)
            writer.writerow(["Arthsavora Balance Sheet Position"])
            writer.writerow(["Workspace ID", sanitize_csv_cell(str(workspace_id))])
            writer.writerow(["As of Date", nw_data["as_of_date"]])
            writer.writerow(["Total Assets", str(nw_data["total_assets"]), nw_data["total_assets_paise"]])
            writer.writerow(["Total Liabilities", str(nw_data["total_liabilities"]), nw_data["total_liabilities_paise"]])
            writer.writerow(["Net Worth", str(nw_data["net_worth"]), nw_data["net_worth_paise"]])
            writer.writerow([])
            writer.writerow(["Asset Accounts", "Type", "Institution", "Identifier", "Balance"])
            for a in nw_data["asset_accounts"]:
                writer.writerow([
                    sanitize_csv_cell(a["name"]),
                    sanitize_csv_cell(a["account_type"]),
                    sanitize_csv_cell(a["institution_name"]),
                    sanitize_csv_cell(a["masked_identifier"]),
                    str(a["current_book_balance"]),
                ])
            writer.writerow([])
            writer.writerow(["Liability Accounts", "Type", "Institution", "Identifier", "Outstanding Liability", "Credit Limit", "Due Date"])
            for l in nw_data["liability_accounts"]:
                writer.writerow([
                    sanitize_csv_cell(l["name"]),
                    sanitize_csv_cell(l["account_type"]),
                    sanitize_csv_cell(l["institution_name"]),
                    sanitize_csv_cell(l["masked_identifier"]),
                    str(l["outstanding_liability"]),
                    str(l["credit_limit"]) if l["credit_limit"] is not None else "",
                    sanitize_csv_cell(l["due_date"]),
                ])

        return output.getvalue()
