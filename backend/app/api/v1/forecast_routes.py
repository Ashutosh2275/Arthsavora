"""
Arthsavora Financial Forecasting, Cash-Flow Prediction & Scenario API Endpoints
Authenticated, workspace-scoped RESTful routes for forward-looking predictions,
budget exhaustion, savings goal pacing, model evaluations, and deterministic what-if scenarios.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.common import ApiResponse
from app.schemas.forecast_schema import (
    BudgetExhaustionResponse,
    CashFlowForecastResponse,
    CategoryForecastResponse,
    EvaluationResponse,
    ExpenseForecastResponse,
    ForecastGenerateRequest,
    GoalTrajectoryResponse,
    IncomeForecastResponse,
    ScenarioCreateRequest,
    ScenarioResponse,
)
from app.services.forecasting.budget_exhaustion_service import BudgetExhaustionService
from app.services.forecasting.forecasting_service import ForecastingService
from app.services.forecasting.goal_projection_service import GoalProjectionService
from app.services.forecasting.scenario_service import ScenarioService

router = APIRouter(tags=["Financial Forecasting, Cash-Flow Prediction & Scenarios"])


# -------------------------------------------------------------------------
# Forecasting Runs & Projections
# -------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=ApiResponse[CashFlowForecastResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Financial Forecast",
    description="Executes a new forecasting run, evaluating out-of-sample models and integrating recurring commitments.",
)
async def generate_forecast(
    request: ForecastGenerateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CashFlowForecastResponse]:
    service = ForecastingService(db)
    result = await service.generate_forecast(
        workspace_id=context.workspace_id,
        request=request,
        user_id=context.user.id,
    )
    return ApiResponse(
        data=result,
        message=f"Financial forecast for {request.horizon_days} days generated successfully.",
    )


@router.get(
    "/latest",
    response_model=ApiResponse[CashFlowForecastResponse],
    summary="Get Latest Forecast Overview",
    description="Retrieves the most recent completed cash-flow forecast, or generates one if none exists.",
)
async def get_latest_forecast(
    horizon_days: int = Query(default=30, ge=7, le=365),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CashFlowForecastResponse]:
    service = ForecastingService(db)
    result = await service.get_latest_cash_flow_forecast(
        workspace_id=context.workspace_id,
        horizon_days=horizon_days,
    )
    return ApiResponse(data=result)


@router.get(
    "/cash-flow",
    response_model=ApiResponse[CashFlowForecastResponse],
    summary="Get Cash-Flow Projections",
    description="Returns forward-looking cash flow and ending balance trajectory with confidence intervals.",
)
async def get_cash_flow_forecast(
    horizon_days: int = Query(default=30, ge=7, le=365),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CashFlowForecastResponse]:
    service = ForecastingService(db)
    result = await service.get_latest_cash_flow_forecast(
        workspace_id=context.workspace_id,
        horizon_days=horizon_days,
    )
    return ApiResponse(data=result)


@router.get(
    "/income",
    response_model=ApiResponse[IncomeForecastResponse],
    summary="Get Income Forecast",
    description="Returns expected income breakdown separating scheduled commitments from statistical estimates.",
)
async def get_income_forecast(
    horizon_days: int = Query(default=30, ge=7, le=365),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[IncomeForecastResponse]:
    service = ForecastingService(db)
    result = await service.get_income_forecast(
        workspace_id=context.workspace_id,
        horizon_days=horizon_days,
    )
    return ApiResponse(data=result)


@router.get(
    "/expenses",
    response_model=ApiResponse[ExpenseForecastResponse],
    summary="Get Expense Forecast",
    description="Returns expected expense breakdown separating scheduled commitments from discretionary spending.",
)
async def get_expense_forecast(
    horizon_days: int = Query(default=30, ge=7, le=365),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ExpenseForecastResponse]:
    service = ForecastingService(db)
    result = await service.get_expense_forecast(
        workspace_id=context.workspace_id,
        horizon_days=horizon_days,
    )
    return ApiResponse(data=result)


@router.get(
    "/categories",
    response_model=ApiResponse[CategoryForecastResponse],
    summary="Get Category Spending Forecasts",
    description="Returns forward spending estimates by category with trend directions.",
)
async def get_category_forecasts(
    horizon_days: int = Query(default=30, ge=7, le=365),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CategoryForecastResponse]:
    service = ForecastingService(db)
    result = await service.get_category_forecast(
        workspace_id=context.workspace_id,
        horizon_days=horizon_days,
    )
    return ApiResponse(data=result)


# -------------------------------------------------------------------------
# Budget Exhaustion & Goal Trajectory Integrations
# -------------------------------------------------------------------------

@router.get(
    "/budget-exhaustion",
    response_model=ApiResponse[BudgetExhaustionResponse],
    summary="Get Budget Exhaustion Estimates",
    description="Calculates current spending burn rate and projects budget exhaustion dates.",
)
async def get_budget_exhaustion(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BudgetExhaustionResponse]:
    service = BudgetExhaustionService(db)
    result = await service.get_exhaustion_estimates(
        workspace_id=context.workspace_id,
        as_of_date=date.today(),
    )
    return ApiResponse(data=result)


@router.get(
    "/goals",
    response_model=ApiResponse[GoalTrajectoryResponse],
    summary="Get Goal Completion Trajectories",
    description="Projects goal completion milestones based on current balance and monthly savings velocity.",
)
async def get_goal_trajectories(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[GoalTrajectoryResponse]:
    service = GoalProjectionService(db)
    result = await service.get_goal_trajectories(
        workspace_id=context.workspace_id,
        as_of_date=date.today(),
    )
    return ApiResponse(data=result)


# -------------------------------------------------------------------------
# Financial Scenarios Engine
# -------------------------------------------------------------------------

@router.post(
    "/scenarios",
    response_model=ApiResponse[ScenarioResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create & Evaluate Financial Scenario",
    description="Executes a deterministic what-if scenario adjusting income, expenses, and one-time items without mutating actual records.",
)
async def create_scenario(
    request: ScenarioCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ScenarioResponse]:
    service = ScenarioService(db)
    result = await service.create_scenario(
        workspace_id=context.workspace_id,
        request=request,
        user_id=context.user.id,
    )
    return ApiResponse(
        data=result,
        message=f"Financial scenario '{request.name}' evaluated successfully.",
    )


@router.get(
    "/scenarios",
    response_model=ApiResponse[List[ScenarioResponse]],
    summary="List Financial Scenarios",
    description="Lists all saved what-if financial scenarios for the workspace.",
)
async def list_scenarios(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[ScenarioResponse]]:
    service = ScenarioService(db)
    results = await service.list_scenarios(
        workspace_id=context.workspace_id,
        skip=skip,
        limit=limit,
    )
    return ApiResponse(data=results)


@router.get(
    "/scenarios/{scenario_id}",
    response_model=ApiResponse[ScenarioResponse],
    summary="Get Financial Scenario Details",
    description="Retrieves assumptions and simulated timeline results for a specific scenario.",
)
async def get_scenario(
    scenario_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ScenarioResponse]:
    service = ScenarioService(db)
    result = await service.get_scenario(
        scenario_id=scenario_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=result)


@router.delete(
    "/scenarios/{scenario_id}",
    response_model=ApiResponse[bool],
    summary="Delete Financial Scenario",
    description="Deletes a hypothetical scenario from the workspace.",
)
async def delete_scenario(
    scenario_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[bool]:
    service = ScenarioService(db)
    await service.delete_scenario(
        scenario_id=scenario_id,
        workspace_id=context.workspace_id,
    )
    return ApiResponse(data=True, message="Scenario deleted successfully.")


# -------------------------------------------------------------------------
# Forecast Evaluations
# -------------------------------------------------------------------------

@router.get(
    "/evaluations",
    response_model=ApiResponse[List[EvaluationResponse]],
    summary="List Forecast Model Evaluations",
    description="Returns time-series empirical accuracy metrics (MAE, RMSE, WAPE, Bias, Interval Coverage).",
)
async def list_evaluations(
    metric_type: Optional[str] = Query(default=None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FORECASTS)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[EvaluationResponse]]:
    from app.repositories.forecast_repository import ForecastRepository
    repo = ForecastRepository(db)
    evals = await repo.list_evaluations(
        workspace_id=context.workspace_id,
        metric_type=metric_type,
    )
    results = []
    for e in evals:
        results.append(
            EvaluationResponse(
                id=e.id,
                workspace_id=e.workspace_id,
                model_name=e.model_name,
                metric_type=e.metric_type,
                horizon_days=e.horizon_days,
                mae_paise=e.mae_paise,
                mae=Decimal(e.mae_paise) / Decimal("100.0000"),
                rmse_paise=e.rmse_paise,
                rmse=Decimal(e.rmse_paise) / Decimal("100.0000"),
                wape=float(e.wape),
                bias_paise=e.bias_paise,
                bias=Decimal(e.bias_paise) / Decimal("100.0000"),
                interval_coverage=float(e.interval_coverage) if e.interval_coverage is not None else None,
                sample_size=e.sample_size,
                is_best_model=e.is_best_model,
                created_at=e.created_at,
            )
        )
    return ApiResponse(data=results)
