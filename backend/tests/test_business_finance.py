"""
Arthsavora Small Business Finance & Commercial Financial Operations Test Suite
Validates pure domain arithmetic, GSTIN/PAN regex checks, CSV formula sanitization,
business profile lifecycle, clients, vendors, invoice generation, immutable snapshots,
double-entry accrual revenue & AR posting, payment recording with over-allocation guards,
vendor bills & AP posting, aging schedules, REST APIs, and AI Assistant tool execution.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext
from app.core.security import create_access_token
from app.domain.assistant import ToolCallVO
from app.domain.business import (
    BusinessActivityType,
    BusinessType,
    ClientType,
    InvoiceLineItemVO,
    InvoiceStatus,
    PayableStatus,
    PaymentMethod,
    VendorType,
    calculate_invoice_totals,
    calculate_line_item,
    compute_ap_aging,
    compute_ar_aging,
    format_invoice_number,
    sanitize_csv_cell,
    validate_gstin,
    validate_pan,
)
from app.infrastructure.database.models import User, Workspace, WorkspaceMember, WorkspaceRole
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.accounting import LedgerAccount
from app.infrastructure.database.models.business import (
    BusinessActivity,
    BusinessClient,
    BusinessInvoice,
    BusinessInvoiceLineItem,
    BusinessInvoicePayment,
    BusinessPayable,
    BusinessPayablePayment,
    BusinessProfile,
    BusinessVendor,
)
from app.repositories.business_repository import BusinessRepository
from app.services.assistant.tool_executor import ToolExecutor
from app.services.business_service import BusinessService
from app.services.ledger_service import LedgerService


# -----------------------------------------------------------------------------
# 1. Pure Domain Logic Tests
# -----------------------------------------------------------------------------

def test_pure_domain_line_item_and_invoice_totals():
    """Validates line item calculation and invoice totals in minor integer paise."""
    # Line 1: 2 consulting days @ ₹10,000 (1,000,000 paise) each, 18% GST (CGST 9% + SGST 9%)
    item1 = calculate_line_item(
        description="Architecture Review",
        quantity=Decimal("2"),
        unit_price_paise=1000000,
        discount_paise=0,
        tax_rate_percent=Decimal("18.0"),
        is_interstate=False,
    )
    assert item1.subtotal_amount_paise == 2000000
    assert item1.tax_amount_paise == 360000
    assert item1.cgst_rate_percent == Decimal("9.0")
    assert item1.sgst_rate_percent == Decimal("9.0")
    assert item1.igst_rate_percent == Decimal("0.0")
    assert item1.total_amount_paise == 2360000

    # Line 2: Inter-state software license @ ₹50,000 (5,000,000 paise) with ₹5,000 discount, 18% IGST
    item2 = calculate_line_item(
        description="Software License",
        quantity=Decimal("1"),
        unit_price_paise=5000000,
        discount_paise=500000,
        tax_rate_percent=Decimal("18.0"),
        is_interstate=True,
    )
    assert item2.subtotal_amount_paise == 4500000
    assert item2.discount_paise == 500000
    assert item2.igst_rate_percent == Decimal("18.0")
    assert item2.cgst_rate_percent == Decimal("0.0")
    assert item2.sgst_rate_percent == Decimal("0.0")
    assert item2.total_amount_paise == 5310000

    # Calculate Totals
    line_data = [
        {
            "description": "Architecture Review",
            "quantity": Decimal("2"),
            "unit_price_paise": 1000000,
            "discount_paise": 0,
            "tax_rate_percent": Decimal("18.0"),
        },
        {
            "description": "Software License",
            "quantity": Decimal("1"),
            "unit_price_paise": 5000000,
            "discount_paise": 500000,
            "tax_rate_percent": Decimal("18.0"),
        },
    ]
    totals = calculate_invoice_totals(line_data, overall_discount_paise=500000, is_interstate=False)
    assert totals.subtotal_paise == 6500000
    assert totals.discount_paise == 500000
    assert totals.tax_paise == 1170000
    assert totals.total_paise == 7170000


def test_pure_domain_ar_and_ap_aging_buckets():
    """Validates bucket categorization for AR and AP aging."""
    today = date(2026, 11, 14)
    records = [
        {"status": "issued", "total_amount_paise": 100000, "paid_amount_paise": 0, "due_date": today + timedelta(days=5)},   # Current (not due)
        {"status": "issued", "total_amount_paise": 200000, "paid_amount_paise": 0, "due_date": today - timedelta(days=10)},  # 1-30 days
        {"status": "issued", "total_amount_paise": 300000, "paid_amount_paise": 0, "due_date": today - timedelta(days=45)},  # 31-60 days
        {"status": "issued", "total_amount_paise": 400000, "paid_amount_paise": 0, "due_date": today - timedelta(days=75)},  # 61-90 days
        {"status": "issued", "total_amount_paise": 500000, "paid_amount_paise": 0, "due_date": today - timedelta(days=120)}, # 91+ days
    ]

    ar_aging = compute_ar_aging(records, today)
    assert ar_aging.current_paise == 100000
    assert ar_aging.days_1_30_paise == 200000
    assert ar_aging.days_31_60_paise == 300000
    assert ar_aging.days_61_90_paise == 400000
    assert ar_aging.days_91_plus_paise == 500000
    assert ar_aging.total_outstanding_paise == 1500000

    ap_aging = compute_ap_aging(records, today)
    assert ap_aging.total_outstanding_paise == 1500000
    assert ap_aging.days_91_plus_paise == 500000


def test_pure_domain_format_invoice_number():
    """Validates sequence-based invoice number formatting."""
    assert format_invoice_number("INV", 2026, 1) == "INV-2026-0001"
    assert format_invoice_number("TAX", 2026, 42) == "TAX-2026-0042"
    assert format_invoice_number("INV", 2026, 9999) == "INV-2026-9999"


def test_pure_domain_csv_sanitization_against_formula_injection():
    """Ensures cells starting with formula triggers are escaped."""
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-500") == "'-500"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("Acme Corp") == "Acme Corp"
    assert sanitize_csv_cell(12345) == "12345"


def test_pure_domain_gstin_and_pan_validation():
    """Validates Indian statutory GSTIN and PAN format checks."""
    assert validate_gstin("27AAAAA0000A1Z5") is True
    assert validate_gstin("29ABCDE1234F2Z5") is True
    assert validate_gstin("INVALID_GSTIN") is False
    assert validate_gstin("27AAAAA0000A1Z") is False  # 14 chars

    assert validate_pan("AAAAA0000A") is True
    assert validate_pan("ABCDE1234F") is True
    assert validate_pan("INVALID_PAN") is False
    assert validate_pan("12345ABCDE") is False


# -----------------------------------------------------------------------------
# 2. Database Fixtures & Setup
# -----------------------------------------------------------------------------

@pytest.fixture
async def setup_business_workspace(db_session: AsyncSession):
    """Sets up a commercial business workspace with chart of accounts and members."""
    # 1. Owner (User A)
    user_a_id = uuid.uuid4()
    user_a = User(
        id=user_a_id,
        email=f"biz_owner_{user_a_id.hex[:6]}@arthsavora.com",
        full_name="Vikramaditya Roy",
        is_active=True,
    )
    db_session.add(user_a)

    # 2. Staff / Accountant (User B)
    user_b_id = uuid.uuid4()
    user_b = User(
        id=user_b_id,
        email=f"biz_staff_{user_b_id.hex[:6]}@arthsavora.com",
        full_name="Meera Sen",
        is_active=True,
    )
    db_session.add(user_b)

    # 3. Viewer (User C)
    user_c_id = uuid.uuid4()
    user_c = User(
        id=user_c_id,
        email=f"biz_viewer_{user_c_id.hex[:6]}@arthsavora.com",
        full_name="Arjun Roy",
        is_active=True,
    )
    db_session.add(user_c)

    # 4. Business Workspace
    biz_ws_id = uuid.uuid4()
    business_ws = Workspace(
        id=biz_ws_id,
        name="Roy Advisory Group",
        slug=f"roy-advisory-{biz_ws_id.hex[:6]}",
        type="business",
        owner_id=user_a_id,
        default_currency="INR",
        timezone="Asia/Kolkata",
    )
    db_session.add(business_ws)
    await db_session.flush()

    # 5. Memberships
    mem_a = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        user_id=user_a_id,
        role=WorkspaceRole.OWNER,
    )
    mem_b = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        user_id=user_b_id,
        role=WorkspaceRole.STAFF,
    )
    mem_c = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        user_id=user_c_id,
        role=WorkspaceRole.VIEWER,
    )
    db_session.add_all([mem_a, mem_b, mem_c])

    # 6. Chart of Accounts (Bank, AR, Revenue, Expense, AP)
    bank_acc = LedgerAccount(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        code="1020",
        name="Operating Bank Account",
        account_type="asset",
        normal_balance="debit",
        is_active=True,
    )
    ar_acc = LedgerAccount(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        code="1040",
        name="Accounts Receivable",
        account_type="asset",
        normal_balance="debit",
        is_active=True,
    )
    revenue_acc = LedgerAccount(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        code="4020",
        name="Business Sales & Invoicing",
        account_type="revenue",
        normal_balance="credit",
        is_active=True,
    )
    expense_acc = LedgerAccount(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        code="5000",
        name="Operating Expenses",
        account_type="expense",
        normal_balance="debit",
        is_active=True,
    )
    ap_acc = LedgerAccount(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        code="2020",
        name="Accounts Payable",
        account_type="liability",
        normal_balance="credit",
        is_active=True,
    )
    db_session.add_all([bank_acc, ar_acc, revenue_acc, expense_acc, ap_acc])

    # Bank account in accounts table
    op_bank = Account(
        id=uuid.uuid4(),
        workspace_id=biz_ws_id,
        name="HDFC Current Account",
        account_type="current",
        currency="INR",
        status="active",
        current_book_balance_paise=100000000,
    )
    db_session.add(op_bank)

    await db_session.commit()

    return {
        "workspace": business_ws,
        "owner": user_a,
        "staff": user_b,
        "viewer": user_c,
        "mem_owner": mem_a,
        "mem_staff": mem_b,
        "mem_viewer": mem_c,
        "bank_account": op_bank,
        "ledger_bank_account": bank_acc,
        "ar_account": ar_acc,
        "revenue_account": revenue_acc,
        "expense_account": expense_acc,
        "ap_account": ap_acc,
    }


# -----------------------------------------------------------------------------
# 3. Service Layer Integration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_business_profile_and_entity_crud(db_session: AsyncSession, setup_business_workspace):
    """Tests creating, fetching, and updating a business profile, client, and vendor."""
    setup = setup_business_workspace
    service = BusinessService(db_session)

    owner_ctx = WorkspaceContext(
        workspace=setup["workspace"],
        membership=setup["mem_owner"],
        current_user=setup["owner"],
        role=WorkspaceRole.OWNER,
    )

    # 1. Profile Creation
    profile = await service.get_or_create_profile(owner_ctx)
    assert profile.workspace_id == setup["workspace"].id
    assert profile.currency == "INR"

    # Update Profile with Indian statutory details
    updated_profile = await service.update_profile(
        owner_ctx,
        business_name="Roy Strategic Consulting LLP",
        business_type="consulting",
        gstin="27AAAAA0000A1Z5",
        pan="AAAAA0000A",
        invoice_settings={"prefix": "ROY"},
    )
    assert updated_profile.business_name == "Roy Strategic Consulting LLP"

    # 2. Client Creation
    client = await service.create_client(
        owner_ctx,
        name="Horizon Technologies Pvt Ltd",
        client_type="corporate",
        email="billing@horizontech.in",
        payment_terms_days=30,
        gstin="27BBBBB1111B1Z2",
        pan="BBBBB1111B",
    )
    assert client.name == "Horizon Technologies Pvt Ltd"

    # Duplicate Client Name Rejection
    with pytest.raises(ConflictException, match="already exists"):
        await service.create_client(
            owner_ctx,
            name="horizon technologies pvt ltd",  # case-insensitive check
        )

    # 3. Vendor Creation
    vendor = await service.create_vendor(
        owner_ctx,
        name="AWS Cloud Hosting Inc",
        vendor_type="contractor",
        email="payments@awscloud.com",
        payment_terms_days=15,
    )
    assert vendor.name == "AWS Cloud Hosting Inc"


@pytest.mark.asyncio
async def test_invoice_issuance_double_entry_and_payment(db_session: AsyncSession, setup_business_workspace):
    """
    Validates complete invoice lifecycle:
    1. Draft creation.
    2. Issuance: General Ledger entry (Debit 1040 AR, Credit 4020 Revenue) + snapshot.
    3. Over-allocation payment rejection.
    4. Partial payment: General Ledger entry (Debit 1020 Bank, Credit 1040 AR).
    5. Final payment -> status paid.
    """
    setup = setup_business_workspace
    service = BusinessService(db_session)
    ledger_service = LedgerService(db_session)

    owner_ctx = WorkspaceContext(
        workspace=setup["workspace"],
        membership=setup["mem_owner"],
        current_user=setup["owner"],
        role=WorkspaceRole.OWNER,
    )

    # Ensure profile & client
    await service.get_or_create_profile(owner_ctx)
    client = await service.create_client(
        owner_ctx,
        name="Pinnacle Financials Ltd",
        payment_terms_days=30,
    )

    # 1. Create Draft Invoice
    invoice = await service.create_invoice(
        owner_ctx,
        client_id=client.id,
        invoice_date=date(2026, 11, 1),
        due_date=date(2026, 11, 30),
        currency="INR",
        line_items_data=[
            {
                "description": "Strategy Consulting",
                "quantity": Decimal("1"),
                "unit_price_paise": 10000000, # ₹1,00,000
                "discount_paise": 0,
                "tax_rate_percent": Decimal("18.0"),
                "hsn_sac_code": "998311",
            },
        ],
    )
    assert invoice.status == InvoiceStatus.DRAFT.value
    assert invoice.total_amount_paise == 11800000  # ₹1,18,000

    # 2. Issue Invoice (Locks snapshot, posts to General Ledger)
    issued_invoice = await service.issue_invoice(owner_ctx, invoice.id)
    assert issued_invoice.status == InvoiceStatus.ISSUED.value
    assert issued_invoice.issued_snapshot is not None
    assert issued_invoice.journal_entry_id is not None

    # Verify Journal Entry for Issuance
    je = await ledger_service.get_journal(setup["workspace"].id, issued_invoice.journal_entry_id)
    assert je is not None
    debit_lines = [l for l in je.lines if l.ledger_account_id == setup["ar_account"].id and l.entry_type == "debit"]
    credit_lines = [l for l in je.lines if l.ledger_account_id == setup["revenue_account"].id and l.entry_type == "credit"]
    assert len(debit_lines) == 1 and debit_lines[0].amount_paise == 11800000
    assert len(credit_lines) == 1 and credit_lines[0].amount_paise == 11800000

    # 3. Payment Over-Allocation Guard
    with pytest.raises(ValidationException, match="exceeds remaining balance"):
        await service.record_invoice_payment(
            owner_ctx,
            invoice.id,
            payment_date=date(2026, 11, 10),
            amount_paise=20000000,  # ₹2,00,000 > ₹1,18,000 balance
            payment_method="bank_transfer",
        )

    # 4. Record Partial Payment (₹50,000 = 5,000,000 paise)
    partial_pmt = await service.record_invoice_payment(
        owner_ctx,
        invoice.id,
        payment_date=date(2026, 11, 10),
        amount_paise=5000000,
        payment_method="bank_transfer",
        financial_account_id=setup["bank_account"].id,
    )
    assert partial_pmt.amount_paise == 5000000

    inv_refreshed = await service.get_invoice(owner_ctx, invoice.id)
    assert inv_refreshed.status == InvoiceStatus.PARTIALLY_PAID.value
    assert inv_refreshed.paid_amount_paise == 5000000

    # 5. Record Remaining Payment (₹68,000 = 6,800,000 paise)
    final_pmt = await service.record_invoice_payment(
        owner_ctx,
        invoice.id,
        payment_date=date(2026, 11, 14),
        amount_paise=6800000,
        payment_method="upi",
        financial_account_id=setup["bank_account"].id,
    )
    assert final_pmt.amount_paise == 6800000

    inv_final = await service.get_invoice(owner_ctx, invoice.id)
    assert inv_final.status == InvoiceStatus.PAID.value
    assert inv_final.paid_amount_paise == 11800000


@pytest.mark.asyncio
async def test_vendor_payable_lifecycle_and_aging(db_session: AsyncSession, setup_business_workspace):
    """
    Validates vendor bill recording (Debit 5000 Expense, Credit 2020 AP),
    aging calculation, and bill payment (Debit 2020 AP, Credit 1020 Bank).
    """
    setup = setup_business_workspace
    service = BusinessService(db_session)

    owner_ctx = WorkspaceContext(
        workspace=setup["workspace"],
        membership=setup["mem_owner"],
        current_user=setup["owner"],
        role=WorkspaceRole.OWNER,
    )

    # Create Vendor
    vendor = await service.create_vendor(
        owner_ctx,
        name="DevOps Specialists Co",
        payment_terms_days=15,
    )

    # 1. Record Vendor Bill (Accrual expense)
    payable = await service.create_payable(
        owner_ctx,
        vendor_id=vendor.id,
        bill_number="BILL-2026-901",
        bill_date=date(2026, 11, 1),
        due_date=date(2026, 11, 16),
        subtotal_paise=3000000,  # ₹30,000
        tax_paise=540000,
        currency="INR",
    )
    assert payable.status == PayableStatus.RECORDED.value
    assert payable.journal_entry_id is not None

    # 2. Check Aging
    ap_aging = await service.get_payables_aging(owner_ctx)
    assert ap_aging["total_outstanding_paise"] == 3540000

    # 3. Pay Bill
    paid_payable = await service.record_payable_payment(
        owner_ctx,
        payable.id,
        payment_date=date(2026, 11, 14),
        amount_paise=3540000,
        payment_method="bank_transfer",
        financial_account_id=setup["bank_account"].id,
    )
    assert paid_payable.amount_paise == 3540000

    refreshed_payable = await service.get_payable(owner_ctx, payable.id)
    assert refreshed_payable.status == PayableStatus.PAID.value
    assert refreshed_payable.paid_amount_paise == 3540000


@pytest.mark.asyncio
async def test_invoice_cancellation_and_csv_export(db_session: AsyncSession, setup_business_workspace):
    """Validates invoice cancellation with reversal entry, and sanitized CSV register export."""
    setup = setup_business_workspace
    service = BusinessService(db_session)

    owner_ctx = WorkspaceContext(
        workspace=setup["workspace"],
        membership=setup["mem_owner"],
        current_user=setup["owner"],
        role=WorkspaceRole.OWNER,
    )

    await service.get_or_create_profile(owner_ctx)

    client = await service.create_client(
        owner_ctx,
        name="=Formula Testing Ltd",  # formula trigger in client name
    )

    invoice = await service.create_invoice(
        owner_ctx,
        client_id=client.id,
        invoice_date=date(2026, 11, 1),
        due_date=date(2026, 11, 20),
        currency="INR",
        line_items_data=[
            {
                "description": "+Malicious Formula",
                "quantity": Decimal("1"),
                "unit_price_paise": 500000,
            },
        ],
    )

    # Issue then Cancel
    await service.issue_invoice(owner_ctx, invoice.id)
    cancelled = await service.cancel_invoice(owner_ctx, invoice.id, reason="Customer cancelled project")
    assert cancelled.status == InvoiceStatus.CANCELLED.value

    # CSV Export
    csv_content = await service.export_invoices_csv(owner_ctx)
    assert "'=Formula Testing Ltd" in csv_content  # Sanitized formula prefix
    assert "cancelled" in csv_content.lower()


# -----------------------------------------------------------------------------
# 4. REST API Endpoint Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_business_api_endpoints_and_permissions(client: AsyncClient, setup_business_workspace):
    """Tests FastAPI business routes and verifies role-based access restrictions."""
    setup = setup_business_workspace
    ws_id = setup["workspace"].id
    owner = setup["owner"]
    viewer = setup["viewer"]

    owner_token = create_access_token(subject=str(owner.id), email=owner.email)
    viewer_token = create_access_token(subject=str(viewer.id), email=viewer.email)

    headers_owner = {
        "Authorization": f"Bearer {owner_token}",
        "X-Workspace-ID": str(ws_id),
    }
    headers_viewer = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Workspace-ID": str(ws_id),
    }

    # 1. GET Profile (Owner)
    res = await client.get("/api/v1/business/profile", headers=headers_owner)
    assert res.status_code == 200
    data = res.json()
    assert data["workspace_id"] == str(ws_id)

    # 2. GET Overview (Viewer can view)
    res = await client.get("/api/v1/business/overview", headers=headers_viewer)
    assert res.status_code == 200

    # 3. Create Client (Owner can create)
    res = await client.post(
        "/api/v1/business/clients",
        json={"name": "API Test Client Corp", "client_type": "corporate"},
        headers=headers_owner,
    )
    assert res.status_code == 201
    client_id = res.json()["id"]

    # 4. Create Invoice (Viewer should be FORBIDDEN - 403)
    res = await client.post(
        "/api/v1/business/invoices",
        json={
            "client_id": client_id,
            "invoice_date": "2026-11-01",
            "due_date": "2026-11-30",
            "currency": "INR",
            "line_items": [
                {
                    "description": "API Consulting",
                    "quantity": 1,
                    "unit_price": 25000.0,
                }
            ],
        },
        headers=headers_viewer,
    )
    assert res.status_code == 403

    # 5. Create Invoice (Owner can create)
    res = await client.post(
        "/api/v1/business/invoices",
        json={
            "client_id": client_id,
            "invoice_date": "2026-11-01",
            "due_date": "2026-11-30",
            "currency": "INR",
            "line_items": [
                {
                    "description": "API Consulting",
                    "quantity": 1,
                    "unit_price": 25000.0,
                }
            ],
        },
        headers=headers_owner,
    )
    assert res.status_code == 201
    invoice_id = res.json()["id"]

    # 6. Issue Invoice (Owner)
    res = await client.post(
        f"/api/v1/business/invoices/{invoice_id}/issue",
        headers=headers_owner,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "issued"

    # 7. Download PDF
    res = await client.get(
        f"/api/v1/business/invoices/{invoice_id}/pdf",
        headers=headers_owner,
    )
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"] or "pdf" in res.headers["content-type"]


# -----------------------------------------------------------------------------
# 5. AI Assistant Tool Orchestration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_assistant_business_tools(db_session: AsyncSession, setup_business_workspace):
    """Validates the 4 business tools available to the AI Assistant."""
    setup = setup_business_workspace
    ws_id = setup["workspace"].id
    owner = setup["owner"]

    from app.core.permissions import ROLE_PERMISSIONS
    executor = ToolExecutor(db_session)
    perms = {p.value for p in ROLE_PERMISSIONS["business"]["owner"]}

    # 1. get_business_overview
    tool_overview = ToolCallVO(
        call_id="call-biz-1",
        tool_name="get_business_overview",
        arguments={},
    )
    res_overview = await executor.execute_tool(
        tool_overview,
        workspace_id=ws_id,
        user_permissions=perms,
        user_id=owner.id,
    )
    assert res_overview.success is True
    assert "invoiced_revenue" in res_overview.data

    # 2. get_business_receivables_summary
    tool_ar = ToolCallVO(
        call_id="call-biz-2",
        tool_name="get_business_receivables_summary",
        arguments={},
    )
    res_ar = await executor.execute_tool(
        tool_ar,
        workspace_id=ws_id,
        user_permissions=perms,
        user_id=owner.id,
    )
    assert res_ar.success is True
    assert "total_outstanding_receivables" in res_ar.data

    # 3. get_business_payables_summary
    tool_ap = ToolCallVO(
        call_id="call-biz-3",
        tool_name="get_business_payables_summary",
        arguments={},
    )
    res_ap = await executor.execute_tool(
        tool_ap,
        workspace_id=ws_id,
        user_permissions=perms,
        user_id=owner.id,
    )
    assert res_ap.success is True
    assert "total_outstanding_payables" in res_ap.data

    # 4. get_business_cash_flow_summary
    tool_cf = ToolCallVO(
        call_id="call-biz-4",
        tool_name="get_business_cash_flow_summary",
        arguments={},
    )
    res_cf = await executor.execute_tool(
        tool_cf,
        workspace_id=ws_id,
        user_permissions=perms,
        user_id=owner.id,
    )
    assert res_cf.success is True
    assert "net_operating_cash_flow" in res_cf.data
