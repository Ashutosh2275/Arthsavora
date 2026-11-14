"""
Arthsavora Financial Forecasting Repository Layer
Data access for forecast runs, point estimates, evaluations, and hypothetical scenarios.
Strictly scoped by workspace_id to guarantee anti-IDOR multi-tenant isolation.
"""

from datetime import date
from typing import List, Optional
import uuid
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.forecast import (
    FinancialScenario,
    ForecastEvaluation,
    ForecastPoint,
    ForecastRun,
)


class ForecastRepository:
    """Repository handling persistence for forecasting runs, points, evaluations, and scenarios."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Forecast Runs
    # -------------------------------------------------------------------------

    async def create_run(self, run: ForecastRun) -> ForecastRun:
        """Persist a new forecast run."""
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def get_run(self, run_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[ForecastRun]:
        """Retrieve a specific forecast run with workspace isolation."""
        stmt = (
            select(ForecastRun)
            .where(
                ForecastRun.id == run_id,
                ForecastRun.workspace_id == workspace_id,
            )
            .options(selectinload(ForecastRun.points))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_run(
        self,
        workspace_id: uuid.UUID,
        forecast_type: Optional[str] = None,
    ) -> Optional[ForecastRun]:
        """Fetch the most recent completed forecast run for a workspace."""
        stmt = (
            select(ForecastRun)
            .where(
                ForecastRun.workspace_id == workspace_id,
                ForecastRun.status == "completed",
            )
            .options(selectinload(ForecastRun.points))
            .order_by(desc(ForecastRun.created_at))
            .limit(1)
        )
        if forecast_type:
            stmt = stmt.where(ForecastRun.forecast_type == forecast_type)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        workspace_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[ForecastRun]:
        """List historical forecast runs."""
        stmt = (
            select(ForecastRun)
            .where(ForecastRun.workspace_id == workspace_id)
            .order_by(desc(ForecastRun.created_at))
            .offset(skip)
            .limit(min(max(limit, 1), 100))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Forecast Points
    # -------------------------------------------------------------------------

    async def create_points(self, points: List[ForecastPoint]) -> List[ForecastPoint]:
        """Bulk persist forecast points."""
        self.db.add_all(points)
        await self.db.flush()
        return points

    async def get_points_by_run(
        self,
        run_id: uuid.UUID,
        workspace_id: uuid.UUID,
        metric_type: Optional[str] = None,
    ) -> List[ForecastPoint]:
        """Retrieve forecast points for a specific run and metric."""
        stmt = (
            select(ForecastPoint)
            .where(
                ForecastPoint.forecast_run_id == run_id,
                ForecastPoint.workspace_id == workspace_id,
            )
            .order_by(ForecastPoint.forecast_date.asc())
        )
        if metric_type:
            stmt = stmt.where(ForecastPoint.metric_type == metric_type)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_points_by_date_range(
        self,
        workspace_id: uuid.UUID,
        start_date: date,
        end_date: date,
        metric_type: Optional[str] = None,
    ) -> List[ForecastPoint]:
        """Query forecast points by date window."""
        stmt = (
            select(ForecastPoint)
            .where(
                ForecastPoint.workspace_id == workspace_id,
                ForecastPoint.forecast_date >= start_date,
                ForecastPoint.forecast_date <= end_date,
            )
            .order_by(ForecastPoint.forecast_date.asc())
        )
        if metric_type:
            stmt = stmt.where(ForecastPoint.metric_type == metric_type)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Financial Scenarios
    # -------------------------------------------------------------------------

    async def create_scenario(self, scenario: FinancialScenario) -> FinancialScenario:
        """Create a new hypothetical scenario."""
        self.db.add(scenario)
        await self.db.flush()
        await self.db.refresh(scenario)
        return scenario

    async def get_scenario(
        self,
        scenario_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[FinancialScenario]:
        """Fetch scenario with workspace boundary."""
        stmt = select(FinancialScenario).where(
            FinancialScenario.id == scenario_id,
            FinancialScenario.workspace_id == workspace_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_scenarios(
        self,
        workspace_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[FinancialScenario]:
        """List scenarios for a workspace."""
        stmt = (
            select(FinancialScenario)
            .where(FinancialScenario.workspace_id == workspace_id)
            .order_by(desc(FinancialScenario.created_at))
            .offset(skip)
            .limit(min(max(limit, 1), 100))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_scenario(
        self,
        scenario_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """Delete scenario with workspace isolation."""
        stmt = delete(FinancialScenario).where(
            FinancialScenario.id == scenario_id,
            FinancialScenario.workspace_id == workspace_id,
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # -------------------------------------------------------------------------
    # Forecast Evaluations
    # -------------------------------------------------------------------------

    async def record_evaluation(self, evaluation: ForecastEvaluation) -> ForecastEvaluation:
        """Save a time-series evaluation record."""
        self.db.add(evaluation)
        await self.db.flush()
        await self.db.refresh(evaluation)
        return evaluation

    async def list_evaluations(
        self,
        workspace_id: uuid.UUID,
        metric_type: Optional[str] = None,
    ) -> List[ForecastEvaluation]:
        """List model evaluations."""
        stmt = (
            select(ForecastEvaluation)
            .where(ForecastEvaluation.workspace_id == workspace_id)
            .order_by(desc(ForecastEvaluation.created_at))
        )
        if metric_type:
            stmt = stmt.where(ForecastEvaluation.metric_type == metric_type)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
