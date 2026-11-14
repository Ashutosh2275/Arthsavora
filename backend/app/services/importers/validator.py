"""
Arthsavora Statement Row Validator
Validates normalized financial data rows and generates structured error lists.
"""

from typing import Any, Dict, List, Tuple
from app.domain.import_types import ValidationStatus


class StatementValidator:
    """Performs pre-ingestion domain validation on normalized transaction candidates."""

    @classmethod
    def validate_candidate(
        cls,
        normalized: Dict[str, Any],
    ) -> Tuple[ValidationStatus, List[str]]:
        """
        Validates normalized candidate dictionary.
        Returns (ValidationStatus, list_of_error_messages).
        """
        errors: List[str] = []

        # 1. Date Validation
        tx_date = normalized.get("transaction_date")
        if not tx_date:
            errors.append("Missing or unparseable transaction date.")

        # 2. Amount Validation
        amt = normalized.get("amount")
        paise = normalized.get("amount_paise")
        if amt is None or paise is None:
            errors.append("Missing or unparseable transaction amount.")
        elif paise <= 0:
            errors.append("Transaction amount must be strictly greater than zero.")

        # 3. Description Validation
        desc = normalized.get("description")
        if not desc or not desc.strip():
            errors.append("Transaction description or narration cannot be empty.")

        # 4. Currency Validation
        curr = normalized.get("currency")
        if not curr or len(curr) != 3:
            errors.append(f"Invalid currency code '{curr}'. Must be a 3-letter ISO code.")

        # 5. Direction Validation
        direction = normalized.get("direction")
        if direction not in ("inflow", "outflow"):
            errors.append(f"Invalid direction '{direction}'. Must be 'inflow' or 'outflow'.")

        # Determine Verdict
        if errors:
            # If critical elements (date, amount) are missing -> INVALID
            if any("date" in e or "amount" in e for e in errors):
                return ValidationStatus.INVALID, errors
            return ValidationStatus.AMBIGUOUS, errors

        return ValidationStatus.VALID, []
