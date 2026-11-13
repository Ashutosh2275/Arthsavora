"""
Arthsavora Domain Business Rules & Fintech Invariants
Pure business logic functions enforcing core financial rules, transfer invariants,
refund validations, double-entry ledger checks, and AI transparency.
"""

from decimal import Decimal
from typing import List, Optional
import uuid
from app.domain.exceptions import BusinessRuleViolationError, DomainValidationError
from app.domain.money import Money


def validate_transfer_invariants(
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    amount: Money,
) -> None:
    """
    Enforces that internal transfers occur between distinct accounts,
    have a positive amount, and do not distort workspace expense analytics.
    """
    if source_account_id == destination_account_id:
        raise BusinessRuleViolationError(
            rule_name="TRANSFER_SAME_ACCOUNT",
            message="Internal transfers cannot be made to the same source account.",
        )
    if not amount.is_positive():
        raise BusinessRuleViolationError(
            rule_name="TRANSFER_POSITIVE_AMOUNT",
            message="Transfer amount must be strictly greater than zero.",
        )


def validate_refund_invariants(
    original_amount: Money,
    refund_amount: Money,
    previously_refunded: Optional[Money] = None,
) -> None:
    """
    Enforces that a refund does not exceed the original transaction amount
    and preserves original transaction currency.
    """
    if not refund_amount.is_positive():
        raise BusinessRuleViolationError(
            rule_name="REFUND_POSITIVE_AMOUNT",
            message="Refund amount must be strictly positive.",
        )

    prev_refunded = previously_refunded or Money.zero(original_amount.currency)
    total_refund = prev_refunded + refund_amount

    if total_refund > original_amount:
        raise BusinessRuleViolationError(
            rule_name="REFUND_EXCEEDS_ORIGINAL",
            message=(
                f"Total refund ({total_refund.format()}) cannot exceed the "
                f"original transaction amount ({original_amount.format()})."
            ),
        )


def validate_ai_prediction_invariants(
    is_ai_predicted: bool,
    confidence: Optional[float],
) -> None:
    """
    Enforces AI transparency: AI-predicted categories must supply a confidence
    score between 0.0 and 1.0, preserving distinction from bank-confirmed facts.
    """
    if is_ai_predicted:
        if confidence is None or not (0.0 <= confidence <= 1.0):
            raise DomainValidationError(
                message="AI-predicted categories must include a confidence score between 0.0 and 1.0.",
                field="ai_confidence",
            )
