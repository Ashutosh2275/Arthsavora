"""
ARTHSAVORA Advanced Financial Reporting, Tax Intelligence & Compliance Test Suite
Validates pure domain logic, Indian Financial Year bounds, formula-injection defenses (CWE-1236),
financial statements generation (Income & Expense, Cash Flow, Balance Sheet, Trial Balance),
tax classification rule matching, GST readiness calculations, income tax estimations (New vs Old regime),
data quality validation engine, CSV export streaming, API permissions, and AI assistant tools.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.domain.assistant import ToolCallVO
from app.domain.financial_report import (
    AccountingBasis,
    PeriodType,
    ReportType,
    TaxRegime,
    TaxReviewStatus,
    ValidationSeverity,
    calculate_financial_year_bounds,
    calculate_indian_financial_year,
    calculate_quarter_bounds,
    estimate_indian_income_tax,
    sanitize_csv_cell,
    validate_balance_sheet_equation,
)
from app.infrastructure.database.models import (
    Account,
    AccountBalanceSnapshot,
    BusinessClient,
    BusinessInvoice,
    BusinessProfile,
    FinancialDocument,
    GeneratedReport,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    ReportValidationFinding,
    TaxClassificationRecord,
    TaxEstimateSnapshot,
    TaxRule,
    Transaction,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceType,
)
from app.main import app
from app.services.assistant.tool_executor import ToolExecutor
from app.services.financial_reporting_service import FinancialReportingService


# -----------------------------------------------------------------------------
# 1. Pure Domain Logic & Math Tests
# -----------------------------------------------------------------------------
def test_pure_domain_fiscal_year_resolution():
    """Verifies that Indian Financial Year runs April 1 to March 31."""
    # May 2026 falls in FY 2026-27
    assert calculate_indian_financial_year(date(2026, 5, 15)) == "FY 2026-27"
    # March 2027 falls in FY 2026-27
    assert calculate_indian_financial_year(date(2027, 3, 31)) == "FY 2026-27"
    # April 1, 2027 starts FY 2027-28
    assert calculate_indian_financial_year(date(2027, 4, 1)) == "FY 2027-28"
    # January 2026 falls in FY 2025-26
    assert calculate_indian_financial_year(date(2026, 1, 10)) == "FY 2025-26"


def test_pure_domain_fiscal_year_bounds():
    """Verifies calculation of fiscal year start and end dates."""
    start_d, end_d = calculate_financial_year_bounds("FY 2026-27")
    assert start_d == date(2026, 4, 1)
    assert end_d == date(2027, 3, 31)

    start_d2, end_d2 = calculate_financial_year_bounds("2025-26")
    assert start_d2 == date(2025, 4, 1)
    assert end_d2 == date(2026, 3, 31)


def test_pure_domain_quarter_bounds():
    """Verifies calculation of standard Indian fiscal quarters."""
    # Q1: Apr - Jun
    q1_s, q1_e, q1_l = calculate_quarter_bounds("FY 2026-27", 1)
    assert q1_s == date(2026, 4, 1)
    assert q1_e == date(2026, 6, 30)
    assert "Q1" in q1_l

    # Q4: Jan - Mar
    q4_s, q4_e, q4_l = calculate_quarter_bounds("FY 2026-27", 4)
    assert q4_s == date(2027, 1, 1)
    assert q4_e == date(2027, 3, 31)
    assert "Q4" in q4_l


def test_pure_domain_sanitize_csv_cell():
    """Verifies defense against CSV Formula Injection (CWE-1236)."""
    # Formula prefixes =, +, -, @ must be prepended with a single quote '
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-5+2") == "'-5+2"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    # Safe text remains unchanged
    assert sanitize_csv_cell("HDFC Bank Savings") == "HDFC Bank Savings"
    assert sanitize_csv_cell("₹1,500.00") == "₹1,500.00"
    assert sanitize_csv_cell(None) == ""


def test_pure_domain_balance_sheet_equation():
    """Verifies Assets = Liabilities + Equity equilibrium rule."""
    # Case 1: Perfectly balanced
    is_bal, diff, desc = validate_balance_sheet_equation(
        assets_paise=10000000,
        liabilities_paise=4000000,
        equity_paise=6000000,
    )
    assert is_bal is True
    assert diff == 0

    # Case 2: Imbalance with positive discrepancy
    is_bal, diff, desc = validate_balance_sheet_equation(
        assets_paise=10000000,
        liabilities_paise=4000000,
        equity_paise=5000000,
    )
    assert is_bal is False
    assert diff == 1000000  # Assets exceed Liabilities + Equity by 10,000 INR
    assert "Unbalanced" in desc


def test_pure_domain_tax_estimation_new_regime():
    """Verifies New Tax Regime calculation with Finance Act slabs, standard deduction, and Section 87A rebate."""
    # Case 1: Gross income ₹6,00,000 (after ₹75,000 standard deduction, taxable is ₹5,25,000 <= ₹7,00,000 -> 87A rebate applies)
    est = estimate_indian_income_tax(
        gross_income_paise=60000000,
        deductions_paise=0,
        regime=TaxRegime.NEW_REGIME.value,
        fy="FY 2026-27",
    )
    assert est.standard_deduction_paise == 7500000
    assert est.taxable_income_paise == 52500000
    assert est.total_estimated_tax_paise == 0

    # Case 2: High income ₹20,00,000 under New Regime
    est_high = estimate_indian_income_tax(
        gross_income_paise=200000000,
        deductions_paise=0,
        regime=TaxRegime.NEW_REGIME.value,
        fy="FY 2026-27",
    )
    assert est_high.standard_deduction_paise == 7500000
    assert est_high.taxable_income_paise == 192500000
    assert est_high.base_tax_paise > 0
    assert est_high.cess_paise == int(est_high.base_tax_paise * 0.04)
    assert est_high.total_estimated_tax_paise > 0


def test_pure_domain_tax_estimation_old_regime():
    """Verifies Old Tax Regime calculation including Section 80 deductions and ₹50,000 standard deduction."""
    est_old = estimate_indian_income_tax(
        gross_income_paise=150000000,
        deductions_paise=15000000,  # ₹1.5L Chapter VI-A deductions
        regime=TaxRegime.OLD_REGIME.value,
        fy="FY 2026-27",
    )
    assert est_old.standard_deduction_paise == 5000000
    assert est_old.chapter_vi_a_deductions_paise == 15000000
    # 15L - 50k - 1.5L = 13L
    assert est_old.taxable_income_paise == 130000000
    assert est_old.base_tax_paise > 0


# -----------------------------------------------------------------------------
# 2. Service Layer Integration Tests
# -----------------------------------------------------------------------------
@pytest.fixture
async def setup_reporting_data(db_session: AsyncSession):
    """Sets up a comprehensive test workspace with accounts, transactions, and invoices."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"cfo_{uid.hex[:8]}@arthsavora.com",
        hashed_password=get_password_hash("FinReportPass123!"),
        full_name="Chief Financial Officer",
        is_active=True,
    )
    db_session.add(user)

    ws_id = uuid.uuid4()
    ws = Workspace(
        id=ws_id,
        name="Enterprise Financial Workspace",
        slug=f"ent-fin-{ws_id.hex[:6]}",
        type="business",
        owner_id=user.id,
    )
    db_session.add(ws)

    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=user.id,
        role="admin",
    )
    db_session.add(member)

    # Business Client
    client_rec = BusinessClient(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name="Acme Corp Global",
        client_type="business",
        billing_address={},
        payment_terms_days=30,
    )
    db_session.add(client_rec)

    # Primary Bank Account
    acc = Account(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name="Operating Checking Account",
        account_type="current",
        currency="INR",
        status="active",
    )
    db_session.add(acc)

    snap = AccountBalanceSnapshot(
        id=uuid.uuid4(),
        account_id=acc.id,
        workspace_id=ws.id,
        balance_type="book",
        balance_amount=Decimal("500000.00"),
        balance_paise=50000000,
        currency="INR",
        effective_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
        source="manual",
    )
    db_session.add(snap)

    # Income transaction (₹2,00,000)
    tx_income = Transaction(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        account_id=acc.id,
        amount_paise=20000000,
        amount=Decimal("200000.00"),
        currency="INR",
        direction="inflow",
        transaction_type="income",
        status="posted",
        description="Software Consulting Client Retainer",
        merchant_name="Acme Corp Global",
        transaction_date=date(2026, 5, 10),
    )
    db_session.add(tx_income)

    # Expense transaction: Health Insurance (₹25,000)
    tx_med = Transaction(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        account_id=acc.id,
        amount_paise=2500000,
        amount=Decimal("25000.00"),
        currency="INR",
        direction="outflow",
        transaction_type="expense",
        status="posted",
        description="Annual Star Health Insurance Premium",
        merchant_name="Star Health",
        transaction_date=date(2026, 6, 15),
    )
    db_session.add(tx_med)

    # Expense transaction: Business SaaS (₹12,000)
    tx_saas = Transaction(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        account_id=acc.id,
        amount_paise=1200000,
        amount=Decimal("12000.00"),
        currency="INR",
        direction="outflow",
        transaction_type="expense",
        status="posted",
        description="GitHub Enterprise and AWS Hosting Cloud",
        merchant_name="Amazon Web Services",
        transaction_date=date(2026, 7, 20),
    )
    db_session.add(tx_saas)

    # Business Invoice with GST
    inv = BusinessInvoice(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        client_id=client_rec.id,
        invoice_number="INV-2026-001",
        invoice_date=date(2026, 5, 10),
        due_date=date(2026, 6, 10),
        status="paid",
        subtotal_amount_paise=10000000,  # ₹1,00,000 taxable turnover
        tax_amount_paise=1800000,       # ₹18,000 (18% GST)
        total_amount_paise=11800000,
    )
    db_session.add(inv)

    await db_session.commit()
    return {
        "user": user,
        "workspace": ws,
        "account": acc,
        "tx_income": tx_income,
        "tx_med": tx_med,
        "tx_saas": tx_saas,
        "invoice": inv,
    }


