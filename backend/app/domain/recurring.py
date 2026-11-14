"""
Arthsavora Recurring Finance Domain Models & Pure Calculation Engine
Enforces date mathematics, leap-year handling, end-of-month policies, cost normalization,
occurrence state evaluation, transaction matching heuristics, and pattern detection algorithms.
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
import math
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid


class RecurringDirection(str, Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class RecurringFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class EndOfMonthPolicy(str, Enum):
    LAST_DAY = "last_day"           # Clamp to last day of target month (e.g. Feb 28/29, Apr 30)
    CLOSEST_BEFORE = "closest_before"  # Move to last available day
    SKIP = "skip"                   # Skip months lacking the scheduled day


class RecurringStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class OccurrenceStatus(str, Enum):
    SCHEDULED = "scheduled"
    UPCOMING = "upcoming"
    DUE = "due"
    MATCHED = "matched"
    CONFIRMED = "confirmed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class BillingFrequency(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class ReminderType(str, Enum):
    UPCOMING_PAYMENT = "upcoming_payment"
    UPCOMING_RENEWAL = "upcoming_renewal"
    TRIAL_ENDING = "trial_ending"
    PAYMENT_OVERDUE = "payment_overdue"
    CANCELLATION_DEADLINE = "cancellation_deadline"


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


# -------------------------------------------------------------------------
# Date Scheduling Calculations
# -------------------------------------------------------------------------

def is_leap_year(year: int) -> bool:
    """Determine whether a given year is a leap year in Gregorian calendar."""
    return calendar.isleap(year)


def get_month_days(year: int, month: int) -> int:
    """Return the number of days in the specified month and year."""
    return calendar.monthrange(year, month)[1]


def add_months(sourcedate: date, months: int) -> Tuple[int, int]:
    """Calculate the target year and month after adding specified months."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    return year, month


