"""
Arthsavora Business Finance REST API Endpoints
Provides authenticated HTTP interfaces for business profiles, clients, vendors,
invoices, payments, payables, receivables/payables aging, analytics, and exports.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.business_schema import (
    BusinessActivityResponse,
    BusinessAnalyticsResponse,
    BusinessClientCreate,
    BusinessClientResponse,
    BusinessClientUpdate,
    BusinessInvoiceCreate,
    BusinessInvoicePaymentCreate,
    BusinessInvoicePaymentResponse,
    BusinessInvoiceResponse,
    BusinessOverviewResponse,
    BusinessPayableCreate,
    BusinessPayablePaymentCreate,
    BusinessPayablePaymentResponse,
    BusinessPayableResponse,
    BusinessProfileResponse,
    BusinessProfileUpdate,
    BusinessVendorCreate,
    BusinessVendorResponse,
    BusinessVendorUpdate,
    CancelInvoiceRequest,
    InvoiceLineItemResponse,
    PayablesAgingResponse,
    ReceivablesAgingResponse,
    decimal_to_paise,
    paise_to_decimal,
)
from app.services.business_service import BusinessService

router = APIRouter(tags=["Business Finance"])


def _map_invoice_response(inv) -> BusinessInvoiceResponse:
    """Helper to transform ORM BusinessInvoice to BusinessInvoiceResponse with decimal conversions."""
    subtotal_dec = paise_to_decimal(inv.subtotal_amount_paise)
    disc_dec = paise_to_decimal(inv.discount_amount_paise)
    tax_dec = paise_to_decimal(inv.tax_amount_paise)
    total_dec = paise_to_decimal(inv.total_amount_paise)
    paid_dec = paise_to_decimal(inv.paid_amount_paise)
    balance_paise = max(0, inv.total_amount_paise - inv.paid_amount_paise)
    balance_dec = paise_to_decimal(balance_paise)

    line_items = [
        InvoiceLineItemResponse(
            id=li.id,
            description=li.description,
            hsn_sac_code=li.hsn_sac_code,
            quantity=li.quantity,
            unit_price_paise=li.unit_price_paise,
            unit_price_decimal=paise_to_decimal(li.unit_price_paise),
            discount_paise=li.discount_paise,
            tax_rate_percent=li.tax_rate_percent,
            cgst_rate_percent=li.cgst_rate_percent,
            sgst_rate_percent=li.sgst_rate_percent,
            igst_rate_percent=li.igst_rate_percent,
            tax_amount_paise=li.tax_amount_paise,
            tax_amount_decimal=paise_to_decimal(li.tax_amount_paise),
            total_amount_paise=li.total_amount_paise,
            total_amount_decimal=paise_to_decimal(li.total_amount_paise),
            line_order=li.line_order,
        )
        for li in (inv.line_items or [])
    ]

    payments = [
        BusinessInvoicePaymentResponse(
            id=p.id,
            invoice_id=p.invoice_id,
            payment_date=p.payment_date,
            amount_paise=p.amount_paise,
            amount_decimal=paise_to_decimal(p.amount_paise),
            payment_method=p.payment_method,
            reference_number=p.reference_number,
            financial_account_id=p.financial_account_id,
            journal_entry_id=p.journal_entry_id,
            notes=p.notes,
            created_at=p.created_at,
        )
        for p in (inv.payments or [])
    ]

    return BusinessInvoiceResponse(
        id=inv.id,
        workspace_id=inv.workspace_id,
        client_id=inv.client_id,
        client_name=inv.client.name if inv.client else None,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        currency=inv.currency,
        subtotal_amount_paise=inv.subtotal_amount_paise,
        subtotal_amount_decimal=subtotal_dec,
        discount_amount_paise=inv.discount_amount_paise,
        discount_amount_decimal=disc_dec,
        tax_amount_paise=inv.tax_amount_paise,
        tax_amount_decimal=tax_dec,
        total_amount_paise=inv.total_amount_paise,
        total_amount_decimal=total_dec,
        paid_amount_paise=inv.paid_amount_paise,
        paid_amount_decimal=paid_dec,
        balance_amount_paise=balance_paise,
        balance_amount_decimal=balance_dec,
        status=inv.status,
        notes=inv.notes,
        payment_instructions=inv.payment_instructions,
        issued_at=inv.issued_at,
        cancelled_at=inv.cancelled_at,
        cancellation_reason=inv.cancellation_reason,
        version=inv.version,
        journal_entry_id=inv.journal_entry_id,
        line_items=line_items,
        payments=payments,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
    )


def _map_payable_response(pay) -> BusinessPayableResponse:
    """Helper to transform ORM BusinessPayable to BusinessPayableResponse with decimal conversions."""
    subtotal_dec = paise_to_decimal(pay.subtotal_amount_paise)
    tax_dec = paise_to_decimal(pay.tax_amount_paise)
    total_dec = paise_to_decimal(pay.total_amount_paise)
    paid_dec = paise_to_decimal(pay.paid_amount_paise)
    balance_paise = max(0, pay.total_amount_paise - pay.paid_amount_paise)
    balance_dec = paise_to_decimal(balance_paise)

    payments = [
        BusinessPayablePaymentResponse(
            id=p.id,
            payable_id=p.payable_id,
            payment_date=p.payment_date,
            amount_paise=p.amount_paise,
            amount_decimal=paise_to_decimal(p.amount_paise),
            payment_method=p.payment_method,
            reference_number=p.reference_number,
            financial_account_id=p.financial_account_id,
            journal_entry_id=p.journal_entry_id,
            notes=p.notes,
            created_at=p.created_at,
        )
        for p in (pay.payments or [])
    ]

    return BusinessPayableResponse(
        id=pay.id,
        workspace_id=pay.workspace_id,
        vendor_id=pay.vendor_id,
        vendor_name=pay.vendor.name if pay.vendor else None,
        bill_number=pay.bill_number,
        bill_date=pay.bill_date,
        due_date=pay.due_date,
        currency=pay.currency,
        subtotal_amount_paise=pay.subtotal_amount_paise,
        subtotal_amount_decimal=subtotal_dec,
        tax_amount_paise=pay.tax_amount_paise,
        tax_amount_decimal=tax_dec,
        total_amount_paise=pay.total_amount_paise,
        total_amount_decimal=total_dec,
        paid_amount_paise=pay.paid_amount_paise,
        paid_amount_decimal=paid_dec,
        balance_amount_paise=balance_paise,
        balance_amount_decimal=balance_dec,
        status=pay.status,
        category_id=pay.category_id,
        document_id=pay.document_id,
        journal_entry_id=pay.journal_entry_id,
        notes=pay.notes,
        payments=payments,
        created_at=pay.created_at,
        updated_at=pay.updated_at,
    )


# ---------------------------------------------------------------------------
# Business Profile Routes
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=BusinessProfileResponse)
async def get_business_profile(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves business profile configuration for the active workspace."""
    service = BusinessService(db)
    return await service.get_or_create_profile(context)


