"""
Arthsavora Document Intelligence & Receipt Domain Entities and Value Objects
Defines domain invariants, Indian GST formatting rules, monetary parsing,
mathematical validation, and structured extraction contracts.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Tuple

from app.domain.money import Money, INTERNAL_QUANTIZATION


class DocumentType(str, Enum):
    RECEIPT = "receipt"
    INVOICE = "invoice"
    BILL = "bill"
    SUPPORTING_DOC = "supporting_doc"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    REVIEW_REQUIRED = "review_required"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    FAILED = "failed"


class TransactionMatchStatus(str, Enum):
    EXACT = "exact"
    CANDIDATE = "candidate"
    AMBIGUOUS = "ambiguous"
    NONE = "none"


class PaymentMethod(str, Enum):
    UPI = "upi"
    CARD = "card"
    CASH = "cash"
    NETBANKING = "netbanking"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    VALID = "valid"
    WARNING = "warning"
    INVALID_MATH = "invalid_math"
    INCOMPLETE = "incomplete"


# Official 15-character Indian Goods and Services Tax Identification Number (GSTIN) Regex
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


def is_valid_gstin(gstin: Optional[str]) -> bool:
    """Validate 15-character alphanumeric Indian GSTIN."""
    if not gstin:
        return False
    cleaned = gstin.strip().upper()
    return bool(GSTIN_REGEX.match(cleaned))


def parse_indian_date(date_str: str) -> Optional[date]:
    """
    Parses date strings commonly encountered in Indian receipts and invoices.
    Supports DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD, DD Mon YYYY, etc.
    """
    if not date_str:
        return None
    cleaned = date_str.strip()
    patterns = [
        r"%d/%m/%Y",
        r"%d-%m-%Y",
        r"%d.%m.%Y",
        r"%Y-%m-%d",
        r"%d %b %Y",
        r"%d %B %Y",
        r"%d/%m/%y",
        r"%d-%m-%y",
        r"%d.%m.%y",
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    return None


def parse_monetary_amount(text_val: str, default_currency: str = "INR") -> Tuple[Decimal, int]:
    """
    Parse monetary amount string with support for Indian comma notations (e.g. 1,50,000.50),
    currency symbols (₹, Rs, Rs.), and formatting tokens.
    Returns (Decimal(18, 4), amount_paise: int).
    """
    if not text_val:
        return Decimal("0.0000"), 0

    cleaned = str(text_val).strip()
    # Remove currency symbols and common indicators
    cleaned = re.sub(r"[₹$€£]|Rs\.?|INR|/-", "", cleaned, flags=re.IGNORECASE).strip()
    # Remove all spaces
    cleaned = re.sub(r"\s+", "", cleaned)

    # Indian comma notation: commas are strictly thousands/lakhs separators
    cleaned = cleaned.replace(",", "")

    # Extract first valid numeric floating/decimal pattern
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return Decimal("0.0000"), 0

    try:
        raw_num = match.group(0)
        dec_val = Decimal(raw_num).quantize(INTERNAL_QUANTIZATION, rounding=ROUND_HALF_EVEN)
        money_obj = Money(amount=dec_val, currency=default_currency)
        return money_obj.amount, money_obj.to_minor_units()
    except (InvalidOperation, ValueError):
        return Decimal("0.0000"), 0


@dataclass
class DocumentLineItemVO:
    description: str
    hsn_sac: Optional[str] = None
    quantity: Decimal = Decimal("1.0000")
    unit_price: Decimal = Decimal("0.0000")
    unit_price_paise: int = 0
    tax_rate: Optional[Decimal] = None
    amount: Decimal = Decimal("0.0000")
    amount_paise: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "hsn_sac": self.hsn_sac,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "unit_price_paise": self.unit_price_paise,
            "tax_rate": str(self.tax_rate) if self.tax_rate is not None else None,
            "amount": str(self.amount),
            "amount_paise": self.amount_paise,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentLineItemVO":
        return cls(
            description=str(data.get("description", "")),
            hsn_sac=data.get("hsn_sac"),
            quantity=Decimal(str(data.get("quantity", "1.0"))),
            unit_price=Decimal(str(data.get("unit_price", "0.0"))),
            unit_price_paise=int(data.get("unit_price_paise", 0)),
            tax_rate=Decimal(str(data["tax_rate"])) if data.get("tax_rate") is not None else None,
            amount=Decimal(str(data.get("amount", "0.0"))),
            amount_paise=int(data.get("amount_paise", 0)),
        )


@dataclass
class TaxBreakdownVO:
    cgst: Decimal = Decimal("0.0000")
    cgst_paise: int = 0
    sgst: Decimal = Decimal("0.0000")
    sgst_paise: int = 0
    igst: Decimal = Decimal("0.0000")
    igst_paise: int = 0
    total_tax: Decimal = Decimal("0.0000")
    total_tax_paise: int = 0
    gstin: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cgst": str(self.cgst),
            "cgst_paise": self.cgst_paise,
            "sgst": str(self.sgst),
            "sgst_paise": self.sgst_paise,
            "igst": str(self.igst),
            "igst_paise": self.igst_paise,
            "total_tax": str(self.total_tax),
            "total_tax_paise": self.total_tax_paise,
            "gstin": self.gstin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaxBreakdownVO":
        return cls(
            cgst=Decimal(str(data.get("cgst", "0.0"))),
            cgst_paise=int(data.get("cgst_paise", 0)),
            sgst=Decimal(str(data.get("sgst", "0.0"))),
            sgst_paise=int(data.get("sgst_paise", 0)),
            igst=Decimal(str(data.get("igst", "0.0"))),
            igst_paise=int(data.get("igst_paise", 0)),
            total_tax=Decimal(str(data.get("total_tax", "0.0"))),
            total_tax_paise=int(data.get("total_tax_paise", 0)),
            gstin=data.get("gstin"),
        )


@dataclass
class StructuredReceiptDataVO:
    merchant_name: Optional[str] = None
    gstin: Optional[str] = None
    receipt_date: Optional[str] = None  # ISO YYYY-MM-DD
    invoice_number: Optional[str] = None
    currency: str = "INR"
    subtotal: Decimal = Decimal("0.0000")
    subtotal_paise: int = 0
    taxes: TaxBreakdownVO = field(default_factory=TaxBreakdownVO)
    discount: Decimal = Decimal("0.0000")
    discount_paise: int = 0
    total_amount: Decimal = Decimal("0.0000")
    total_amount_paise: int = 0
    payment_method: str = "unknown"
    payment_reference: Optional[str] = None
    suggested_category_id: Optional[str] = None
    suggested_category_name: Optional[str] = None
    line_items: List[DocumentLineItemVO] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant_name": self.merchant_name,
            "gstin": self.gstin,
            "receipt_date": self.receipt_date,
            "invoice_number": self.invoice_number,
            "currency": self.currency,
            "subtotal": str(self.subtotal),
            "subtotal_paise": self.subtotal_paise,
            "taxes": self.taxes.to_dict(),
            "discount": str(self.discount),
            "discount_paise": self.discount_paise,
            "total_amount": str(self.total_amount),
            "total_amount_paise": self.total_amount_paise,
            "payment_method": self.payment_method,
            "payment_reference": self.payment_reference,
            "suggested_category_id": self.suggested_category_id,
            "suggested_category_name": self.suggested_category_name,
            "line_items": [item.to_dict() for item in self.line_items],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredReceiptDataVO":
        taxes_raw = data.get("taxes") or {}
        taxes_vo = TaxBreakdownVO.from_dict(taxes_raw) if isinstance(taxes_raw, dict) else TaxBreakdownVO()
        raw_items = data.get("line_items") or []
        line_items = [
            DocumentLineItemVO.from_dict(item) if isinstance(item, dict) else item
            for item in raw_items
        ]
        return cls(
            merchant_name=data.get("merchant_name"),
            gstin=data.get("gstin"),
            receipt_date=data.get("receipt_date"),
            invoice_number=data.get("invoice_number"),
            currency=data.get("currency", "INR"),
            subtotal=Decimal(str(data.get("subtotal", "0.0"))),
            subtotal_paise=int(data.get("subtotal_paise", 0)),
            taxes=taxes_vo,
            discount=Decimal(str(data.get("discount", "0.0"))),
            discount_paise=int(data.get("discount_paise", 0)),
            total_amount=Decimal(str(data.get("total_amount", "0.0"))),
            total_amount_paise=int(data.get("total_amount_paise", 0)),
            payment_method=data.get("payment_method", "unknown"),
            payment_reference=data.get("payment_reference"),
            suggested_category_id=data.get("suggested_category_id"),
            suggested_category_name=data.get("suggested_category_name"),
            line_items=line_items,
        )


def validate_receipt_math(
    subtotal_paise: int,
    total_tax_paise: int,
    discount_paise: int,
    total_amount_paise: int,
    line_items: List[DocumentLineItemVO],
) -> Tuple[ValidationStatus, List[str]]:
    """
    Perform rigorous arithmetic reconciliation:
    1. subtotal + taxes - discount == total_amount (within rounding tolerance of 100 paise / ₹1)
    2. sum(line_item amounts) == subtotal or total_amount
    Returns (ValidationStatus, list of warning messages).
    """
    warnings: List[str] = []
    status = ValidationStatus.VALID

    # Check 1: Missing total
    if total_amount_paise <= 0:
        warnings.append("Document does not contain a positive total monetary amount.")
        return ValidationStatus.INCOMPLETE, warnings

    # Check 2: Tax / Subtotal reconciliation
    if subtotal_paise > 0:
        expected_total = subtotal_paise + total_tax_paise - discount_paise
        discrepancy = abs(expected_total - total_amount_paise)
        if discrepancy > 100:  # > 1 Rupee discrepancy
            status = ValidationStatus.INVALID_MATH
            diff_inr = Decimal(discrepancy) / Decimal(100)
            warnings.append(
                f"Arithmetic mismatch: Subtotal ({subtotal_paise / 100:.2f}) + "
                f"Tax ({total_tax_paise / 100:.2f}) - Discount ({discount_paise / 100:.2f}) != "
                f"Total ({total_amount_paise / 100:.2f}). Discrepancy: ₹{diff_inr:.2f}."
            )
        elif discrepancy > 0:
            warnings.append(f"Minor rounding discrepancy of {discrepancy} paise observed.")

    # Check 3: Line items reconciliation
    if line_items:
        items_total_paise = sum(item.amount_paise for item in line_items)
        if items_total_paise > 0:
            target_paise = subtotal_paise if subtotal_paise > 0 else total_amount_paise
            items_discrepancy = abs(items_total_paise - target_paise)
            if items_discrepancy > 100:
                if status == ValidationStatus.VALID:
                    status = ValidationStatus.WARNING
                warnings.append(
                    f"Line items total (₹{items_total_paise / 100:.2f}) does not match "
                    f"reconciled target (₹{target_paise / 100:.2f})."
                )

    return status, warnings
