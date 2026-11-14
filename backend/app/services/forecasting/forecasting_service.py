"""
Arthsavora Forecasting Engine Application Service
Orchestrates model selection, time-series projections, recurring commitments integration,
uncertainty interval calculation, and forecast persistence.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.forecasting import (
    ForecastPointVO,
    calculate_cash_flow_projection,
    forecast_exponential_smoothing,
    forecast_historical_mean,
    forecast_holt_winters,
    forecast_linear_trend,
    forecast_moving_average,
    select_best_model,
)
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.forecast import (
    ForecastEvaluation,
    ForecastPoint,
    ForecastRun,
)
from app.repositories.category_repository import CategoryRepository
from app.repositories.forecast_repository import ForecastRepository
from app.repositories.recurring_repository import RecurringRepository
from app.schemas.forecast_schema import (
    CashFlowForecastResponse,
    CategoryForecastItem,
    CategoryForecastResponse,
    ExpenseForecastResponse,
    ForecastGenerateRequest,
    ForecastPointResponse,
    IncomeForecastResponse,
)
from app.services.forecasting.data_prep_service import DataPreparationService


class ForecastingService:
    """Core application service managing the financial forecasting lifecycle."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ForecastRepository(db)
        self.data_prep = DataPreparationService(db)
        self.recurring_repo = RecurringRepository(db)
        self.category_repo = CategoryRepository(db)

    async def generate_forecast(
        self,
        workspace_id: uuid.UUID,
        request: ForecastGenerateRequest,
        user_id: Optional[uuid.UUID] = None,
    ) -> CashFlowForecastResponse:
        """
        Executes a complete financial forecast run:
        1. Prepares historical data and checks eligibility.
        2. Selects best model or uses requested preferred model.
        3. Projects income, expense, and category expenditure.
        4. Integrates Prompt 15 recurring occurrences without double-counting.
        5. Computes ending balance trajectory with lower/upper confidence bounds.
        6. Persists forecast run, points, and evaluations.
        """
        horizon = request.horizon_days
        conf_level = request.confidence_level

        # 1. Starting cash balance and historical time-series
        start_balance_paise = await self.data_prep.get_starting_balance(workspace_id)
        inflow_series, outflow_series, hist_start, hist_end = await self.data_prep.extract_daily_series(
            workspace_id=workspace_id,
            lookback_days=max(90, horizon * 2),
        )

        # 2. Model selection for Outflows (expenses)
        if request.preferred_model:
            outflow_model = request.preferred_model
            from app.domain.forecasting import evaluate_time_series_walk_forward
            eval_metrics = evaluate_time_series_walk_forward(outflow_series, model_name=outflow_model)
        else:
            outflow_model, eval_metrics = select_best_model(outflow_series)

        # Record evaluation
        eval_record = ForecastEvaluation(
            workspace_id=workspace_id,
            model_name=outflow_model,
            metric_type="expense",
            horizon_days=horizon,
            mae_paise=eval_metrics.mae_paise,
            rmse_paise=eval_metrics.rmse_paise,
            wape=Decimal(str(eval_metrics.wape)),
            bias_paise=eval_metrics.bias_paise,
            interval_coverage=Decimal(str(eval_metrics.interval_coverage)) if eval_metrics.interval_coverage else None,
            sample_size=eval_metrics.sample_size,
            evaluation_period_start=hist_start,
            evaluation_period_end=hist_end,
            is_best_model=True,
            metadata_={"confidence_level": conf_level},
        )
        await self.repo.record_evaluation(eval_record)

        # 3. Model execution
        model_dispatch = {
            "holt_winters": forecast_holt_winters,
            "moving_average": forecast_moving_average,
            "exponential_smoothing": forecast_exponential_smoothing,
            "linear_trend": forecast_linear_trend,
            "historical_mean": forecast_historical_mean,
        }
        predictor = model_dispatch.get(outflow_model, forecast_moving_average)

        outflow_points = predictor(outflow_series, steps=horizon, confidence_level=conf_level)
        inflow_points = forecast_historical_mean(inflow_series, steps=horizon, confidence_level=conf_level)

        # 4. Recurring commitments integration (Prompt 15)
        recurring_occurrences = []
        if request.include_recurring:
            as_of = date.today()
            window_end = as_of + timedelta(days=horizon)
            recurring_occurrences = await self.recurring_repo.list_occurrences(
                workspace_id=workspace_id,
                start_date=as_of,
                end_date=window_end,
                limit=300,
            )

        # 5. Daily cash-flow & balance projection
        timeline = calculate_cash_flow_projection(
            starting_balance_paise=start_balance_paise,
            inflow_points=inflow_points,
            outflow_points=outflow_points,
            recurring_occurrences=recurring_occurrences,
        )

        tot_in_paise = sum(pt["inflow_paise"] for pt in timeline)
        tot_out_paise = sum(pt["outflow_paise"] for pt in timeline)
        net_cash_flow_paise = tot_in_paise - tot_out_paise
        ending_balance_paise = timeline[-1]["projected_balance_paise"] if timeline else start_balance_paise

        # 6. Persist Forecast Run
        forecast_run = ForecastRun(
            workspace_id=workspace_id,
            forecast_type="comprehensive",
            horizon_days=horizon,
            resolution=request.resolution,
            currency="INR",
            starting_balance_paise=start_balance_paise,
            starting_balance=Decimal(start_balance_paise) / Decimal("100.0000"),
            historical_start_date=hist_start,
            historical_end_date=hist_end,
            model_name=outflow_model,
            model_version="v1.0.0",
            data_quality_score=Decimal("1.0000"),
            status="completed",
            created_by_id=user_id,
            metadata_={
                "wape": float(eval_metrics.wape),
                "mae_paise": eval_metrics.mae_paise,
                "confidence_level": conf_level,
                "recurring_count": len(recurring_occurrences),
            },
        )
        saved_run = await self.repo.create_run(forecast_run)

        # 7. Bulk Persist Forecast Points
        db_points: List[ForecastPoint] = []
        for pt in timeline:
            dt = pt["date"]
            # Inflow point
            db_points.append(
                ForecastPoint(
                    forecast_run_id=saved_run.id,
                    workspace_id=workspace_id,
                    forecast_date=dt,
                    metric_type="income",
                    point_estimate_paise=pt["inflow_paise"],
                    point_estimate=Decimal(pt["inflow_paise"]) / Decimal("100.0000"),
                    lower_estimate_paise=pt["inflow_paise"],
                    lower_estimate=Decimal(pt["inflow_paise"]) / Decimal("100.0000"),
                    upper_estimate_paise=pt["inflow_paise"],
                    upper_estimate=Decimal(pt["inflow_paise"]) / Decimal("100.0000"),
                    confidence_level=Decimal(str(conf_level)),
                    is_recurring_commitment=(pt["inflow_recurring_paise"] > 0),
                    breakdown_metadata={"recurring_paise": pt["inflow_recurring_paise"]},
                )
            )
            # Outflow point
            db_points.append(
                ForecastPoint(
                    forecast_run_id=saved_run.id,
                    workspace_id=workspace_id,
                    forecast_date=dt,
                    metric_type="expense",
                    point_estimate_paise=pt["outflow_paise"],
                    point_estimate=Decimal(pt["outflow_paise"]) / Decimal("100.0000"),
                    lower_estimate_paise=pt["outflow_paise"],
                    lower_estimate=Decimal(pt["outflow_paise"]) / Decimal("100.0000"),
                    upper_estimate_paise=pt["outflow_paise"],
                    upper_estimate=Decimal(pt["outflow_paise"]) / Decimal("100.0000"),
                    confidence_level=Decimal(str(conf_level)),
                    is_recurring_commitment=(pt["outflow_recurring_paise"] > 0),
                    breakdown_metadata={"recurring_paise": pt["outflow_recurring_paise"]},
                )
            )
            # Balance point
            db_points.append(
                ForecastPoint(
                    forecast_run_id=saved_run.id,
                    workspace_id=workspace_id,
                    forecast_date=dt,
                    metric_type="projected_balance",
                    point_estimate_paise=pt["projected_balance_paise"],
                    point_estimate=Decimal(pt["projected_balance_paise"]) / Decimal("100.0000"),
                    lower_estimate_paise=pt["lower_balance_paise"],
                    lower_estimate=Decimal(pt["lower_balance_paise"]) / Decimal("100.0000"),
                    upper_estimate_paise=pt["upper_balance_paise"],
                    upper_estimate=Decimal(pt["upper_balance_paise"]) / Decimal("100.0000"),
                    confidence_level=Decimal(str(conf_level)),
                    is_recurring_commitment=False,
                    breakdown_metadata={},
                )
            )

        await self.repo.create_points(db_points)

        return CashFlowForecastResponse(
            workspace_id=workspace_id,
            forecast_run_id=saved_run.id,
            horizon_days=horizon,
            resolution=request.resolution,
            currency="INR",
            starting_balance_paise=start_balance_paise,
            starting_balance=Decimal(start_balance_paise) / Decimal("100.0000"),
            projected_ending_balance_paise=ending_balance_paise,
            projected_ending_balance=Decimal(ending_balance_paise) / Decimal("100.0000"),
            total_projected_inflow_paise=tot_in_paise,
            total_projected_inflow=Decimal(tot_in_paise) / Decimal("100.0000"),
            total_projected_outflow_paise=tot_out_paise,
            total_projected_outflow=Decimal(tot_out_paise) / Decimal("100.0000"),
            net_cash_flow_paise=net_cash_flow_paise,
            net_cash_flow=Decimal(net_cash_flow_paise) / Decimal("100.0000"),
            model_name=outflow_model,
            model_version="v1.0.0",
            data_quality_score=1.0,
            status="completed",
            timeline=timeline,
            created_at=saved_run.created_at,
        )

    async def get_latest_cash_flow_forecast(
        self,
        workspace_id: uuid.UUID,
        horizon_days: int = 30,
    ) -> CashFlowForecastResponse:
        """Retrieves or automatically generates the latest cash-flow forecast."""
        latest_run = await self.repo.get_latest_run(workspace_id=workspace_id)
        if not latest_run:
            return await self.generate_forecast(
                workspace_id=workspace_id,
                request=ForecastGenerateRequest(horizon_days=horizon_days),
            )

        points = await self.repo.get_points_by_run(run_id=latest_run.id, workspace_id=workspace_id)
        balance_pts = [p for p in points if p.metric_type == "projected_balance"]
        in_pts = [p for p in points if p.metric_type == "income"]
        out_pts = [p for p in points if p.metric_type == "expense"]

        tot_in = sum(p.point_estimate_paise for p in in_pts)
        tot_out = sum(p.point_estimate_paise for p in out_pts)
        net_flow = tot_in - tot_out
        end_bal = balance_pts[-1].point_estimate_paise if balance_pts else latest_run.starting_balance_paise

        timeline = []
        for b, i, o in zip(balance_pts, in_pts, out_pts):
            timeline.append({
                "date": b.forecast_date,
                "starting_balance_paise": b.point_estimate_paise - (i.point_estimate_paise - o.point_estimate_paise),
                "inflow_paise": i.point_estimate_paise,
                "inflow_recurring_paise": i.breakdown_metadata.get("recurring_paise", 0),
                "outflow_paise": o.point_estimate_paise,
                "outflow_recurring_paise": o.breakdown_metadata.get("recurring_paise", 0),
                "net_cash_flow_paise": i.point_estimate_paise - o.point_estimate_paise,
                "projected_balance_paise": b.point_estimate_paise,
                "lower_balance_paise": b.lower_estimate_paise,
                "upper_balance_paise": b.upper_estimate_paise,
            })

        return CashFlowForecastResponse(
            workspace_id=workspace_id,
            forecast_run_id=latest_run.id,
            horizon_days=latest_run.horizon_days,
            resolution=latest_run.resolution,
            currency=latest_run.currency,
            starting_balance_paise=latest_run.starting_balance_paise,
            starting_balance=latest_run.starting_balance,
            projected_ending_balance_paise=end_bal,
            projected_ending_balance=Decimal(end_bal) / Decimal("100.0000"),
            total_projected_inflow_paise=tot_in,
            total_projected_inflow=Decimal(tot_in) / Decimal("100.0000"),
            total_projected_outflow_paise=tot_out,
            total_projected_outflow=Decimal(tot_out) / Decimal("100.0000"),
            net_cash_flow_paise=net_flow,
            net_cash_flow=Decimal(net_flow) / Decimal("100.0000"),
            model_name=latest_run.model_name,
            model_version=latest_run.model_version,
            data_quality_score=float(latest_run.data_quality_score),
            status=latest_run.status,
            timeline=timeline,
            created_at=latest_run.created_at,
        )

    async def get_income_forecast(
        self,
        workspace_id: uuid.UUID,
        horizon_days: int = 30,
    ) -> IncomeForecastResponse:
        """Retrieves forward income estimates separating scheduled income from discretionary."""
        latest_run = await self.repo.get_latest_run(workspace_id=workspace_id)
        if not latest_run:
            cf = await self.generate_forecast(workspace_id=workspace_id, request=ForecastGenerateRequest(horizon_days=horizon_days))
            run_id = cf.forecast_run_id
        else:
            run_id = latest_run.id

        pts = await self.repo.get_points_by_run(run_id=run_id, workspace_id=workspace_id, metric_type="income")
        total_income = sum(p.point_estimate_paise for p in pts)
        scheduled = sum(p.breakdown_metadata.get("recurring_paise", 0) for p in pts)
        discretionary = max(0, total_income - scheduled)

        return IncomeForecastResponse(
            workspace_id=workspace_id,
            forecast_run_id=run_id,
            horizon_days=horizon_days,
            total_expected_income_paise=total_income,
            total_expected_income=Decimal(total_income) / Decimal("100.0000"),
            scheduled_income_paise=scheduled,
            scheduled_income=Decimal(scheduled) / Decimal("100.0000"),
            estimated_discretionary_income_paise=discretionary,
            estimated_discretionary_income=Decimal(discretionary) / Decimal("100.0000"),
            model_used=latest_run.model_name if latest_run else "moving_average",
            points=[ForecastPointResponse.model_validate(p) for p in pts],
        )

    async def get_expense_forecast(
        self,
        workspace_id: uuid.UUID,
        horizon_days: int = 30,
    ) -> ExpenseForecastResponse:
        """Retrieves forward expense estimates separating scheduled commitments from discretionary."""
        latest_run = await self.repo.get_latest_run(workspace_id=workspace_id)
        if not latest_run:
            cf = await self.generate_forecast(workspace_id=workspace_id, request=ForecastGenerateRequest(horizon_days=horizon_days))
            run_id = cf.forecast_run_id
        else:
            run_id = latest_run.id

        pts = await self.repo.get_points_by_run(run_id=run_id, workspace_id=workspace_id, metric_type="expense")
        total_expense = sum(p.point_estimate_paise for p in pts)
        scheduled = sum(p.breakdown_metadata.get("recurring_paise", 0) for p in pts)
        discretionary = max(0, total_expense - scheduled)

        return ExpenseForecastResponse(
            workspace_id=workspace_id,
            forecast_run_id=run_id,
            horizon_days=horizon_days,
            total_expected_expense_paise=total_expense,
            total_expected_expense=Decimal(total_expense) / Decimal("100.0000"),
            scheduled_commitments_paise=scheduled,
            scheduled_commitments=Decimal(scheduled) / Decimal("100.0000"),
            discretionary_expense_paise=discretionary,
            discretionary_expense=Decimal(discretionary) / Decimal("100.0000"),
            model_used=latest_run.model_name if latest_run else "moving_average",
            points=[ForecastPointResponse.model_validate(p) for p in pts],
        )

    async def get_category_forecast(
        self,
        workspace_id: uuid.UUID,
        horizon_days: int = 30,
    ) -> CategoryForecastResponse:
        """Computes future category-level expenditures using historical series trends."""
        latest_run = await self.repo.get_latest_run(workspace_id=workspace_id)
        if not latest_run:
            cf = await self.generate_forecast(workspace_id=workspace_id, request=ForecastGenerateRequest(horizon_days=horizon_days))
            run_id = cf.forecast_run_id
        else:
            run_id = latest_run.id

        cat_series = await self.data_prep.extract_category_spending(workspace_id=workspace_id, lookback_days=90)
        categories = await self.category_repo.list_categories(workspace_id=workspace_id)
        cat_name_map = {c.id: c.name for c in categories}

        items: List[CategoryForecastItem] = []
        for cat_id, series in cat_series.items():
            if not series:
                continue
            cat_name = cat_name_map.get(cat_id, "Uncategorized")
            pts = forecast_moving_average(series, steps=horizon_days, window=14)
            tot_proj = sum(p.point_estimate_paise for p in pts)
            tot_lower = sum(p.lower_estimate_paise for p in pts)
            tot_upper = sum(p.upper_estimate_paise for p in pts)

            hist_tot = sum(p.amount_paise for p in series)
            monthly_avg = int(round(hist_tot / 3.0))

            trend = "stable"
            if tot_proj > monthly_avg * 1.10:
                trend = "increasing"
            elif tot_proj < monthly_avg * 0.90:
                trend = "decreasing"

            items.append(
                CategoryForecastItem(
                    category_id=cat_id,
                    category_name=cat_name,
                    projected_amount_paise=tot_proj,
                    projected_amount=Decimal(tot_proj) / Decimal("100.0000"),
                    lower_amount_paise=tot_lower,
                    lower_amount=Decimal(tot_lower) / Decimal("100.0000"),
                    upper_amount_paise=tot_upper,
                    upper_amount=Decimal(tot_upper) / Decimal("100.0000"),
                    historical_monthly_average_paise=monthly_avg,
                    historical_monthly_average=Decimal(monthly_avg) / Decimal("100.0000"),
                    trend_direction=trend,
                )
            )

        items.sort(key=lambda x: x.projected_amount_paise, reverse=True)

        return CategoryForecastResponse(
            workspace_id=workspace_id,
            forecast_run_id=run_id,
            horizon_days=horizon_days,
            categories=items,
        )