@router.put("/profile", response_model=BusinessProfileResponse)
async def update_business_profile(
    payload: BusinessProfileUpdate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_BUSINESS_PROFILE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Updates business profile metadata, tax identifiers, and invoice configuration."""
    service = BusinessService(db)
    return await service.update_profile(
        context=context,
        business_name=payload.business_name,
        business_type=payload.business_type,
        business_description=payload.business_description,
        business_email=payload.business_email,
        business_phone=payload.business_phone,
        business_address=payload.business_address,
        country=payload.country,
        currency=payload.currency,
        financial_year_start_month=payload.financial_year_start_month,
        timezone_str=payload.timezone,
        gstin=payload.gstin,
        pan=payload.pan,
        tax_configuration=payload.tax_configuration,
        invoice_settings=payload.invoice_settings,
    )


# ---------------------------------------------------------------------------
# Business Overview & KPIs
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=BusinessOverviewResponse)
async def get_business_overview(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Provides high-level commercial KPIs across invoices, payments, and payables."""
    service = BusinessService(db)
    kpis = await service.get_overview(context)
    return BusinessOverviewResponse(
        invoiced_revenue_paise=kpis["invoiced_revenue_paise"],
        invoiced_revenue_decimal=paise_to_decimal(kpis["invoiced_revenue_paise"]),
        collected_revenue_paise=kpis["collected_revenue_paise"],
        collected_revenue_decimal=paise_to_decimal(kpis["collected_revenue_paise"]),
        total_receivables_paise=kpis["total_receivables_paise"],
        total_receivables_decimal=paise_to_decimal(kpis["total_receivables_paise"]),
        total_bills_paise=kpis["total_bills_paise"],
        total_bills_decimal=paise_to_decimal(kpis["total_bills_paise"]),
        paid_bills_paise=kpis["paid_bills_paise"],
        paid_bills_decimal=paise_to_decimal(kpis["paid_bills_paise"]),
        total_payables_paise=kpis["total_payables_paise"],
        total_payables_decimal=paise_to_decimal(kpis["total_payables_paise"]),
        net_operating_result_paise=kpis["net_operating_result_paise"],
        net_operating_result_decimal=paise_to_decimal(kpis["net_operating_result_paise"]),
        net_cash_result_paise=kpis["net_cash_result_paise"],
        net_cash_result_decimal=paise_to_decimal(kpis["net_cash_result_paise"]),
        active_clients_count=kpis["active_clients_count"],
        active_vendors_count=kpis["active_vendors_count"],
        total_invoices_count=kpis["total_invoices_count"],
        overdue_invoices_count=kpis["overdue_invoices_count"],
    )


# ---------------------------------------------------------------------------
# Client Management Routes
# ---------------------------------------------------------------------------

@router.get("/clients", response_model=List[BusinessClientResponse])
async def list_clients(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Lists business clients with search and status filtering."""
    service = BusinessService(db)
    clients, _ = await service.list_clients(context, search=search, status=status, limit=limit, offset=offset)
    return clients


@router.post("/clients", response_model=BusinessClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: BusinessClientCreate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_CLIENTS)),
    db: AsyncSession = Depends(get_db_session),
):
    """Creates a new business client with duplicate name checking."""
    service = BusinessService(db)
    return await service.create_client(
        context=context,
        name=payload.name,
        client_type=payload.client_type,
        email=payload.email,
        phone=payload.phone,
        billing_address=payload.billing_address,
        gstin=payload.gstin,
        pan=payload.pan,
        payment_terms_days=payload.payment_terms_days,
        currency=payload.currency,
        notes=payload.notes,
    )


@router.get("/clients/{client_id}", response_model=BusinessClientResponse)
async def get_client(
    client_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves single client by id."""
    service = BusinessService(db)
    return await service.get_client(context, client_id)


@router.put("/clients/{client_id}", response_model=BusinessClientResponse)
async def update_client(
    client_id: uuid.UUID,
    payload: BusinessClientUpdate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_CLIENTS)),
    db: AsyncSession = Depends(get_db_session),
):
    """Updates client attributes."""
    service = BusinessService(db)
    return await service.update_client(
        context=context,
        client_id=client_id,
        name=payload.name,
        client_type=payload.client_type,
        email=payload.email,
        phone=payload.phone,
        billing_address=payload.billing_address,
        gstin=payload.gstin,
        pan=payload.pan,
        payment_terms_days=payload.payment_terms_days,
        currency=payload.currency,
        notes=payload.notes,
        status=payload.status,
    )


