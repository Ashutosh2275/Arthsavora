"""
Arthsavora Financial Analytics Pydantic Request & Response Schemas
Exact decimal and integer minor unit (paise) representation, ISO dates, and strict type validation.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.domain.analytics import PeriodGrouping, ReportType


class DataQualityIndicator(BaseModel):
    """Integrity and data completeness metrics for the analytical period."""
    uncategorized_count: int = Field(..., description="Number of posted transactions lacking a category")
    uncategorized_amount_paise: int = Field(..., description="Uncategorized transaction volume in paise")
    uncategorized_amount: Decimal = Field(..., description="Uncategorized transaction volume in major units")
    excluded_transfers_count: int = Field(..., description="Transfers excluded from income/expense to prevent turnover inflation")
    excluded_transfers_amount_paise: int = Field(..., description="Excluded transfer volume in paise")
    excluded_transfers_amount: Decimal = Field(..., description="Excluded transfer volume in major units")
    excluded_pending_count: int = Field(..., description="Pending transactions safely omitted from authoritative totals")
    excluded_pending_amount_paise: int = Field(..., description="Excluded pending volume in paise")
    excluded_pending_amount: Decimal = Field(..., description="Excluded pending volume in major units")

    model_config = ConfigDict(from_attributes=True)


class FinancialOverviewResponse(BaseModel):
    """Authoritative high-level financial summary KPIs."""
    workspace_id: uuid.UUID
    currency: str = "INR"
    start_date: date
    end_date: date
    total_income_paise: int
    total_income: Decimal
    gross_expenses_paise: int
    refunds_paise: int
    total_expenses_paise: int
    total_expenses: Decimal
    net_cash_flow_paise: int
    net_cash_flow: Decimal
    savings_paise: int
    savings: Decimal
    savings_rate_percentage: float
    transaction_count: int
    average_daily_spend_paise: int
    average_daily_spend: Decimal
    days_in_period: int
    data_quality: DataQualityIndicator

    model_config = ConfigDict(from_attributes=True)


class CashFlowTrendPoint(BaseModel):
    """Single aggregated temporal bucket in a cash-flow series."""
    period_start: str
    period_label: str
    income_paise: int
    income: Decimal
    expenses_paise: int
    expenses: Decimal
    net_cash_flow_paise: int
    net_cash_flow: Decimal
    cumulative_cash_flow_paise: int
    cumulative_cash_flow: Decimal
    transaction_count: int

    model_config = ConfigDict(from_attributes=True)


class CashFlowTrendsResponse(BaseModel):
    """Series of cash flow trend points over requested time intervals."""
    currency: str
    grouping: PeriodGrouping
    start_date: date
    end_date: date
    trends: List[CashFlowTrendPoint]

    model_config = ConfigDict(from_attributes=True)


class CategorySpendingItem(BaseModel):
    """Category breakdown metric line item."""
    category_id: Optional[uuid.UUID] = None
    category_name: str
    category_slug: str
    icon: str
    color: str
    is_system: bool
    is_uncategorized: bool
    total_amount_paise: int
    total_amount: Decimal
    percentage_of_total: float
    transaction_count: int

    model_config = ConfigDict(from_attributes=True)


class CategorySpendingResponse(BaseModel):
    """Expenditure distribution across categories."""
    direction: str
    currency: str
    total_spend_paise: int
    total_spend: Decimal
    categories: List[CategorySpendingItem]

    model_config = ConfigDict(from_attributes=True)


class MerchantSpendingItem(BaseModel):
    """Merchant ranking and ticket metrics."""
    merchant_name: str
    total_amount_paise: int
    total_amount: Decimal
    percentage_of_total: float
    transaction_count: int
    average_ticket_paise: int
    average_ticket: Decimal
    last_transaction_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MerchantSpendingResponse(BaseModel):
    """Expenditure distribution across commercial merchants."""
    currency: str
    total_spend_paise: int
    total_spend: Decimal
    merchants: List[MerchantSpendingItem]

    model_config = ConfigDict(from_attributes=True)


class AssetAccountSummary(BaseModel):
    """Asset account balance line item."""
    id: uuid.UUID
    name: str
    account_type: str
    institution_name: Optional[str] = None
    masked_identifier: Optional[str] = None
    current_book_balance_paise: int
    current_book_balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class LiabilityAccountSummary(BaseModel):
    """Liability account debt line item."""
    id: uuid.UUID
    name: str
    account_type: str
    institution_name: Optional[str] = None
    masked_identifier: Optional[str] = None
    outstanding_liability_paise: int
    outstanding_liability: Decimal
    credit_limit_paise: Optional[int] = None
    credit_limit: Optional[Decimal] = None
    due_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NetWorthResponse(BaseModel):
    """Balance sheet summary computing total assets, liabilities, and net worth."""
    workspace_id: uuid.UUID
    currency: str
    as_of_date: str
    total_assets_paise: int
    total_assets: Decimal
    total_liabilities_paise: int
    total_liabilities: Decimal
    net_worth_paise: int
    net_worth: Decimal
    asset_accounts: List[AssetAccountSummary]
    liability_accounts: List[LiabilityAccountSummary]

    model_config = ConfigDict(from_attributes=True)


class PeriodMetrics(BaseModel):
    """Metrics snapshot for a specific evaluation period."""
    start_date: str
    end_date: str
    income_paise: int
    income: Decimal
    expenses_paise: int
    expenses: Decimal
    net_cash_flow_paise: int
    net_cash_flow: Decimal
    savings_rate_percentage: float

    model_config = ConfigDict(from_attributes=True)


class PeriodDeltas(BaseModel):
    """Comparative variations between periods."""
    income_delta_paise: int
    income_delta: Decimal
    income_percentage_delta: Optional[float] = None
    income_sentiment: str
    expenses_delta_paise: int
    expenses_delta: Decimal
    expenses_percentage_delta: Optional[float] = None
    expenses_sentiment: str
    net_cash_flow_delta_paise: int
    net_cash_flow_delta: Decimal
    net_cash_flow_percentage_delta: Optional[float] = None
    net_cash_flow_sentiment: str
    savings_rate_delta_percentage: float
    savings_rate_sentiment: str

    model_config = ConfigDict(from_attributes=True)


class PeriodComparisonResponse(BaseModel):
    """Side-by-side period performance comparison."""
    currency: str
    current_period: PeriodMetrics
    previous_period: PeriodMetrics
    deltas: PeriodDeltas

    model_config = ConfigDict(from_attributes=True)