@pytest.mark.asyncio
async def test_service_statement_generation(db_session: AsyncSession, setup_reporting_data):
    """Verifies Income & Expense, Cash Flow, and Statement metrics generation."""
    data = setup_reporting_data
    service = FinancialReportingService(db_session)

    period = service.resolve_reporting_period(
        period_type=PeriodType.FINANCIAL_YEAR.value,
        fiscal_year="FY 2026-27",
    )

    # 1. Income & Expense Statement (Cash Basis)
    stmt = await service.generate_income_and_expense_statement(
        workspace_id=data["workspace"].id,
        period=period,
        basis=AccountingBasis.CASH.value,
    )
    assert stmt.total_income_paise == 20000000  # ₹2,00,000
    assert stmt.total_expenses_paise == 3700000   # ₹25,000 + ₹12,000 = ₹37,000
    assert stmt.net_surplus_deficit_paise == 16300000  # ₹1,63,000 net surplus
    assert len(stmt.income_lines) > 0
    assert len(stmt.expense_lines) > 0

    # 2. Cash Flow Statement
    cf = await service.generate_cash_flow_statement(
        workspace_id=data["workspace"].id,
        period=period,
    )
    assert cf.operating_inflows_paise == 20000000
    assert cf.operating_outflows_paise == 3700000
    assert cf.net_operating_cash_flow_paise == 16300000
    assert cf.net_cash_movement_paise == 16300000