# ---------------------------------------------------------------------------
# Vendor Management Routes
# ---------------------------------------------------------------------------

@router.get("/vendors", response_model=List[BusinessVendorResponse])
async def list_vendors(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Lists business vendors with search and status filtering."""
    service = BusinessService(db)
    vendors, _ = await service.list_vendors(context, search=search, status=status, limit=limit, offset=offset)
    return vendors


@router.post("/vendors", response_model=BusinessVendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: BusinessVendorCreate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_VENDORS)),
    db: AsyncSession = Depends(get_db_session),
):
    """Creates a new vendor with duplicate checking."""
    service = BusinessService(db)
    return await service.create_vendor(
        context=context,
        name=payload.name,
        vendor_type=payload.vendor_type,
        email=payload.email,
        phone=payload.phone,
        billing_details=payload.billing_details,
        gstin=payload.gstin,
        pan=payload.pan,
        payment_terms_days=payload.payment_terms_days,
        notes=payload.notes,
    )


@router.get("/vendors/{vendor_id}", response_model=BusinessVendorResponse)
async def get_vendor(
    vendor_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves vendor by id."""
    service = BusinessService(db)
    return await service.get_vendor(context, vendor_id)


@router.put("/vendors/{vendor_id}", response_model=BusinessVendorResponse)
async def update_vendor(
    vendor_id: uuid.UUID,
    payload: BusinessVendorUpdate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_VENDORS)),
    db: AsyncSession = Depends(get_db_session),
):
    """Updates vendor attributes."""
    service = BusinessService(db)
    return await service.update_vendor(
        context=context,
        vendor_id=vendor_id,
        name=payload.name,
        vendor_type=payload.vendor_type,
        email=payload.email,
        phone=payload.phone,
        billing_details=payload.billing_details,
        gstin=payload.gstin,
        pan=payload.pan,
        payment_terms_days=payload.payment_terms_days,
        notes=payload.notes,
        status=payload.status,
    )


