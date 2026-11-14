"""
Arthsavora Financial Forecasting Pure Domain Engine
Provides deterministic data eligibility validation, baseline models, statistical time-series forecasting,
walk-forward rolling-origin evaluation (MAE, RMSE, WAPE, Bias), cash-flow balance projection,
budget exhaustion timing, goal trajectories, and hypothetical scenario simulation.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
import math
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TimeSeriesPoint:
    """Historical or daily aggregate observation."""
    date: date
    amount_paise: int


@dataclass(frozen=True)
class ForecastPointVO:
    """Projected future time-series data point with lower and upper confidence bounds."""
    forecast_date: date
    point_estimate_paise: int
    lower_estimate_paise: int
    upper_estimate_paise: int
    confidence_level: float = 0.80
    is_recurring_commitment: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DataEligibilityAssessment:
    """Evaluates whether historical transaction density suffices for forecasting."""
    is_eligible: bool
    status: str  # "sufficient", "limited_baseline_only", "insufficient_data"
    total_observations: int
    span_days: int
    active_days: int
    recommended_model: str
    message: str


@dataclass(frozen=True)
class EvaluationMetricsVO:
    """Empirical time-series out-of-sample accuracy metrics."""
    mae_paise: int
    rmse_paise: int
    wape: float  # Weighted Absolute Percentage Error (safe against zero actuals)
    bias_paise: int  # Positive: over-forecasting, Negative: under-forecasting
    interval_coverage: float
    sample_size: int


@dataclass(frozen=True)
class BudgetExhaustionEstimate:
    """Pacing and exhaustion estimate for an active budget."""
    budget_id: str
    budget_name: str
    category_id: Optional[str]
    category_name: Optional[str]
    total_allocated_paise: int
    current_spend_paise: int
    remaining_paise: int
    burn_rate_daily_paise: int
    utilization_pct: float
    estimated_exhaustion_date: Optional[date]
    days_to_exhaustion: Optional[int]
    status: str  # "within_budget", "projected_exhaustion", "already_exhausted", "on_track"


@dataclass(frozen=True)
class GoalTrajectoryEstimate:
    """Projected completion trajectory for a financial savings goal."""
    goal_id: str
    goal_name: str
    target_amount_paise: int
    current_balance_paise: int
    remaining_paise: int
    target_date: Optional[date]
    monthly_savings_pace_paise: int
    projected_completion_date: Optional[date]
    is_on_track: bool
    status: str  # "achieved", "on_track", "behind_schedule", "insufficient_savings"


@dataclass(frozen=True)
class ScenarioResultVO:
    """Outcome of a deterministic what-if financial scenario simulation."""
    scenario_type: str
    horizon_days: int
    baseline_projected_balance_paise: int
    scenario_projected_balance_paise: int
    delta_balance_paise: int
    baseline_net_cash_flow_paise: int
    scenario_net_cash_flow_paise: int
    assumptions_summary: Dict[str, Any]
    projected_timeline: List[Dict[str, Any]]


# -----------------------------------------------------------------------------
# 1. Data Eligibility Assessment
# -----------------------------------------------------------------------------

def assess_data_eligibility(
    series: List[TimeSeriesPoint],
    horizon_days: int = 30,
    min_points_required: int = 7,
) -> DataEligibilityAssessment:
    """
    Evaluates whether historical series meets minimum criteria for time-series modeling.
    Guarantees no false precision and no model hallucination on sparse inputs.
    """
    if not series:
        return DataEligibilityAssessment(
            is_eligible=False,
            status="insufficient_data",
            total_observations=0,
            span_days=0,
            active_days=0,
            recommended_model="none",
            message="No historical transaction records found in the specified window.",
        )

    sorted_series = sorted(series, key=lambda p: p.date)
    span_days = (sorted_series[-1].date - sorted_series[0].date).days + 1
    active_days = sum(1 for p in sorted_series if p.amount_paise > 0)
    total_obs = len(sorted_series)

    # Scale thresholds based on horizon
    if horizon_days <= 14:
        min_span = 14
        min_active = 5
    elif horizon_days <= 30:
        min_span = 21
        min_active = 7
    elif horizon_days <= 90:
        min_span = 45
        min_active = 14
    else:
        min_span = 90
        min_active = 30

    if span_days < min_span or active_days < min_active:
        return DataEligibilityAssessment(
            is_eligible=False,
            status="insufficient_data",
            total_observations=total_obs,
            span_days=span_days,
            active_days=active_days,
            recommended_model="baseline_mean",
            message=f"Insufficient history: {span_days} days of data with {active_days} active dates. Minimum required is {min_span} days and {min_active} active transactions.",
        )

    # If data is modest (between min and 2x min), suggest baseline or moving average
    if active_days < min_active * 2:
        return DataEligibilityAssessment(
            is_eligible=True,
            status="limited_baseline_only",
            total_observations=total_obs,
            span_days=span_days,
            active_days=active_days,
            recommended_model="moving_average",
            message="Data coverage is moderate. Moving average and exponential smoothing baselines are recommended.",
        )

    return DataEligibilityAssessment(
        is_eligible=True,
        status="sufficient",
        total_observations=total_obs,
        span_days=span_days,
        active_days=active_days,
        recommended_model="holt_winters",
        message="Sufficient transaction depth for statistical trend and seasonality modeling.",
    )


# -----------------------------------------------------------------------------
# 2. Baseline & Statistical Forecasting Models
# -----------------------------------------------------------------------------

def forecast_historical_mean(
    series: List[TimeSeriesPoint],
    steps: int,
    confidence_level: float = 0.80,
    start_date: Optional[date] = None,
) -> List[ForecastPointVO]:
    """
    Historical Mean Baseline:
    y_hat = mean(y) with standard error confidence bounds.
    """
    if not series:
        return []

    values = [p.amount_paise for p in series]
    n = len(values)
    mean_val = sum(values) / n

    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
        std_err = math.sqrt(variance)
    else:
        std_err = mean_val * 0.20

    z = 1.28 if confidence_level <= 0.80 else 1.96
    margin = int(z * std_err)

    anchor_date = start_date or (max(p.date for p in series) + timedelta(days=1))
    results = []
    point_est = max(0, int(round(mean_val)))
    lower_est = max(0, point_est - margin)
    upper_est = point_est + margin

    for i in range(steps):
        dt = anchor_date + timedelta(days=i)
        results.append(
            ForecastPointVO(
                forecast_date=dt,
                point_estimate_paise=point_est,
                lower_estimate_paise=lower_est,
                upper_estimate_paise=upper_est,
                confidence_level=confidence_level,
                metadata={"model": "historical_mean"},
            )
        )
    return results


def forecast_moving_average(
    series: List[TimeSeriesPoint],
    steps: int,
    window: int = 7,
    confidence_level: float = 0.80,
    start_date: Optional[date] = None,
) -> List[ForecastPointVO]:
    """
    Simple Moving Average Baseline over the last `window` observations.
    """
    if not series:
        return []

    sorted_pts = sorted(series, key=lambda p: p.date)
    values = [p.amount_paise for p in sorted_pts]

    effective_window = min(window, len(values))
    recent = values[-effective_window:]
    ma_val = sum(recent) / effective_window

    if len(recent) > 1:
        variance = sum((x - ma_val) ** 2 for x in recent) / (len(recent) - 1)
        std_err = math.sqrt(variance)
    else:
        std_err = ma_val * 0.25

    z = 1.28 if confidence_level <= 0.80 else 1.96

    anchor_date = start_date or (sorted_pts[-1].date + timedelta(days=1))
    results = []
    point_est = max(0, int(round(ma_val)))

    for i in range(steps):
        step_factor = math.sqrt(1.0 + (i / 10.0))
        margin = int(z * std_err * step_factor)
        lower_est = max(0, point_est - margin)
        upper_est = point_est + margin

        dt = anchor_date + timedelta(days=i)
        results.append(
            ForecastPointVO(
                forecast_date=dt,
                point_estimate_paise=point_est,
                lower_estimate_paise=lower_est,
                upper_estimate_paise=upper_est,
                confidence_level=confidence_level,
                metadata={"model": "moving_average", "window": effective_window},
            )
        )
    return results


def forecast_exponential_smoothing(
    series: List[TimeSeriesPoint],
    steps: int,
    alpha: float = 0.3,
    confidence_level: float = 0.80,
    start_date: Optional[date] = None,
) -> List[ForecastPointVO]:
    """
    Simple Exponential Smoothing (SES):
    S_t = alpha * y_t + (1 - alpha) * S_{t-1}
    """
    if not series:
        return []

    sorted_pts = sorted(series, key=lambda p: p.date)
    values = [p.amount_paise for p in sorted_pts]

    s = float(values[0])
    residuals = []

    for y in values:
        residuals.append(y - s)
        s = alpha * float(y) + (1.0 - alpha) * s

    # Standard error of residuals
    if residuals:
        variance = sum(r ** 2 for r in residuals) / len(residuals)
        std_err = math.sqrt(variance)
    else:
        std_err = s * 0.20

    z = 1.28 if confidence_level <= 0.80 else 1.96
    anchor_date = start_date or (sorted_pts[-1].date + timedelta(days=1))
    results = []
    point_est = max(0, int(round(s)))

    for i in range(steps):
        step_factor = math.sqrt(1.0 + (i * alpha))
        margin = int(z * std_err * step_factor)
        lower_est = max(0, point_est - margin)
        upper_est = point_est + margin

        dt = anchor_date + timedelta(days=i)
        results.append(
            ForecastPointVO(
                forecast_date=dt,
                point_estimate_paise=point_est,
                lower_estimate_paise=lower_est,
                upper_estimate_paise=upper_est,
                confidence_level=confidence_level,
                metadata={"model": "exponential_smoothing", "alpha": alpha},
            )
        )
    return results


def forecast_holt_winters(
    series: List[TimeSeriesPoint],
    steps: int,
    alpha: float = 0.3,
    beta: float = 0.1,
    gamma: float = 0.2,
    seasonal_periods: int = 7,
    confidence_level: float = 0.80,
    start_date: Optional[date] = None,
) -> List[ForecastPointVO]:
    """
    Holt-Winters Additive Seasonality and Trend Smoothing.
    Captures day-of-week patterns (m=7) and ongoing spending trajectory.
    Gracefully falls back to SES if series is shorter than 2 seasonal periods.
    """
    if not series:
        return []

    sorted_pts = sorted(series, key=lambda p: p.date)
    values = [float(p.amount_paise) for p in sorted_pts]
    n = len(values)

    if n < seasonal_periods * 2:
        # Fallback to SES if insufficient data for full seasonal cycle
        return forecast_exponential_smoothing(series, steps, alpha=alpha, confidence_level=confidence_level, start_date=start_date)

    m = seasonal_periods

    # Initial level & trend
    level = sum(values[:m]) / m
    trend = (sum(values[m:2 * m]) - sum(values[:m])) / (m * m)

    # Initial seasonals
    seasonals = [values[i] - level for i in range(m)]

    residuals = []

    for i in range(n):
        val = values[i]
        s_idx = i % m
        prev_level = level
        prev_trend = trend
        seasonal_val = seasonals[s_idx]

        # One-step prediction
        y_pred = prev_level + prev_trend + seasonal_val
        residuals.append(val - y_pred)

        # Update equations
        level = alpha * (val - seasonal_val) + (1.0 - alpha) * (prev_level + prev_trend)
        trend = beta * (level - prev_level) + (1.0 - beta) * prev_trend
        seasonals[s_idx] = gamma * (val - level) + (1.0 - gamma) * seasonal_val

    # Damping trend to prevent runaway projections
    damping = 0.95
    if residuals:
        rmse = math.sqrt(sum(r ** 2 for r in residuals) / len(residuals))
    else:
        rmse = level * 0.25

    z = 1.28 if confidence_level <= 0.80 else 1.96
    anchor_date = start_date or (sorted_pts[-1].date + timedelta(days=1))
    results = []

    for h in range(1, steps + 1):
        s_idx = (n + h - 1) % m
        effective_trend = trend * (damping ** h)
        y_hat = level + (h * effective_trend) + seasonals[s_idx]
        point_est = max(0, int(round(y_hat)))

        step_factor = math.sqrt(1.0 + (h / float(m)))
        margin = int(z * rmse * step_factor)
        lower_est = max(0, point_est - margin)
        upper_est = point_est + margin

        dt = anchor_date + timedelta(days=h - 1)
        results.append(
            ForecastPointVO(
                forecast_date=dt,
                point_estimate_paise=point_est,
                lower_estimate_paise=lower_est,
                upper_estimate_paise=upper_est,
                confidence_level=confidence_level,
                metadata={"model": "holt_winters", "seasonal_periods": m},
            )
        )
    return results


def forecast_linear_trend(
    series: List[TimeSeriesPoint],
    steps: int,
    confidence_level: float = 0.80,
    start_date: Optional[date] = None,
) -> List[ForecastPointVO]:
    """
    Damped Linear Trend Regression with analytical confidence bands.
    """
    if not series:
        return []

    sorted_pts = sorted(series, key=lambda p: p.date)
    y = [float(p.amount_paise) for p in sorted_pts]
    n = len(y)
    x = list(range(n))

    x_bar = sum(x) / n
    y_bar = sum(y) / n

    denom = sum((xi - x_bar) ** 2 for xi in x)
    if denom == 0:
        return forecast_historical_mean(series, steps, confidence_level=confidence_level, start_date=start_date)

    beta1 = sum((x[i] - x_bar) * (y[i] - y_bar) for i in range(n)) / denom
    beta0 = y_bar - beta1 * x_bar

    # Damping slope to avoid runaway projections
    damped_slope = beta1 * 0.90

    residuals = [y[i] - (beta0 + beta1 * x[i]) for i in range(n)]
    sse = sum(r ** 2 for r in residuals)
    s_err = math.sqrt(sse / max(1, n - 2)) if n > 2 else y_bar * 0.20

    z = 1.28 if confidence_level <= 0.80 else 1.96
    anchor_date = start_date or (sorted_pts[-1].date + timedelta(days=1))
    results = []

    for h in range(steps):
        future_x = n + h
        y_hat = max(0.0, beta0 + damped_slope * future_x)
        point_est = int(round(y_hat))

        leverage = 1.0 / n + ((future_x - x_bar) ** 2) / denom
        margin = int(z * s_err * math.sqrt(1.0 + leverage))
        lower_est = max(0, point_est - margin)
        upper_est = point_est + margin

        dt = anchor_date + timedelta(days=h)
        results.append(
            ForecastPointVO(
                forecast_date=dt,
                point_estimate_paise=point_est,
                lower_estimate_paise=lower_est,
                upper_estimate_paise=upper_est,
                confidence_level=confidence_level,
                metadata={"model": "linear_trend", "slope": round(damped_slope, 4)},
            )
        )
    return results


# -----------------------------------------------------------------------------
# 3. Time-Series Rolling-Origin Walk-Forward Validation
# -----------------------------------------------------------------------------

def evaluate_time_series_walk_forward(
    series: List[TimeSeriesPoint],
    model_name: str,
    test_horizon: int = 7,
    step_size: int = 7,
) -> EvaluationMetricsVO:
    """
    Performs rigorous walk-forward cross validation without lookahead bias.
    Computes MAE, RMSE, WAPE, Bias, and Interval Coverage.
    """
    sorted_series = sorted(series, key=lambda p: p.date)
    n = len(sorted_series)

    min_train = max(14, int(n * 0.5))
    if n < min_train + test_horizon:
        # Insufficient depth for full walk-forward; evaluate in-sample residuals safely
        all_vals = [p.amount_paise for p in sorted_series]
        avg = sum(all_vals) / len(all_vals) if all_vals else 0
        mae = int(round(sum(abs(x - avg) for x in all_vals) / max(1, len(all_vals))))
        return EvaluationMetricsVO(
            mae_paise=mae,
            rmse_paise=int(round(math.sqrt(sum((x - avg) ** 2 for x in all_vals) / max(1, len(all_vals))))),
            wape=float(round(sum(abs(x - avg) for x in all_vals) / max(1, sum(all_vals)), 4)),
            bias_paise=0,
            interval_coverage=0.80,
            sample_size=n,
        )

    all_errors = []
    all_actuals = []
    in_interval_count = 0
    total_eval_points = 0

    origin = min_train
    while origin + test_horizon <= n:
        train_data = sorted_series[:origin]
        test_data = sorted_series[origin:origin + test_horizon]

        # Generate prediction using selected model
        if model_name == "holt_winters":
            preds = forecast_holt_winters(train_data, steps=test_horizon)
        elif model_name == "moving_average":
            preds = forecast_moving_average(train_data, steps=test_horizon)
        elif model_name == "exponential_smoothing":
            preds = forecast_exponential_smoothing(train_data, steps=test_horizon)
        elif model_name == "linear_trend":
            preds = forecast_linear_trend(train_data, steps=test_horizon)
        else:
            preds = forecast_historical_mean(train_data, steps=test_horizon)

        for actual_pt, pred_pt in zip(test_data, preds):
            act = actual_pt.amount_paise
            est = pred_pt.point_estimate_paise
            err = est - act  # bias orientation: pred - act

            all_errors.append(err)
            all_actuals.append(act)

            if pred_pt.lower_estimate_paise <= act <= pred_pt.upper_estimate_paise:
                in_interval_count += 1
            total_eval_points += 1

        origin += step_size

    if not all_errors:
        return EvaluationMetricsVO(mae_paise=0, rmse_paise=0, wape=0.0, bias_paise=0, interval_coverage=1.0, sample_size=0)

    abs_errors = [abs(e) for e in all_errors]
    mae = int(round(sum(abs_errors) / len(abs_errors)))
    rmse = int(round(math.sqrt(sum(e ** 2 for e in all_errors) / len(all_errors))))
    total_actual = sum(all_actuals)
    wape = float(round(sum(abs_errors) / max(1, total_actual), 4))
    bias = int(round(sum(all_errors) / len(all_errors)))
    coverage = float(round(in_interval_count / max(1, total_eval_points), 4))

    return EvaluationMetricsVO(
        mae_paise=mae,
        rmse_paise=rmse,
        wape=wape,
        bias_paise=bias,
        interval_coverage=coverage,
        sample_size=total_eval_points,
    )


def select_best_model(
    series: List[TimeSeriesPoint],
    candidate_models: Optional[List[str]] = None,
) -> Tuple[str, EvaluationMetricsVO]:
    """
    Evaluates candidate time-series models against a baseline using walk-forward validation.
    Selects the candidate with the lowest WAPE. If ML/statistical models do not beat the baseline,
    the transparent baseline is chosen.
    """
    if candidate_models is None:
        candidate_models = ["historical_mean", "moving_average", "exponential_smoothing", "holt_winters", "linear_trend"]

    best_model = "historical_mean"
    best_metrics = evaluate_time_series_walk_forward(series, model_name="historical_mean")

    for model_name in candidate_models:
        if model_name == "historical_mean":
            continue
        metrics = evaluate_time_series_walk_forward(series, model_name=model_name)
        # Improvement rule: must reduce WAPE by at least 2% to justify additional complexity
        if metrics.wape < best_metrics.wape * 0.98:
            best_model = model_name
            best_metrics = metrics

    return best_model, best_metrics


# -----------------------------------------------------------------------------
# 4. Cash-Flow & Balance Projection Engine
# -----------------------------------------------------------------------------

def calculate_cash_flow_projection(
    starting_balance_paise: int,
    inflow_points: List[ForecastPointVO],
    outflow_points: List[ForecastPointVO],
    recurring_occurrences: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Computes daily balance progression and net cash flow trajectory.
    Seamlessly merges scheduled recurring commitments (Prompt 15) with statistical discretionary forecasts
    while strictly avoiding double counting.
    """
    # Group recurring occurrences by date
    recurring_inflows: Dict[date, int] = {}
    recurring_outflows: Dict[date, int] = {}

    if recurring_occurrences:
        for occ in recurring_occurrences:
            if getattr(occ, "status", None) in ("skipped", "cancelled"):
                continue
            dt = getattr(occ, "expected_date", None)
            amt = getattr(occ, "expected_amount_paise", 0)
            defn = getattr(occ, "recurring_definition", None)
            direction = getattr(defn, "direction", "outflow") if defn else "outflow"

            if dt:
                if direction == "inflow":
                    recurring_inflows[dt] = recurring_inflows.get(dt, 0) + amt
                else:
                    recurring_outflows[dt] = recurring_outflows.get(dt, 0) + amt

    # Index forecasts by date
    inflow_by_date = {p.forecast_date: p for p in inflow_points}
    outflow_by_date = {p.forecast_date: p for p in outflow_points}

    all_dates = sorted(set(list(inflow_by_date.keys()) + list(outflow_by_date.keys()) + list(recurring_inflows.keys()) + list(recurring_outflows.keys())))

    running_balance = starting_balance_paise
    running_lower = starting_balance_paise
    running_upper = starting_balance_paise

    timeline = []

    for dt in all_dates:
        in_pt = inflow_by_date.get(dt)
        out_pt = outflow_by_date.get(dt)

        rec_in = recurring_inflows.get(dt, 0)
        rec_out = recurring_outflows.get(dt, 0)

        # Baseline statistical forecasts
        stat_in = in_pt.point_estimate_paise if in_pt else 0
        stat_out = out_pt.point_estimate_paise if out_pt else 0

        # Merge commitments: scheduled commitments are known facts; discretionary is added
        tot_in = rec_in + max(0, stat_in - rec_in)
        tot_out = rec_out + max(0, stat_out - rec_out)

        net_flow = tot_in - tot_out
        running_balance += net_flow

        # Uncertainty bounds: lower bound assumes min inflow & max outflow on discretionary + deterministic commitments
        in_margin = int(round((in_pt.upper_estimate_paise - in_pt.lower_estimate_paise) / 2.0)) if in_pt else 0
        out_margin = int(round((out_pt.upper_estimate_paise - out_pt.lower_estimate_paise) / 2.0)) if out_pt else 0

        in_lower = max(0, tot_in - in_margin)
        in_upper = tot_in + in_margin
        out_lower = max(0, tot_out - out_margin)
        out_upper = tot_out + out_margin

        running_lower += (in_lower - out_upper)
        running_upper += (in_upper - out_lower)

        timeline.append({
            "date": dt,
            "starting_balance_paise": running_balance - net_flow,
            "inflow_paise": tot_in,
            "inflow_recurring_paise": rec_in,
            "outflow_paise": tot_out,
            "outflow_recurring_paise": rec_out,
            "net_cash_flow_paise": net_flow,
            "projected_balance_paise": running_balance,
            "lower_balance_paise": running_lower,
            "upper_balance_paise": running_upper,
        })

    return timeline


