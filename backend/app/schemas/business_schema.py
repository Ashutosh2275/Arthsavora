"""
Arthsavora Business Finance Pydantic Schemas
Defines request and response serialization contracts for business profiles,
clients, vendors, invoices, payments, payables, and analytics.
Provides minor-unit (paise) and decimal financial conversions.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


def paise_to_decimal(paise: int) -> Decimal:
    """Converts integer minor units (paise) to Decimal representation."""
    return Decimal(paise) / Decimal("100.0")


def decimal_to_paise(amount: Decimal | float | int) -> int:
    """Converts decimal major units into integer minor units (paise)."""
    return int(round(Decimal(str(amount)) * Decimal("100.0")))


# ---------------------------------------------------------------------------
# Business Profile Schemas
# ---------------------------------------------------------------------------

class BusinessProfileUpdate(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=255)
    business_type: str = Field(default="freelancer", max_length=50)
    business_description: Optional[str] = Field(default=None, max_length=1000)
    business_email: Optional[str] = Field(default=None, max_length=255)
    business_phone: Optional[str] = Field(default=None, max_length=50)
    business_address: Optional[Dict[str, Any]] = None
    country: str = Field(default="IN", min_length=2, max_length=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    financial_year_start_month: int = Field(default=4, ge=1, le=12)
    timezone: str = Field(default="Asia/Kolkata", max_length=50)
    gstin: Optional[str] = Field(default=None, max_length=15)
    pan: Optional[str] = Field(default=None, max_length=10)
    tax_configuration: Optional[Dict[str, Any]] = None
    invoice_settings: Optional[Dict[str, Any]] = None


class BusinessProfileResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    business_name: str
    business_type: str
    business_description: Optional[str] = None
    business_email: Optional[str] = None
    business_phone: Optional[str] = None
    business_address: Dict[str, Any] = {}
    country: str
    currency: str
    financial_year_start_month: int
    timezone: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    tax_configuration: Dict[str, Any] = {}
    invoice_settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Client Schemas
# ---------------------------------------------------------------------------

class BusinessClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client_type: str = Field(default="business", max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    billing_address: Optional[Dict[str, Any]] = None
    gstin: Optional[str] = Field(default=None, max_length=15)
    pan: Optional[str] = Field(default=None, max_length=10)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    notes: Optional[str] = Field(default=None, max_length=1000)


class BusinessClientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    client_type: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    billing_address: Optional[Dict[str, Any]] = None
    gstin: Optional[str] = Field(default=None, max_length=15)
    pan: Optional[str] = Field(default=None, max_length=10)
    payment_terms_days: Optional[int] = Field(default=None, ge=0, le=365)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    notes: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, max_length=20)


class BusinessClientResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    client_type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Dict[str, Any] = {}
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms_days: int
    currency: str
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Vendor Schemas
# ---------------------------------------------------------------------------

class BusinessVendorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    vendor_type: str = Field(default="service_provider", max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    billing_details: Optional[Dict[str, Any]] = None
    gstin: Optional[str] = Field(default=None, max_length=15)
    pan: Optional[str] = Field(default=None, max_length=10)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    notes: Optional[str] = Field(default=None, max_length=1000)


class BusinessVendorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    vendor_type: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    billing_details: Optional[Dict[str, Any]] = None
    gstin: Optional[str] = Field(default=None, max_length=15)
    pan: Optional[str] = Field(default=None, max_length=10)
    payment_terms_days: Optional[int] = Field(default=None, ge=0, le=365)
    notes: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, max_length=20)


class BusinessVendorResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    vendor_type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    billing_details: Dict[str, Any] = {}
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms_days: int
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Invoice Schemas
# ---------------------------------------------------------------------------

class InvoiceLineItemCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    hsn_sac_code: Optional[str] = Field(default=None, max_length=20)
    quantity: Decimal = Field(default=Decimal("1.0"), gt=Decimal("0.0"))
    unit_price: Decimal = Field(..., ge=Decimal("0.0"))
    discount: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    tax_rate_percent: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), le=Decimal("100.0"))
    line_order: int = Field(default=0)


class BusinessInvoiceCreate(BaseModel):
    client_id: uuid.UUID
    invoice_date: date
    due_date: date
    currency: str = Field(default="INR", min_length=3, max_length=3)
    line_items: List[InvoiceLineItemCreate] = Field(..., min_length=1)
    overall_discount: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    is_interstate: bool = Field(default=False)
    custom_invoice_number: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=1000)
    payment_instructions: Optional[str] = Field(default=None, max_length=1000)


class InvoiceLineItemResponse(BaseModel):
    id: uuid.UUID
    description: str
    hsn_sac_code: Optional[str] = None
    quantity: Decimal
    unit_price_paise: int
    unit_price_decimal: Decimal
    discount_paise: int
    tax_rate_percent: Decimal
    cgst_rate_percent: Decimal
    sgst_rate_percent: Decimal
    igst_rate_percent: Decimal
    tax_amount_paise: int
    tax_amount_decimal: Decimal
    total_amount_paise: int
    total_amount_decimal: Decimal
    line_order: int

    model_config = ConfigDict(from_attributes=True)


class BusinessInvoicePaymentCreate(BaseModel):
    payment_date: date
    amount: Decimal = Field(..., gt=Decimal("0.0"))
    payment_method: str = Field(default="bank_transfer", max_length=30)
    reference_number: Optional[str] = Field(default=None, max_length=100)
    financial_account_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class BusinessInvoicePaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    payment_date: date
    amount_paise: int
    amount_decimal: Decimal
    payment_method: str
    reference_number: Optional[str] = None
    financial_account_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessInvoiceResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    client_id: uuid.UUID
    client_name: Optional[str] = None
    invoice_number: str
    invoice_date: date
    due_date: date
    currency: str
    subtotal_amount_paise: int
    subtotal_amount_decimal: Decimal
    discount_amount_paise: int
    discount_amount_decimal: Decimal
    tax_amount_paise: int
    tax_amount_decimal: Decimal
    total_amount_paise: int
    total_amount_decimal: Decimal
    paid_amount_paise: int
    paid_amount_decimal: Decimal
    balance_amount_paise: int
    balance_amount_decimal: Decimal
    status: str
    notes: Optional[str] = None
    payment_instructions: Optional[str] = None
    issued_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    version: int
    journal_entry_id: Optional[uuid.UUID] = None
    line_items: List[InvoiceLineItemResponse] = []
    payments: List[BusinessInvoicePaymentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CancelInvoiceRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Payable (Vendor Bill) Schemas
# ---------------------------------------------------------------------------

class BusinessPayableCreate(BaseModel):
    vendor_id: uuid.UUID
    bill_number: Optional[str] = Field(default=None, max_length=50)
    bill_date: date
    due_date: date
    subtotal_amount: Decimal = Field(..., ge=Decimal("0.0"))
    tax_amount: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    currency: str = Field(default="INR", min_length=3, max_length=3)
    category_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class BusinessPayablePaymentCreate(BaseModel):
    payment_date: date
    amount: Decimal = Field(..., gt=Decimal("0.0"))
    payment_method: str = Field(default="bank_transfer", max_length=30)
    reference_number: Optional[str] = Field(default=None, max_length=100)
    financial_account_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class BusinessPayablePaymentResponse(BaseModel):
    id: uuid.UUID
    payable_id: uuid.UUID
    payment_date: date
    amount_paise: int
    amount_decimal: Decimal
    payment_method: str
    reference_number: Optional[str] = None
    financial_account_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessPayableResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: date
    due_date: date
    currency: str
    subtotal_amount_paise: int
    subtotal_amount_decimal: Decimal
    tax_amount_paise: int
    tax_amount_decimal: Decimal
    total_amount_paise: int
    total_amount_decimal: Decimal
    paid_amount_paise: int
    paid_amount_decimal: Decimal
    balance_amount_paise: int
    balance_amount_decimal: Decimal
    status: str
    category_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    journal_entry_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    payments: List[BusinessPayablePaymentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Overview & Analytics Schemas
# ---------------------------------------------------------------------------

class ReceivablesAgingResponse(BaseModel):
    current_paise: int
    current_decimal: Decimal
    days_1_30_paise: int
    days_1_30_decimal: Decimal
    days_31_60_paise: int
    days_31_60_decimal: Decimal
    days_61_90_paise: int
    days_61_90_decimal: Decimal
    days_91_plus_paise: int
    days_91_plus_decimal: Decimal
    total_outstanding_paise: int
    total_outstanding_decimal: Decimal


class PayablesAgingResponse(BaseModel):
    current_paise: int
    current_decimal: Decimal
    days_1_30_paise: int
    days_1_30_decimal: Decimal
    days_31_60_paise: int
    days_31_60_decimal: Decimal
    days_61_90_paise: int
    days_61_90_decimal: Decimal
    days_91_plus_paise: int
    days_91_plus_decimal: Decimal
    total_outstanding_paise: int
    total_outstanding_decimal: Decimal


class BusinessOverviewResponse(BaseModel):
    invoiced_revenue_paise: int
    invoiced_revenue_decimal: Decimal
    collected_revenue_paise: int
    collected_revenue_decimal: Decimal
    total_receivables_paise: int
    total_receivables_decimal: Decimal
    total_bills_paise: int
    total_bills_decimal: Decimal
    paid_bills_paise: int
    paid_bills_decimal: Decimal
    total_payables_paise: int
    total_payables_decimal: Decimal
    net_operating_result_paise: int
    net_operating_result_decimal: Decimal
    net_cash_result_paise: int
    net_cash_result_decimal: Decimal
    active_clients_count: int
    active_vendors_count: int
    total_invoices_count: int
    overdue_invoices_count: int


class BusinessAnalyticsResponse(BaseModel):
    kpis: BusinessOverviewResponse
    ar_aging: ReceivablesAgingResponse
    ap_aging: PayablesAgingResponse
    top_clients: List[Dict[str, Any]]
    top_vendors: List[Dict[str, Any]]


class BusinessActivityResponse(BaseModel):
    id: uuid.UUID
    activity_type: str
    description: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    actor_user_id: Optional[uuid.UUID] = None
    metadata_json: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
