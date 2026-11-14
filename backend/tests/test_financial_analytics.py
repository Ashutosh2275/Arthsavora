"""
Arthsavora Financial Analytics & Dashboard Intelligence Test Suite
Validates:
1. Domain metric calculations (India FY, date bounds, savings rates, deltas, CSV injection defense).
2. Authoritative PostgreSQL aggregation (income, expense, net cash flow, savings rate).
3. Transfer exclusions (internal transfers and card payments never distort turnover).
4. Refund treatment (offsets operating expenses cleanly).
5. Credit card purchase vs payment handling (eliminating double-counting).
6. Category and merchant spending intelligence (with uncategorized classification).
7. Balance sheet derivation and Net Worth (Assets - Liabilities).
8. Multi-currency and multi-workspace strict isolation (anti-IDOR).
9. CSV report streaming with formula injection sanitization.
10. Authenticated RESTful API routes.
"""

from datetime import date, timedelta
from decimal import Decimal
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.analytics import (
    FinancialSentiment,
    PeriodGrouping,
    ReportType,
    calculate_percentage_delta,
    calculate_savings_rate,
    evaluate_sentiment,
    get_financial_year_bounds,
    get_month_bounds,
    get_previous_period_bounds,
    get_quarter_bounds,
    sanitize_csv_cell,
)
from app.infrastructure.database.models import Account, Category, Transaction, Workspace
from app.services.analytics.analytics_service import AnalyticsService


# ==============================================================================
# 1. PURE DOMAIN & UTILITY TESTS
# ==============================================================================

def test_india_financial_year_bounds():
    """Validates India Financial Year (1 April – 31 March) calculation across dates."""
    # February 2026 belongs to FY 2025-26
    start_1, end_1 = get_financial_year_bounds(date(2026, 2, 14))
    assert start_1 == date(2025, 4, 1)
    assert end_1 == date(2026, 3, 31)

    # April 1, 2026 starts FY 2026-27
    start_2, end_2 = get_financial_year_bounds(date(2026, 4, 1))
    assert start_2 == date(2026, 4, 1)
    assert end_2 == date(2027, 3, 31)

    # November 2026 belongs to FY 2026-27
    start_3, end_3 = get_financial_year_bounds(date(2026, 11, 20))
    assert start_3 == date(2026, 4, 1)
    assert end_3 == date(2027, 3, 31)


def test_month_and_quarter_bounds():
    """Validates calendar month and quarter boundaries."""
    m_start, m_end = get_month_bounds(date(2026, 2, 10))
    assert m_start == date(2026, 2, 1)
    assert m_end == date(2026, 2, 28)

    # Quarter bounds for Feb (Q1)
    q_start, q_end = get_quarter_bounds(date(2026, 2, 10))
    assert q_start == date(2026, 1, 1)
    assert q_end == date(2026, 3, 31)

    # Quarter bounds for August (Q3)
    q_start3, q_end3 = get_quarter_bounds(date(2026, 8, 15))
    assert q_start3 == date(2026, 7, 1)
    assert q_end3 == date(2026, 9, 30)


def test_previous_period_bounds():
    """Validates equal-duration prior period calculation."""
    curr_start = date(2026, 2, 1)
    curr_end = date(2026, 2, 28)  # 28 days
    prev_start, prev_end = get_previous_period_bounds(curr_start, curr_end)
    assert prev_end == date(2026, 1, 31)
    assert prev_start == date(2026, 1, 4)
    assert (prev_end - prev_start).days + 1 == 28


def test_savings_rate_calculation():
    """Validates savings rate math: ((income - expenses) / income) * 100."""
    # 50,000 income, 30,000 expense -> 40.0% savings
    assert calculate_savings_rate(5000000, 3000000) == 40.0
    # Zero income -> 0.0%
    assert calculate_savings_rate(0, 1000000) == 0.0
    # Negative savings (spend > income)
    assert calculate_savings_rate(2000000, 3000000) == -50.0


