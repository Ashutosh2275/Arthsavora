"""
Arthsavora Unified Notifications & Financial Alerts Domain Model
Pure functional domain contracts, event catalog, deduplication keys, and quiet-hour rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
import zoneinfo


class NotificationCategory(str, Enum):
    """Broad functional grouping of notifications."""
    TRANSACTION = "transaction"
    BUDGET = "budget"
    GOAL = "goal"
    RECURRING = "recurring"
    FORECAST = "forecast"
    ANOMALY = "anomaly"
    DOCUMENT = "document"
    ASSISTANT = "assistant"
    SECURITY = "security"
    SYSTEM = "system"


class NotificationSeverity(str, Enum):
    """Urgency / visual weighting of the alert."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Delivery mechanisms supported across ARTHSAVORA."""
    IN_APP = "in_app"
    EMAIL = "email"
    WEB_PUSH = "web_push"
    MOBILE_PUSH = "mobile_push"


class DeliveryStatus(str, Enum):
    """Lifecycle states of an outbound channel delivery."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCELLED = "cancelled"


class NotificationEventType(str, Enum):
    """Granular event types across the FinTech ecosystem."""
    # Transactions
    TRANSACTION_RECORDED = "transaction.recorded"
    TRANSACTION_IMPORTED = "transaction.imported"
    TRANSACTION_CONFIRMED = "transaction.confirmed"
    TRANSACTION_REVERSED = "transaction.reversed"
    TRANSACTION_REVIEW_REQUIRED = "transaction.review_required"

    # Budgets
    BUDGET_APPROACHING = "budget.approaching"
    BUDGET_THRESHOLD_REACHED = "budget.threshold_reached"
    BUDGET_EXCEEDED = "budget.exceeded"
    CATEGORY_OVERSPENDING = "budget.category_overspending"

    # Goals
    GOAL_CONTRIBUTION = "goal.contribution"
    GOAL_MILESTONE = "goal.milestone"
    GOAL_NEARING_TARGET = "goal.nearing_target"
    GOAL_COMPLETED = "goal.completed"

    # Recurring Finance
    UPCOMING_PAYMENT = "recurring.upcoming_payment"
    PAYMENT_DUE = "recurring.payment_due"
    PAYMENT_OVERDUE = "recurring.payment_overdue"
    UPCOMING_SALARY = "recurring.upcoming_salary"
    SUBSCRIPTION_RENEWAL = "recurring.subscription_renewal"
    TRIAL_ENDING = "recurring.trial_ending"
    SUBSCRIPTION_CANCELLED = "recurring.subscription_cancelled"

    # Forecasting & Predictive Intelligence (Always explicitly labeled as estimates)
    FORECAST_BUDGET_EXHAUSTION = "forecast.budget_exhaustion"
    FORECAST_CASHFLOW_CHANGE = "forecast.cashflow_change"
    FORECAST_LOW_BALANCE = "forecast.low_balance"

    # Anomaly & Risk (Always non-alarmist, never labeled as confirmed fraud)
    ANOMALY_UNUSUAL_TRANSACTION = "anomaly.unusual_transaction"
    ANOMALY_SPENDING_PATTERN = "anomaly.spending_pattern"
    ANOMALY_UNEXPECTED_RECURRING = "anomaly.unexpected_recurring"
    ANOMALY_BALANCE_DISCREPANCY = "anomaly.balance_discrepancy"

    # Document & Receipt Intelligence
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_REVIEW_REQUIRED = "document.review_required"
    DOCUMENT_FAILED = "document.failed"
    DOCUMENT_MATCHED = "document.matched"

    # AI Assistant
    ASSISTANT_TASK_COMPLETED = "assistant.task_completed"
    ASSISTANT_ACTION_COMPLETED = "assistant.action_completed"
    ASSISTANT_ACTION_ATTENTION = "assistant.action_attention"

    # Security & Authentication (Never expose secrets or tokens)
    SECURITY_NEW_LOGIN = "security.new_login"
    SECURITY_PASSWORD_CHANGED = "security.password_changed"
    SECURITY_AUTH_EVENT = "security.auth_event"


# Severity order for comparison
SEVERITY_WEIGHTS: Dict[NotificationSeverity, int] = {
    NotificationSeverity.INFO: 1,
    NotificationSeverity.SUCCESS: 2,
    NotificationSeverity.WARNING: 3,
    NotificationSeverity.CRITICAL: 4,
}


@dataclass(frozen=True)
class NotificationPayloadVO:
    """Immutable domain event payload triggering a notification."""
    recipient_user_id: UUID
    category: NotificationCategory
    event_type: NotificationEventType
    title: str
    message: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    workspace_id: Optional[UUID] = None
    related_resource_type: Optional[str] = None
    related_resource_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_timestamp: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    deduplication_key: Optional[str] = None


def generate_deduplication_key(
    recipient_user_id: UUID,
    event_type: NotificationEventType,
    resource_id: Optional[str] = None,
    period_token: Optional[str] = None,
) -> str:
    """
    Builds a deterministic deduplication key to eliminate duplicate notification spam.
    Example: 'notif_dedup:user_id:budget.threshold_reached:bg-123:2026-11'
    """
    elements = [
        str(recipient_user_id),
        event_type.value,
        str(resource_id or "global"),
        str(period_token or "instant"),
    ]
    raw = ":".join(elements)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"dedup:{event_type.value}:{digest}"


def is_in_quiet_hours(
    now_utc: datetime,
    tz_name: str,
    quiet_start_str: str,
    quiet_end_str: str,
) -> bool:
    """
    Evaluates whether `now_utc` falls inside the user's localized quiet-hours window.
    Handles midnight-crossing windows (e.g. 22:00 to 07:00).
    """
    try:
        user_tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        user_tz = zoneinfo.ZoneInfo("Asia/Kolkata")

    user_local_dt = now_utc.astimezone(user_tz)
    current_time = user_local_dt.time()

    # Parse HH:MM
    try:
        sh, sm = map(int, quiet_start_str.split(":", 1))
        eh, em = map(int, quiet_end_str.split(":", 1))
        start_t = time(hour=sh, minute=sm)
        end_t = time(hour=eh, minute=em)
    except Exception:
        return False

    if start_t <= end_t:
        # Standard daytime or non-midnight window, e.g. 13:00 to 14:00
        return start_t <= current_time < end_t
    else:
        # Midnight-crossing window, e.g. 22:00 to 07:00
        return current_time >= start_t or current_time < end_t


def mask_sensitive_financial_payload(text: str) -> str:
    """
    Defensive regex scrubber preventing sensitive payment credentials, CVV,
    or full PANs from leaking into outbound notifications or push previews.
    """
    if not text:
        return text

    # Mask 16-digit card patterns -> **** **** **** 1234
    text = re.sub(r"\b([0-9]{4})[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})\b", r"**** **** **** \4", text)

    # Mask CVV mentions
    text = re.sub(r"\bCVV[\s\:\=]*[0-9]{3,4}\b", "CVV: ***", text, flags=re.IGNORECASE)

    # Mask OTP / PIN
    text = re.sub(r"\b(OTP|PIN|MPIN)[\s\:\=]*[0-9]{4,6}\b", r"\1: ******", text, flags=re.IGNORECASE)

    return text