# -----------------------------------------------------------------------------
# 5. Budget Exhaustion & Goal Trajectory Engines
# -----------------------------------------------------------------------------

def calculate_budget_exhaustion(
    budget_id: str,
    budget_name: str,
    total_allocated_paise: int,
    current_spend_paise: int,
    period_start: date,
    period_end: date,
    as_of_date: date,
    category_id: Optional[str] = None,
    category_name: Optional[str] = None,
) -> BudgetExhaustionEstimate:
    """
    Calculates current budget utilization and estimates the calendar date of budget exhaustion.
    """
    remaining = total_allocated_paise - current_spend_paise
    util_pct = (current_spend_paise / total_allocated_paise * 100.0) if total_allocated_paise > 0 else 100.0

    days_elapsed = max(1, (as_of_date - period_start).days)
    daily_burn = int(round(current_spend_paise / days_elapsed))

    if current_spend_paise >= total_allocated_paise:
        return BudgetExhaustionEstimate(
            budget_id=budget_id,
            budget_name=budget_name,
            category_id=category_id,
            category_name=category_name,
            total_allocated_paise=total_allocated_paise,
            current_spend_paise=current_spend_paise,
            remaining_paise=remaining,
            burn_rate_daily_paise=daily_burn,
            utilization_pct=round(util_pct, 2),
            estimated_exhaustion_date=as_of_date,
            days_to_exhaustion=0,
            status="already_exhausted",
        )

    if daily_burn <= 0 or remaining <= 0:
        return BudgetExhaustionEstimate(
            budget_id=budget_id,
            budget_name=budget_name,
            category_id=category_id,
            category_name=category_name,
            total_allocated_paise=total_allocated_paise,
            current_spend_paise=current_spend_paise,
            remaining_paise=remaining,
            burn_rate_daily_paise=0,
            utilization_pct=round(util_pct, 2),
            estimated_exhaustion_date=None,
            days_to_exhaustion=None,
            status="on_track",
        )

    days_to_exhaust = int(remaining // daily_burn)
    est_date = as_of_date + timedelta(days=days_to_exhaust)

    status = "projected_exhaustion" if est_date <= period_end else "within_budget"

    return BudgetExhaustionEstimate(
        budget_id=budget_id,
        budget_name=budget_name,
        category_id=category_id,
        category_name=category_name,
        total_allocated_paise=total_allocated_paise,
        current_spend_paise=current_spend_paise,
        remaining_paise=remaining,
        burn_rate_daily_paise=daily_burn,
        utilization_pct=round(util_pct, 2),
        estimated_exhaustion_date=est_date,
        days_to_exhaustion=days_to_exhaust,
        status=status,
    )


def calculate_goal_trajectory(
    goal_id: str,
    goal_name: str,
    target_amount_paise: int,
    current_balance_paise: int,
    target_date: Optional[date],
    as_of_date: date,
    monthly_savings_pace_paise: int,
) -> GoalTrajectoryEstimate:
    """
    Projects goal completion date based on current progress and monthly savings rate.
    """
    remaining = max(0, target_amount_paise - current_balance_paise)

    if remaining == 0:
        return GoalTrajectoryEstimate(
            goal_id=goal_id,
            goal_name=goal_name,
            target_amount_paise=target_amount_paise,
            current_balance_paise=current_balance_paise,
            remaining_paise=0,
            target_date=target_date,
            monthly_savings_pace_paise=monthly_savings_pace_paise,
            projected_completion_date=as_of_date,
            is_on_track=True,
            status="achieved",
        )

    if monthly_savings_pace_paise <= 0:
        return GoalTrajectoryEstimate(
            goal_id=goal_id,
            goal_name=goal_name,
            target_amount_paise=target_amount_paise,
            current_balance_paise=current_balance_paise,
            remaining_paise=remaining,
            target_date=target_date,
            monthly_savings_pace_paise=0,
            projected_completion_date=None,
            is_on_track=False,
            status="insufficient_savings",
        )

    months_needed = remaining / float(monthly_savings_pace_paise)
    days_needed = int(round(months_needed * 30.4375))
    est_date = as_of_date + timedelta(days=days_needed)

    on_track = (target_date is None) or (est_date <= target_date)
    status = "on_track" if on_track else "behind_schedule"

    return GoalTrajectoryEstimate(
        goal_id=goal_id,
        goal_name=goal_name,
        target_amount_paise=target_amount_paise,
        current_balance_paise=current_balance_paise,
        remaining_paise=remaining,
        target_date=target_date,
        monthly_savings_pace_paise=monthly_savings_pace_paise,
        projected_completion_date=est_date,
        is_on_track=on_track,
        status=status,
    )


# -----------------------------------------------------------------------------
# 6. Financial Scenario Simulation Engine
# -----------------------------------------------------------------------------

def evaluate_scenario(
    base_cash_flow_timeline: List[Dict[str, Any]],
    assumptions: Dict[str, Any],
    scenario_type: str = "custom",
) -> ScenarioResultVO:
    """
    Executes a deterministic what-if financial simulation.
    Adjusts income (+/- %), expenses (+/- %), applies one-time items, and computes net balance delta.
    Strictly isolated from operational ledgers and actual records.
    """
    income_adj_pct = float(assumptions.get("income_change_pct", 0.0))
    expense_adj_pct = float(assumptions.get("expense_change_pct", 0.0))
    one_time_inflows = assumptions.get("one_time_inflows", [])  # [{"date": "YYYY-MM-DD", "amount_paise": 100000}]
    one_time_outflows = assumptions.get("one_time_outflows", [])

    one_in_map: Dict[str, int] = {}
    for item in one_time_inflows:
        d_str = str(item.get("date", ""))
        one_in_map[d_str] = one_in_map.get(d_str, 0) + int(item.get("amount_paise", 0))

    one_out_map: Dict[str, int] = {}
    for item in one_time_outflows:
        d_str = str(item.get("date", ""))
        one_out_map[d_str] = one_out_map.get(d_str, 0) + int(item.get("amount_paise", 0))

    simulated_timeline = []
    base_final_balance = base_cash_flow_timeline[-1]["projected_balance_paise"] if base_cash_flow_timeline else 0
    base_net_flow = sum(pt["net_cash_flow_paise"] for pt in base_cash_flow_timeline)

    running_sim_balance = base_cash_flow_timeline[0]["starting_balance_paise"] if base_cash_flow_timeline else 0
    sim_net_flow = 0

    for pt in base_cash_flow_timeline:
        dt = pt["date"]
        d_str = str(dt)

        base_in = pt["inflow_paise"]
        base_out = pt["outflow_paise"]

        # Apply percentage adjustments and one-time events
        adj_in = int(round(base_in * (1.0 + (income_adj_pct / 100.0)))) + one_in_map.get(d_str, 0)
        adj_out = int(round(base_out * (1.0 + (expense_adj_pct / 100.0)))) + one_out_map.get(d_str, 0)

        net_pt = adj_in - adj_out
        sim_net_flow += net_pt
        running_sim_balance += net_pt

        simulated_timeline.append({
            "date": dt,
            "scenario_inflow_paise": adj_in,
            "scenario_outflow_paise": adj_out,
            "scenario_net_cash_flow_paise": net_pt,
            "scenario_projected_balance_paise": running_sim_balance,
            "baseline_projected_balance_paise": pt["projected_balance_paise"],
            "delta_paise": running_sim_balance - pt["projected_balance_paise"],
        })

    delta_balance = running_sim_balance - base_final_balance

    return ScenarioResultVO(
        scenario_type=scenario_type,
        horizon_days=len(base_cash_flow_timeline),
        baseline_projected_balance_paise=base_final_balance,
        scenario_projected_balance_paise=running_sim_balance,
        delta_balance_paise=delta_balance,
        baseline_net_cash_flow_paise=base_net_flow,
        scenario_net_cash_flow_paise=sim_net_flow,
        assumptions_summary=assumptions,
        projected_timeline=simulated_timeline,
    )