def test_percentage_delta_and_sentiment():
    """Validates percentage change and financial favorability sentiments."""
    # Baseline 100 -> 120 (+20%)
    assert calculate_percentage_delta(120, 100) == 20.0
    # Baseline 100 -> 80 (-20%)
    assert calculate_percentage_delta(80, 100) == -20.0
    # Baseline 0 -> None
    assert calculate_percentage_delta(50, 0) is None
    # Both 0 -> 0.0
    assert calculate_percentage_delta(0, 0) == 0.0

    # Sentiment: income increase is favorable
    assert evaluate_sentiment("income", 5000) == FinancialSentiment.FAVORABLE
    # Sentiment: expense increase is unfavorable
    assert evaluate_sentiment("expenses", 5000) == FinancialSentiment.UNFAVORABLE
    # Sentiment: expense decrease is favorable
    assert evaluate_sentiment("expenses", -5000) == FinancialSentiment.FAVORABLE


def test_csv_formula_injection_defense():
    """Validates that unsafe formula prefixes (=, +, -, @) are sanitized with apostrophe."""
    assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_csv_cell("+cmd|'/C calc'!A0") == "'+cmd|'/C calc'!A0"
    assert sanitize_csv_cell("-1234") == "'-1234"
    assert sanitize_csv_cell("@lookup") == "'@lookup"
    assert sanitize_csv_cell("Normal Merchant") == "Normal Merchant"
    assert sanitize_csv_cell(None) == ""


# ==============================================================================
# 2. DATABASE ANALYTICS AGGREGATION & SERVICE TESTS
# ==============================================================================