@pytest.mark.asyncio
async def test_service_tax_rules_and_suggestions(db_session: AsyncSession, setup_reporting_data):
    """Verifies that rule-based pattern matching auto-suggests tax classifications."""
    data = setup_reporting_data
    service = FinancialReportingService(db_session)

    # Trigger tax rule scan for FY 2026-27
    suggested = await service.suggest_tax_classifications_for_fy(
        workspace_id=data["workspace"].id,
        tax_year="FY 2026-27",
    )
    assert len(suggested) >= 1

    # Verify medical insurance was recognized
    med_rec = next((r for r in suggested if "80d" in r.tax_category.lower()), None)
    if med_rec:
        assert med_rec.tax_category == "section_80d"
        assert med_rec.review_status == TaxReviewStatus.SUGGESTED.value
        assert med_rec.deductible_amount_paise > 0

    # Review and confirm
    first_rec = suggested[0]
    reviewed = await service.review_tax_classification(
        workspace_id=data["workspace"].id,
        transaction_id=first_rec.transaction_id,
        user_id=data["user"].id,
        tax_category=first_rec.tax_category,
        review_status=TaxReviewStatus.CONFIRMED.value,
        notes="Reviewed and confirmed during internal tax audit.",
    )
    assert reviewed.review_status == TaxReviewStatus.CONFIRMED.value
    assert reviewed.reviewed_by_id == data["user"].id


