"""
Arthsavora Transaction Types & Lifecycle Domain Enums
Authoritative domain classifications, directions, sources, and state machine transitions.
"""

from enum import Enum
from typing import Dict, Set
from app.domain.exceptions import BusinessRuleViolationError


class TransactionType(str, Enum):
    # General transactions
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    REFUND = "refund"
    REVERSAL = "reversal"
    ADJUSTMENT = "adjustment"

    # Banking transactions
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    INTEREST = "interest"
    BANK_FEE = "bank_fee"
    TAX = "tax"

    # Credit transactions
    CREDIT_CARD_PURCHASE = "credit_card_purchase"
    CREDIT_CARD_PAYMENT = "credit_card_payment"
    CREDIT_CARD_REFUND = "credit_card_refund"
    CREDIT_CARD_FEE = "credit_card_fee"
    CREDIT_CARD_INTEREST = "credit_card_interest"

    # Loan transactions
    LOAN_DISBURSAL = "loan_disbursal"
    LOAN_PRINCIPAL_REPAYMENT = "loan_principal_repayment"
    LOAN_INTEREST_PAYMENT = "loan_interest_payment"
    LOAN_FEE = "loan_fee"

    # Investment transactions
    INVESTMENT_CONTRIBUTION = "investment_contribution"
    INVESTMENT_WITHDRAWAL = "investment_withdrawal"
    DIVIDEND = "dividend"
    INTEREST_INCOME = "interest_income"
    INVESTMENT_FEE = "investment_fee"

    # Other
    CASH_TRANSACTION = "cash_transaction"
    UNKNOWN = "unknown"


class TransactionDirection(str, Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    NEUTRAL = "neutral"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVERSED = "reversed"


class TransactionSourceType(str, Enum):
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    PDF_IMPORT = "pdf_import"
    BANK_FEED = "bank_feed"
    ACCOUNT_AGGREGATOR = "account_aggregator"
    CREDIT_CARD_STATEMENT = "credit_card_statement"
    OCR = "ocr"
    INTERNAL_ADJUSTMENT = "internal_adjustment"
    SYSTEM = "system"


# Canonical mapping from TransactionType to default TransactionDirection
DEFAULT_TYPE_DIRECTIONS: Dict[str, TransactionDirection] = {
    # Inflow (adds funds to asset account, or disburses loan capital)
    TransactionType.INCOME.value: TransactionDirection.INFLOW,
    TransactionType.DEPOSIT.value: TransactionDirection.INFLOW,
    TransactionType.DIVIDEND.value: TransactionDirection.INFLOW,
    TransactionType.INTEREST_INCOME.value: TransactionDirection.INFLOW,
    TransactionType.REFUND.value: TransactionDirection.INFLOW,
    TransactionType.CREDIT_CARD_REFUND.value: TransactionDirection.INFLOW,
    TransactionType.LOAN_DISBURSAL.value: TransactionDirection.INFLOW,
    TransactionType.INVESTMENT_WITHDRAWAL.value: TransactionDirection.INFLOW,

    # Outflow (removes funds from asset account, or increases credit card debt / repays loan)
    TransactionType.EXPENSE.value: TransactionDirection.OUTFLOW,
    TransactionType.WITHDRAWAL.value: TransactionDirection.OUTFLOW,
    TransactionType.BANK_FEE.value: TransactionDirection.OUTFLOW,
    TransactionType.TAX.value: TransactionDirection.OUTFLOW,
    TransactionType.CREDIT_CARD_PURCHASE.value: TransactionDirection.OUTFLOW,
    TransactionType.CREDIT_CARD_PAYMENT.value: TransactionDirection.OUTFLOW,
    TransactionType.CREDIT_CARD_FEE.value: TransactionDirection.OUTFLOW,
    TransactionType.CREDIT_CARD_INTEREST.value: TransactionDirection.OUTFLOW,
    TransactionType.LOAN_PRINCIPAL_REPAYMENT.value: TransactionDirection.OUTFLOW,
    TransactionType.LOAN_INTEREST_PAYMENT.value: TransactionDirection.OUTFLOW,
    TransactionType.LOAN_FEE.value: TransactionDirection.OUTFLOW,
    TransactionType.INVESTMENT_CONTRIBUTION.value: TransactionDirection.OUTFLOW,
    TransactionType.INVESTMENT_FEE.value: TransactionDirection.OUTFLOW,
    TransactionType.CASH_TRANSACTION.value: TransactionDirection.OUTFLOW,

    # Neutral (paired transfers, symmetric adjustments)
    TransactionType.TRANSFER.value: TransactionDirection.NEUTRAL,
    TransactionType.ADJUSTMENT.value: TransactionDirection.NEUTRAL,
    TransactionType.REVERSAL.value: TransactionDirection.NEUTRAL,
    TransactionType.UNKNOWN.value: TransactionDirection.NEUTRAL,
}


def resolve_transaction_direction(
    transaction_type: str,
    explicit_direction: str | None = None,
) -> str:
    """
    Resolves the canonical transaction direction.
    If explicitly provided, validates consistency with transaction type.
    """
    clean_type = transaction_type.lower().strip()
    if explicit_direction:
        clean_dir = explicit_direction.lower().strip()
        if clean_dir not in [d.value for d in TransactionDirection]:
            raise BusinessRuleViolationError(
                rule_name="INVALID_TRANSACTION_DIRECTION",
                message=f"Invalid transaction direction '{clean_dir}'. Allowed: inflow, outflow, neutral.",
            )
        return clean_dir

    default_dir = DEFAULT_TYPE_DIRECTIONS.get(clean_type, TransactionDirection.NEUTRAL)
    return default_dir.value


# Deterministic state machine transition matrix
VALID_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    # Pending can be posted, cancelled, or failed
    TransactionStatus.PENDING.value: {
        TransactionStatus.POSTED.value,
        TransactionStatus.CANCELLED.value,
        TransactionStatus.FAILED.value,
    },
    # Posted can only be reversed via formal reversal mechanism
    TransactionStatus.POSTED.value: {
        TransactionStatus.REVERSED.value,
    },
    # Terminal states
    TransactionStatus.CANCELLED.value: set(),
    TransactionStatus.FAILED.value: {TransactionStatus.CANCELLED.value},
    TransactionStatus.REVERSED.value: set(),
}


def validate_transaction_lifecycle_transition(current_status: str, target_status: str) -> None:
    """
    Enforces the financial transaction lifecycle state machine.
    Prevents silent overwrites, reposting of cancelled items, or arbitrary transitions.
    """
    curr = current_status.lower().strip()
    target = target_status.lower().strip()

    if curr == target:
        return

    allowed = VALID_STATUS_TRANSITIONS.get(curr, set())
    if target not in allowed:
        raise BusinessRuleViolationError(
            rule_name="INVALID_STATUS_TRANSITION",
            message=f"Cannot transition transaction from '{curr}' to '{target}'. Allowed transitions: {', '.join(sorted(allowed)) if allowed else 'None (terminal state)'}.",
        )
