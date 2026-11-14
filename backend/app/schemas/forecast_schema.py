"""
Arthsavora Financial Forecasting Pydantic Request & Response Schemas
Exact minor currency unit (paise) and major Decimal(18, 4) representations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ForecastGenerateRequest(BaseModel):
    """Request payload to trigger a financial forecasting run."""
    horizon_days: int = Field(default=30, ge=7, le=365, description="Forecast window (7, 30, 90, 180, 365 days)")
    resolution: str = Field(default="daily", description="Aggregation resolution: daily, weekly, or monthly")
    preferred_model: Optional[str] = Field(default=None, description="Optional forced model identifier or None for auto-selection")
    include_recurring: bool = Field(default=True, description="Whether to include confirmed recurring commitments from Prompt 15")
    confidence_level: float = Field(default=0.80, ge=0.50, le=0.99, description="Confidence interval width (default 80%)")


class ForecastPointResponse(BaseModel):
    """Projected time-series point."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = None
    forecast_date: date
    metric_type: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    point_estimate_paise: int
    point_estimate: Decimal
    lower_estimate_paise: int
    lower_estimate: Decimal
    upper_estimate_paise: int
    upper_estimate: Decimal
    confidence_level: float
    is_recurring_commitment: bool = False
    breakdown_metadata: Dict[str, Any] = Field(default_factory=dict)


class CashFlowForecastResponse(BaseModel):
    """Complete cash-flow forward projection."""
    workspace_id: uuid.UUID
    forecast_run_id: uuid.UUID
    horizon_days: int
    resolution: str
    currency: str
    starting_balance_paise: int
    starting_balance: Decimal
    projected_ending_balance_paise: int
    projected_ending_balance: Decimal
    total_projected_inflow_paise: int
    total_projected_inflow: Decimal
    total_projected_outflow_paise: int
    total_projected_outflow: Decimal
    net_cash_flow_paise: int
    net_cash_flow: Decimal
    model_name: str
    model_version: str
    data_quality_score: float
    status: str
    timeline: List[Dict[str, Any]]
    created_at: datetime


class IncomeForecastResponse(BaseModel):
    """Income projection breakdown."""
    workspace_id: uuid.UUID
    forecast_run_id: uuid.UUID
    horizon_days: int
    total_expected_income_paise: int
    total_expected_income: Decimal
    scheduled_income_paise: int
    scheduled_income: Decimal
    estimated_discretionary_income_paise: int
    estimated_discretionary_income: Decimal
    model_used: str
    points: List[ForecastPointResponse]


class ExpenseForecastResponse(BaseModel):
    """Expense projection breakdown."""
    workspace_id: uuid.UUID
    forecast_run_id: uuid.UUID
    horizon_days: int
    total_expected_expense_paise: int
    total_expected_expense: Decimal
    scheduled_commitments_paise: int
    scheduled_commitments: Decimal
    discretionary_expense_paise: int
    discretionary_expense: Decimal
    model_used: str
    points: List[ForecastPointResponse]


class CategoryForecastItem(BaseModel):
    """Category-wise forward expenditure."""
    category_id: Optional[uuid.UUID] = None
    category_name: str
    projected_amount_paise: int
    projected_amount: Decimal
    lower_amount_paise: int
    lower_amount: Decimal
    upper_amount_paise: int
    upper_amount: Decimal
    historical_monthly_average_paise: int
    historical_monthly_average: Decimal
    trend_direction: str


class CategoryForecastResponse(BaseModel):
    """Category spending projections."""
    workspace_id: uuid.UUID
    forecast_run_id: uuid.UUID
    horizon_days: int
    categories: List[CategoryForecastItem]


class BudgetExhaustionResponse(BaseModel):
    """Budget exhaustion estimates."""
    workspace_id: uuid.UUID
    as_of_date: date
    estimates: List[Dict[str, Any]]


class GoalTrajectoryResponse(BaseModel):
    """Savings goal trajectory estimates."""
    workspace_id: uuid.UUID
    as_of_date: date
    goals: List[Dict[str, Any]]


class ScenarioCreateRequest(BaseModel):
    """Payload to build a deterministic what-if scenario."""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    scenario_type: str = Field(default="custom", description="baseline, optimistic, conservative, custom")
    horizon_days: int = Field(default=30, ge=7, le=365)
    income_change_pct: float = Field(default=0.0, description="Percentage change to regular income (e.g. +10.0 or -5.0)")
    expense_change_pct: float = Field(default=0.0, description="Percentage change to discretionary expenses (e.g. -15.0)")
    one_time_inflows: List[Dict[str, Any]] = Field(default_factory=list, description="List of {date: YYYY-MM-DD, amount_paise: int, description: str}")
    one_time_outflows: List[Dict[str, Any]] = Field(default_factory=list, description="List of {date: YYYY-MM-DD, amount_paise: int, description: str}")
    monthly_savings_change_paise: int = Field(default=0)


class ScenarioResponse(BaseModel):
    """Deterministic scenario calculation result."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    scenario_type: str
    horizon_days: int
    assumptions: Dict[str, Any]
    results: Dict[str, Any]
    created_at: datetime


class EvaluationResponse(BaseModel):
    """Empirical time-series model evaluation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    model_name: str
    metric_type: str
    horizon_days: int
    mae_paise: int
    mae: Decimal
    rmse_paise: int
    rmse: Decimal
    wape: float
    bias_paise: int
    bias: Decimal
    interval_coverage: Optional[float] = None
    sample_size: int
    is_best_model: bool
    created_at: datetime
