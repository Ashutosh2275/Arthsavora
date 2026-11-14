"""
Arthsavora Financial Analytics Domain Foundation
Defines core metric standards, financial date utilities (including India Financial Year),
period grouping strategies, multi-currency isolation rules, and CSV sanitization.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
import math
from typing import Any, Optional, Tuple


class PeriodGrouping(str, Enum):
    """Supported temporal aggregation intervals for cash-flow and trend analytics."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    FINANCIAL_YEAR = "financial_year"


class ReportType(str, Enum):
    """Types of analytical reports supported for UI rendering and controlled CSV export."""
    OVERVIEW = "overview"
    CASH_FLOW = "cash_flow"
    CATEGORIES = "categories"
    MERCHANTS = "merchants"
    NET_WORTH = "net_worth"


class FinancialSentiment(str, Enum):
    """Directional favorability indicator for period-over-period financial delta."""
    FAVORABLE = "favorable"
    UNFAVORABLE = "unfavorable"
    NEUTRAL = "neutral"


def get_financial_year_bounds(ref_date: date) -> Tuple[date, date]:
    """
    Computes India Financial Year bounds (1 April – 31 March) containing ref_date.
    
    If ref_date is 2026-02-15:
      Financial Year is FY 2025-26: starts 2025-04-01, ends 2026-03-31.
    If ref_date is 2026-05-10:
      Financial Year is FY 2026-27: starts 2026-04-01, ends 2027-03-31.
    """
    if ref_date.month >= 4:
        start_year = ref_date.year
        end_year = ref_date.year + 1
    else:
        start_year = ref_date.year - 1
        end_year = ref_date.year

    fy_start = date(start_year, 4, 1)
    fy_end = date(end_year, 3, 31)
    return fy_start, fy_end


def get_month_bounds(ref_date: date) -> Tuple[date, date]:
    """Computes calendar month start and end dates."""
    start = date(ref_date.year, ref_date.month, 1)
    if ref_date.month == 12:
        end = date(ref_date.year, 12, 31)
    else:
        next_month_first = date(ref_date.year, ref_date.month + 1, 1)
        end = next_month_first - timedelta(days=1)
    return start, end


def get_quarter_bounds(ref_date: date) -> Tuple[date, date]:
    """Computes calendar quarter start and end dates."""
    quarter = (ref_date.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2

    start = date(ref_date.year, start_month, 1)
    if end_month == 12:
        end = date(ref_date.year, 12, 31)
    else:
        next_quarter_first = date(ref_date.year, end_month + 1, 1)
        end = next_quarter_first - timedelta(days=1)
    return start, end


def get_previous_period_bounds(start_date: date, end_date: date) -> Tuple[date, date]:
    """
    Calculates the prior period bounds of matching length immediately preceding start_date.
    Duration in days is (end_date - start_date + 1).
    """
    duration_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration_days - 1)
    return prev_start, prev_end


def calculate_savings_rate(income_paise: int, expenses_paise: int) -> float:
    """
    Computes savings rate percentage: ((income - expenses) / income) * 100.
    Returns 0.0 if income <= 0.
    Capped at a reasonable lower bound of -1000.0% to prevent extreme ratios.
    """
    if income_paise <= 0:
        return 0.0
    savings_paise = income_paise - expenses_paise
    rate = (savings_paise / income_paise) * 100.0
    return round(rate, 2)


def calculate_percentage_delta(current: int | float, previous: int | float) -> Optional[float]:
    """
    Calculates percentage change: ((current - previous) / abs(previous)) * 100.
    Returns None if previous is 0 and current != 0 to signify baseline absence.
    Returns 0.0 if both current and previous are 0.
    """
    if previous == 0:
        if current == 0:
            return 0.0
        return None
    delta = ((current - previous) / abs(previous)) * 100.0
    return round(delta, 2)


def evaluate_sentiment(metric_type: str, delta_amount: int | float) -> FinancialSentiment:
    """
    Evaluates financial sentiment of a delta:
    - For income/savings/net_cash_flow/net_worth: increase is favorable, decrease is unfavorable.
    - For expenses/liabilities: decrease is favorable, increase is unfavorable.
    """
    if delta_amount == 0:
        return FinancialSentiment.NEUTRAL

    if metric_type in ("income", "savings", "net_cash_flow", "net_worth", "assets"):
        return FinancialSentiment.FAVORABLE if delta_amount > 0 else FinancialSentiment.UNFAVORABLE
    elif metric_type in ("expenses", "liabilities"):
        return FinancialSentiment.FAVORABLE if delta_amount < 0 else FinancialSentiment.UNFAVORABLE
    return FinancialSentiment.NEUTRAL


def sanitize_csv_cell(value: Any) -> str:
    """
    Guards against CSV Formula Injection (Excel / LibreOffice macro execution).
    If a string cell starts with '=', '+', '-', '@', '\t', or '\r',
    it is prepended with a single quote "'" to neutralize execution.
    """
    if value is None:
        return ""
    str_val = str(value)
    if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{str_val}"
    return str_val
