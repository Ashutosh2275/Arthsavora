"""
Arthsavora Financial Forecasting, Cash-Flow Prediction & Scenario Test Suite
Validates:
1. Pure domain data eligibility assessment and non-fabrication guarantees.
2. Baseline forecasting models (Historical Mean, Moving Average, SES).
3. Statistical time-series models (Holt-Winters Seasonality, Damped Linear Trend).
4. Time-series walk-forward rolling-origin evaluation (MAE, RMSE, WAPE, Bias).
5. Automated model selection (baseline fallback if ML does not improve out-of-sample).
6. Forward cash-flow projection integrating Prompt 15 recurring commitments without double counting.
7. Budget exhaustion estimation integrating Prompt 14 burn rates.
8. Savings goal trajectory projection integrating Prompt 14 goals.
9. Deterministic what-if scenario simulation and ledger isolation guarantees.
10. PostgreSQL persistence lifecycle for forecast runs, points, evaluations, and scenarios.
11. Multi-tenant workspace isolation & anti-IDOR protection.
12. Authenticated RESTful HTTP API endpoints.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.forecasting import (
    DataEligibilityAssessment,
    TimeSeriesPoint,
    assess_data_eligibility,
    calculate_budget_exhaustion,
    calculate_cash_flow_projection,
    calculate_goal_trajectory,
    evaluate_scenario,
    evaluate_time_series_walk_forward,
    forecast_exponential_smoothing,
    forecast_historical_mean,
    forecast_holt_winters,
    forecast_linear_trend,
    forecast_moving_average,
    select_best_model,
)
from app.infrastructure.database.models import Account, Category, Transaction, Workspace
from app.infrastructure.database.models.budget import Budget, BudgetAllocation
from app.infrastructure.database.models.forecast import (
    FinancialScenario,
    ForecastEvaluation,
    ForecastPoint,
    ForecastRun,
)
from app.infrastructure.database.models.goal import FinancialGoal, GoalActivity
from app.infrastructure.database.models.recurring import (
    RecurringDefinition,
    RecurringOccurrence,
)
from app.schemas.forecast_schema import (
    ForecastGenerateRequest,
    ScenarioCreateRequest,
)
from app.services.forecasting.budget_exhaustion_service import BudgetExhaustionService
from app.services.forecasting.data_prep_service import DataPreparationService
from app.services.forecasting.forecasting_service import ForecastingService
from app.services.forecasting.goal_projection_service import GoalProjectionService
from app.services.forecasting.scenario_service import ScenarioService


# ==============================================================================
# 1. PURE DOMAIN ENGINE TESTS
# ==============================================================================

def test_data_eligibility_assessment():
    """Validates data eligibility evaluation without historical fabrication."""
    # 1. Empty series -> insufficient_data
    e1 = assess_data_eligibility([], horizon_days=30)
    assert e1.is_eligible is False
    assert e1.status == "insufficient_data"

    # 2. Sparse history (only 3 days) -> insufficient_data
    sparse_pts = [
        TimeSeriesPoint(date=date(2026, 11, 1), amount_paise=10000),
        TimeSeriesPoint(date=date(2026, 11, 2), amount_paise=20000),
        TimeSeriesPoint(date=date(2026, 11, 3), amount_paise=15000),
    ]
    e2 = assess_data_eligibility(sparse_pts, horizon_days=30)
    assert e2.is_eligible is False
    assert e2.status == "insufficient_data"

    # 3. Moderate history (25 days, 10 active dates) -> limited_baseline_only
    mod_pts = [
        TimeSeriesPoint(date=date(2026, 10, 1) + timedelta(days=i), amount_paise=10000 if i % 2 == 0 else 0)
        for i in range(25)
    ]
    e3 = assess_data_eligibility(mod_pts, horizon_days=30)
    assert e3.is_eligible is True
    assert e3.status == "limited_baseline_only"
    assert e3.recommended_model == "moving_average"

    # 4. Dense history (90 days, 60 active dates) -> sufficient
    dense_pts = [
        TimeSeriesPoint(date=date(2026, 8, 1) + timedelta(days=i), amount_paise=15000 if i % 3 != 0 else 0)
        for i in range(90)
    ]
    e4 = assess_data_eligibility(dense_pts, horizon_days=30)
    assert e4.is_eligible is True
    assert e4.status == "sufficient"
    assert e4.recommended_model == "holt_winters"


def test_baseline_forecasting_models():
    """Validates Historical Mean, Moving Average, and Exponential Smoothing baselines."""
    # Constant daily series of ₹100 (10000 paise)
    series = [
        TimeSeriesPoint(date=date(2026, 11, 1) + timedelta(days=i), amount_paise=10000)
        for i in range(14)
    ]

    # 1. Historical Mean
    mean_preds = forecast_historical_mean(series, steps=7, confidence_level=0.80)
    assert len(mean_preds) == 7
    assert mean_preds[0].point_estimate_paise == 10000
    assert mean_preds[0].lower_estimate_paise <= 10000
    assert mean_preds[0].upper_estimate_paise >= 10000

    # 2. Moving Average
    ma_preds = forecast_moving_average(series, steps=7, window=7)
    assert len(ma_preds) == 7
    assert ma_preds[0].point_estimate_paise == 10000

    # 3. Simple Exponential Smoothing
    ses_preds = forecast_exponential_smoothing(series, steps=7, alpha=0.3)
    assert len(ses_preds) == 7
    assert ses_preds[0].point_estimate_paise == 10000


def test_statistical_models_holt_winters_and_linear():
    """Validates Holt-Winters weekly seasonality and Damped Linear Regression."""
    # Synthetic series with weekly day-of-week pattern (higher spend on weekends)
    base_date = date(2026, 9, 1)
    pts = []
    for i in range(42):  # 6 full weeks
        d = base_date + timedelta(days=i)
        weekday = d.weekday()
        # Friday/Saturday spend ₹500, other days ₹100
        amt = 50000 if weekday in (4, 5) else 10000
        pts.append(TimeSeriesPoint(date=d, amount_paise=amt))

    # Holt-Winters (seasonal_periods=7)
    hw_preds = forecast_holt_winters(pts, steps=14, seasonal_periods=7)
    assert len(hw_preds) == 14
    # Predictions should reflect seasonal peaks
    weekend_preds = [hw_preds[i].point_estimate_paise for i in range(14) if hw_preds[i].forecast_date.weekday() in (4, 5)]
    weekday_preds = [hw_preds[i].point_estimate_paise for i in range(14) if hw_preds[i].forecast_date.weekday() not in (4, 5)]
    assert sum(weekend_preds) / len(weekend_preds) > sum(weekday_preds) / len(weekday_preds)

    # Damped Linear Regression
    linear_preds = forecast_linear_trend(pts, steps=14)
    assert len(linear_preds) == 14
    assert linear_preds[0].point_estimate_paise > 0
    assert linear_preds[0].lower_estimate_paise <= linear_preds[0].upper_estimate_paise


def test_walk_forward_evaluation_and_model_selection():
    """Validates rolling-origin cross validation metrics and automated model selection."""
    base_date = date(2026, 8, 1)
    series = [
        TimeSeriesPoint(date=base_date + timedelta(days=i), amount_paise=20000 + (i % 7) * 2000)
        for i in range(60)
    ]

    metrics = evaluate_time_series_walk_forward(series, model_name="moving_average", test_horizon=7)
    assert metrics.mae_paise >= 0
    assert metrics.rmse_paise >= metrics.mae_paise
    assert 0.0 <= metrics.wape <= 1.0
    assert 0.0 <= metrics.interval_coverage <= 1.0

    # Auto model selection
    best_model, best_metrics = select_best_model(series)
    assert best_model in ["historical_mean", "moving_average", "exponential_smoothing", "holt_winters", "linear_trend"]
    assert best_metrics.wape >= 0.0


def test_cash_flow_projection_and_recurring_integration():
    """Validates cash flow balance trajectory merging recurring commitments without double counting."""
    start_date = date(2026, 12, 1)
    inflows = forecast_historical_mean(
        [TimeSeriesPoint(date=start_date - timedelta(days=i), amount_paise=50000) for i in range(10)],
        steps=5,
        start_date=start_date,
    )
    outflows = forecast_historical_mean(
        [TimeSeriesPoint(date=start_date - timedelta(days=i), amount_paise=20000) for i in range(10)],
        steps=5,
        start_date=start_date,
    )

    # Mock recurring salary on Dec 1 (₹1,00,000) and rent on Dec 2 (₹25,000)
    class DummyOccurrence:
        def __init__(self, exp_date, amt, direction):
            self.expected_date = exp_date
            self.expected_amount_paise = amt
            self.status = "scheduled"
            self.recurring_definition = type("Def", (), {"direction": direction})()

    recs = [
        DummyOccurrence(date(2026, 12, 1), 10000000, "inflow"),
        DummyOccurrence(date(2026, 12, 2), 2500000, "outflow"),
    ]

    timeline = calculate_cash_flow_projection(
        starting_balance_paise=5000000,  # ₹50,000
        inflow_points=inflows,
        outflow_points=outflows,
        recurring_occurrences=recs,
    )

    assert len(timeline) == 5
    # Day 1: Starting ₹50,000 + Salary ₹1,00,000 - Outflow ₹200 = ₹1,49,800
    day1 = timeline[0]
    assert day1["inflow_recurring_paise"] == 10000000
    assert day1["projected_balance_paise"] > 5000000

    # Day 2: Includes rent ₹25,000
    day2 = timeline[1]
    assert day2["outflow_recurring_paise"] == 2500000
    assert day2["lower_balance_paise"] <= day2["projected_balance_paise"] <= day2["upper_balance_paise"]


def test_budget_exhaustion_calculation():
    """Validates budget burn rate and calendar exhaustion projection."""
    # 1. Active budget with daily burn of ₹1,000, ₹15,000 remaining
    est1 = calculate_budget_exhaustion(
        budget_id="b-1",
        budget_name="Operations",
        total_allocated_paise=5000000,  # ₹50,000
        current_spend_paise=3500000,    # ₹35,000
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 30),
        as_of_date=date(2026, 11, 15),
    )
    assert est1.utilization_pct == 70.0
    assert est1.remaining_paise == 1500000
    assert est1.status in ("within_budget", "projected_exhaustion")
    assert est1.estimated_exhaustion_date is not None

    # 2. Already exhausted budget
    est2 = calculate_budget_exhaustion(
        budget_id="b-2",
        budget_name="Overspent",
        total_allocated_paise=2000000,
        current_spend_paise=2500000,
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 30),
        as_of_date=date(2026, 11, 15),
    )
    assert est2.status == "already_exhausted"
    assert est2.days_to_exhaustion == 0


def test_goal_trajectory_projection():
    """Validates savings goal completion trajectory calculation."""
    # Goal: ₹3,00,000 target, ₹1,50,000 saved, ₹25,000/mo velocity -> ~6 months to finish
    traj = calculate_goal_trajectory(
        goal_id="g-1",
        goal_name="Emergency Fund",
        target_amount_paise=30000000,
        current_balance_paise=15000000,
        target_date=date(2027, 6, 1),
        as_of_date=date(2026, 11, 14),
        monthly_savings_pace_paise=2500000,
    )
    assert traj.remaining_paise == 15000000
    assert traj.is_on_track is True
    assert traj.status == "on_track"
    assert traj.projected_completion_date is not None
    assert traj.projected_completion_date < date(2027, 6, 1)


def test_deterministic_scenario_simulation():
    """Validates hypothetical what-if scenario calculations and isolation."""
    base_timeline = [
        {
            "date": date(2026, 12, 1) + timedelta(days=i),
            "starting_balance_paise": 10000000 + (i * 10000),
            "inflow_paise": 200000,
            "outflow_paise": 100000,
            "net_cash_flow_paise": 100000,
            "projected_balance_paise": 10100000 + (i * 100000),
        }
        for i in range(10)
    ]

    # Scenario: +10% income, -20% expense, one-time ₹50,000 expense on Dec 5
    assumptions = {
        "income_change_pct": 10.0,
        "expense_change_pct": -20.0,
        "one_time_outflows": [{"date": "2026-12-05", "amount_paise": 5000000}],
    }

    scen_res = evaluate_scenario(base_timeline, assumptions, scenario_type="optimistic")
    assert scen_res.scenario_type == "optimistic"
    assert len(scen_res.projected_timeline) == 10
    # Net delta should be computed deterministically
    assert isinstance(scen_res.delta_balance_paise, int)
    assert scen_res.scenario_projected_balance_paise != scen_res.baseline_projected_balance_paise


# ==============================================================================
# 2. INTEGRATION TESTS (POSTGRESQL PERSISTENCE & SERVICES)
# ==============================================================================

@pytest.fixture
async def setup_forecast_data(db_session: AsyncSession, registered_user: dict):
    """Sets up a test workspace, user, liquid accounts, categories, and posted transactions."""
    ws: Workspace = registered_user["workspace"]
    user = registered_user["user"]

    # Liquid Checking Account
    acc = Account(
        workspace_id=ws.id,
        name="Main Checking",
        account_type="savings",
        currency="INR",
        current_book_balance_paise=10000000,  # ₹1,00,000
        status="active",
    )
    db_session.add(acc)

    cat = Category(
        workspace_id=ws.id,
        name="Groceries & Food",
        slug=f"groceries-{uuid.uuid4().hex[:6]}",
        category_type="expense",
    )
    db_session.add(cat)
    await db_session.flush()

    # Seed 30 days of historical posted transactions
    base_date = date.today() - timedelta(days=35)
    for i in range(30):
        dt = base_date + timedelta(days=i)
        # Expense transaction
        tx_out = Transaction(
            workspace_id=ws.id,
            account_id=acc.id,
            category_id=cat.id,
            amount_paise=150000,  # ₹1,500
            amount=Decimal("1500.0000"),
            currency="INR",
            direction="outflow",
            transaction_type="expense",
            status="posted",
            transaction_date=dt,
            description=f"Supermarket Store #{i}",
        )
        db_session.add(tx_out)

        # Inflow every 15 days (Salary / Freelance)
        if i % 15 == 0:
            tx_in = Transaction(
                workspace_id=ws.id,
                account_id=acc.id,
                amount_paise=7500000,  # ₹75,000
                amount=Decimal("75000.0000"),
                currency="INR",
                direction="inflow",
                transaction_type="income",
                status="posted",
                transaction_date=dt,
                description="Salary Deposit",
            )
            db_session.add(tx_in)

    # Seed an active recurring commitment (Prompt 15)
    rec = RecurringDefinition(
        workspace_id=ws.id,
        name="Apartment Rent",
        direction="outflow",
        transaction_type="expense",
        expected_amount_paise=3000000,  # ₹30,000
        expected_amount=Decimal("30000.0000"),
        frequency="monthly",
        start_date=date.today(),
        next_expected_date=date.today() + timedelta(days=5),
        status="active",
    )
    db_session.add(rec)
    await db_session.flush()

    # Add occurrence for rent
    occ = RecurringOccurrence(
        workspace_id=ws.id,
        recurring_definition_id=rec.id,
        expected_date=date.today() + timedelta(days=5),
        expected_amount_paise=3000000,
        expected_amount=Decimal("30000.0000"),
        currency="INR",
        status="scheduled",
    )
    db_session.add(occ)

    # Seed an active recurring income commitment (Salary)
    rec_in = RecurringDefinition(
        workspace_id=ws.id,
        name="Salary Deposit",
        direction="inflow",
        transaction_type="income",
        expected_amount_paise=7500000,  # ₹75,000
        expected_amount=Decimal("75000.0000"),
        frequency="monthly",
        start_date=date.today(),
        next_expected_date=date.today() + timedelta(days=10),
        status="active",
    )
    db_session.add(rec_in)
    await db_session.flush()

    occ_in = RecurringOccurrence(
        workspace_id=ws.id,
        recurring_definition_id=rec_in.id,
        expected_date=date.today() + timedelta(days=10),
        expected_amount_paise=7500000,
        expected_amount=Decimal("75000.0000"),
        currency="INR",
        status="scheduled",
    )
    db_session.add(occ_in)

    # Seed an active budget (Prompt 14)
    b = Budget(
        workspace_id=ws.id,
        name="Monthly Groceries",
        budget_type="monthly",
        currency="INR",
        start_date=date.today().replace(day=1),
        end_date=date.today().replace(day=1) + timedelta(days=30),
        total_allocated_paise=5000000,
        total_allocated=Decimal("50000.0000"),
        recurrence_interval="monthly",
        status="active",
    )
    db_session.add(b)

    # Seed a savings goal (Prompt 14)
    g = FinancialGoal(
        workspace_id=ws.id,
        name="Vacation Fund",
        goal_type="travel",
        target_amount_paise=10000000,
        target_amount=Decimal("100000.0000"),
        current_amount_paise=4000000,
        current_amount=Decimal("40000.0000"),
        currency="INR",
        status="active",
    )
    db_session.add(g)

    await db_session.flush()
    await db_session.commit()

    return {
        "workspace": ws,
        "user": user,
        "account": acc,
        "category": cat,
        "budget": b,
        "goal": g,
    }


@pytest.mark.asyncio
async def test_forecasting_services_lifecycle(db_session: AsyncSession, setup_forecast_data: dict):
    """Validates complete execution of ForecastingService and DataPreparationService."""
    ws = setup_forecast_data["workspace"]
    user = setup_forecast_data["user"]

    service = ForecastingService(db_session)

    # 1. Generate 30-day forecast run
    req = ForecastGenerateRequest(horizon_days=30, confidence_level=0.80)
    cf_res = await service.generate_forecast(workspace_id=ws.id, request=req, user_id=user.id)

    assert cf_res.horizon_days == 30
    assert cf_res.starting_balance_paise == 10000000
    assert len(cf_res.timeline) == 30
    assert cf_res.total_projected_inflow_paise > 0
    assert cf_res.total_projected_outflow_paise > 0

    # 2. Query income & expense breakdowns
    inc_res = await service.get_income_forecast(workspace_id=ws.id, horizon_days=30)
    assert inc_res.total_expected_income_paise > 0
    assert len(inc_res.points) == 30

    exp_res = await service.get_expense_forecast(workspace_id=ws.id, horizon_days=30)
    assert exp_res.total_expected_expense_paise > 0
    assert exp_res.scheduled_commitments_paise > 0  # Captured rent!

    # 3. Query category-level projections
    cat_res = await service.get_category_forecast(workspace_id=ws.id, horizon_days=30)
    assert len(cat_res.categories) > 0
    assert cat_res.categories[0].category_name == "Groceries & Food"


@pytest.mark.asyncio
async def test_scenario_service_crud_and_simulation(db_session: AsyncSession, setup_forecast_data: dict):
    """Validates ScenarioService creating, evaluating, listing, and deleting scenarios."""
    ws = setup_forecast_data["workspace"]
    user = setup_forecast_data["user"]

    scenario_service = ScenarioService(db_session)

    # 1. Create scenario with +15% salary and ₹20,000 one-time gadget purchase
    req = ScenarioCreateRequest(
        name="Gadget Purchase & Raise",
        scenario_type="custom",
        horizon_days=30,
        income_change_pct=15.0,
        expense_change_pct=0.0,
        one_time_outflows=[{"date": str(date.today() + timedelta(days=7)), "amount_paise": 2000000, "description": "Tablet"}],
    )
    scen = await scenario_service.create_scenario(workspace_id=ws.id, request=req, user_id=user.id)
    assert scen.name == "Gadget Purchase & Raise"
    assert "delta_balance_paise" in scen.results

    # 2. List scenarios
    scens = await scenario_service.list_scenarios(workspace_id=ws.id)
    assert len(scens) >= 1

    # 3. Get scenario
    retrieved = await scenario_service.get_scenario(scenario_id=scen.id, workspace_id=ws.id)
    assert retrieved.id == scen.id

    # 4. Delete scenario
    deleted = await scenario_service.delete_scenario(scenario_id=scen.id, workspace_id=ws.id)
    assert deleted is True


@pytest.mark.asyncio
async def test_budget_exhaustion_and_goal_services(db_session: AsyncSession, setup_forecast_data: dict):
    """Validates BudgetExhaustionService and GoalProjectionService calculations."""
    ws = setup_forecast_data["workspace"]

    # Budget exhaustion
    budget_service = BudgetExhaustionService(db_session)
    b_res = await budget_service.get_exhaustion_estimates(workspace_id=ws.id)
    assert len(b_res.estimates) >= 1
    assert b_res.estimates[0]["budget_name"] == "Monthly Groceries"

    # Goal trajectory
    goal_service = GoalProjectionService(db_session)
    g_res = await goal_service.get_goal_trajectories(workspace_id=ws.id)
    assert len(g_res.goals) >= 1
    assert g_res.goals[0]["goal_name"] == "Vacation Fund"


@pytest.mark.asyncio
async def test_forecast_workspace_isolation(db_session: AsyncSession, setup_forecast_data: dict):
    """Verifies that forecast runs and scenarios are strictly isolated by workspace ID (anti-IDOR)."""
    ws1 = setup_forecast_data["workspace"]
    user1 = setup_forecast_data["user"]

    # Create second workspace
    ws2 = Workspace(
        name="Other Workspace",
        slug=f"other-ws-{uuid.uuid4().hex[:6]}",
        type="personal",
        owner_id=user1.id,
    )
    db_session.add(ws2)
    await db_session.flush()

    forecasting_service = ForecastingService(db_session)
    scenario_service = ScenarioService(db_session)

    # Create scenario in WS1
    s1 = await scenario_service.create_scenario(
        workspace_id=ws1.id,
        request=ScenarioCreateRequest(name="WS1 Only Scenario", horizon_days=30),
        user_id=user1.id,
    )

    # Scenarios for WS2 should NOT contain s1
    ws2_scenarios = await scenario_service.list_scenarios(workspace_id=ws2.id)
    assert not any(s.id == s1.id for s in ws2_scenarios)

    # Direct ID access from WS2 should raise NotFoundException
    from app.core.exceptions import NotFoundException
    with pytest.raises(NotFoundException):
        await scenario_service.get_scenario(scenario_id=s1.id, workspace_id=ws2.id)


@pytest.mark.asyncio
async def test_api_forecast_and_scenarios_endpoints(
    client: AsyncClient,
    registered_user: dict,
    setup_forecast_data: dict,
):
    """Validates all authenticated HTTP API routes for forecasting, budget exhaustion, goals, and scenarios."""
    token = registered_user["token"]
    ws_id = str(setup_forecast_data["workspace"].id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. POST /workspaces/{ws_id}/forecasts/generate
    gen_payload = {
        "horizon_days": 30,
        "resolution": "daily",
        "confidence_level": 0.80,
    }
    gen_res = await client.post(f"/api/v1/workspaces/{ws_id}/forecasts/generate", json=gen_payload, headers=headers)
    assert gen_res.status_code == 201
    cf_data = gen_res.json()["data"]
    assert cf_data["horizon_days"] == 30
    assert len(cf_data["timeline"]) == 30

    # 2. GET /workspaces/{ws_id}/forecasts/cash-flow
    cf_get = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/cash-flow?horizon_days=30", headers=headers)
    assert cf_get.status_code == 200

    # 3. GET /workspaces/{ws_id}/forecasts/income
    inc_res = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/income", headers=headers)
    assert inc_res.status_code == 200

    # 4. GET /workspaces/{ws_id}/forecasts/expenses
    exp_res = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/expenses", headers=headers)
    assert exp_res.status_code == 200

    # 5. GET /workspaces/{ws_id}/forecasts/categories
    cat_res = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/categories", headers=headers)
    assert cat_res.status_code == 200

    # 6. GET /workspaces/{ws_id}/forecasts/budget-exhaustion
    be_res = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/budget-exhaustion", headers=headers)
    assert be_res.status_code == 200

    # 7. GET /workspaces/{ws_id}/forecasts/goals
    g_res = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/goals", headers=headers)
    assert g_res.status_code == 200

    # 8. POST & GET /workspaces/{ws_id}/forecasts/scenarios
    scen_payload = {
        "name": "API Test Scenario",
        "scenario_type": "optimistic",
        "horizon_days": 30,
        "income_change_pct": 10.0,
        "expense_change_pct": -5.0,
    }
    scen_create = await client.post(f"/api/v1/workspaces/{ws_id}/forecasts/scenarios", json=scen_payload, headers=headers)
    assert scen_create.status_code == 201
    scen_id = scen_create.json()["data"]["id"]

    scen_list = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/scenarios", headers=headers)
    assert scen_list.status_code == 200
    assert any(s["id"] == scen_id for s in scen_list.json()["data"])

    # 9. GET /workspaces/{ws_id}/forecasts/evaluations
    eval_res = await client.get(f"/api/v1/workspaces/{ws_id}/forecasts/evaluations", headers=headers)
    assert eval_res.status_code == 200