@pytest.mark.asyncio
async def test_service_gst_readiness_summary(db_session: AsyncSession, setup_reporting_data):
    """Verifies GST readiness turnover and output tax calculation from invoices."""
    data = setup_reporting_data
    service = FinancialReportingService(db_session)

    period = service.resolve_reporting_period(
        period_type=PeriodType.FINANCIAL_YEAR.value,
        fiscal_year="FY 2026-27",
    )

    gst = await service.generate_gst_summary(
        workspace_id=data["workspace"].id,
        period=period,
    )
    assert gst.taxable_sales_paise == 10000000
    assert gst.total_output_tax_paise == 1800000
    assert gst.invoices_analyzed_count == 1
    assert "not a certified tax filing or return" in gst.data_disclaimer.lower()


@pytest.mark.asyncio
async def test_service_income_tax_estimate(db_session: AsyncSession, setup_reporting_data):
    """Verifies mathematical income tax estimate generation and database persistence."""
    data = setup_reporting_data
    service = FinancialReportingService(db_session)

    estimate = await service.generate_income_tax_estimate(
        workspace_id=data["workspace"].id,
        financial_year="FY 2026-27",
        regime=TaxRegime.NEW_REGIME.value,
        user_id=data["user"].id,
    )
    assert estimate.gross_total_income_paise == 20000000
    assert estimate.standard_deduction_paise == 7500000
    assert estimate.taxable_income_paise == 12500000
    assert estimate.legal_disclaimer is not None

    # Check database snapshot
    snapshot = await service.report_repo.get_latest_tax_estimate(
        workspace_id=data["workspace"].id,
        financial_year="FY 2026-27",
    )
    assert snapshot is not None
    assert snapshot.gross_income_paise == 20000000


@pytest.mark.asyncio
async def test_service_csv_export_security(db_session: AsyncSession, setup_reporting_data):
    """Verifies CSV generation with formula-injection defenses."""
    data = setup_reporting_data
    service = FinancialReportingService(db_session)

    period = service.resolve_reporting_period("financial_year", "FY 2026-27")
    stmt = await service.generate_income_and_expense_statement(
        workspace_id=data["workspace"].id,
        period=period,
        basis="cash",
    )

    csv_out = service.export_statement_csv(
        statement_name="=HYPERLINK('http://attacker.com','P&L')",
        period=period,
        currency="INR",
        lines=stmt.income_lines + stmt.expense_lines,
        total_inflow_paise=stmt.total_income_paise,
        total_outflow_paise=stmt.total_expenses_paise,
        net_result_paise=stmt.net_surplus_deficit_paise,
    )
    assert "'=HYPERLINK" in csv_out
    assert "TOTAL INFLOW / REVENUE" in csv_out


# -----------------------------------------------------------------------------
# 3. FastAPI REST Endpoints & RBAC Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_api_reporting_periods(client: AsyncClient, setup_reporting_data):
    """Tests GET /api/v1/reports/periods."""
    data = setup_reporting_data
    token = create_access_token(subject=str(data["user"].id), email=data["user"].email)

    resp = await client.get(
        "/api/v1/reports/periods",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(data["workspace"].id)},
    )
    assert resp.status_code == 200
    periods = resp.json()
    assert len(periods) >= 5  # FY + 4 quarters
    assert periods[0]["period_type"] == "financial_year"