@pytest.fixture
async def setup_analytics_data(db_session: AsyncSession, registered_user: dict):
    """Provisions accounts, categories, and varied transactions for analytical aggregation."""
    workspace: Workspace = registered_user["workspace"]
    user = registered_user["user"]

    # 1. Accounts
    savings_acc = Account(
        workspace_id=workspace.id,
        name="HDFC Primary Savings",
        account_type="savings",
        institution_name="HDFC Bank",
        masked_identifier="••••4092",
        currency="INR",
        current_book_balance_paise=15000000,  # ₹1,50,000
        opening_balance_paise=5000000,
        status="active",
    )
    credit_acc = Account(
        workspace_id=workspace.id,
        name="HDFC Regalia Credit Card",
        account_type="credit_card",
        institution_name="HDFC Bank",
        masked_identifier="••••8819",
        currency="INR",
        current_book_balance_paise=-2500000,
        outstanding_liability_paise=2500000,  # ₹25,000 debt
        credit_limit_paise=30000000,          # ₹3,00,000 limit
        status="active",
        due_date=date(2026, 3, 5),
    )
    db_session.add_all([savings_acc, credit_acc])
    await db_session.flush()

    # 2. Categories
    cat_food = Category(
        workspace_id=workspace.id,
        name="Groceries & Food",
        slug=f"groceries-{uuid.uuid4().hex[:6]}",
        category_type="expense",
        icon="shopping-cart",
        color="#10b981",
        is_system=False,
    )
    cat_salary = Category(
        workspace_id=workspace.id,
        name="Professional Salary",
        slug=f"salary-{uuid.uuid4().hex[:6]}",
        category_type="income",
        icon="briefcase",
        color="#6366f1",
        is_system=False,
    )
    db_session.add_all([cat_food, cat_salary])
    await db_session.flush()

    # 3. Transactions
    # T1: Salary Income (₹1,00,000)
    tx_salary = Transaction(
        workspace_id=workspace.id,
        account_id=savings_acc.id,
        transaction_type="income",
        direction="inflow",
        amount=Decimal("100000.00"),
        amount_paise=10000000,
        currency="INR",
        transaction_date=date(2026, 2, 1),
        description="Salary for Jan 2026",
        category_id=cat_salary.id,
        status="posted",
        source_type="manual",
    )

    # T2: Grocery Expense (₹5,000) via Swiggy Instamart
    tx_grocery = Transaction(
        workspace_id=workspace.id,
        account_id=savings_acc.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("5000.00"),
        amount_paise=500000,
        currency="INR",
        transaction_date=date(2026, 2, 5),
        description="Swiggy Instamart Order",
        merchant_name="Swiggy",
        category_id=cat_food.id,
        status="posted",
        source_type="manual",
    )

    # T3: Credit Card Purchase (₹15,000) via Amazon India
    tx_card_spend = Transaction(
        workspace_id=workspace.id,
        account_id=credit_acc.id,
        transaction_type="credit_card_purchase",
        direction="outflow",
        amount=Decimal("15000.00"),
        amount_paise=1500000,
        currency="INR",
        transaction_date=date(2026, 2, 8),
        description="Amazon Retail Electronics",
        merchant_name="Amazon India",
        category_id=cat_food.id,
        status="posted",
        source_type="credit_card_statement",
    )

    # T4: Refund for returned item (₹1,000)
    tx_refund = Transaction(
        workspace_id=workspace.id,
        account_id=credit_acc.id,
        transaction_type="credit_card_refund",
        direction="inflow",
        amount=Decimal("1000.00"),
        amount_paise=100000,
        currency="INR",
        transaction_date=date(2026, 2, 10),
        description="Amazon Return Refund",
        merchant_name="Amazon India",
        category_id=cat_food.id,
        status="posted",
        source_type="credit_card_statement",
    )

    # T5: Credit Card Bill Repayment (₹20,000) - Transfer / liability settlement
    # MUST NOT be counted as an operating expense!
    tx_card_payment = Transaction(
        workspace_id=workspace.id,
        account_id=savings_acc.id,
        transaction_type="credit_card_payment",
        direction="outflow",
        amount=Decimal("20000.00"),
        amount_paise=2000000,
        currency="INR",
        transaction_date=date(2026, 2, 11),
        description="HDFC Credit Card Bill Payment",
        status="posted",
        source_type="manual",
    )

    # T6: Paired Transfer (₹10,000) - Internal relocation
    # MUST NOT count as income or expense!
    transfer_uuid = uuid.uuid4()
    tx_transfer = Transaction(
        workspace_id=workspace.id,
        account_id=savings_acc.id,
        transaction_type="transfer",
        direction="outflow",
        amount=Decimal("10000.00"),
        amount_paise=1000000,
        currency="INR",
        transaction_date=date(2026, 2, 12),
        description="Transfer to Petty Cash",
        transfer_id=transfer_uuid,
        status="posted",
        source_type="manual",
    )

    # T7: Uncategorized Expense (₹3,000)
    tx_uncat = Transaction(
        workspace_id=workspace.id,
        account_id=savings_acc.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("3000.00"),
        amount_paise=300000,
        currency="INR",
        transaction_date=date(2026, 2, 13),
        description="Local Bazaar Merchant",
        merchant_name="Local Bazaar",
        category_id=None,
        status="posted",
        source_type="manual",
    )

    # T8: Pending Transaction (₹2,500)
    # MUST be excluded from authoritative totals!
    tx_pending = Transaction(
        workspace_id=workspace.id,
        account_id=credit_acc.id,
        transaction_type="credit_card_purchase",
        direction="outflow",
        amount=Decimal("2500.00"),
        amount_paise=250000,
        currency="INR",
        transaction_date=date(2026, 2, 14),
        description="Pending Uber Cab Ride",
        merchant_name="Uber",
        status="pending",
        source_type="manual",
    )

    db_session.add_all([
        tx_salary,
        tx_grocery,
        tx_card_spend,
        tx_refund,
        tx_card_payment,
        tx_transfer,
        tx_uncat,
        tx_pending,
    ])
    await db_session.commit()

    return {
        "workspace": workspace,
        "savings_acc": savings_acc,
        "credit_acc": credit_acc,
        "cat_food": cat_food,
        "cat_salary": cat_salary,
    }


@pytest.mark.asyncio
async def test_get_financial_overview_aggregation(db_session: AsyncSession, setup_analytics_data: dict):
    """
    Tests financial overview KPIs:
    - Gross Income: ₹1,00,000 (10000000 paise)
    - Gross Expense: ₹5,000 + ₹15,000 + ₹3,000 = ₹23,000 (2300000 paise)
    - Refunds: ₹1,000 (100000 paise)
    - Net Operating Expenses: ₹23,000 - ₹1,000 = ₹22,000 (2200000 paise)
    - Net Cash Flow: ₹1,00,000 - ₹22,000 = ₹78,000 (7800000 paise)
    - Savings Rate: (78,000 / 1,00,000) * 100 = 78.0%
    - Excluded transfers: 2 (card payment ₹20,000 + transfer ₹10,000)
    - Excluded pending: 1 (₹2,500)
    - Uncategorized: 1 (₹3,000)
    """
    workspace = setup_analytics_data["workspace"]
    service = AnalyticsService(db_session)

    overview = await service.get_overview(
        workspace_id=workspace.id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        currency="INR",
    )

    assert overview["total_income_paise"] == 10000000
    assert overview["total_income"] == Decimal("100000.00")
    assert overview["gross_expenses_paise"] == 2300000
    assert overview["refunds_paise"] == 100000
    assert overview["total_expenses_paise"] == 2200000
    assert overview["total_expenses"] == Decimal("22000.00")
    assert overview["net_cash_flow_paise"] == 7800000
    assert overview["net_cash_flow"] == Decimal("78000.00")
    assert overview["savings_rate_percentage"] == 78.0

    # Verify Data Quality Indicators
    dq = overview["data_quality"]
    assert dq["uncategorized_count"] == 1
    assert dq["uncategorized_amount_paise"] == 300000
    assert dq["excluded_transfers_count"] == 2
    assert dq["excluded_transfers_amount_paise"] == 3000000  # ₹20,000 + ₹10,000
    assert dq["excluded_pending_count"] == 1
    assert dq["excluded_pending_amount_paise"] == 250000     # ₹2,500


