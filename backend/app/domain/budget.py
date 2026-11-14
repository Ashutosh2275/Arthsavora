"""
Arthsavora Budget & Goal Domain Foundation
Defines core budget types, goal classifications, calculation standards,
deterministic spending projections, and period boundary generators.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class BudgetType(str, Enum):
    """Supported budget structural forms."""
    MONTHLY = "monthly"
    CATEGORY = "category"
    OVERALL = "overall"
    CUSTOM = "custom"
    ANNUAL = "annual"
    FLEXIBLE = "flexible"


class RecurrenceInterval(str, Enum):
    """Recurring interval frequency for automatic period generation."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    NONE = "none"


class BudgetStatus(str, Enum):
    """Lifecycle statuses for a budget."""
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    CLOSED = "closed"


class BudgetWarningState(str, Enum):
    """Utilization status indicator for visual badges and alerts."""
    NORMAL = "normal"
    WARNING = "warning"
    EXHAUSTED = "exhausted"
    EXCEEDED = "exceeded"


class GoalType(str, Enum):
    """Purpose-oriented savings goal types."""
    EMERGENCY_FUND = "emergency_fund"
    EDUCATION = "education"
    TRAVEL = "travel"
    VEHICLE = "vehicle"
    HOME = "home"
    DEBT_REPAYMENT = "debt_repayment"
    PERSONAL_SAVINGS = "personal_savings"
    CUSTOM = "custom"


class GoalStatus(str, Enum):
    """Lifecycle statuses for financial goals."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ARCHIVED = "archived"


class GoalPriority(str, Enum):
    """Priority weights for goal planning."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GoalActivityType(str, Enum):
    """Immutable ledger activity classifications for savings goals."""
    CONTRIBUTION = "contribution"
    WITHDRAWAL = "withdrawal"
    REVERSAL = "reversal"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


# ==============================================================================
# DETERMINISTIC BUDGET CALCULATION ENGINE
# ==============================================================================

@dataclass(frozen=True)
class BudgetProgressResult:
    """Calculated financial progress metrics for an overall budget or category allocation."""
    allocated_amount_paise: int
    allocated_amount: Decimal
    actual_spent_paise: int
    actual_spent: Decimal
    remaining_amount_paise: int
    remaining_amount: Decimal
    utilization_percentage: float
    overspent_amount_paise: int
    overspent_amount: Decimal
    is_overspent: bool
    warning_state: BudgetWarningState


def calculate_budget_progress(
    allocated_amount_paise: int,
    actual_spent_paise: int,
    warning_threshold_pct: int = 80,
) -> BudgetProgressResult:
    """
    Computes exact financial budget metrics without floating-point inaccuracies.
    
    Formula:
      Remaining = Allocated - Actual
      Utilization = (Actual / Allocated) * 100 (if Allocated > 0, else 0.0)
      Overspent = max(0, Actual - Allocated)
    """
    safe_allocated = max(0, allocated_amount_paise)
    safe_spent = max(0, actual_spent_paise)

    remaining_paise = safe_allocated - safe_spent
    overspent_paise = max(0, safe_spent - safe_allocated)
    is_overspent = safe_spent > safe_allocated

    if safe_allocated > 0:
        utilization = round((safe_spent / safe_allocated) * 100.0, 2)
    else:
        # Zero allocation: if any money was spent, utilization is infinite/100%, else 0.0%
        utilization = 100.0 if safe_spent > 0 else 0.0

    # Determine warning state
    if safe_spent > safe_allocated:
        warning_state = BudgetWarningState.EXCEEDED
    elif safe_spent == safe_allocated and safe_allocated > 0:
        warning_state = BudgetWarningState.EXHAUSTED
    elif utilization >= warning_threshold_pct and safe_allocated > 0:
        warning_state = BudgetWarningState.WARNING
    else:
        warning_state = BudgetWarningState.NORMAL

    return BudgetProgressResult(
        allocated_amount_paise=safe_allocated,
        allocated_amount=Decimal(safe_allocated) / Decimal(100),
        actual_spent_paise=safe_spent,
        actual_spent=Decimal(safe_spent) / Decimal(100),
        remaining_amount_paise=remaining_paise,
        remaining_amount=Decimal(remaining_paise) / Decimal(100),
        utilization_percentage=utilization,
        overspent_amount_paise=overspent_paise,
        overspent_amount=Decimal(overspent_paise) / Decimal(100),
        is_overspent=is_overspent,
        warning_state=warning_state,
    )


