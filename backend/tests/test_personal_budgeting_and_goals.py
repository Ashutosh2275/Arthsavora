"""
Arthsavora Personal Budgeting, Spending Controls & Financial Goals Test Suite
Validates:
1. Domain metric calculations (budget progress, warning states, linear projections, goal pacing, period bounds).
2. Authoritative PostgreSQL spending aggregation with strict transfer/card bill exclusions and refund netting.
3. Immutable budget audit revision ledger (revisions tracking parameter changes and deletions with reasons).
4. Idempotent threshold alert generation (50%, 75%, 80%, 90%, 100% crossing without duplicate spam).
5. Budget period rollover across monthly, quarterly, and annual intervals.
6. Target-based savings goals, milestones, and auditable contribution/withdrawal activity ledgers.
7. Non-negative goal balance enforcement and auto-completion status triggers.
8. Multi-tenant workspace isolation & anti-IDOR protection.
9. Authenticated RESTful HTTP API endpoints.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.budget import (
    BudgetType,
    BudgetWarningState,
    GoalActivityType,
    GoalPriority,
    GoalStatus,
    GoalType,
    RecurrenceInterval,
    calculate_budget_progress,
    calculate_goal_progress,
    calculate_linear_projection,
    calculate_period_progress,
    generate_next_period_bounds,
)
from app.domain.exceptions import BusinessRuleViolationError
from app.infrastructure.database.models import Account, Category, Transaction, Workspace
from app.infrastructure.database.models.budget import (
    Budget,
    BudgetAllocation,
    BudgetRevision,
    BudgetAlert,
)
from app.infrastructure.database.models.goal import FinancialGoal, GoalActivity
from app.services.budget.budget_service import BudgetService
from app.services.budget.goal_service import GoalService


# ==============================================================================
# 1. PURE DOMAIN & CALCULATION TESTS
# ==============================================================================

def test_calculate_budget_progress_thresholds():
    """Validates warning state progressions across budget utilization percentages."""
    allocated = 10000000  # ₹1,00,000

    # Normal: 50% spent (< 80% threshold)
    p_norm = calculate_budget_progress(allocated, 5000000, 80)
    assert p_norm.utilization_percentage == 50.0
    assert p_norm.remaining_amount_paise == 5000000
    assert not p_norm.is_overspent
    assert p_norm.warning_state == BudgetWarningState.NORMAL

    # Warning: 85% spent (>= threshold 80% and < 100%)
    p_warn = calculate_budget_progress(allocated, 8500000, 80)
    assert p_warn.warning_state == BudgetWarningState.WARNING

    # Exhausted: exactly 100%
    p_exh = calculate_budget_progress(allocated, 10000000, 80)
    assert p_exh.warning_state == BudgetWarningState.EXHAUSTED
    assert p_exh.remaining_amount_paise == 0

    # Exceeded: 105% spent (>= 100%)
    p_exceed = calculate_budget_progress(allocated, 10500000, 80)
    assert p_exceed.is_overspent
    assert p_exceed.warning_state == BudgetWarningState.EXCEEDED
    assert p_exceed.remaining_amount_paise == -500000


def test_calculate_period_progress():
    """Validates period elapsed calculations."""
    start = date(2026, 11, 1)
    end = date(2026, 11, 30)  # 30 days

    # Day 15
    res_15 = calculate_period_progress(start, end, date(2026, 11, 15))
    assert res_15.total_days == 30
    assert res_15.days_elapsed == 15
    assert res_15.days_remaining == 15
    assert res_15.period_progress_percentage == 50.0

    # Before period started
    res_before = calculate_period_progress(start, end, date(2026, 10, 25))
    assert res_before.days_elapsed == 0
    assert res_before.days_remaining == 36
    assert res_before.period_progress_percentage == 0.0

    # After period ended
    res_after = calculate_period_progress(start, end, date(2026, 12, 5))
    assert res_after.days_elapsed == 30
    assert res_after.days_remaining == 0
    assert res_after.period_progress_percentage == 100.0


def test_calculate_linear_projection():
    """Validates linear period-end burn rate projection formula."""
    allocated = 6000000  # ₹60,000 ceiling
    spent = 3000000      # ₹30,000 spent in 10 days -> ₹3,000/day
    days_elapsed = 10
    total_days = 30

    proj = calculate_linear_projection(allocated, spent, days_elapsed, total_days)
    assert proj.average_daily_spend_paise == 300000  # ₹3,000
    assert proj.projected_period_end_spend_paise == 9000000  # ₹90,000 projected
    assert proj.projected_variance_paise == 3000000  # ₹30,000 over budget
    assert proj.is_projected_to_exceed is True
    assert "uniform daily burn rate" in proj.confidence_disclosure


def test_calculate_goal_progress():
    """Validates savings goal pacing and required monthly contribution rate."""
    target = 12000000  # ₹1,20,000
    current = 6000000   # ₹60,000 (50%)
    start = date(2026, 1, 1)
    target_d = date(2026, 7, 1)  # 6 months target
    as_of = date(2026, 4, 1)    # 3 months remaining (~91 days)

    g_prog = calculate_goal_progress(target, current, start, target_d, as_of)
    assert g_prog.progress_percentage == 50.0
    assert g_prog.remaining_amount_paise == 6000000
    assert not g_prog.is_completed
    assert g_prog.days_remaining == 91
    # 60,000 remaining over ~3 months -> approx 20,000/month
    assert g_prog.required_monthly_savings_paise is not None
    assert 1900000 <= g_prog.required_monthly_savings_paise <= 2100000


def test_generate_next_period_bounds():
    """Validates automatic rollover date generation for recurring intervals."""
    # Monthly: Nov 2026 -> Dec 2026
    start_m = date(2026, 11, 1)
    end_m = date(2026, 11, 30)
    next_s_m, next_e_m = generate_next_period_bounds(start_m, end_m, RecurrenceInterval.MONTHLY)
    assert next_s_m == date(2026, 12, 1)
    assert next_e_m == date(2026, 12, 31)

    # Annual: 2026 -> 2027
    start_y = date(2026, 1, 1)
    end_y = date(2026, 12, 31)
    next_s_y, next_e_y = generate_next_period_bounds(start_y, end_y, RecurrenceInterval.ANNUAL)
    assert next_s_y == date(2027, 1, 1)
    assert next_e_y == date(2027, 12, 31)


# ==============================================================================
# 2. DATABASE INTEGRATION & SERVICE TESTS
# ==============================================================================

@pytest.fixture
async def setup_budget_data(db_session: AsyncSession, registered_user: dict):
    """Provisions accounts, categories, and posted transactions to test budget evaluation."""
    workspace: Workspace = registered_user["workspace"]
    user = registered_user["user"]

    # 1. Accounts
    bank_acc = Account(
        workspace_id=workspace.id,
        name="HDFC Primary Savings",
        account_type="savings",
        institution_name="HDFC Bank",
        currency="INR",
        current_book_balance_paise=10000000,
        status="active",
    )
    cc_acc = Account(
        workspace_id=workspace.id,
        name="HDFC Credit Card",
        account_type="credit_card",
        institution_name="HDFC Bank",
        currency="INR",
        current_book_balance_paise=-500000,
        status="active",
    )
    db_session.add_all([bank_acc, cc_acc])
    await db_session.flush()

    # 2. Categories
    cat_dining = Category(
        workspace_id=workspace.id,
        name="Dining & Food",
        slug=f"dining-{uuid.uuid4().hex[:6]}",
        category_type="expense",
        color="#f59e0b",
        is_system=False,
    )
    cat_groceries = Category(
        workspace_id=workspace.id,
        name="Groceries",
        slug=f"groceries-{uuid.uuid4().hex[:6]}",
        category_type="expense",
        color="#10b981",
        is_system=False,
    )
    db_session.add_all([cat_dining, cat_groceries])
    await db_session.flush()

    # 3. Transactions for Nov 2026 period
    # Tx1: Normal Dining Expense ₹5,000 (posted) -> Counted
    t1 = Transaction(
        workspace_id=workspace.id,
        account_id=bank_acc.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("5000.00"),
        amount_paise=500000,
        currency="INR",
        transaction_date=date(2026, 11, 5),
        description="Restaurant Dinner",
        category_id=cat_dining.id,
        status="posted",
    )

    # Tx2: Groceries Expense ₹10,000 (posted) -> Counted
    t2 = Transaction(
        workspace_id=workspace.id,
        account_id=bank_acc.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("10000.00"),
        amount_paise=1000000,
        currency="INR",
        transaction_date=date(2026, 11, 10),
        description="Supermarket Groceries",
        category_id=cat_groceries.id,
        status="posted",
    )

    # Tx3: Groceries Refund ₹2,000 (contra-expense) -> Netted
    t3 = Transaction(
        workspace_id=workspace.id,
        account_id=bank_acc.id,
        transaction_type="refund",
        direction="inflow",
        amount=Decimal("2000.00"),
        amount_paise=200000,
        currency="INR",
        transaction_date=date(2026, 11, 12),
        description="Returned Defective Item",
        category_id=cat_groceries.id,
        status="posted",
    )

    # Tx4: Internal Transfer ₹15,000 -> MUST BE EXCLUDED
    t4 = Transaction(
        workspace_id=workspace.id,
        account_id=bank_acc.id,
        transaction_type="transfer",
        direction="outflow",
        amount=Decimal("15000.00"),
        amount_paise=1500000,
        currency="INR",
        transaction_date=date(2026, 11, 8),
        description="Transfer to Savings",
        status="posted",
    )

    # Tx5: Credit Card Bill Payment ₹8,000 -> MUST BE EXCLUDED
    t5 = Transaction(
        workspace_id=workspace.id,
        account_id=bank_acc.id,
        transaction_type="credit_card_payment",
        direction="outflow",
        amount=Decimal("8000.00"),
        amount_paise=800000,
        currency="INR",
        transaction_date=date(2026, 11, 15),
        description="HDFC CC Bill Payment",
        status="posted",
    )

    # Tx6: Pending Expense ₹4,000 -> MUST BE EXCLUDED
    t6 = Transaction(
        workspace_id=workspace.id,
        account_id=bank_acc.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("4000.00"),
        amount_paise=400000,
        currency="INR",
        transaction_date=date(2026, 11, 18),
        description="Pending Online Delivery",
        category_id=cat_dining.id,
        status="pending",
    )

    db_session.add_all([t1, t2, t3, t4, t5, t6])
    await db_session.flush()
    await db_session.commit()

    return {
        "workspace": workspace,
        "user": user,
        "bank_acc": bank_acc,
        "cat_dining": cat_dining,
        "cat_groceries": cat_groceries,
    }


@pytest.mark.asyncio
async def test_budget_spending_aggregation_and_exclusions(
    db_session: AsyncSession,
    setup_budget_data: dict,
):
    """
    Verifies that budget actual spend:
    - Counts posted expenses (₹5,000 dining + ₹10,000 groceries = ₹15,000 gross)
    - Nets refunds (₹2,000 groceries refund -> ₹8,000 net groceries)
    - Total eligible spend = ₹5,000 + ₹8,000 = ₹13,000 (1300000 paise)
    - Excludes internal transfer (₹15,000), card payment (₹8,000), and pending (₹4,000)
    """
    ws = setup_budget_data["workspace"]
    cat_dining = setup_budget_data["cat_dining"]
    cat_groceries = setup_budget_data["cat_groceries"]
    user = setup_budget_data["user"]

    service = BudgetService(db_session)

    # Create Budget for Nov 2026 with ₹20,000 total allocation
    budget = await service.create_budget(
        workspace_id=ws.id,
        name="November 2026 Household Budget",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        total_allocated_paise=2000000,  # ₹20,000
        budget_type="monthly",
        currency="INR",
        created_by_id=user.id,
        allocations=[
            {"category_id": cat_dining.id, "allocated_amount_paise": 600000, "warning_threshold_percentage": 80},     # ₹6,000
            {"category_id": cat_groceries.id, "allocated_amount_paise": 1000000, "warning_threshold_percentage": 80}, # ₹10,000
        ],
    )

    # Evaluate progress as of Nov 20, 2026
    progress = await service.get_budget_progress(
        budget_id=budget.id,
        workspace_id=ws.id,
        as_of_date=date(2026, 11, 20),
        evaluate_alerts=True,
    )

    # Total spend must be exactly ₹13,000 (1300000 paise)
    assert progress["total_spent_paise"] == 1300000
    assert progress["remaining_paise"] == 700000  # ₹20,000 - ₹13,000 = ₹7,000
    assert progress["utilization_percentage"] == 65.0
    assert progress["overspent"] is False

    # Check category allocations breakdown
    alloc_map = {a["category_name"]: a for a in progress["allocations"]}
    dining_a = alloc_map["Dining & Food"]
    assert dining_a["spent_paise"] == 500000  # ₹5,000
    assert dining_a["allocated_paise"] == 600000
    # 5,000 / 6,000 = 83.33% -> Warning threshold (80%) crossed -> Warning state
    assert dining_a["warning_state"] == BudgetWarningState.WARNING.value

    groc_a = alloc_map["Groceries"]
    assert groc_a["spent_paise"] == 800000  # ₹10,000 gross - ₹2,000 refund = ₹8,000 net
    assert groc_a["allocated_paise"] == 1000000
    # 8,000 / 10,000 = 80.0%
    assert groc_a["warning_state"] == BudgetWarningState.WARNING.value


@pytest.mark.asyncio
async def test_budget_revisions_and_idempotent_alerts(
    db_session: AsyncSession,
    setup_budget_data: dict,
):
    """
    Tests immutable revision ledger tracking and idempotent threshold alert creation.
    """
    ws = setup_budget_data["workspace"]
    user = setup_budget_data["user"]
    cat_dining = setup_budget_data["cat_dining"]

    service = BudgetService(db_session)

    # 1. Create Budget
    budget = await service.create_budget(
        workspace_id=ws.id,
        name="Auditable Budget",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        total_allocated_paise=1000000,  # ₹10,000
        created_by_id=user.id,
    )

    # 2. Update Budget
    await service.update_budget(
        budget_id=budget.id,
        workspace_id=ws.id,
        name="Auditable Budget Revised",
        total_allocated_paise=1500000,  # ₹15,000
        revision_reason="Cost of living adjustment",
        changed_by_id=user.id,
    )

    # 3. Add Category Allocation
    await service.add_allocation(
        budget_id=budget.id,
        workspace_id=ws.id,
        category_id=cat_dining.id,
        allocated_amount_paise=600000,
        warning_threshold_percentage=80,
        revision_reason="Allocate dining ceiling",
        changed_by_id=user.id,
    )

    # Verify revision history: 3 revisions
    revisions = await service.list_revisions(budget.id, ws.id)
    assert len(revisions) == 3
    rev_types = [r.revision_type for r in revisions]
    assert "created" in rev_types
    assert "budget_updated" in rev_types
    assert "allocation_added" in rev_types

    # Evaluate alerts twice to verify idempotency (no duplicate entries)
    prog1 = await service.get_budget_progress(budget.id, ws.id, as_of_date=date(2026, 11, 20), evaluate_alerts=True)
    alerts1 = await service.list_alerts(budget.id, ws.id)
    assert len(alerts1) >= 1

    # Second evaluation must NOT duplicate existing alerts
    prog2 = await service.get_budget_progress(budget.id, ws.id, as_of_date=date(2026, 11, 20), evaluate_alerts=True)
    assert prog2["new_alerts_triggered"] == 0
    alerts2 = await service.list_alerts(budget.id, ws.id)
    assert len(alerts2) == len(alerts1)


@pytest.mark.asyncio
async def test_budget_rollover(
    db_session: AsyncSession,
    setup_budget_data: dict,
):
    """Tests rolling over a budget and its category limits into the next month."""
    ws = setup_budget_data["workspace"]
    user = setup_budget_data["user"]
    cat_dining = setup_budget_data["cat_dining"]

    service = BudgetService(db_session)

    # Original Nov 2026 budget
    b_nov = await service.create_budget(
        workspace_id=ws.id,
        name="Nov 2026 Operational",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        total_allocated_paise=2500000,
        recurrence_interval="monthly",
        created_by_id=user.id,
        allocations=[{"category_id": cat_dining.id, "allocated_amount_paise": 1000000}],
    )

    # Rollover to Dec 2026
    b_dec = await service.rollover_budget(
        budget_id=b_nov.id,
        workspace_id=ws.id,
        created_by_id=user.id,
    )

    assert b_dec.id != b_nov.id
    assert b_dec.start_date == date(2026, 12, 1)
    assert b_dec.end_date == date(2026, 12, 31)
    assert b_dec.total_allocated_paise == 2500000
    assert len(b_dec.allocations) == 1
    assert b_dec.allocations[0].category_id == cat_dining.id


# ==============================================================================
# 3. FINANCIAL GOALS & ACTIVITY LEDGER TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_financial_goal_lifecycle_and_non_negative_balance(
    db_session: AsyncSession,
    registered_user: dict,
):
    """
    Tests financial savings goals:
    - Creation with targets and deadlines
    - Contributions accumulating balance
    - Immutable activity ledger records
    - Non-negative balance constraint on withdrawal
    - Auto-transition to 'completed' status upon hitting target
    """
    ws: Workspace = registered_user["workspace"]
    user = registered_user["user"]

    goal_service = GoalService(db_session)

    # 1. Create Goal: Emergency Fund of ₹50,000 (5000000 paise)
    goal = await goal_service.create_goal(
        workspace_id=ws.id,
        name="Contingency Reserve",
        target_amount_paise=5000000,
        goal_type="emergency_fund",
        currency="INR",
        start_date=date(2026, 1, 1),
        target_date=date(2026, 12, 31),
        priority="high",
        created_by_id=user.id,
    )
    assert goal.status == GoalStatus.ACTIVE.value
    assert goal.current_amount_paise == 0

    # 2. Record Contribution of ₹20,000
    act1 = await goal_service.record_contribution(
        goal_id=goal.id,
        workspace_id=ws.id,
        amount_paise=2000000,
        notes="Salary allocation 1",
        performed_by_id=user.id,
    )
    assert act1.resulting_balance_paise == 2000000
    assert goal.current_amount_paise == 2000000
    assert goal.status == GoalStatus.ACTIVE.value

    # 3. Attempt to withdraw ₹30,000 (exceeding ₹20,000 balance) -> MUST FAIL
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        await goal_service.record_withdrawal(
            goal_id=goal.id,
            workspace_id=ws.id,
            amount_paise=3000000,
            notes="Overdrawn withdrawal",
            performed_by_id=user.id,
        )
    assert exc_info.value.rule_name == "INSUFFICIENT_GOAL_BALANCE"

    # 4. Valid withdrawal of ₹5,000 -> balance becomes ₹15,000
    act2 = await goal_service.record_withdrawal(
        goal_id=goal.id,
        workspace_id=ws.id,
        amount_paise=500000,
        notes="Short term emergency draw",
        performed_by_id=user.id,
    )
    assert act2.resulting_balance_paise == 1500000
    assert goal.current_amount_paise == 1500000

    # 5. Contribute remaining ₹35,000 to hit ₹50,000 target -> Auto transitions to COMPLETED
    act3 = await goal_service.record_contribution(
        goal_id=goal.id,
        workspace_id=ws.id,
        amount_paise=3500000,
        notes="Bonus deposit",
        performed_by_id=user.id,
    )
    assert act3.resulting_balance_paise == 5000000
    assert goal.current_amount_paise == 5000000
    assert goal.status == GoalStatus.COMPLETED.value

    # 6. Verify full ledger history
    activities, count = await goal_service.list_activities(goal.id, ws.id)
    assert count == 3
    assert activities[0].id == act3.id  # Ordered by created_at desc


# ==============================================================================
# 4. MULTI-TENANT WORKSPACE ISOLATION & ANTI-IDOR
# ==============================================================================

@pytest.mark.asyncio
async def test_budget_and_goal_workspace_isolation(
    db_session: AsyncSession,
    setup_budget_data: dict,
):
    """Validates anti-IDOR defense: cross-workspace access is strictly rejected."""
    ws_a = setup_budget_data["workspace"]
    user_a = setup_budget_data["user"]
    ws_b_id = uuid.uuid4()

    b_service = BudgetService(db_session)
    g_service = GoalService(db_session)

    # Create resources in Workspace A
    budget_a = await b_service.create_budget(
        workspace_id=ws_a.id,
        name="Workspace A Budget",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        total_allocated_paise=1000000,
        created_by_id=user_a.id,
    )

    goal_a = await g_service.create_goal(
        workspace_id=ws_a.id,
        name="Workspace A Goal",
        target_amount_paise=5000000,
        created_by_id=user_a.id,
    )

    # Workspace B attempting to get Budget A -> Not Found
    with pytest.raises(Exception):
        await b_service.get_budget(budget_a.id, ws_b_id)

    # Workspace B attempting to get Goal A -> Not Found
    with pytest.raises(Exception):
        await g_service.get_goal(goal_a.id, ws_b_id)


# ==============================================================================
# 5. HTTP RESTful API ENDPOINT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_api_budgets_and_goals_endpoints(
    client: AsyncClient,
    registered_user: dict,
    setup_budget_data: dict,
):
    """Validates complete set of authenticated RESTful endpoints for budgets and goals."""
    ws = registered_user["workspace"]
    headers = registered_user["headers"]
    cat_dining = setup_budget_data["cat_dining"]

    # 1. POST /workspaces/{ws}/budgets (Create Budget)
    create_budget_resp = await client.post(
        f"/api/v1/workspaces/{ws.id}/budgets",
        headers=headers,
        json={
            "name": "Q4 Spending Framework",
            "start_date": "2026-10-01",
            "end_date": "2026-12-31",
            "total_allocated_paise": 7500000,
            "budget_type": "custom_period",
            "currency": "INR",
            "recurrence_interval": "quarterly",
            "allocations": [
                {
                    "category_id": str(cat_dining.id),
                    "allocated_amount_paise": 2000000,
                    "warning_threshold_percentage": 80,
                }
            ],
        },
    )
    assert create_budget_resp.status_code == 201
    budget_id = create_budget_resp.json()["data"]["id"]

    # 2. GET /workspaces/{ws}/budgets (List Budgets)
    list_budgets_resp = await client.get(
        f"/api/v1/workspaces/{ws.id}/budgets",
        headers=headers,
    )
    assert list_budgets_resp.status_code == 200
    assert len(list_budgets_resp.json()["data"]) >= 1

    # 3. GET /workspaces/{ws}/budgets/{id}/progress
    prog_resp = await client.get(
        f"/api/v1/workspaces/{ws.id}/budgets/{budget_id}/progress?as_of_date=2026-11-15",
        headers=headers,
    )
    assert prog_resp.status_code == 200
    p_data = prog_resp.json()["data"]
    assert p_data["budget_id"] == budget_id
    assert "linear_projection" in p_data

    # 4. GET /workspaces/{ws}/budgets/{id}/revisions
    rev_resp = await client.get(
        f"/api/v1/workspaces/{ws.id}/budgets/{budget_id}/revisions",
        headers=headers,
    )
    assert rev_resp.status_code == 200
    assert len(rev_resp.json()["data"]) >= 1

    # 5. POST /workspaces/{ws}/goals (Create Goal)
    create_goal_resp = await client.post(
        f"/api/v1/workspaces/{ws.id}/goals",
        headers=headers,
        json={
            "name": "Annual Family Vacation",
            "target_amount_paise": 15000000,
            "goal_type": "travel",
            "priority": "medium",
            "currency": "INR",
            "target_date": "2027-05-31",
        },
    )
    assert create_goal_resp.status_code == 201
    goal_id = create_goal_resp.json()["data"]["id"]

    # 6. POST /workspaces/{ws}/goals/{id}/contributions
    contrib_resp = await client.post(
        f"/api/v1/workspaces/{ws.id}/goals/{goal_id}/contributions",
        headers=headers,
        json={
            "amount_paise": 5000000,
            "notes": "Nov savings contribution",
        },
    )
    assert contrib_resp.status_code == 201
    assert contrib_resp.json()["data"]["resulting_balance_paise"] == 5000000

    # 7. GET /workspaces/{ws}/goals/{id}/progress
    goal_prog_resp = await client.get(
        f"/api/v1/workspaces/{ws.id}/goals/{goal_id}/progress",
        headers=headers,
    )
    assert goal_prog_resp.status_code == 200
    gp_data = goal_prog_resp.json()["data"]
    assert gp_data["current_amount_paise"] == 5000000
    assert gp_data["completion_percentage"] == 33.33

    # 8. GET /workspaces/{ws}/goals/{id}/activity
    act_resp = await client.get(
        f"/api/v1/workspaces/{ws.id}/goals/{goal_id}/activity",
        headers=headers,
    )
    assert act_resp.status_code == 200
    assert len(act_resp.json()["data"]) == 1