# ---------------------------------------------------------------------------
# Invoicing Routes
# ---------------------------------------------------------------------------

@router.get("/invoices", response_model=List[BusinessInvoiceResponse])
async def list_invoices(
    client_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Lists business invoices with filters."""
    service = BusinessService(db)
    invoices, _ = await service.list_invoices(
        context=context,
        client_id=client_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return [_map_invoice_response(inv) for inv in invoices]


@router.post("/invoices", response_model=BusinessInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: BusinessInvoiceCreate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_INVOICES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Creates a draft invoice with exact minor unit calculations."""
    service = BusinessService(db)
    raw_lines = [
        {
            "description": li.description,
            "hsn_sac_code": li.hsn_sac_code,
            "quantity": li.quantity,
            "unit_price_paise": decimal_to_paise(li.unit_price),
            "discount_paise": decimal_to_paise(li.discount),
            "tax_rate_percent": li.tax_rate_percent,
            "line_order": li.line_order,
        }
        for li in payload.line_items
    ]

    invoice = await service.create_invoice(
        context=context,
        client_id=payload.client_id,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        line_items_data=raw_lines,
        currency=payload.currency,
        overall_discount_paise=decimal_to_paise(payload.overall_discount),
        is_interstate=payload.is_interstate,
        custom_invoice_number=payload.custom_invoice_number,
        notes=payload.notes,
        payment_instructions=payload.payment_instructions,
    )
    return _map_invoice_response(invoice)


@router.get("/invoices/{invoice_id}", response_model=BusinessInvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves invoice with line items, payments, and client."""
    service = BusinessService(db)
    invoice = await service.get_invoice(context, invoice_id)
    return _map_invoice_response(invoice)


@router.post("/invoices/{invoice_id}/issue", response_model=BusinessInvoiceResponse)
async def issue_invoice(
    invoice_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_INVOICES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Issues invoice, locks immutable snapshot, and posts double-entry accrual entry."""
    service = BusinessService(db)
    invoice = await service.issue_invoice(context, invoice_id)
    return _map_invoice_response(invoice)


@router.post("/invoices/{invoice_id}/cancel", response_model=BusinessInvoiceResponse)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    payload: CancelInvoiceRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_INVOICES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Cancels invoice and reverses General Ledger journal entry."""
    service = BusinessService(db)
    invoice = await service.cancel_invoice(context, invoice_id, reason=payload.reason)
    return _map_invoice_response(invoice)


@router.post("/invoices/{invoice_id}/payments", response_model=BusinessInvoicePaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_invoice_payment(
    invoice_id: uuid.UUID,
    payload: BusinessInvoicePaymentCreate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_INVOICES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Records payment allocation against invoice and posts double-entry entry."""
    service = BusinessService(db)
    payment = await service.record_invoice_payment(
        context=context,
        invoice_id=invoice_id,
        payment_date=payload.payment_date,
        amount_paise=decimal_to_paise(payload.amount),
        payment_method=payload.payment_method,
        reference_number=payload.reference_number,
        financial_account_id=payload.financial_account_id,
        notes=payload.notes,
    )
    return BusinessInvoicePaymentResponse(
        id=payment.id,
        invoice_id=payment.invoice_id,
        payment_date=payment.payment_date,
        amount_paise=payment.amount_paise,
        amount_decimal=paise_to_decimal(payment.amount_paise),
        payment_method=payment.payment_method,
        reference_number=payment.reference_number,
        financial_account_id=payment.financial_account_id,
        journal_entry_id=payment.journal_entry_id,
        notes=payment.notes,
        created_at=payment.created_at,
    )


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Renders printable HTML document for the invoice."""
    service = BusinessService(db)
    html = await service.generate_invoice_html(context, invoice_id)
    return Response(content=html, media_type="text/html")


# ---------------------------------------------------------------------------
# Payables (Vendor Bills) Routes
# ---------------------------------------------------------------------------

@router.get("/payables", response_model=List[BusinessPayableResponse])
async def list_payables(
    vendor_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Lists vendor bills with filters."""
    service = BusinessService(db)
    payables, _ = await service.list_payables(
        context=context,
        vendor_id=vendor_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return [_map_payable_response(pay) for pay in payables]


@router.post("/payables", response_model=BusinessPayableResponse, status_code=status.HTTP_201_CREATED)
async def create_payable(
    payload: BusinessPayableCreate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_PAYABLES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Records a vendor bill and posts double-entry accrual entry."""
    service = BusinessService(db)
    payable = await service.create_payable(
        context=context,
        vendor_id=payload.vendor_id,
        bill_date=payload.bill_date,
        due_date=payload.due_date,
        subtotal_paise=decimal_to_paise(payload.subtotal_amount),
        tax_paise=decimal_to_paise(payload.tax_amount),
        currency=payload.currency,
        bill_number=payload.bill_number,
        category_id=payload.category_id,
        document_id=payload.document_id,
        notes=payload.notes,
    )
    return _map_payable_response(payable)


@router.get("/payables/{payable_id}", response_model=BusinessPayableResponse)
async def get_payable(
    payable_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves payable by id."""
    service = BusinessService(db)
    payable = await service.get_payable(context, payable_id)
    return _map_payable_response(payable)


@router.post("/payables/{payable_id}/payments", response_model=BusinessPayablePaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payable_payment(
    payable_id: uuid.UUID,
    payload: BusinessPayablePaymentCreate,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_PAYABLES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Records payment against vendor bill and posts double-entry entry."""
    service = BusinessService(db)
    payment = await service.record_payable_payment(
        context=context,
        payable_id=payable_id,
        payment_date=payload.payment_date,
        amount_paise=decimal_to_paise(payload.amount),
        payment_method=payload.payment_method,
        reference_number=payload.reference_number,
        financial_account_id=payload.financial_account_id,
        notes=payload.notes,
    )
    return BusinessPayablePaymentResponse(
        id=payment.id,
        payable_id=payment.payable_id,
        payment_date=payment.payment_date,
        amount_paise=payment.amount_paise,
        amount_decimal=paise_to_decimal(payment.amount_paise),
        payment_method=payment.payment_method,
        reference_number=payment.reference_number,
        financial_account_id=payment.financial_account_id,
        journal_entry_id=payment.journal_entry_id,
        notes=payment.notes,
        created_at=payment.created_at,
    )


# ---------------------------------------------------------------------------
# Receivables & Payables Aging Schedules
# ---------------------------------------------------------------------------

@router.get("/receivables", response_model=ReceivablesAgingResponse)
async def get_receivables_aging(
    as_of_date: Optional[date] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Calculates Accounts Receivable (AR) aging buckets."""
    service = BusinessService(db)
    res = await service.get_receivables_aging(context, as_of_date=as_of_date)
    return ReceivablesAgingResponse(
        current_paise=res["current_paise"],
        current_decimal=paise_to_decimal(res["current_paise"]),
        days_1_30_paise=res["days_1_30_paise"],
        days_1_30_decimal=paise_to_decimal(res["days_1_30_paise"]),
        days_31_60_paise=res["days_31_60_paise"],
        days_31_60_decimal=paise_to_decimal(res["days_31_60_paise"]),
        days_61_90_paise=res["days_61_90_paise"],
        days_61_90_decimal=paise_to_decimal(res["days_61_90_paise"]),
        days_91_plus_paise=res["days_91_plus_paise"],
        days_91_plus_decimal=paise_to_decimal(res["days_91_plus_paise"]),
        total_outstanding_paise=res["total_outstanding_paise"],
        total_outstanding_decimal=paise_to_decimal(res["total_outstanding_paise"]),
    )


@router.get("/payables/summary", response_model=PayablesAgingResponse)
async def get_payables_summary(
    as_of_date: Optional[date] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Calculates Accounts Payable (AP) aging buckets."""
    service = BusinessService(db)
    res = await service.get_payables_aging(context, as_of_date=as_of_date)
    return PayablesAgingResponse(
        current_paise=res["current_paise"],
        current_decimal=paise_to_decimal(res["current_paise"]),
        days_1_30_paise=res["days_1_30_paise"],
        days_1_30_decimal=paise_to_decimal(res["days_1_30_paise"]),
        days_31_60_paise=res["days_31_60_paise"],
        days_31_60_decimal=paise_to_decimal(res["days_31_60_paise"]),
        days_61_90_paise=res["days_61_90_paise"],
        days_61_90_decimal=paise_to_decimal(res["days_61_90_paise"]),
        days_91_plus_paise=res["days_91_plus_paise"],
        days_91_plus_decimal=paise_to_decimal(res["days_91_plus_paise"]),
        total_outstanding_paise=res["total_outstanding_paise"],
        total_outstanding_decimal=paise_to_decimal(res["total_outstanding_paise"]),
    )


# ---------------------------------------------------------------------------
# Business Analytics & Reports
# ---------------------------------------------------------------------------

@router.get("/analytics", response_model=BusinessAnalyticsResponse)
async def get_business_analytics(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves business intelligence, top clients, top vendors, and aging."""
    service = BusinessService(db)
    data = await service.get_analytics_summary(context)
    kpis = data["kpis"]
    ar_aging = data["ar_aging"]
    ap_aging = data["ap_aging"]

    kpis_resp = BusinessOverviewResponse(
        invoiced_revenue_paise=kpis["invoiced_revenue_paise"],
        invoiced_revenue_decimal=paise_to_decimal(kpis["invoiced_revenue_paise"]),
        collected_revenue_paise=kpis["collected_revenue_paise"],
        collected_revenue_decimal=paise_to_decimal(kpis["collected_revenue_paise"]),
        total_receivables_paise=kpis["total_receivables_paise"],
        total_receivables_decimal=paise_to_decimal(kpis["total_receivables_paise"]),
        total_bills_paise=kpis["total_bills_paise"],
        total_bills_decimal=paise_to_decimal(kpis["total_bills_paise"]),
        paid_bills_paise=kpis["paid_bills_paise"],
        paid_bills_decimal=paise_to_decimal(kpis["paid_bills_paise"]),
        total_payables_paise=kpis["total_payables_paise"],
        total_payables_decimal=paise_to_decimal(kpis["total_payables_paise"]),
        net_operating_result_paise=kpis["net_operating_result_paise"],
        net_operating_result_decimal=paise_to_decimal(kpis["net_operating_result_paise"]),
        net_cash_result_paise=kpis["net_cash_result_paise"],
        net_cash_result_decimal=paise_to_decimal(kpis["net_cash_result_paise"]),
        active_clients_count=kpis["active_clients_count"],
        active_vendors_count=kpis["active_vendors_count"],
        total_invoices_count=kpis["total_invoices_count"],
        overdue_invoices_count=kpis["overdue_invoices_count"],
    )

    ar_resp = ReceivablesAgingResponse(
        current_paise=ar_aging["current_paise"],
        current_decimal=paise_to_decimal(ar_aging["current_paise"]),
        days_1_30_paise=ar_aging["days_1_30_paise"],
        days_1_30_decimal=paise_to_decimal(ar_aging["days_1_30_paise"]),
        days_31_60_paise=ar_aging["days_31_60_paise"],
        days_31_60_decimal=paise_to_decimal(ar_aging["days_31_60_paise"]),
        days_61_90_paise=ar_aging["days_61_90_paise"],
        days_61_90_decimal=paise_to_decimal(ar_aging["days_61_90_paise"]),
        days_91_plus_paise=ar_aging["days_91_plus_paise"],
        days_91_plus_decimal=paise_to_decimal(ar_aging["days_91_plus_paise"]),
        total_outstanding_paise=ar_aging["total_outstanding_paise"],
        total_outstanding_decimal=paise_to_decimal(ar_aging["total_outstanding_paise"]),
    )

    ap_resp = PayablesAgingResponse(
        current_paise=ap_aging["current_paise"],
        current_decimal=paise_to_decimal(ap_aging["current_paise"]),
        days_1_30_paise=ap_aging["days_1_30_paise"],
        days_1_30_decimal=paise_to_decimal(ap_aging["days_1_30_paise"]),
        days_31_60_paise=ap_aging["days_31_60_paise"],
        days_31_60_decimal=paise_to_decimal(ap_aging["days_31_60_paise"]),
        days_61_90_paise=ap_aging["days_61_90_paise"],
        days_61_90_decimal=paise_to_decimal(ap_aging["days_61_90_paise"]),
        days_91_plus_paise=ap_aging["days_91_plus_paise"],
        days_91_plus_decimal=paise_to_decimal(ap_aging["days_91_plus_paise"]),
        total_outstanding_paise=ap_aging["total_outstanding_paise"],
        total_outstanding_decimal=paise_to_decimal(ap_aging["total_outstanding_paise"]),
    )

    return BusinessAnalyticsResponse(
        kpis=kpis_resp,
        ar_aging=ar_resp,
        ap_aging=ap_resp,
        top_clients=data["top_clients"],
        top_vendors=data["top_vendors"],
    )


@router.get("/reports/export")
async def export_invoices_report(
    format: str = Query("csv"),
    context: WorkspaceContext = Depends(require_permission(Permission.EXPORT_ANALYTICS)),
    db: AsyncSession = Depends(get_db_session),
):
    """Exports invoice register to CSV with formula injection sanitization."""
    service = BusinessService(db)
    csv_content = await service.export_invoices_csv(context)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="invoices.csv"'},
    )


@router.get("/activity", response_model=List[BusinessActivityResponse])
async def list_business_activities(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_BUSINESS_FINANCE)),
    db: AsyncSession = Depends(get_db_session),
):
    """Lists recent chronological business activities."""
    service = BusinessService(db)
    return await service.list_activities(context, limit=limit, offset=offset)
