"""
Arthsavora Statement Normalizer
Normalizes dates, Indian number formats, transaction directions, paise, and descriptions.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, Optional, Tuple
from app.domain.transaction_types import TransactionDirection, TransactionType


class StatementNormalizer:
    """Deterministic normalizer for statement records into canonical financial structures."""

    # Common Indian and international date formats
    DATE_FORMATS = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d-%B-%Y",
        "%d %B %Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%m/%d/%Y",
    ]

    @classmethod
    def parse_date(cls, raw_date: Optional[str]) -> Tuple[Optional[date], Optional[str]]:
        """
        Parses a date string using standard date conventions.
        Returns (date_obj, iso_date_str).
        """
        if not raw_date or not str(raw_date).strip():
            return None, None

        cleaned = str(raw_date).strip()
        # Clean extra time parts if present (e.g. "14/11/2026 12:30:00")
        if " " in cleaned and len(cleaned.split(" ")[0]) >= 8:
            first_token = cleaned.split(" ")[0]
            if any(sep in first_token for sep in ("/", "-", ".")):
                cleaned = first_token

        for fmt in cls.DATE_FORMATS:
            try:
                dt = datetime.strptime(cleaned, fmt).date()
                return dt, dt.isoformat()
            except ValueError:
                continue

        return None, None

    @classmethod
    def parse_amount(cls, raw_amount: Optional[str]) -> Tuple[Optional[Decimal], Optional[int], bool]:
        """
        Parses an amount string with Indian numbering support, parentheses, and currency symbols.
        Returns (decimal_amount, amount_paise, is_negative).
        """
        if raw_amount is None:
            return None, None, False

        cleaned = str(raw_amount).strip()
        if not cleaned:
            return None, None, False

        # Remove currency markers and spaces
        cleaned = re.sub(r"(?i)\b(?:INR|Rs\.?)\b", "", cleaned)
        cleaned = re.sub(r"[₹\$\s]", "", cleaned)

        # Detect and handle parentheses indicating negative numbers (e.g. "(1,250.50)")
        is_negative = False
        if cleaned.startswith("(") and cleaned.endswith(")"):
            is_negative = True
            cleaned = cleaned[1:-1].strip()
        elif cleaned.startswith("-") or cleaned.endswith("-") or cleaned.endswith("Dr") or cleaned.endswith("DR"):
            is_negative = True
            cleaned = cleaned.replace("-", "").replace("Dr", "").replace("DR", "").strip()
        elif cleaned.endswith("Cr") or cleaned.endswith("CR"):
            cleaned = cleaned.replace("Cr", "").replace("CR", "").strip()

        # Remove commas from Indian formatting (e.g. 1,25,000.50 -> 125000.50)
        cleaned = cleaned.replace(",", "")

        if not cleaned:
            return None, None, False

        try:
            val = Decimal(cleaned)
            abs_val = abs(val)
            quantized = abs_val.quantize(Decimal("0.0001"))
            paise = int(round(quantized * 100))
            if val < 0:
                is_negative = True
            return quantized, paise, is_negative
        except InvalidOperation:
            return None, None, False

    @classmethod
    def normalize_row(
        cls,
        row_number: int,
        raw_data: Dict[str, str],
        date_str: Optional[str],
        description_str: Optional[str],
        amount_str: Optional[str],
        debit_str: Optional[str],
        credit_str: Optional[str],
        balance_str: Optional[str],
        ref_str: Optional[str],
        default_currency: str = "INR",
    ) -> Dict[str, Any]:
        """
        Transforms parsed row text into a normalized candidate dictionary.
        """
        date_obj, iso_date = cls.parse_date(date_str)
        
        # Clean description
        clean_desc = (description_str or "").strip()
        clean_desc = re.sub(r"\s+", " ", clean_desc)

        # Reference number
        clean_ref = (ref_str or "").strip() or None

        # Determine Amount and Direction
        debit_amt, debit_paise, _ = cls.parse_amount(debit_str)
        credit_amt, credit_paise, _ = cls.parse_amount(credit_str)
        single_amt, single_paise, is_neg = cls.parse_amount(amount_str)

        direction = TransactionDirection.OUTFLOW.value
        final_amount: Optional[Decimal] = None
        final_paise: Optional[int] = None
        tx_type = TransactionType.EXPENSE.value

        if debit_amt is not None and debit_amt > 0:
            direction = TransactionDirection.OUTFLOW.value
            final_amount = debit_amt
            final_paise = debit_paise
            tx_type = TransactionType.EXPENSE.value
        elif credit_amt is not None and credit_amt > 0:
            direction = TransactionDirection.INFLOW.value
            final_amount = credit_amt
            final_paise = credit_paise
            tx_type = TransactionType.INCOME.value
        elif single_amt is not None:
            if is_neg:
                direction = TransactionDirection.OUTFLOW.value
                final_amount = single_amt
                final_paise = single_paise
                tx_type = TransactionType.EXPENSE.value
            else:
                direction = TransactionDirection.INFLOW.value
                final_amount = single_amt
                final_paise = single_paise
                tx_type = TransactionType.INCOME.value

        # Infer refined transaction types based on description keywords
        desc_upper = clean_desc.upper()
        if "SALARY" in desc_upper or "PAYROLL" in desc_upper:
            tx_type = TransactionType.INCOME.value
            direction = TransactionDirection.INFLOW.value
        elif "DIVIDEND" in desc_upper:
            tx_type = TransactionType.DIVIDEND.value
            direction = TransactionDirection.INFLOW.value
        elif "INTEREST" in desc_upper and direction == TransactionDirection.INFLOW.value:
            tx_type = TransactionType.INTEREST.value
        elif "ATM" in desc_upper or "CASH WDL" in desc_upper:
            tx_type = TransactionType.WITHDRAWAL.value
        elif "REFUND" in desc_upper or "CASHBACK" in desc_upper:
            tx_type = TransactionType.REFUND.value
            direction = TransactionDirection.INFLOW.value
        elif "CREDIT CARD" in desc_upper or "CARD PAYMENT" in desc_upper:
            tx_type = TransactionType.CREDIT_CARD_PAYMENT.value
        elif "TRANSFER" in desc_upper or "NEFT" in desc_upper or "RTGS" in desc_upper:
            tx_type = TransactionType.TRANSFER.value

        # Balance parsing
        bal_amt, bal_paise, _ = cls.parse_amount(balance_str)

        return {
            "source_row_number": row_number,
            "transaction_date": iso_date,
            "description": clean_desc,
            "amount": str(final_amount) if final_amount is not None else None,
            "amount_paise": final_paise,
            "direction": direction,
            "transaction_type": tx_type,
            "currency": default_currency.upper(),
            "reference_number": clean_ref,
            "balance": str(bal_amt) if bal_amt is not None else None,
            "balance_paise": bal_paise,
        }