@dataclass(frozen=True)
class PeriodProgressResult:
    """Temporal progress metrics for a budget window."""
    total_days: int
    days_elapsed: int
    days_remaining: int
    period_progress_percentage: float


def calculate_period_progress(
    start_date: date,
    end_date: date,
    as_of_date: Optional[date] = None,
) -> PeriodProgressResult:
    """Calculates temporal elapsed and remaining days within a budget window."""
    current = as_of_date or date.today()
    total_days = max(1, (end_date - start_date).days + 1)

    if current < start_date:
        days_elapsed = 0
    elif current > end_date:
        days_elapsed = total_days
    else:
        days_elapsed = (current - start_date).days + 1

    days_remaining = max(0, (end_date - current).days) if current <= end_date else 0
    progress_pct = round((days_elapsed / total_days) * 100.0, 2)

    return PeriodProgressResult(
        total_days=total_days,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        period_progress_percentage=min(100.0, progress_pct),
    )


@dataclass(frozen=True)
class LinearProjectionResult:
    """
    Transparent deterministic projection baseline.
    Discloses assumption: assumes historical daily run-rate continues linearly through period end.
    """
    average_daily_spend_paise: int
    average_daily_spend: Decimal
    projected_period_end_spend_paise: int
    projected_period_end_spend: Decimal
    projected_variance_paise: int
    projected_variance: Decimal
    is_projected_to_exceed: bool
    confidence_disclosure: str


