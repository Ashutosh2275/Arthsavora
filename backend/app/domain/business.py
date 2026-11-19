"""
Arthsavora Business Finance Domain Layer
Pure business logic for invoicing, exact minor-unit calculations (paise),
tax breakdowns (CGST/SGST/IGST), AR/AP aging calculations, and validation rules.
Zero framework or database dependencies.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid


class BusinessType(str, Enum):
    FREELANCER = "freelancer"
    CONSULTANT = "consultant"
    INDEPENDENT_PROFESSIONAL = "independent_professional"
    SERVICE_PROVIDER = "service_provider"
    SMALL_AGENCY = "small_agency"
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    OTHER = "other"


class ClientType(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    ORGANIZATION = "organization"


class VendorType(str, Enum):
    CONTRACTOR = "contractor"
    SOFTWARE_SAAS = "software_saas"
    SERVICE_PROVIDER = "service_provider"
    UTILITY = "utility"
    LANDLORD = "landlord"
    OTHER = "other"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PayableStatus(str, Enum):
    DRAFT = "draft"
    RECORDED = "recorded"
    DUE = "due"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    NEFT_RTGS = "neft_rtgs"
    CHEQUE = "cheque"
    CARD = "card"
    CASH = "cash"
    OTHER = "other"


class BusinessActivityType(str, Enum):
    PROFILE_UPDATED = "profile_updated"
    CLIENT_CREATED = "client_created"
    CLIENT_UPDATED = "client_updated"
    VENDOR_CREATED = "vendor_created"
    VENDOR_UPDATED = "vendor_updated"
    INVOICE_CREATED = "invoice_created"
    INVOICE_ISSUED = "invoice_issued"
    INVOICE_PAID = "invoice_paid"
    INVOICE_CANCELLED = "invoice_cancelled"
    PAYABLE_RECORDED = "payable_recorded"
    PAYABLE_PAID = "payable_paid"
    PAYABLE_CANCELLED = "payable_cancelled"


# Regex patterns for Indian statutory tax identifiers
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")


def validate_gstin(gstin: Optional[str]) -> bool:
    """Validates 15-character Goods and Services Tax Identification Number (India)."""
    if not gstin:
        return True
    return bool(GSTIN_REGEX.match(gstin.strip().upper()))


def validate_pan(pan: Optional[str]) -> bool:
    """Validates 10-character Permanent Account Number (India)."""
    if not pan:
        return True
    return bool(PAN_REGEX.match(pan.strip().upper()))


@dataclass(frozen=True)
class InvoiceLineItemVO:
    description: str
    quantity: Decimal
    unit_price_paise: int
    discount_paise: int = 0
    tax_rate_percent: Decimal = Decimal("0.0")
    cgst_rate_percent: Decimal = Decimal("0.0")
    sgst_rate_percent: Decimal = Decimal("0.0")
    igst_rate_percent: Decimal = Decimal("0.0")
    subtotal_amount_paise: int = 0
    tax_amount_paise: int = 0
    total_amount_paise: int = 0
    hsn_sac_code: Optional[str] = None
    line_order: int = 0


@dataclass(frozen=True)
class InvoiceTotalsVO:
    subtotal_paise: int
    discount_paise: int
    tax_paise: int
    total_paise: int
    line_items: List[InvoiceLineItemVO]


@dataclass(frozen=True)
class ReceivablesAgingVO:
    current_paise: int
    days_1_30_paise: int
    days_31_60_paise: int
    days_61_90_paise: int
    days_91_plus_paise: int
    total_outstanding_paise: int


@dataclass(frozen=True)
class PayablesAgingVO:
    current_paise: int
    days_1_30_paise: int
    days_31_60_paise: int
    days_61_90_paise: int
    days_91_plus_paise: int
    total_outstanding_paise: int


@dataclass(frozen=True)
class CashFlowSummaryVO:
    operating_inflows_paise: int
    operating_outflows_paise: int
    net_operating_cash_flow_paise: int
    accounts_receivable_paise: int
    accounts_payable_paise: int
    cash_balance_paise: int


def calculate_line_item(
    description: str,
    quantity: Decimal,
    unit_price_paise: int,
    discount_paise: int = 0,
    tax_rate_percent: Decimal = Decimal("0.0"),
    is_interstate: bool = False,
    hsn_sac_code: Optional[str] = None,
    line_order: int = 0,
) -> InvoiceLineItemVO:
    """
    Computes exact line totals in integer minor units (paise).
    Applies CGST/SGST or IGST depending on inter-state designation.
    """
    if quantity <= 0:
        raise ValueError("Line item quantity must be strictly greater than zero.")
    if unit_price_paise < 0:
        raise ValueError("Line item unit price cannot be negative.")
    if discount_paise < 0:
        raise ValueError("Line item discount cannot be negative.")

    raw_subtotal = int(round(Decimal(unit_price_paise) * quantity))
    line_subtotal = max(0, raw_subtotal - discount_paise)

    # Tax computation
    if is_interstate:
        cgst_rate = Decimal("0.0")
        sgst_rate = Decimal("0.0")
        igst_rate = tax_rate_percent
    else:
        cgst_rate = tax_rate_percent / Decimal("2.0")
        sgst_rate = tax_rate_percent / Decimal("2.0")
        igst_rate = Decimal("0.0")

    tax_amount_paise = int(round(Decimal(line_subtotal) * (tax_rate_percent / Decimal("100.0"))))
    total_paise = line_subtotal + tax_amount_paise

    return InvoiceLineItemVO(
        description=description,
        quantity=quantity,
        unit_price_paise=unit_price_paise,
        discount_paise=discount_paise,
        tax_rate_percent=tax_rate_percent,
        cgst_rate_percent=cgst_rate,
        sgst_rate_percent=sgst_rate,
        igst_rate_percent=igst_rate,
        subtotal_amount_paise=line_subtotal,
        tax_amount_paise=tax_amount_paise,
        total_amount_paise=total_paise,
        hsn_sac_code=hsn_sac_code,
        line_order=line_order,
    )


def calculate_invoice_totals(
    line_items_data: List[Dict[str, Any]],
    overall_discount_paise: int = 0,
    is_interstate: bool = False,
) -> InvoiceTotalsVO:
    """
    Calculates subtotal, taxes, and final total in exact integer paise.
    Guarantees: Total = Sum(Line Subtotals) - Overall Discount + Sum(Taxes).
    """
    if not line_items_data:
        raise ValueError("An invoice must contain at least one line item.")
    if overall_discount_paise < 0:
        raise ValueError("Overall discount cannot be negative.")

    calculated_items: List[InvoiceLineItemVO] = []
    subtotal_sum = 0
    tax_sum = 0

    for idx, item in enumerate(line_items_data):
        vo = calculate_line_item(
            description=item.get("description", "").strip(),
            quantity=Decimal(str(item.get("quantity", 1))),
            unit_price_paise=int(item.get("unit_price_paise", 0)),
            discount_paise=int(item.get("discount_paise", 0)),
            tax_rate_percent=Decimal(str(item.get("tax_rate_percent", "0.0"))),
            is_interstate=is_interstate,
            hsn_sac_code=item.get("hsn_sac_code"),
            line_order=item.get("line_order", idx),
        )
        calculated_items.append(vo)
        subtotal_sum += vo.subtotal_amount_paise
        tax_sum += vo.tax_amount_paise

    total_paise = max(0, subtotal_sum - overall_discount_paise + tax_sum)

    return InvoiceTotalsVO(
        subtotal_paise=subtotal_sum,
        discount_paise=overall_discount_paise,
        tax_paise=tax_sum,
        total_paise=total_paise,
        line_items=calculated_items,
    )


def compute_ar_aging(
    invoices: List[Dict[str, Any]],
    as_of_date: Optional[date] = None,
) -> ReceivablesAgingVO:
    """
    Categorizes unpaid and partially paid invoices into standard aging buckets:
    - Current (due today or in the future)
    - 1-30 days past due
    - 31-60 days past due
    - 61-90 days past due
    - 91+ days past due
    """
    as_of = as_of_date or date.today()
    current = 0
    d1_30 = 0
    d31_60 = 0
    d61_90 = 0
    d91_plus = 0
    total = 0

    for inv in invoices:
        status = inv.get("status")
        if status in (InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value, InvoiceStatus.DRAFT.value):
            continue

        total_amount = int(inv.get("total_amount_paise", 0))
        paid_amount = int(inv.get("paid_amount_paise", 0))
        balance = max(0, total_amount - paid_amount)
        if balance == 0:
            continue

        due_date = inv.get("due_date")
        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date)

        days_overdue = (as_of - due_date).days

        if days_overdue <= 0:
            current += balance
        elif 1 <= days_overdue <= 30:
            d1_30 += balance
        elif 31 <= days_overdue <= 60:
            d31_60 += balance
        elif 61 <= days_overdue <= 90:
            d61_90 += balance
        else:
            d91_plus += balance

        total += balance

    return ReceivablesAgingVO(
        current_paise=current,
        days_1_30_paise=d1_30,
        days_31_60_paise=d31_60,
        days_61_90_paise=d61_90,
        days_91_plus_paise=d91_plus,
        total_outstanding_paise=total,
    )


def compute_ap_aging(
    payables: List[Dict[str, Any]],
    as_of_date: Optional[date] = None,
) -> PayablesAgingVO:
    """
    Categorizes outstanding vendor bills into standard aging buckets.
    """
    as_of = as_of_date or date.today()
    current = 0
    d1_30 = 0
    d31_60 = 0
    d61_90 = 0
    d91_plus = 0
    total = 0

    for bill in payables:
        status = bill.get("status")
        if status in (PayableStatus.PAID.value, PayableStatus.CANCELLED.value, PayableStatus.DRAFT.value):
            continue

        total_amount = int(bill.get("total_amount_paise", 0))
        paid_amount = int(bill.get("paid_amount_paise", 0))
        balance = max(0, total_amount - paid_amount)
        if balance == 0:
            continue

        due_date = bill.get("due_date")
        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date)

        days_overdue = (as_of - due_date).days

        if days_overdue <= 0:
            current += balance
        elif 1 <= days_overdue <= 30:
            d1_30 += balance
        elif 31 <= days_overdue <= 60:
            d31_60 += balance
        elif 61 <= days_overdue <= 90:
            d61_90 += balance
        else:
            d91_plus += balance

        total += balance

    return PayablesAgingVO(
        current_paise=current,
        days_1_30_paise=d1_30,
        days_31_60_paise=d31_60,
        days_61_90_paise=d61_90,
        days_91_plus_paise=d91_plus,
        total_outstanding_paise=total,
    )


def format_invoice_number(prefix: str, year: int, sequence_number: int) -> str:
    """Generates unique business-scoped invoice identifier, e.g. 'INV-2026-0001'."""
    clean_prefix = (prefix or "INV").strip().upper()
    return f"{clean_prefix}-{year}-{sequence_number:04d}"


def sanitize_csv_cell(value: Any) -> str:
    """
    Sanitizes formula injection vulnerabilities in CSV exports.
    Prepends a single quote to characters ('=', '+', '-', '@', tab, CR) if present at start.
    """
    if value is None:
        return ""
    str_val = str(value)
    if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{str_val}"
    return str_val