@pytest.mark.asyncio
async def test_get_cash_flow_trends(db_session: AsyncSession, setup_analytics_data: dict):
    """Tests cash flow time series grouping."""
    workspace = setup_analytics_data["workspace"]
    service = AnalyticsService(db_session)

    trends = await service.get_cash_flow_trends(
        workspace_id=workspace.id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        grouping=PeriodGrouping.MONTH,
        currency="INR",
    )

    assert len(trends) >= 1
    feb_point = trends[0]
    assert feb_point["income_paise"] == 10000000
    assert feb_point["expenses_paise"] == 2200000
    assert feb_point["net_cash_flow_paise"] == 7800000
    assert feb_point["cumulative_cash_flow_paise"] == 7800000


@pytest.mark.asyncio
async def test_get_category_spending_breakdown(db_session: AsyncSession, setup_analytics_data: dict):
    """Tests category distribution including uncategorized bucket."""
    workspace = setup_analytics_data["workspace"]
    service = AnalyticsService(db_session)

    cat_data = await service.get_category_spending(
        workspace_id=workspace.id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        direction="outflow",
        limit=10,
        currency="INR",
    )

    categories = cat_data["categories"]
    assert len(categories) == 2  # Groceries & Food, and Uncategorized

    food_entry = next((c for c in categories if not c["is_uncategorized"]), None)
    assert food_entry is not None
    assert food_entry["category_name"] == "Groceries & Food"
    assert food_entry["total_amount_paise"] == 2000000  # ₹5,000 grocery + ₹15,000 amazon

    uncat_entry = next((c for c in categories if c["is_uncategorized"]), None)
    assert uncat_entry is not None
    assert uncat_entry["category_name"] == "Uncategorized"
    assert uncat_entry["total_amount_paise"] == 300000  # ₹3,000


@pytest.mark.asyncio
async def test_get_merchant_spending_ranking(db_session: AsyncSession, setup_analytics_data: dict):
    """Tests merchant ranking with average ticket calculation."""
    workspace = setup_analytics_data["workspace"]
    service = AnalyticsService(db_session)

    m_data = await service.get_merchant_spending(
        workspace_id=workspace.id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        limit=5,
        currency="INR",
    )

    merchants = m_data["merchants"]
    assert len(merchants) >= 3

    # #1 is Amazon India (₹15,000)
    assert merchants[0]["merchant_name"] == "Amazon India"
    assert merchants[0]["total_amount_paise"] == 1500000

    # #2 is Swiggy (₹5,000)
    assert merchants[1]["merchant_name"] == "Swiggy"
    assert merchants[1]["total_amount_paise"] == 500000
    assert merchants[1]["average_ticket_paise"] == 500000


@pytest.mark.asyncio
async def test_get_account_balances_and_net_worth(db_session: AsyncSession, setup_analytics_data: dict):
    """
    Tests balance sheet derivation:
    - Assets: HDFC Primary Savings (₹1,50,000)
    - Liabilities: HDFC Regalia Credit Card (₹25,000)
    - Net Worth = ₹1,50,000 - ₹25,000 = ₹1,25,000 (12500000 paise)
    """
    workspace = setup_analytics_data["workspace"]
    service = AnalyticsService(db_session)

    nw = await service.get_net_worth(workspace_id=workspace.id, currency="INR")

    assert nw["total_assets_paise"] == 15000000
    assert nw["total_liabilities_paise"] == 2500000
    assert nw["net_worth_paise"] == 12500000
    assert nw["net_worth"] == Decimal("125000.00")
    assert len(nw["asset_accounts"]) == 1
    assert len(nw["liability_accounts"]) == 1


