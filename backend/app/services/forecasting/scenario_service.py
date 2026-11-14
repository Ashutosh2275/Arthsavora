"""
Arthsavora Financial Scenario Application Service
Orchestrates deterministic what-if financial simulations, isolated from real accounting ledgers.
"""

from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.domain.forecasting import evaluate_scenario
from app.infrastructure.database.models.forecast import FinancialScenario
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast_schema import ScenarioCreateRequest, ScenarioResponse
from app.services.forecasting.forecasting_service import ForecastingService


class ScenarioService:
    """Manages creation, execution, and lifecycle of what-if financial scenarios."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ForecastRepository(db)
        self.forecasting = ForecastingService(db)

    async def create_scenario(
        self,
        workspace_id: uuid.UUID,
        request: ScenarioCreateRequest,
        user_id: Optional[uuid.UUID] = None,
    ) -> ScenarioResponse:
        """
        Executes a deterministic what-if simulation:
        1. Retrieves baseline cash-flow timeline.
        2. Applies hypothetical percentage and one-time adjustments.
        3. Persists scenario definition and computed results.
        """
        cf_response = await self.forecasting.get_latest_cash_flow_forecast(
            workspace_id=workspace_id,
            horizon_days=request.horizon_days,
        )

        assumptions = {
            "income_change_pct": request.income_change_pct,
            "expense_change_pct": request.expense_change_pct,
            "one_time_inflows": request.one_time_inflows,
            "one_time_outflows": request.one_time_outflows,
            "monthly_savings_change_paise": request.monthly_savings_change_paise,
        }

        scenario_res = evaluate_scenario(
            base_cash_flow_timeline=cf_response.timeline,
            assumptions=assumptions,
            scenario_type=request.scenario_type,
        )

        scenario = FinancialScenario(
            workspace_id=workspace_id,
            name=request.name,
            description=request.description,
            scenario_type=request.scenario_type,
            horizon_days=request.horizon_days,
            base_forecast_run_id=cf_response.forecast_run_id,
            assumptions=assumptions,
            results={
                "baseline_projected_balance_paise": scenario_res.baseline_projected_balance_paise,
                "scenario_projected_balance_paise": scenario_res.scenario_projected_balance_paise,
                "delta_balance_paise": scenario_res.delta_balance_paise,
                "baseline_net_cash_flow_paise": scenario_res.baseline_net_cash_flow_paise,
                "scenario_net_cash_flow_paise": scenario_res.scenario_net_cash_flow_paise,
                "timeline": [
                    {
                        "date": str(pt["date"]),
                        "scenario_inflow_paise": pt["scenario_inflow_paise"],
                        "scenario_outflow_paise": pt["scenario_outflow_paise"],
                        "scenario_net_cash_flow_paise": pt["scenario_net_cash_flow_paise"],
                        "scenario_projected_balance_paise": pt["scenario_projected_balance_paise"],
                        "baseline_projected_balance_paise": pt["baseline_projected_balance_paise"],
                        "delta_paise": pt["delta_paise"],
                    }
                    for pt in scenario_res.projected_timeline
                ],
            },
            created_by_id=user_id,
        )

        saved = await self.repo.create_scenario(scenario)
        return ScenarioResponse.model_validate(saved)

    async def get_scenario(
        self,
        scenario_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> ScenarioResponse:
        """Fetch scenario with workspace isolation."""
        s = await self.repo.get_scenario(scenario_id=scenario_id, workspace_id=workspace_id)
        if not s:
            raise NotFoundException("Financial scenario not found.")
        return ScenarioResponse.model_validate(s)

    async def list_scenarios(
        self,
        workspace_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[ScenarioResponse]:
        """List scenarios for workspace."""
        scenarios = await self.repo.list_scenarios(workspace_id=workspace_id, skip=skip, limit=limit)
        return [ScenarioResponse.model_validate(s) for s in scenarios]

    async def delete_scenario(
        self,
        scenario_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """Delete scenario with workspace isolation."""
        deleted = await self.repo.delete_scenario(scenario_id=scenario_id, workspace_id=workspace_id)
        if not deleted:
            raise NotFoundException("Financial scenario not found.")
        return True
