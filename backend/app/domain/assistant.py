"""
Arthsavora AI Financial Assistant Domain Models & Intent Understanding
Pure functional domain logic for intent classification, date range parsing,
monetary extraction, prompt injection defense, and financial safety verification.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid


class FinancialIntentEnum(str, Enum):
    """Categorized domain intents for financial queries and assistant workflows."""
    OVERVIEW = "financial_overview"
    INCOME = "income_summary"
    EXPENSE = "expense_summary"
    CASH_FLOW = "cash_flow_analysis"
    CATEGORY = "category_analysis"
    MERCHANT = "merchant_analysis"
    TRANSACTIONS = "transaction_search"
    ACCOUNT = "account_balances"
    BUDGET = "budget_status"
    GOAL = "goal_progress"
    RECURRING = "recurring_commitments"
    SUBSCRIPTIONS = "subscription_summary"
    FORECAST = "forecast_interpretation"
    ANOMALY = "anomaly_explanation"
    EDUCATION = "financial_education"
    HELP = "general_help"

    # Action Intents (Proposed as drafts requiring human confirmation)
    ACTION_BUDGET = "action_create_budget"
    ACTION_GOAL = "action_create_goal"
    ACTION_RECURRING = "action_create_recurring"
    ACTION_FILTER = "action_prepare_filter"

    UNKNOWN = "unknown_intent"


class DataSensitivityEnum(str, Enum):
    """Classification of data exposed by financial tools."""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED_FINANCIAL = "restricted_financial"
    CONFIDENTIAL = "confidential"


class ActionDraftStatus(str, Enum):
    """Lifecycle state of an assistant action draft."""
    PENDING = "pending_confirmation"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass(frozen=True)
class DateRangeVO:
    """Immutable date window with human-readable period label."""
    start_date: date
    end_date: date
    label: str


@dataclass(frozen=True)
class IntentResultVO:
    """Structured extraction of user intent and extracted financial parameters."""
    intent: FinancialIntentEnum
    confidence: float
    date_range: Optional[DateRangeVO] = None
    category_name: Optional[str] = None
    merchant_name: Optional[str] = None
    amount_paise: Optional[int] = None
    currency: str = "INR"
    is_action: bool = False
    action_type: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None


@dataclass(frozen=True)
class FinancialToolDefinitionVO:
    """Metadata contract and authorization schema for an assistant tool."""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    required_permission: str
    sensitivity: DataSensitivityEnum = DataSensitivityEnum.RESTRICTED_FINANCIAL
    timeout_seconds: int = 15


@dataclass(frozen=True)
class ToolCallVO:
    """Individual tool call requested by the assistant orchestration layer."""
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class ToolResultVO:
    """Validated output or error produced by executing a financial service tool."""
    call_id: str
    tool_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass(frozen=True)
class ModelCapabilities:
    """Declared and verified capabilities of an LLM provider."""
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_structured_output: bool = True
    max_context_tokens: int = 8192


# -----------------------------------------------------------------------------
# 1. Deterministic Natural-Language Date Parsing
# -----------------------------------------------------------------------------

def parse_financial_date_range(text: str, as_of_date: Optional[date] = None) -> DateRangeVO:
    """
    Parses natural English date expressions into precise financial boundaries [start_date, end_date].
    Uses the user's reference date (defaulting to current date) with zero external dependencies.
    """
    ref = as_of_date or date.today()
    q = text.lower()

    # 1. Today & Yesterday
    if "today" in q:
        return DateRangeVO(ref, ref, "Today")
    if "yesterday" in q:
        yest = ref - timedelta(days=1)
        return DateRangeVO(yest, yest, "Yesterday")

    # 2. Last N Days
    match_days = re.search(r"last\s+(\d+)\s+days?", q)
    if match_days:
        n = int(match_days.group(1))
        return DateRangeVO(ref - timedelta(days=n), ref, f"Last {n} Days")

    # 3. This / Current Week
    if "this week" in q or "current week" in q:
        start = ref - timedelta(days=ref.weekday())
        end = start + timedelta(days=6)
        return DateRangeVO(start, end, "This Week")

    # 4. Last / Previous Week
    if "last week" in q or "previous week" in q:
        end = ref - timedelta(days=ref.weekday() + 1)
        start = end - timedelta(days=6)
        return DateRangeVO(start, end, "Last Week")

    # 5. This / Current Month
    if "this month" in q or "current month" in q:
        start = ref.replace(day=1)
        # Next month start - 1 day
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
        return DateRangeVO(start, end, f"{ref.strftime('%B %Y')}")

    # 6. Last / Previous Month
    if "last month" in q or "previous month" in q:
        first_current = ref.replace(day=1)
        end = first_current - timedelta(days=1)
        start = end.replace(day=1)
        return DateRangeVO(start, end, f"{start.strftime('%B %Y')}")

    # 7. Named Month Check (e.g., "in october", "for august 2026")
    month_names = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    for m_name, m_num in month_names.items():
        pattern = rf"\b{m_name}\b(?:\s+(\d{{4}}))?"
        m_match = re.search(pattern, q)
        if m_match:
            year = int(m_match.group(1)) if m_match.group(1) else ref.year
            start = date(year, m_num, 1)
            next_m = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_m - timedelta(days=1)
            return DateRangeVO(start, end, f"{start.strftime('%B %Y')}")

    # 8. This Year / Financial Year
    if "this year" in q or "current year" in q:
        start = date(ref.year, 1, 1)
        end = date(ref.year, 12, 31)
        return DateRangeVO(start, end, f"Year {ref.year}")

    # 9. Last Year
    if "last year" in q or "previous year" in q:
        prev_yr = ref.year - 1
        return DateRangeVO(date(prev_yr, 1, 1), date(prev_yr, 12, 31), f"Year {prev_yr}")

    # Default fallback: Current calendar month
    start = ref.replace(day=1)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)
    return DateRangeVO(start, end, f"{ref.strftime('%B %Y')}")


# -----------------------------------------------------------------------------
# 2. Monetary & Currency Parsing
# -----------------------------------------------------------------------------

def parse_currency_and_amount(text: str) -> Tuple[str, Optional[int]]:
    """
    Extracts currency code and monetary integer minor units (paise).
    Handles ₹, Rs, Rs., INR, USD, $, EUR, and multipliers like 'k', 'lakh', 'cr'.
    """
    currency = "INR"
    if "$" in text or "usd" in text.lower():
        currency = "USD"
    elif "€" in text or "eur" in text.lower():
        currency = "EUR"
    elif "£" in text or "gbp" in text.lower():
        currency = "GBP"

    # Regex for currency prefixes and numbers
    # Matches: ₹5000, ₹ 5,000, 50k, 1.5 lakh, 5000 rs
    clean = text.replace(",", "")

    # Lakh / Crore
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac)s?", clean, re.IGNORECASE)
    if lakh_match:
        val = float(lakh_match.group(1)) * 100000.0
        return currency, int(round(val * 100))

    cr_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crore|cr)s?", clean, re.IGNORECASE)
    if cr_match:
        val = float(cr_match.group(1)) * 10000000.0
        return currency, int(round(val * 100))

    k_match = re.search(r"(\d+(?:\.\d+)?)\s*k\b", clean, re.IGNORECASE)
    if k_match:
        val = float(k_match.group(1)) * 1000.0
        return currency, int(round(val * 100))

    num_match = re.search(r"(?:₹|rs\.?|\$|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees|paise)?", clean, re.IGNORECASE)
    if num_match:
        val = float(num_match.group(1))
        # If explicitly paise
        if "paise" in text.lower():
            return currency, int(round(val))
        return currency, int(round(val * 100))

    return currency, None


# -----------------------------------------------------------------------------
# 3. Intent Detection & Classification
# -----------------------------------------------------------------------------

COMMON_CATEGORIES = [
    "food", "dining", "groceries", "restaurant", "shopping", "utilities",
    "rent", "travel", "transport", "entertainment", "health", "medical",
    "education", "bills", "personal", "investment", "salary",
]


def detect_financial_intent(query: str, as_of_date: Optional[date] = None) -> IntentResultVO:
    """
    Deterministic natural language intent classifier for financial operations.
    Extracts structured intent, temporal ranges, category filters, and action payloads.
    """
    q = query.lower().strip()
    ref_date = as_of_date or date.today()
    date_range = parse_financial_date_range(query, ref_date)
    curr, amt_paise = parse_currency_and_amount(query)

    # Detect mentioned category
    cat_match = None
    for c in COMMON_CATEGORIES:
        if re.search(rf"\b{c}\b", q):
            cat_match = c.capitalize()
            break

    # 1. Action Intents (Draft creation requesting confirmation)
    if re.search(r"\b(create|set up|set|add)\b.*\b(budget)\b", q):
        return IntentResultVO(
            intent=FinancialIntentEnum.ACTION_BUDGET,
            confidence=0.95,
            is_action=True,
            action_type="create_budget_draft",
            amount_paise=amt_paise or 1000000,  # ₹10,000 default if omitted
            category_name=cat_match or "General",
            currency=curr,
            parameters={
                "name": f"{cat_match or 'Monthly'} Budget",
                "period": "monthly",
                "limit_paise": amt_paise or 1000000,
                "category_name": cat_match,
                "currency": curr,
            },
        )

    if re.search(r"\b(create|set up|set|add)\b.*\b(goal|saving goal)\b", q):
        return IntentResultVO(
            intent=FinancialIntentEnum.ACTION_GOAL,
            confidence=0.95,
            is_action=True,
            action_type="create_goal_draft",
            amount_paise=amt_paise or 5000000,  # ₹50,000 default
            currency=curr,
            parameters={
                "name": "Financial Savings Goal",
                "target_amount_paise": amt_paise or 5000000,
                "currency": curr,
                "target_date": (ref_date + timedelta(days=180)).isoformat(),
            },
        )

    if re.search(r"\b(create|add|schedule|set|set up)\b.*\b(recurring|subscription)\b", q):
        return IntentResultVO(
            intent=FinancialIntentEnum.ACTION_RECURRING,
            confidence=0.95,
            is_action=True,
            action_type="create_recurring_draft",
            amount_paise=amt_paise or 99900,  # ₹999 default
            currency=curr,
            parameters={
                "name": "Scheduled Subscription",
                "expected_amount_paise": amt_paise or 99900,
                "frequency": "monthly",
                "currency": curr,
            },
        )

    # 2. Informational & Analytical Read-Only Intents

    # Cash Flow
    if any(k in q for k in ["cash flow", "cashflow", "net flow", "inflow and outflow", "money in and out"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.CASH_FLOW,
            confidence=0.92,
            date_range=date_range,
            currency=curr,
        )

    # Forecast / Predictions
    if any(k in q for k in ["forecast", "projected", "predict", "next month spend", "future cash flow", "future income", "run out of money"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.FORECAST,
            confidence=0.90,
            date_range=date_range,
            currency=curr,
        )

    # Anomaly / Unusual Activity / Fraud Signals
    if any(k in q for k in ["unusual", "anomaly", "anomalies", "suspicious", "strange charge", "why was this flagged", "risk"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.ANOMALY,
            confidence=0.92,
            date_range=date_range,
            currency=curr,
        )

    # Subscriptions
    if any(k in q for k in ["subscription", "subscriptions", "recurring payment", "recurring charge", "active plan"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.SUBSCRIPTIONS,
            confidence=0.94,
            date_range=date_range,
            currency=curr,
        )

    # Recurring / Upcoming Commitments / Due Bills
    if any(k in q for k in ["due this week", "upcoming bill", "upcoming payment", "commitment", "bills due", "emi due", "rent due"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.RECURRING,
            confidence=0.94,
            date_range=date_range,
            currency=curr,
        )

    # Budget Status
    if any(k in q for k in ["budget", "budget status", "exceed budget", "over budget", "remaining budget", "budget limit"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.BUDGET,
            confidence=0.93,
            date_range=date_range,
            category_name=cat_match,
            currency=curr,
        )

    # Goal Progress
    if any(k in q for k in ["goal", "goals", "reach my goal", "saving target", "save monthly"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.GOAL,
            confidence=0.93,
            date_range=date_range,
            currency=curr,
        )

    # Account Balances
    if any(k in q for k in ["balance", "balances", "how much money do i have", "account balance", "bank balance"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.ACCOUNT,
            confidence=0.95,
            date_range=date_range,
            currency=curr,
        )

    # Income Summary
    if any(k in q for k in ["income", "earned", "salary", "how much did i make", "revenue", "inflow"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.INCOME,
            confidence=0.92,
            date_range=date_range,
            currency=curr,
        )

    # Category Spending (e.g., "How much did I spend on food?")
    if cat_match and any(k in q for k in ["spend", "spent", "where is my money going", "breakdown", "category"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.CATEGORY,
            confidence=0.95,
            date_range=date_range,
            category_name=cat_match,
            currency=curr,
        )

    # Merchant Spending (e.g., "spending at Swiggy", "transactions at Amazon", "merchant Uber")
    if "merchant" in q or (" at " in q and any(k in q for k in ["spend", "spent", "spending", "paid", "transactions", "show"])):
        m = re.search(r"\b(?:at|with|to)\s+([A-Za-z0-9_-]+)", q)
        merchant_name = m.group(1).capitalize() if m else None
        return IntentResultVO(
            intent=FinancialIntentEnum.MERCHANT,
            confidence=0.93,
            date_range=date_range,
            merchant_name=merchant_name,
            currency=curr,
        )

    # General Expense Summary / "Where did my money go?"
    if any(k in q for k in ["expense", "expenses", "spend", "spent", "where did my money go", "where is most of my money going", "spending"]):
        # Check if comparing two periods
        if "compare" in q or "versus" in q or "vs" in q:
            return IntentResultVO(
                intent=FinancialIntentEnum.EXPENSE,
                confidence=0.90,
                date_range=date_range,
                currency=curr,
                parameters={"comparison": True},
            )
        return IntentResultVO(
            intent=FinancialIntentEnum.EXPENSE,
            confidence=0.94,
            date_range=date_range,
            category_name=cat_match,
            currency=curr,
        )

    # Search Transactions
    if any(k in q for k in ["transaction", "transactions", "show payments", "recent payments", "search", "payments above"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.TRANSACTIONS,
            confidence=0.91,
            date_range=date_range,
            amount_paise=amt_paise,
            category_name=cat_match,
            currency=curr,
        )

    # Overall Financial Summary / Overview
    if any(k in q for k in ["overview", "summary", "financial health", "how am i doing", "financial snapshot", "report"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.OVERVIEW,
            confidence=0.90,
            date_range=date_range,
            currency=curr,
        )

    # Help / Capabilities
    if any(k in q for k in ["help", "what can you do", "features", "commands", "who are you"]):
        return IntentResultVO(
            intent=FinancialIntentEnum.HELP,
            confidence=0.95,
            currency=curr,
        )

    # Default Fallback: Financial Overview
    return IntentResultVO(
        intent=FinancialIntentEnum.OVERVIEW,
        confidence=0.60,
        date_range=date_range,
        currency=curr,
    )


# -----------------------------------------------------------------------------
# 4. Prompt Injection Defense & Sanitization
# -----------------------------------------------------------------------------

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"<\s*/\s*system\s*>", re.IGNORECASE),
    re.compile(r"reveal\s+(?:your\s+)?(?:system\s+)?prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+dan", re.IGNORECASE),
    re.compile(r"bypass\s+(?:security|permission|authorization)", re.IGNORECASE),
    re.compile(r"grant\s+(?:all\s+)?permissions?", re.IGNORECASE),
    re.compile(r"drop\s+table", re.IGNORECASE),
    re.compile(r"select\s+\*\s+from", re.IGNORECASE),
]


def sanitize_and_detect_prompt_injection(user_input: str) -> Tuple[str, bool, Optional[str]]:
    """
    Scans incoming user input for adversarial injection strings or system prompt manipulation.
    Returns: (sanitized_input, was_injection_detected, reason)
    """
    for pat in INJECTION_PATTERNS:
        if pat.search(user_input):
            return (
                "Show my financial summary for this month.",  # Safe sanitized fallback
                True,
                "Adversarial instruction or system delimiter detected. Request neutralized.",
            )

    # Clean XML-style delimiters to prevent structure confusion
    cleaned = (
        user_input.replace("<system>", "")
        .replace("</system>", "")
        .replace("<assistant>", "")
        .replace("</assistant>", "")
        .replace("<tool>", "")
        .replace("</tool>", "")
        .strip()
    )
    return cleaned, False, None


# -----------------------------------------------------------------------------
# 5. Financial Safety Policy & Disclaimer Injection
# -----------------------------------------------------------------------------

def apply_financial_safety_policy(response_text: str, intent: FinancialIntentEnum) -> str:
    """
    Enforces regulatory compliance and non-speculative guidelines.
    Adds concise, contextual disclaimers to forward-looking forecasts or advice queries.
    """
    text = response_text.strip()

    # Forecasts: Add informational uncertainty notice if not already present
    if intent == FinancialIntentEnum.FORECAST:
        disclaimer = "\n\n> *Note: Projections are model-based statistical estimates based on historical activity and scheduled commitments, not guaranteed financial outcomes.*"
        if "not guaranteed" not in text.lower():
            text += disclaimer

    # Anomaly / Risk: Ensure neutral tone
    elif intent == FinancialIntentEnum.ANOMALY:
        neutral_reminder = "\n\n> *Reminder: An anomaly indicates an unusual statistical deviation, not confirmed fraud. Legitimate one-off expenses frequently deviate from baseline patterns.*"
        if "not confirmed fraud" not in text.lower() and "unusual statistical deviation" not in text.lower():
            text += neutral_reminder

    return text