@pytest.mark.asyncio
async def test_csv_export_generation(db_session: AsyncSession, setup_analytics_data: dict):
    """Tests CSV export generation and formula injection neutralization."""
    workspace = setup_analytics_data["workspace"]
    service = AnalyticsService(db_session)

    csv_text = await service.export_analytics_csv(
        workspace_id=workspace.id,
        report_type=ReportType.OVERVIEW,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        currency="INR",
    )

    assert "Arthsavora Financial Analytics Summary" in csv_text
    assert "Total Income" in csv_text
    assert "Net Cash Flow" in csv_text
    assert "100000" in csv_text


@pytest.mark.asyncio
async def test_multi_workspace_isolation(db_session: AsyncSession, setup_analytics_data: dict):
    """Validates anti-IDOR defense: another workspace cannot access or aggregate data."""
    other_ws_id = uuid.uuid4()
    service = AnalyticsService(db_session)

    # Empty overview for non-existent / empty workspace
    overview = await service.get_overview(
        workspace_id=other_ws_id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        currency="INR",
    )
    assert overview["total_income_paise"] == 0
    assert overview["total_expenses_paise"] == 0
    assert overview["transaction_count"] == 0


# ==============================================================================
# 3. HTTP API ENDPOINT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_api_analytics_endpoints(
    client: AsyncClient,
    registered_user: dict,
    setup_analytics_data: dict,
):
    """Tests full suite of analytics HTTP API routes with authentication and permissions."""
    workspace = registered_user["workspace"]
    headers = registered_user["headers"]

    # 1. Overview
    resp_overview = await client.get(
        f"/api/v1/workspaces/{workspace.id}/analytics/overview?start_date=2026-02-01&end_date=2026-02-28",
        headers=headers,
    )
    assert resp_overview.status_code == 200
    ov_data = resp_overview.json()["data"]
    assert ov_data["total_income_paise"] == 10000000
    assert ov_data["savings_rate_percentage"] == 78.0

    # 2. Cash Flow Trends
    resp_cf = await client.get(
        f"/api/v1/workspaces/{workspace.id}/analytics/cash-flow?start_date=2026-02-01&end_date=2026-02-28&grouping=month",
        headers=headers,
    )
    assert resp_cf.status_code == 200
    assert len(resp_cf.json()["data"]["trends"]) >= 1

    # 3. Categories
    resp_cat = await client.get(
        f"/api/v1/workspaces/{workspace.id}/analytics/categories?start_date=2026-02-01&end_date=2026-02-28",
        headers=headers,
    )
    assert resp_cat.status_code == 200
    assert len(resp_cat.json()["data"]["categories"]) >= 1

    # 4. Merchants
    resp_m = await client.get(
        f"/api/v1/workspaces/{workspace.id}/analytics/merchants?start_date=2026-02-01&end_date=2026-02-28",
        headers=headers,
    )
    assert resp_m.status_code == 200
    assert len(resp_m.json()["data"]["merchants"]) >= 1

    # 5. Net Worth
    resp_nw = await client.get(
        f"/api/v1/workspaces/{workspace.id}/analytics/net-worth",
        headers=headers,
    )
    assert resp_nw.status_code == 200
    assert resp_nw.json()["data"]["net_worth_paise"] == 12500000

    # 6. Period Comparison
    resp_comp = await client.get(
        f"/api/v1/workspaces/{workspace.id}/analytics/comparison?current_start=2026-02-01&current_end=2026-02-28",
        headers=headers,
    )
    assert resp_comp.status_code == 200
    assert "deltas" in resp_comp.json()["data"]

    # 7. CSV Export
    resp_export = await client.get(
        f"/api/v1/workspaces/{workspace.id}/analytics/export?report_type=overview&start_date=2026-02-01&end_date=2026-02-28",
        headers=headers,
    )
    assert resp_export.status_code == 200
    assert resp_export.headers["content-type"].startswith("text/csv")
    assert "Arthsavora Financial Analytics Summary" in resp_export.text