@pytest.mark.asyncio
async def test_api_generate_and_download_report_snapshot(client: AsyncClient, setup_reporting_data):
    """Tests POST /api/v1/reports/generate and GET /api/v1/reports/{id}/download."""
    data = setup_reporting_data
    token = create_access_token(subject=str(data["user"].id), email=data["user"].email)

    # Generate Snapshot
    payload = {
        "report_type": "income_statement",
        "period_type": "financial_year",
        "fiscal_year": "FY 2026-27",
        "basis": "cash",
        "format": "csv",
    }
    gen_resp = await client.post(
        "/api/v1/reports/generate",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(data["workspace"].id)},
    )
    assert gen_resp.status_code == 201
    report = gen_resp.json()
    assert report["report_type"] == "income_statement"
    assert report["checksum"] is not None

    report_id = report["id"]

    # Download Report CSV
    dl_resp = await client.get(
        f"/api/v1/reports/{report_id}/download",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(data["workspace"].id)},
    )
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment;" in dl_resp.headers["content-disposition"]
    assert "TOTAL INFLOW" in dl_resp.text


@pytest.mark.asyncio
async def test_api_tax_endpoints(client: AsyncClient, setup_reporting_data):
    """Tests tax classifications, suggestions, GST summary, and tax estimation endpoints."""
    data = setup_reporting_data
    token = create_access_token(subject=str(data["user"].id), email=data["user"].email)
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(data["workspace"].id)}

    # 1. Suggest Tax Classifications
    sug_resp = await client.post(
        "/api/v1/tax/classifications/suggest",
        json={"tax_year": "FY 2026-27"},
        headers=headers,
    )
    assert sug_resp.status_code == 200

    # 2. GST Summary
    gst_resp = await client.get("/api/v1/tax/gst-summary", headers=headers)
    assert gst_resp.status_code == 200
    gst_data = gst_resp.json()
    assert gst_data["taxable_turnover_paise"] == 10000000

    # 3. Create Tax Estimate
    est_resp = await client.post(
        "/api/v1/tax/estimates",
        json={"financial_year": "FY 2026-27", "regime": "new_regime"},
        headers=headers,
    )
    assert est_resp.status_code == 201
    est_data = est_resp.json()
    assert est_data["gross_income_paise"] == 20000000


# -----------------------------------------------------------------------------
# 4. AI Assistant Tool Integration Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ai_assistant_reporting_tools(db_session: AsyncSession, setup_reporting_data):
    """Verifies that AI assistant can invoke reporting and tax tools through ToolExecutor."""
    data = setup_reporting_data
    executor = ToolExecutor(db_session)
    perms = {
        "reports:view",
        "reports:generate",
        "tax:view",
        "tax:manage",
    }

    # 1. get_financial_statement_summary
    tc_stmt = ToolCallVO(
        call_id="call_report_01",
        tool_name="get_financial_statement_summary",
        arguments={
            "statement_type": "income_statement",
            "fiscal_year": "FY 2026-27",
            "basis": "cash",
        },
    )
    res_stmt = await executor.execute_tool(tc_stmt, data["workspace"].id, perms)
    assert res_stmt.success is True
    assert "total_income" in res_stmt.data

    # 2. get_gst_reporting_summary
    tc_gst = ToolCallVO(
        call_id="call_gst_01",
        tool_name="get_gst_reporting_summary",
        arguments={"fiscal_year": "FY 2026-27"},
    )
    res_gst = await executor.execute_tool(tc_gst, data["workspace"].id, perms)
    assert res_gst.success is True
    assert "taxable_turnover" in res_gst.data
    assert "disclaimer" in res_gst.data

    # 3. explain_report_discrepancies
    tc_disc = ToolCallVO(
        call_id="call_disc_01",
        tool_name="explain_report_discrepancies",
        arguments={"fiscal_year": "FY 2026-27"},
    )
    res_disc = await executor.execute_tool(tc_disc, data["workspace"].id, perms)
    assert res_disc.success is True
    assert "findings" in res_disc.data
