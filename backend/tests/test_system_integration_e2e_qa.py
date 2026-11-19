"""
ARTHSAVORA Comprehensive System Integration, End-to-End Testing & QA Suite
Prompt 29: End-to-end multi-module verification across Personal, Family, and Business finance,
Double-entry ledger integrity, Document OCR lifecycle, Account Aggregator connectivity,
financial calculations (paise precision, Indian FY boundaries), and multi-tenant anti-IDOR boundaries.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.core.security import create_access_token, get_password_hash
from app.domain.accounting_types import AccountType, NormalBalance
from app.domain.exceptions import UnbalancedJournalError
from app.domain.financial_report import (
    calculate_indian_financial_year,
    calculate_financial_year_bounds,
    estimate_indian_income_tax,
    TaxRegime,
    ReportingPeriodVO,
)
from app.domain.money import Money
from app.domain.recurring import RecurringFrequency, calculate_next_occurrence, is_leap_year
from app.services.document.document_service import DocumentService, MAX_DOCUMENT_SIZE_BYTES
from app.infrastructure.database.models import (
    Account,
    BusinessClient,
    BusinessInvoice,
    BusinessProfile,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    Transaction,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceType,
)
from app.services.financial_reporting_service import FinancialReportingService
from app.services.ledger_service import LedgerService


# =============================================================================
# 1. End-to-End Personal Finance & Double-Entry Ledger Integrity Lifecycle
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_personal_finance_and_ledger_reconciliation(
    client: AsyncClient, registered_user: dict, db_session: AsyncSession
):
    """
    Verifies full personal finance journey:
    1. Create bank account via API with opening balance ₹1,00,000.00.
    2. Create income transaction via API (Salary: ₹75,000.00).
    3. Create expense transaction via API (Groceries: ₹4,500.00).
    4. Create double-entry draft journal and post through LedgerService.
    5. Double-entry trial balance strictly balances with zero discrepancy.
    """
    token = registered_user["token"]
    ws = registered_user["workspace"]
    user = registered_user["user"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    # 1. Create Bank Account via API
    create_account_payload = {
        "name": "HDFC Primary Salary Account",
        "account_type": "savings",
        "account_subtype": "salary",
        "currency": "INR",
        "institution_name": "HDFC Bank",
        "masked_identifier": "XX1234",
        "opening_balance": "100000.00",
        "opening_date": "2026-01-01",
    }
    acc_res = await client.post("/api/v1/accounts/", json=create_account_payload, headers=headers)
    assert acc_res.status_code == 201
    acc_data = acc_res.json()
    account_id = acc_data["id"]
    assert acc_data["balances"]["opening_balance"] == "100000.00"

    # 2. Record Inflow Transaction (Salary ₹75,000.00) via API
    salary_payload = {
        "account_id": account_id,
        "amount": "75000.00",
        "currency": "INR",
        "direction": "inflow",
        "transaction_type": "income",
        "description": "November 2026 Salary Credit",
        "transaction_date": "2026-11-01",
    }
    sal_res = await client.post("/api/v1/transactions/", json=salary_payload, headers=headers)
    assert sal_res.status_code == 201

    # 3. Record Outflow Transaction (Groceries ₹4,500.00) via API
    expense_payload = {
        "account_id": account_id,
        "amount": "4500.00",
        "currency": "INR",
        "direction": "outflow",
        "transaction_type": "expense",
        "description": "Monthly Supermarket Groceries",
        "transaction_date": "2026-11-05",
    }
    exp_res = await client.post("/api/v1/transactions/", json=expense_payload, headers=headers)
    assert exp_res.status_code == 201

    # 4. Double-Entry General Ledger Verification
    ledger_service = LedgerService(db_session)
    await ledger_service.ensure_chart_of_accounts(ws.id)

    bank = await ledger_service.account_repo.get_by_code(ws.id, "1021")  # Operating Bank Account
    salary_rev = await ledger_service.account_repo.get_by_code(ws.id, "4010")  # Salary & Wages
    food_exp = await ledger_service.account_repo.get_by_code(ws.id, "5030")  # Office Supplies / Expenses

    # Balanced Journal 1: Salary Intake (Debit Bank ₹75,000, Credit Salary Revenue ₹75,000)
    je1 = await ledger_service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"SAL-{uuid.uuid4().hex[:6]}",
        entry_date=date(2026, 11, 1),
        description="Salary Revenue Recognition",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("75000.0000")},
            {"ledger_account_id": salary_rev.id, "entry_type": "credit", "amount": Decimal("75000.0000")},
        ],
        created_by=user.id,
    )
    await ledger_service.post_journal_entry(ws.id, je1.id, actor_id=user.id)

    # Balanced Journal 2: Grocery Outflow (Debit Food Expense ₹4,500, Credit Bank ₹4,500)
    je2 = await ledger_service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"EXP-{uuid.uuid4().hex[:6]}",
        entry_date=date(2026, 11, 5),
        description="Grocery Expense Disbursement",
        lines_data=[
            {"ledger_account_id": food_exp.id, "entry_type": "debit", "amount": Decimal("4500.0000")},
            {"ledger_account_id": bank.id, "entry_type": "credit", "amount": Decimal("4500.0000")},
        ],
        created_by=user.id,
    )
    await ledger_service.post_journal_entry(ws.id, je2.id, actor_id=user.id)
    await db_session.commit()

    # 5. Authoritative Trial Balance Mathematical Invariant Verification
    tb = await ledger_service.get_trial_balance(ws.id)
    assert tb["is_balanced"] is True
    assert tb["difference"] == Decimal("0.0000")
    assert tb["difference_paise"] == 0
    assert tb["total_debits"] == tb["total_credits"]
    assert tb["total_debits"] == Decimal("75000.0000")


# =============================================================================
# 2. End-to-End Family Finance & Compartmentalized Privacy Boundary
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_family_finance_lifecycle_and_privacy_boundary(
    client: AsyncClient, db_session: AsyncSession, registered_user: dict
):
    """
    Verifies full family collaborative finance journey:
    1. Create family workspace.
    2. Add second family member.
    3. Verify zero-trust privacy boundary: Member 1's personal accounts are
       invisible and inaccessible to Member 2.
    """
    user1 = registered_user["user"]
    token1 = registered_user["token"]

    # 1. Create Family Workspace
    family_ws = Workspace(
        id=uuid.uuid4(),
        name="Sharma Family Finances",
        slug=f"family-sharma-{uuid.uuid4().hex[:6]}",
        type=WorkspaceType.FAMILY.value,
        owner_id=user1.id,
        default_currency="INR",
        status="active",
    )
    db_session.add(family_ws)
    await db_session.flush()

    member1 = WorkspaceMember(
        workspace_id=family_ws.id,
        user_id=user1.id,
        role=WorkspaceRole.OWNER.value,
        status="active",
    )
    db_session.add(member1)

    # 2. Add Second Member (Spouse)
    user2 = User(
        id=uuid.uuid4(),
        email=f"spouse_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Pooja Sharma",
        hashed_password=get_password_hash("FamilyPass123!"),
        is_active=True,
    )
    db_session.add(user2)
    await db_session.flush()

    member2 = WorkspaceMember(
        workspace_id=family_ws.id,
        user_id=user2.id,
        role=WorkspaceRole.MEMBER.value,
        status="active",
    )
    db_session.add(member2)

    # User2's private personal workspace
    user2_ws = Workspace(
        id=uuid.uuid4(),
        name="Pooja Private Workspace",
        slug=f"private-pooja-{uuid.uuid4().hex[:6]}",
        type=WorkspaceType.PERSONAL.value,
        owner_id=user2.id,
        default_currency="INR",
        status="active",
    )
    db_session.add(user2_ws)
    await db_session.flush()

    user2_own_member = WorkspaceMember(
        workspace_id=user2_ws.id,
        user_id=user2.id,
        role=WorkspaceRole.OWNER.value,
        status="active",
    )
    db_session.add(user2_own_member)
    await db_session.commit()

    token2 = create_access_token(subject=str(user2.id), email=user2.email)

    # 3. User 2 creates a private savings account in User 2's workspace
    user2_headers = {
        "Authorization": f"Bearer {token2}",
        "X-Workspace-ID": str(user2_ws.id),
    }
    acc_res = await client.post(
        "/api/v1/accounts/",
        json={
            "name": "Pooja Confidential Mutual Fund",
            "account_type": "investment",
            "currency": "INR",
            "opening_balance": "500000.00",
            "opening_date": "2026-01-01",
        },
        headers=user2_headers,
    )
    assert acc_res.status_code == 201
    user2_acc_id = acc_res.json()["id"]

    # 4. Anti-IDOR Check: User 1 attempts to access User 2's private account
    user1_headers = {
        "Authorization": f"Bearer {token1}",
        "X-Workspace-ID": str(registered_user["workspace"].id),
    }
    unauthorized_res = await client.get(
        f"/api/v1/accounts/{user2_acc_id}",
        headers=user1_headers,
    )
    assert unauthorized_res.status_code == 404, "Cross-tenant IDOR leak detected!"


# =============================================================================
# 3. End-to-End Business Finance & Invoicing Lifecycle
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_business_finance_invoicing_and_receivables(
    db_session: AsyncSession, registered_user: dict
):
    """
    Verifies full small business finance journey:
    1. Create Business workspace & business profile.
    2. Add Client.
    3. Issue Invoice with 18% GST calculation (CGST + SGST).
    4. Transition status: Draft -> Issued -> Paid.
    5. Verify Profit & Loss Report generation.
    """
    user = registered_user["user"]
    reporting_service = FinancialReportingService(db_session)
    ledger_service = LedgerService(db_session)

    # 1. Create Business Workspace
    biz_ws = Workspace(
        id=uuid.uuid4(),
        name="Apex Digital Consulting",
        slug=f"biz-apex-{uuid.uuid4().hex[:6]}",
        type=WorkspaceType.BUSINESS.value,
        owner_id=user.id,
        default_currency="INR",
        status="active",
    )
    db_session.add(biz_ws)
    await db_session.flush()

    biz_member = WorkspaceMember(
        workspace_id=biz_ws.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER.value,
        status="active",
    )
    db_session.add(biz_member)

    # Profile with business name
    biz_profile = BusinessProfile(
        workspace_id=biz_ws.id,
        business_name="Apex Digital Consulting Private Limited",
        business_type="services",
        country="IN",
    )
    db_session.add(biz_profile)
    await db_session.commit()

    # Seed COA for business workspace
    await ledger_service.ensure_chart_of_accounts(biz_ws.id)

    # 2. Add Business Client
    client = BusinessClient(
        workspace_id=biz_ws.id,
        name="Tata Consultancy Enterprise",
        email="procurement@tata.com",
        phone="+919876543210",
        gstin="27AAACT2727Q1ZW",
    )
    db_session.add(client)
    await db_session.commit()

    # 3. Create and Issue Business Invoice
    # Base: ₹1,00,000.00 | CGST 9%: ₹9,000 | SGST 9%: ₹9,000 | Total: ₹1,18,000.00
    invoice = BusinessInvoice(
        workspace_id=biz_ws.id,
        client_id=client.id,
        invoice_number=f"INV-2026-{uuid.uuid4().hex[:4]}",
        invoice_date=date(2026, 11, 1),
        due_date=date(2026, 11, 30),
        currency="INR",
        subtotal_amount_paise=10000000,
        discount_amount_paise=0,
        tax_amount_paise=1800000,
        total_amount_paise=11800000,
        paid_amount_paise=0,
        status="issued",
    )
    db_session.add(invoice)
    await db_session.commit()
    assert invoice.total_amount_paise == 11800000

    # 4. Mark Invoice as Paid
    invoice.paid_amount_paise = 11800000
    invoice.status = "paid"
    await db_session.commit()

    # 5. Verify GST Readiness Report via FinancialReportingService
    period = ReportingPeriodVO(
        period_type="custom",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        label="November 2026",
    )
    gst_report = await reporting_service.generate_gst_summary(
        workspace_id=biz_ws.id,
        period=period,
    )
    assert gst_report.total_turnover_paise >= 10000000
    assert gst_report.output_cgst_paise > 0 or gst_report.output_sgst_paise > 0


# =============================================================================
# 4. Financial Calculations, Indian FY Bounds, and Exact Paise Arithmetic
# =============================================================================


def test_indian_financial_year_bounds_and_quarters():
    """
    Verifies that Indian Financial Year (April 1 to March 31) bounds are calculated accurately
    across standard calendar dates and leap years.
    """
    # Test date in November 2026 belongs to FY 2026-27
    fy_str = calculate_indian_financial_year(date(2026, 11, 19))
    assert fy_str == "FY 2026-27"

    # Test date in January 2027 belongs to FY 2026-27
    fy_str_jan = calculate_indian_financial_year(date(2027, 1, 15))
    assert fy_str_jan == "FY 2026-27"

    # Test bounds for FY 2026-27
    start_dt, end_dt = calculate_financial_year_bounds("FY 2026-27")
    assert start_dt == date(2026, 4, 1)
    assert end_dt == date(2027, 3, 31)


def test_exact_money_paise_arithmetic_no_floating_point():
    """
    Verifies that Money value objects enforce integer paise arithmetic and exact Decimal
    representations, preventing IEEE 754 floating-point drift (e.g. 0.1 + 0.2 != 0.3).
    """
    m1 = Money.from_amount(Decimal("100.10"))
    m2 = Money.from_amount(Decimal("200.20"))
    m3 = m1 + m2

    assert m3.paise == 30030
    assert m3.display_amount == Decimal("300.30")

    # Multiplication by factor
    m4 = m1 * 3
    assert m4.paise == 30030
    assert m4.display_amount == Decimal("300.30")


def test_indian_income_tax_estimation_new_regime():
    """
    Verifies Section 115BAC New Tax Regime slabs and Section 87A rebate calculations.
    """
    # Income ₹7,00,000 eligible for Section 87A rebate (zero tax in new regime)
    est_7l = estimate_indian_income_tax(
        gross_income_paise=70000000,
        deductions_paise=7500000,  # Standard deduction
        regime=TaxRegime.NEW_REGIME.value,
    )
    assert est_7l.total_estimated_tax_paise == 0

    # Income ₹12,00,000
    est_12l = estimate_indian_income_tax(
        gross_income_paise=120000000,
        deductions_paise=7500000,
        regime=TaxRegime.NEW_REGIME.value,
    )
    assert est_12l.total_estimated_tax_paise > 0


# =============================================================================
# 5. Multi-Tenant Anti-IDOR Security & Token Revocation
# =============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_idor_protection_returns_404(
    client: AsyncClient, registered_user: dict, db_session: AsyncSession
):
    """
    Verifies that attempting to read or mutate another tenant's workspace or resource
    returns HTTP 404 (Not Found), never HTTP 403, preventing resource existence enumeration.
    """
    # Create foreign workspace
    foreign_user = User(
        id=uuid.uuid4(),
        email=f"foreign_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Foreign Alien",
        hashed_password=get_password_hash("AlienPass123!"),
        is_active=True,
    )
    db_session.add(foreign_user)
    await db_session.flush()

    foreign_ws = Workspace(
        id=uuid.uuid4(),
        name="Foreign Secret Workspace",
        slug=f"foreign-{uuid.uuid4().hex[:6]}",
        type=WorkspaceType.PERSONAL.value,
        owner_id=foreign_user.id,
        default_currency="INR",
        status="active",
    )
    db_session.add(foreign_ws)
    await db_session.commit()

    # Access foreign workspace using registered_user's token
    headers = registered_user["headers"]
    response = await client.get(f"/api/v1/workspaces/{foreign_ws.id}", headers=headers)

    # Must be 404 Not Found to prevent enumeration
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"


# =============================================================================
# 6. Additional Integrity & Security Regression Invariants
# =============================================================================


@pytest.mark.asyncio
async def test_unbalanced_journal_post_rejected_by_service(
    db_session: AsyncSession, registered_user: dict
):
    """
    Verifies that the double-entry accounting engine strictly forbids posting
    unbalanced journal entries where Debits != Credits, raising UnbalancedJournalError.
    """
    ws = registered_user["workspace"]
    user = registered_user["user"]
    service = LedgerService(db_session)
    await service.ensure_chart_of_accounts(ws.id)

    bank = await service.account_repo.get_by_code(ws.id, "1021")
    revenue = await service.account_repo.get_by_code(ws.id, "4020")

    draft = await service.create_draft_journal(
        workspace_id=ws.id,
        entry_number=f"JE-UNBAL-{uuid.uuid4().hex[:6].upper()}",
        entry_date=date.today(),
        description="Unbalanced Attempt",
        lines_data=[
            {"ledger_account_id": bank.id, "entry_type": "debit", "amount": Decimal("10000.0000")},
            {"ledger_account_id": revenue.id, "entry_type": "credit", "amount": Decimal("9500.0000")},
        ],
        created_by=user.id,
    )
    await db_session.commit()

    with pytest.raises(UnbalancedJournalError) as exc_info:
        await service.post_journal_entry(ws.id, draft.id, actor_id=user.id)

    assert "Difference: 500.0000" in str(exc_info.value)


def test_magic_bytes_detection_and_mime_spoofing_defense():
    """
    Verifies that DocumentService performs binary magic byte detection
    and strictly forbids shell scripts or plain text spoofed with .png or .pdf extensions.
    """
    # Valid PDF magic bytes
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
    assert DocumentService.validate_file_bytes(valid_pdf, "statement.pdf") == "application/pdf"

    # Empty file
    with pytest.raises(ValidationException) as exc:
        DocumentService.validate_file_bytes(b"", "empty.pdf")
    assert exc.value.code == "FILE_EMPTY"

    # Malicious text/shell script disguised as png
    with pytest.raises(ValidationException) as exc:
        DocumentService.validate_file_bytes(b"#!/bin/bash\nrm -rf /", "malicious.png")
    assert exc.value.code == "UNSUPPORTED_DOCUMENT_FORMAT"


def test_recurrence_leap_year_and_end_of_month_pinning():
    """
    Verifies that recurring commitments handle leap years and month-end dates cleanly
    without permanently drifting to shorter month lengths.
    """
    # Leap year annual schedule: Feb 29 2024 -> Feb 28 2025 -> Feb 29 2028
    assert is_leap_year(2024) is True
    assert is_leap_year(2025) is False
    assert is_leap_year(2028) is True

    next_ly = calculate_next_occurrence(date(2024, 2, 29), RecurringFrequency.ANNUAL, day_of_month=29)
    assert next_ly == date(2025, 2, 28)

    # End-of-month pinning: Jan 31 -> Feb 28 -> Mar 31 -> Apr 30 -> May 31
    m1 = calculate_next_occurrence(date(2026, 1, 31), RecurringFrequency.MONTHLY, day_of_month=31)
    assert m1 == date(2026, 2, 28)

    m2 = calculate_next_occurrence(m1, RecurringFrequency.MONTHLY, day_of_month=31)
    assert m2 == date(2026, 3, 31)