def calculate_next_occurrence(
    base_date: date,
    frequency: RecurringFrequency | str,
    interval: int = 1,
    day_of_month: Optional[int] = None,
    day_of_week: Optional[int] = None,
    end_of_month_policy: EndOfMonthPolicy | str = EndOfMonthPolicy.LAST_DAY,
) -> date:
    """
    Deterministically computes the next occurrence date after base_date.
    
    Guarantees:
    - Never drifts permanently if original schedule day was 31 (Feb -> 28/29, Mar -> 31).
    - Respects leap years for February 29th schedules.
    - Follows configured end_of_month_policy.
    """
    if interval < 1:
        interval = 1

    freq_str = frequency.value if isinstance(frequency, RecurringFrequency) else str(frequency).lower()
    policy_str = end_of_month_policy.value if isinstance(end_of_month_policy, EndOfMonthPolicy) else str(end_of_month_policy).lower()

    if freq_str == RecurringFrequency.DAILY.value:
        return base_date + timedelta(days=interval)

    elif freq_str == RecurringFrequency.WEEKLY.value:
        if day_of_week is not None and 0 <= day_of_week <= 6:
            # Advance interval weeks, pinned to specific weekday
            days_ahead = (day_of_week - base_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7 * interval
            else:
                days_ahead = days_ahead + 7 * (interval - 1)
            return base_date + timedelta(days=days_ahead)
        return base_date + timedelta(weeks=interval)

    elif freq_str == RecurringFrequency.BIWEEKLY.value:
        return base_date + timedelta(weeks=2 * interval)

    elif freq_str in (RecurringFrequency.MONTHLY.value, RecurringFrequency.QUARTERLY.value,
                      RecurringFrequency.SEMI_ANNUAL.value, RecurringFrequency.ANNUAL.value,
                      RecurringFrequency.CUSTOM.value):
        # Determine number of months to add
        months_to_add = interval
        if freq_str == RecurringFrequency.QUARTERLY.value:
            months_to_add = 3 * interval
        elif freq_str == RecurringFrequency.SEMI_ANNUAL.value:
            months_to_add = 6 * interval
        elif freq_str == RecurringFrequency.ANNUAL.value:
            months_to_add = 12 * interval

        target_year, target_month = add_months(base_date, months_to_add)
        max_days = get_month_days(target_year, target_month)

        target_day = day_of_month if day_of_month is not None else base_date.day

        if target_day > max_days:
            if policy_str == EndOfMonthPolicy.SKIP.value:
                # Recursively advance to next eligible month
                return calculate_next_occurrence(
                    date(target_year, target_month, 1),
                    frequency,
                    interval=1,
                    day_of_month=day_of_month,
                    end_of_month_policy=end_of_month_policy,
                )
            else:  # LAST_DAY or CLOSEST_BEFORE
                target_day = max_days

        return date(target_year, target_month, target_day)

    # Fallback to monthly
    target_year, target_month = add_months(base_date, 1)
    max_days = get_month_days(target_year, target_month)
    return date(target_year, target_month, min(base_date.day, max_days))


def generate_occurrence_dates_in_window(
    start_from: date,
    window_end: date,
    frequency: RecurringFrequency | str,
    interval: int = 1,
    day_of_month: Optional[int] = None,
    day_of_week: Optional[int] = None,
    end_of_month_policy: EndOfMonthPolicy | str = EndOfMonthPolicy.LAST_DAY,
    end_date: Optional[date] = None,
    limit: int = 120,
) -> List[date]:
    """
    Generates an idempotent sequence of expected occurrence dates between start_from and window_end.
    Does not exceed end_date (if specified) or limit.
    """
    occurrences: List[date] = []
    current = start_from

    # If start_from is already within range
    effective_max = window_end if end_date is None else min(window_end, end_date)

    while current <= effective_max and len(occurrences) < limit:
        occurrences.append(current)
        current = calculate_next_occurrence(
            base_date=current,
            frequency=frequency,
            interval=interval,
            day_of_month=day_of_month,
            day_of_week=day_of_week,
            end_of_month_policy=end_of_month_policy,
        )

    return occurrences


# -------------------------------------------------------------------------
# Cost Normalization Mathematics
# -------------------------------------------------------------------------

def normalize_cost_to_monthly_and_annual(
    amount_paise: int,
    frequency: str,
    cycle_interval: int = 1,
) -> Tuple[int, int]:
    """
    Normalizes a recurring monetary amount (in paise) to estimated monthly and annual amounts.
    Returns: (monthly_paise, annual_paise)
    """
    if amount_paise <= 0:
        return 0, 0

    if cycle_interval < 1:
        cycle_interval = 1

    freq = frequency.lower()

    if freq == "daily":
        annual = amount_paise * 365 // cycle_interval
        monthly = math.ceil(annual / 12)
        return monthly, annual

    elif freq == "weekly":
        annual = amount_paise * 52 // cycle_interval
        monthly = math.ceil(annual / 12)
        return monthly, annual

    elif freq == "biweekly":
        annual = amount_paise * 26 // cycle_interval
        monthly = math.ceil(annual / 12)
        return monthly, annual

    elif freq == "monthly":
        monthly = math.ceil(amount_paise / cycle_interval)
        annual = math.ceil(amount_paise * 12 / cycle_interval)
        return monthly, annual

    elif freq == "quarterly":
        annual = math.ceil(amount_paise * 4 / cycle_interval)
        monthly = math.ceil(annual / 12)
        return monthly, annual

    elif freq == "semi_annual":
        annual = math.ceil(amount_paise * 2 / cycle_interval)
        monthly = math.ceil(annual / 12)
        return monthly, annual

    elif freq == "annual":
        annual = math.ceil(amount_paise / cycle_interval)
        monthly = math.ceil(annual / 12)
        return monthly, annual

    # Fallback to monthly assumption
    return amount_paise, amount_paise * 12


# -------------------------------------------------------------------------
# Occurrence State Derivation
# -------------------------------------------------------------------------

def evaluate_occurrence_state(
    expected_date: date,
    current_date: date,
    matched_transaction_id: Optional[uuid.UUID] = None,
    is_confirmed: bool = False,
    is_skipped: bool = False,
    is_cancelled: bool = False,
    existing_status: Optional[str] = None,
) -> OccurrenceStatus:
    """
    Evaluates the authoritative lifecycle state of an occurrence given current date and reconciliation flags.
    """
    if is_cancelled or existing_status == OccurrenceStatus.CANCELLED.value:
        return OccurrenceStatus.CANCELLED
    if is_skipped or existing_status == OccurrenceStatus.SKIPPED.value:
        return OccurrenceStatus.SKIPPED
    if is_confirmed or existing_status == OccurrenceStatus.CONFIRMED.value:
        return OccurrenceStatus.CONFIRMED
    if matched_transaction_id is not None or existing_status == OccurrenceStatus.MATCHED.value:
        return OccurrenceStatus.MATCHED

    if current_date > expected_date:
        return OccurrenceStatus.OVERDUE
    elif current_date == expected_date:
        return OccurrenceStatus.DUE
    elif expected_date - timedelta(days=3) <= current_date < expected_date:
        return OccurrenceStatus.UPCOMING
    else:
        return OccurrenceStatus.SCHEDULED


# -------------------------------------------------------------------------
# Transaction Matching Engine
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class MatchCandidateResult:
    is_match: bool
    confidence_score: Decimal
    match_tier: str  # exact, strong, ambiguous, none
    amount_variance_paise: int
    variance_percentage: Decimal
    date_difference_days: int
    reason: str


def calculate_transaction_match(
    expected_amount_paise: int,
    tx_amount_paise: int,
    expected_date: date,
    tx_date: date,
    expected_merchant_name: Optional[str] = None,
    tx_merchant_name: Optional[str] = None,
    expected_description: Optional[str] = None,
    tx_description: Optional[str] = None,
    is_variable_amount: bool = False,
    direction_match: bool = True,
    account_match: bool = True,
) -> MatchCandidateResult:
    """
    Calculates deterministic matching heuristics between an expected occurrence and an actual transaction.
    
    Tiers:
    - exact: exact amount + within 2 days + merchant match (score 0.95 - 1.00)
    - strong: amount within variance tolerance + within 5 days + merchant/desc match (score 0.75 - 0.94)
    - ambiguous: amount match but date gap (6-10 days) or merchant uncertain (score 0.50 - 0.74)
    - none: amount mismatch > tolerance or date gap > 10 days or direction mismatch (score < 0.50)
    """
    if not direction_match:
        return MatchCandidateResult(
            is_match=False,
            confidence_score=Decimal("0.00"),
            match_tier="none",
            amount_variance_paise=abs(tx_amount_paise - expected_amount_paise),
            variance_percentage=Decimal("100.00"),
            date_difference_days=abs((tx_date - expected_date).days),
            reason="Transaction direction mismatch",
        )

    date_diff = abs((tx_date - expected_date).days)
    if date_diff > 10:
        return MatchCandidateResult(
            is_match=False,
            confidence_score=Decimal("0.10"),
            match_tier="none",
            amount_variance_paise=abs(tx_amount_paise - expected_amount_paise),
            variance_percentage=Decimal("100.00"),
            date_difference_days=date_diff,
            reason=f"Date difference of {date_diff} days exceeds maximum matching window of 10 days",
        )

    amount_diff_paise = tx_amount_paise - expected_amount_paise
    abs_amount_diff = abs(amount_diff_paise)

    if expected_amount_paise > 0:
        variance_pct = Decimal(str(round((abs_amount_diff / expected_amount_paise) * 100, 2)))
    else:
        variance_pct = Decimal("0.00") if abs_amount_diff == 0 else Decimal("100.00")

    # Allowed variance threshold
    max_variance_pct = Decimal("30.00") if is_variable_amount else Decimal("5.00")

    if variance_pct > max_variance_pct and not is_variable_amount:
        return MatchCandidateResult(
            is_match=False,
            confidence_score=Decimal("0.20"),
            match_tier="none",
            amount_variance_paise=amount_diff_paise,
            variance_percentage=variance_pct,
            date_difference_days=date_diff,
            reason=f"Amount variance of {variance_pct}% exceeds allowed limit",
        )

    # Merchant / description similarity
    merchant_match = False
    if expected_merchant_name and tx_merchant_name:
        exp_clean = re.sub(r"[^a-zA-Z0-9]", "", expected_merchant_name.lower())
        tx_clean = re.sub(r"[^a-zA-Z0-9]", "", tx_merchant_name.lower())
        if exp_clean in tx_clean or tx_clean in exp_clean:
            merchant_match = True
    elif expected_description and tx_description:
        exp_words = set(re.findall(r"\w+", expected_description.lower()))
        tx_words = set(re.findall(r"\w+", tx_description.lower()))
        if exp_words and tx_words and len(exp_words.intersection(tx_words)) >= 1:
            merchant_match = True

    # Scoring formulation
    score = Decimal("1.00")

    # Deduct for date difference (0.05 per day)
    score -= Decimal(str(date_diff * 0.05))

    # Deduct for amount variance
    score -= (variance_pct / Decimal("100.00")) * Decimal("0.40")

    # Deduct if merchant not positively matched
    if not merchant_match and expected_merchant_name:
        score -= Decimal("0.25")

    # Bonus if account matched
    if account_match:
        score += Decimal("0.05")

    score = max(Decimal("0.00"), min(Decimal("1.00"), round(score, 2)))

    if score >= Decimal("0.85") and abs_amount_diff == 0 and date_diff <= 2:
        tier = "exact"
        is_match = True
        reason = "Exact amount, close date proximity, and verified merchant"
    elif score >= Decimal("0.70"):
        tier = "strong"
        is_match = True
        reason = f"Strong match with {date_diff} day(s) date gap and {variance_pct}% variance"
    elif score >= Decimal("0.50"):
        tier = "ambiguous"
        is_match = False
        reason = f"Ambiguous candidate: date gap {date_diff} days, requires explicit user confirmation"
    else:
        tier = "none"
        is_match = False
        reason = "Insufficient matching signals"

    return MatchCandidateResult(
        is_match=is_match,
        confidence_score=score,
        match_tier=tier,
        amount_variance_paise=amount_diff_paise,
        variance_percentage=variance_pct,
        date_difference_days=date_diff,
        reason=reason,
    )


# -------------------------------------------------------------------------
# Recurring Pattern Detection Engine
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class DetectedRecurringPattern:
    merchant_name: str
    normalized_description: str
    direction: str
    suggested_frequency: RecurringFrequency
    suggested_amount_paise: int
    min_amount_paise: int
    max_amount_paise: int
    confidence_score: Decimal
    evidence_count: int
    first_seen_date: date
    last_seen_date: date
    estimated_next_date: date
    evidence_summary: Dict[str, Any]


def detect_recurring_patterns_from_transactions(
    transactions: List[Dict[str, Any]],
    as_of_date: Optional[date] = None,
) -> List[DetectedRecurringPattern]:
    """
    Analyzes historical posted transactions and detects recurring pattern candidates.
    
    Algorithm:
    1. Clusters transactions by (direction, normalized_merchant_or_desc).
    2. Filters clusters with count < 2 (minimum repetition).
    3. Evaluates chronological intervals between consecutive transactions.
    4. Categorizes interval:
       - 6 to 8 days -> weekly
       - 12 to 16 days -> biweekly
       - 26 to 35 days -> monthly
       - 80 to 100 days -> quarterly
       - 350 to 380 days -> annual
    5. Calculates standard deviation of intervals and variance of amounts.
    6. Produces explainable confidence score.
    """
    if not transactions or len(transactions) < 2:
        return []

    evaluation_date = as_of_date or date.today()

    # Cluster transactions
    clusters: Dict[str, List[Dict[str, Any]]] = {}

    for tx in transactions:
        # Require posted status and valid date
        if tx.get("status") != "posted":
            continue

        raw_merchant = tx.get("merchant_name") or ""
        raw_desc = tx.get("description") or ""
        direction = tx.get("direction") or "outflow"

        # Normalized identifier
        key_name = raw_merchant.strip().lower() or raw_desc.strip().lower()
        if not key_name or len(key_name) < 3:
            continue

        # Clean noise characters
        clean_key = re.sub(r"[^a-z0-9]", "", key_name)
        if not clean_key:
            continue

        cluster_key = f"{direction}:{clean_key}"
        if cluster_key not in clusters:
            clusters[cluster_key] = []
        clusters[cluster_key].append(tx)

    detected: List[DetectedRecurringPattern] = []

    for cluster_key, items in clusters.items():
        if len(items) < 2:
            continue

        # Sort chronologically
        sorted_items = sorted(items, key=lambda x: x["transaction_date"])
        dates = [item["transaction_date"] for item in sorted_items]
        amounts = [item["amount_paise"] for item in sorted_items]

        # Calculate consecutive day intervals
        intervals: List[int] = []
        for i in range(1, len(dates)):
            diff = (dates[i] - dates[i - 1]).days
            if diff > 0:
                intervals.append(diff)

        if not intervals:
            continue

        avg_interval = sum(intervals) / len(intervals)

        # Classify candidate frequency
        candidate_freq: Optional[RecurringFrequency] = None
        if 5 <= avg_interval <= 9:
            candidate_freq = RecurringFrequency.WEEKLY
            expected_cycle = 7
        elif 12 <= avg_interval <= 16:
            candidate_freq = RecurringFrequency.BIWEEKLY
            expected_cycle = 14
        elif 25 <= avg_interval <= 35:
            candidate_freq = RecurringFrequency.MONTHLY
            expected_cycle = 30
        elif 80 <= avg_interval <= 100:
            candidate_freq = RecurringFrequency.QUARTERLY
            expected_cycle = 91
        elif 340 <= avg_interval <= 380:
            candidate_freq = RecurringFrequency.ANNUAL
            expected_cycle = 365
        else:
            # Irregular interval that doesn't fit standard recurring cycle
            continue

        # Interval standard deviation
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = math.sqrt(variance)

        # Amount metrics
        min_amt = min(amounts)
        max_amt = max(amounts)
        avg_amt = sum(amounts) // len(amounts)
        amt_variance = sum((a - avg_amt) ** 2 for a in amounts) / len(amounts)
        amt_std_dev = math.sqrt(amt_variance)

        # Confidence Calculation
        # Base confidence from repetition count
        count = len(sorted_items)
        conf = Decimal("0.50")
        if count >= 3:
            conf += Decimal("0.15")
        if count >= 5:
            conf += Decimal("0.10")

        # Penalty for interval jitter
        jitter_ratio = std_dev / expected_cycle
        if jitter_ratio <= 0.10:
            conf += Decimal("0.15")
        elif jitter_ratio <= 0.20:
            conf += Decimal("0.05")
        else:
            conf -= Decimal("0.15")

        # Penalty for amount variance (if fixed subscription vs variable utility)
        if avg_amt > 0:
            amt_cv = amt_std_dev / avg_amt
            if amt_cv <= 0.05:
                conf += Decimal("0.10")  # Exact fixed subscription
            elif amt_cv > 0.35:
                conf -= Decimal("0.10")  # High variance

        conf = max(Decimal("0.50"), min(Decimal("0.98"), round(conf, 2)))

        first_seen = dates[0]
        last_seen = dates[-1]

        # Estimate next date
        next_date = calculate_next_occurrence(
            base_date=last_seen,
            frequency=candidate_freq,
            day_of_month=last_seen.day,
        )
        if next_date < evaluation_date:
            # Advance until in future
            while next_date < evaluation_date:
                next_date = calculate_next_occurrence(
                    base_date=next_date,
                    frequency=candidate_freq,
                    day_of_month=last_seen.day,
                )

        rep_item = sorted_items[-1]
        merchant_name = rep_item.get("merchant_name") or rep_item.get("description") or "Unknown Merchant"
        direction = cluster_key.split(":")[0]

        evidence_summary = {
            "count": count,
            "average_interval_days": round(avg_interval, 1),
            "interval_std_dev": round(std_dev, 2),
            "amounts_paise": amounts,
            "dates": [d.isoformat() for d in dates],
            "is_fixed_amount": amt_std_dev == 0,
        }

        detected.append(
            DetectedRecurringPattern(
                merchant_name=merchant_name,
                normalized_description=rep_item.get("description") or merchant_name,
                direction=direction,
                suggested_frequency=candidate_freq,
                suggested_amount_paise=avg_amt,
                min_amount_paise=min_amt,
                max_amount_paise=max_amt,
                confidence_score=conf,
                evidence_count=count,
                first_seen_date=first_seen,
                last_seen_date=last_seen,
                estimated_next_date=next_date,
                evidence_summary=evidence_summary,
            )
        )

    # Sort descending by confidence score and evidence count
    return sorted(detected, key=lambda x: (x.confidence_score, x.evidence_count), reverse=True)
