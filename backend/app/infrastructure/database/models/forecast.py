"""
Arthsavora Financial Forecasting, Cash-Flow Prediction & Scenario Models
PostgreSQL source of truth for forecast runs, point estimates, interval bounds,
evaluations, and deterministic financial what-if scenarios.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.workspace import Workspace
    from app.infrastructure.database.models.category import Category
    from app.infrastructure.database.models.user import User


class ForecastRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Metadata and summary of an executed financial forecasting job for a workspace.
    Distinguishes historical facts from model predictions and assumptions.
    """
    __tablename__ = "forecast_runs"
    __table_args__ = (
        Index("ix_forecast_runs_ws_status", "workspace_id", "status"),
        Index("ix_forecast_runs_ws_created", "workspace_id", "created_at"),
        Index("ix_forecast_runs_ws_type", "workspace_id", "forecast_type"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forecast_type: Mapped[str] = mapped_column(String(50), default="comprehensive", nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    starting_balance_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    starting_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    historical_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    historical_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    model_name: Mapped[str] = mapped_column(String(50), default="ensemble_baseline", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0.0", nullable=False)
    data_quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.0000"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)  # completed, in_progress, failed, stale

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    created_by: Mapped[Optional["User"]] = relationship("User")
    points: Mapped[List["ForecastPoint"]] = relationship(
        "ForecastPoint",
        back_populates="forecast_run",
        cascade="all, delete-orphan",
        order_by="ForecastPoint.forecast_date.asc()",
    )

    def __repr__(self) -> str:
        return f"<ForecastRun id={self.id} type={self.forecast_type} horizon={self.horizon_days}d status={self.status}>"


class ForecastPoint(Base, UUIDPrimaryKeyMixin):
    """
    Individual projected time-series point with uncertainty bounds.
    Stores values in 64-bit integer minor currency units (paise) and fixed-point Numeric(18, 4).
    """
    __tablename__ = "forecast_points"
    __table_args__ = (
        Index("ix_forecast_points_run_metric", "forecast_run_id", "metric_type"),
        Index("ix_forecast_points_ws_date", "workspace_id", "forecast_date"),
        Index("ix_forecast_points_ws_metric_date", "workspace_id", "metric_type", "forecast_date"),
    )

    forecast_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # income, expense, net_cash_flow, projected_balance, category_expense

    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    point_estimate_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    point_estimate: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    lower_estimate_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lower_estimate: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    upper_estimate_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    upper_estimate: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    confidence_level: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.8000"), nullable=False)
    is_recurring_commitment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    breakdown_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    forecast_run: Mapped["ForecastRun"] = relationship("ForecastRun", back_populates="points")
    category: Mapped[Optional["Category"]] = relationship("Category")

    def __repr__(self) -> str:
        return f"<ForecastPoint date={self.forecast_date} metric={self.metric_type} est={self.point_estimate}>"


class FinancialScenario(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User-defined deterministic what-if scenario.
    Enables exploring income changes, expense adjustments, and goal shifts without mutating actual data.
    """
    __tablename__ = "financial_scenarios"
    __table_args__ = (
        Index("ix_financial_scenarios_ws_type", "workspace_id", "scenario_type"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scenario_type: Mapped[str] = mapped_column(String(50), default="custom", nullable=False)  # baseline, optimistic, conservative, custom
    horizon_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    base_forecast_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("forecast_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    assumptions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    results: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    created_by: Mapped[Optional["User"]] = relationship("User")
    base_forecast_run: Mapped[Optional["ForecastRun"]] = relationship("ForecastRun")

    def __repr__(self) -> str:
        return f"<FinancialScenario id={self.id} name='{self.name}' type={self.scenario_type}>"


class ForecastEvaluation(Base, UUIDPrimaryKeyMixin):
    """
    Empirical accuracy metrics derived from time-series rolling-origin walk-forward evaluation.
    Used for objective model selection and out-of-sample performance validation.
    """
    __tablename__ = "forecast_evaluations"
    __table_args__ = (
        Index("ix_forecast_eval_ws_metric", "workspace_id", "metric_type"),
        Index("ix_forecast_eval_ws_model", "workspace_id", "model_name"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # income, expense, net_cash_flow, category_expense
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)

    mae_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rmse_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wape: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    bias_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    interval_coverage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)

    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evaluation_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    evaluation_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    is_best_model: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")

    def __repr__(self) -> str:
        return f"<ForecastEvaluation model={self.model_name} metric={self.metric_type} wape={self.wape}>"