def calculate_linear_projection(
    allocated_amount_paise: int,
    actual_spent_paise: int,
    days_elapsed: int,
    total_days: int,
) -> LinearProjectionResult:
    """
    Calculates deterministic run-rate projection.
    Formula: Projected = (Actual Spent / Elapsed Days) * Total Days
    """
    if days_elapsed <= 0 or actual_spent_paise <= 0:
        # Zero baseline projection
        return LinearProjectionResult(
            average_daily_spend_paise=0,
            average_daily_spend=Decimal("0.00"),
            projected_period_end_spend_paise=actual_spent_paise,
            projected_period_end_spend=Decimal(actual_spent_paise) / Decimal(100),
            projected_variance_paise=actual_spent_paise - allocated_amount_paise,
            projected_variance=Decimal(actual_spent_paise - allocated_amount_paise) / Decimal(100),
            is_projected_to_exceed=actual_spent_paise > allocated_amount_paise,
            confidence_disclosure="Deterministic baseline: Insufficient days elapsed for run-rate projection.",
        )

    avg_daily_paise = int(actual_spent_paise // days_elapsed)
    projected_paise = int(avg_daily_paise * total_days)
    variance_paise = projected_paise - allocated_amount_paise
    is_exceeding = projected_paise > allocated_amount_paise

    return LinearProjectionResult(
        average_daily_spend_paise=avg_daily_paise,
        average_daily_spend=Decimal(avg_daily_paise) / Decimal(100),
        projected_period_end_spend_paise=projected_paise,
        projected_period_end_spend=Decimal(projected_paise) / Decimal(100),
        projected_variance_paise=variance_paise,
        projected_variance=Decimal(variance_paise) / Decimal(100),
        is_projected_to_exceed=is_exceeding,
        confidence_disclosure="Deterministic baseline assuming uniform daily burn rate through period end.",
    )


# ==============================================================================
# FINANCIAL GOAL CALCULATIONS
# ==============================================================================

@dataclass(frozen=True)
class GoalProgressResult:
    """Calculated progress and pacing metrics for a financial savings goal."""
    target_amount_paise: int
    target_amount: Decimal
    current_amount_paise: int
    current_amount: Decimal
    remaining_amount_paise: int
    remaining_amount: Decimal
    progress_percentage: float
    is_completed: bool
    is_overfunded: bool
    days_remaining: Optional[int]
    required_monthly_savings_paise: Optional[int]
    required_monthly_savings: Optional[Decimal]


def calculate_goal_progress(
    target_amount_paise: int,
    current_amount_paise: int,
    start_date: date,
    target_date: Optional[date] = None,
    as_of_date: Optional[date] = None,
) -> GoalProgressResult:
    """
    Computes financial goal milestones, completion percentage, and required pacing.
    """
    current_ref = as_of_date or date.today()
    safe_target = max(0, target_amount_paise)
    safe_current = max(0, current_amount_paise)

    remaining_paise = max(0, safe_target - safe_current)
    is_completed = safe_current >= safe_target
    is_overfunded = safe_current > safe_target

    if safe_target > 0:
        progress_pct = min(100.0, round((safe_current / safe_target) * 100.0, 2))
    else:
        progress_pct = 100.0

    days_remaining: Optional[int] = None
    required_monthly_paise: Optional[int] = None
    required_monthly_dec: Optional[Decimal] = None

    if target_date:
        days_rem = (target_date - current_ref).days
        days_remaining = max(0, days_rem)
        if days_remaining > 0 and remaining_paise > 0:
            months_remaining = max(Decimal("0.5"), Decimal(days_remaining) / Decimal(30.4375))
            req_paise = int(math.ceil(Decimal(remaining_paise) / months_remaining))
            required_monthly_paise = req_paise
            required_monthly_dec = Decimal(req_paise) / Decimal(100)
        elif remaining_paise == 0:
            required_monthly_paise = 0
            required_monthly_dec = Decimal("0.00")

    return GoalProgressResult(
        target_amount_paise=safe_target,
        target_amount=Decimal(safe_target) / Decimal(100),
        current_amount_paise=safe_current,
        current_amount=Decimal(safe_current) / Decimal(100),
        remaining_amount_paise=remaining_paise,
        remaining_amount=Decimal(remaining_paise) / Decimal(100),
        progress_percentage=progress_pct,
        is_completed=is_completed,
        is_overfunded=is_overfunded,
        days_remaining=days_remaining,
        required_monthly_savings_paise=required_monthly_paise,
        required_monthly_savings=required_monthly_dec,
    )


# ==============================================================================
# PERIOD BOUNDARY & ROLLOVER GENERATORS
# ==============================================================================

def generate_next_period_bounds(
    current_start: date,
    current_end: date,
    interval: RecurrenceInterval,
) -> Tuple[date, date]:
    """
    Generates subsequent budget period boundaries following calendar and India FY standards.
    Supports leap years and variable month lengths idempotently.
    """
    if interval == RecurrenceInterval.MONTHLY:
        # Move to next month
        if current_end.month == 12:
            next_start = date(current_end.year + 1, 1, 1)
            next_end = date(current_end.year + 1, 1, 31)
        else:
            next_start = date(current_end.year, current_end.month + 1, 1)
            # Find last day of next month
            if next_start.month == 12:
                next_end = date(next_start.year, 12, 31)
            else:
                next_end = date(next_start.year, next_start.month + 1, 1) - timedelta(days=1)
        return next_start, next_end

    elif interval == RecurrenceInterval.QUARTERLY:
        next_start = current_end + timedelta(days=1)
        quarter = (next_start.month - 1) // 3 + 1
        end_month = quarter * 3
        if end_month == 12:
            next_end = date(next_start.year, 12, 31)
        else:
            next_end = date(next_start.year, end_month + 1, 1) - timedelta(days=1)
        return next_start, next_end

    elif interval == RecurrenceInterval.ANNUAL:
        # If aligned to India FY (April 1 - March 31)
        if current_start.month == 4 and current_start.day == 1:
            next_start = date(current_start.year + 1, 4, 1)
            next_end = date(current_start.year + 2, 3, 31)
        else:
            next_start = date(current_start.year + 1, 1, 1)
            next_end = date(current_start.year + 1, 12, 31)
        return next_start, next_end

    else:
        # Default fallback: shift by the exact length of the custom period
        span = (current_end - current_start).days + 1
        next_start = current_end + timedelta(days=1)
        next_end = next_start + timedelta(days=span - 1)
        return next_start, next_end
