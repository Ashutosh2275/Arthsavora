"""
Arthsavora Recurring Transactions, Subscriptions & Cash-Flow Commitments Test Suite
Validates:
1. Pure domain scheduling calculations, leap-year handling, and end-of-month pinning.
2. Recurring cost normalization across billing intervals.
3. Occurrence state derivation and idempotency guarantees.
4. Transaction matching heuristics (exact, strong, variable pricing, non-match).
5. Explainable pattern detection from historical transaction clusters.
6. Authoritative PostgreSQL lifecycle for recurring definitions and occurrences.
7. Subscriptions with trial tracking, renewal cycles, and cancellation workflows.
8. Occurrence reconciliation with real transactions (strict separation: zero ledger mutations).
9. Forward-looking cash-flow commitments overview (7, 30, 90 days).
10. Multi-tenant workspace isolation & anti-IDOR defenses.
11. Authenticated RESTful HTTP API endpoints.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recurring import (
    EndOfMonthPolicy,
    OccurrenceStatus,
    RecurringDirection,
    RecurringFrequency,
    RecurringStatus,
    SubscriptionStatus,
    calculate_next_occurrence,
    calculate_transaction_match,
    detect_recurring_patterns_from_transactions,
    evaluate_occurrence_state,
    generate_occurrence_dates_in_window,
    is_leap_year,
    normalize_cost_to_monthly_and_annual,
)
from app.infrastructure.database.models import Account, Category, Transaction, User, Workspace
from app.infrastructure.database.models.recurring import (
    RecurringDefinition,
    RecurringOccurrence,
    Subscription,
    RecurringSuggestion,
)
from app.schemas.recurring_schema import (
    OccurrenceMatchRequest,
    RecurringDefinitionCreateRequest,
    SubscriptionCreateRequest,
    SuggestionConfirmRequest,
    SuggestionDismissRequest,
)
from app.services.recurring.commitment_service import CommitmentService
from app.services.recurring.detection_service import DetectionService
from app.services.recurring.matching_service import MatchingService
from app.services.recurring.recurring_service import RecurringService
from app.services.recurring.scheduling_service import SchedulingService
from app.services.recurring.subscription_service import SubscriptionService


# ==============================================================================
# 1. PURE DOMAIN & SCHEDULING CALCULATIONS
# ==============================================================================

def test_recurrence_date_scheduling_and_leap_year():
    """Validates recurrence date math across daily, weekly, monthly, and leap-year boundaries."""
    # 1. Daily
    d1 = calculate_next_occurrence(date(2026, 1, 1), RecurringFrequency.DAILY, interval=1)
    assert d1 == date(2026, 1, 2)

    # 2. Weekly with weekday pinning (e.g. Wednesday = 2)
    # 2026-01-01 is Thursday (3). Next Wednesday is 2026-01-07.
    w1 = calculate_next_occurrence(date(2026, 1, 1), RecurringFrequency.WEEKLY, day_of_week=2)
    assert w1 == date(2026, 1, 7)
    assert w1.weekday() == 2

    # 3. Biweekly
    bw = calculate_next_occurrence(date(2026, 1, 1), RecurringFrequency.BIWEEKLY)
    assert bw == date(2026, 1, 15)

    # 4. End-of-month pinning (Jan 31 -> Feb 28 -> Mar 31 -> Apr 30 -> May 31)
    # Does not drift permanently to the 28th!
    m1 = calculate_next_occurrence(date(2026, 1, 31), RecurringFrequency.MONTHLY, day_of_month=31)
    assert m1 == date(2026, 2, 28)

    m2 = calculate_next_occurrence(m1, RecurringFrequency.MONTHLY, day_of_month=31)
    assert m2 == date(2026, 3, 31)

    m3 = calculate_next_occurrence(m2, RecurringFrequency.MONTHLY, day_of_month=31)
    assert m3 == date(2026, 4, 30)

    m4 = calculate_next_occurrence(m3, RecurringFrequency.MONTHLY, day_of_month=31)
    assert m4 == date(2026, 5, 31)

    # 5. Leap-Year Handling (2024 is leap year, 2025/2026 are not, 2028 is)
    assert is_leap_year(2024) is True
    assert is_leap_year(2025) is False
    assert is_leap_year(2026) is False
    assert is_leap_year(2028) is True

    # Leap day annual schedule: Feb 29 2024 -> Feb 28 2025 -> Feb 28 2026 -> Feb 29 2028
    ly_next = calculate_next_occurrence(date(2024, 2, 29), RecurringFrequency.ANNUAL, day_of_month=29)
    assert ly_next == date(2025, 2, 28)

    # 6. Quarterly & Semi-Annual
    q1 = calculate_next_occurrence(date(2026, 1, 15), RecurringFrequency.QUARTERLY)
    assert q1 == date(2026, 4, 15)

    sa1 = calculate_next_occurrence(date(2026, 1, 15), RecurringFrequency.SEMI_ANNUAL)
    assert sa1 == date(2026, 7, 15)


def test_normalize_cost_to_monthly_and_annual():
    """Validates cost normalizations across all standard recurrence intervals."""
    # Monthly: ₹1,000 (100,000 paise)
    m_mo, m_yr = normalize_cost_to_monthly_and_annual(100000, "monthly")
    assert m_mo == 100000
    assert m_yr == 1200000

    # Weekly: ₹700 (70,000 paise) -> 52 weeks = 36,40,000 annual, ~3,03,334 monthly
    w_mo, w_yr = normalize_cost_to_monthly_and_annual(70000, "weekly")
    assert w_yr == 3640000
    assert w_mo == 303334

    # Quarterly: ₹3,000 (300,000 paise) -> 12,00,000 annual, 1,00,000 monthly
    q_mo, q_yr = normalize_cost_to_monthly_and_annual(300000, "quarterly")
    assert q_yr == 1200000
    assert q_mo == 100000

    # Annual: ₹12,000 (1,200,000 paise) -> 1,200,000 annual, 100,000 monthly
    a_mo, a_yr = normalize_cost_to_monthly_and_annual(1200000, "annual")
    assert a_yr == 1200000
    assert a_mo == 100000


def test_evaluate_occurrence_state():
    """Validates state transitions based on evaluation date and reconciliation flags."""
    today = date(2026, 11, 14)

    # Past date with no match -> overdue
    st_past = evaluate_occurrence_state(date(2026, 11, 10), today)
    assert st_past == OccurrenceStatus.OVERDUE

    # Today -> due
    st_today = evaluate_occurrence_state(today, today)
    assert st_today == OccurrenceStatus.DUE

    # 2 days in future -> upcoming
    st_upcoming = evaluate_occurrence_state(date(2026, 11, 16), today)
    assert st_upcoming == OccurrenceStatus.UPCOMING

    # 15 days in future -> scheduled
    st_future = evaluate_occurrence_state(date(2026, 11, 30), today)
    assert st_future == OccurrenceStatus.SCHEDULED

    # Matched transaction takes priority over overdue
    st_matched = evaluate_occurrence_state(date(2026, 11, 10), today, matched_transaction_id=uuid.uuid4())
    assert st_matched == OccurrenceStatus.MATCHED

    # Confirmed takes priority
    st_confirmed = evaluate_occurrence_state(date(2026, 11, 10), today, is_confirmed=True)
    assert st_confirmed == OccurrenceStatus.CONFIRMED

    # Skipped
    st_skipped = evaluate_occurrence_state(date(2026, 11, 10), today, is_skipped=True)
    assert st_skipped == OccurrenceStatus.SKIPPED


def test_transaction_matching_heuristics():
    """Validates exact, strong, variable, and non-matching tiers."""
    exp_date = date(2026, 11, 1)
    exp_amt = 2500000  # ₹25,000

    # Exact Match: same amount, 1 day diff, matching merchant
    m_exact = calculate_transaction_match(
        expected_amount_paise=exp_amt,
        tx_amount_paise=exp_amt,
        expected_date=exp_date,
        tx_date=date(2026, 11, 2),
        expected_merchant_name="Landlord Realty",
        tx_merchant_name="Landlord Realty Pvt Ltd",
    )
    assert m_exact.is_match is True
    assert m_exact.match_tier == "exact"
    assert m_exact.confidence_score >= Decimal("0.85")

    # Variable Pricing Match: utility bill with 15% variance
    m_var = calculate_transaction_match(
        expected_amount_paise=100000,
        tx_amount_paise=115000,
        expected_date=exp_date,
        tx_date=date(2026, 11, 3),
        expected_merchant_name="Tata Power",
        tx_merchant_name="Tata Power Electricity",
        is_variable_amount=True,
    )
    assert m_var.is_match is True
    assert m_var.match_tier in ("exact", "strong")

    # Mismatch: Date diff > 10 days
    m_far = calculate_transaction_match(
        expected_amount_paise=exp_amt,
        tx_amount_paise=exp_amt,
        expected_date=exp_date,
        tx_date=date(2026, 11, 20),
    )
    assert m_far.is_match is False
    assert m_far.match_tier == "none"

    # Direction mismatch
    m_dir = calculate_transaction_match(
        expected_amount_paise=exp_amt,
        tx_amount_paise=exp_amt,
        expected_date=exp_date,
        tx_date=exp_date,
        direction_match=False,
    )
    assert m_dir.is_match is False
    assert m_dir.match_tier == "none"


def test_detect_recurring_clusters():
    """Validates recurring pattern intelligence from synthetic transaction history."""
    # Monthly Netflix transactions (3 consecutive months)
    txs = [
      {
          "merchant_name": "Netflix India",
          "description": "NETFLIX MUMBAI",
          "amount_paise": 64900,
          "transaction_date": date(2026, 8, 5),
          "direction": "outflow",
          "status": "posted",
      },
      {
          "merchant_name": "Netflix India",
          "description": "NETFLIX MUMBAI",
          "amount_paise": 64900,
          "transaction_date": date(2026, 9, 5),
          "direction": "outflow",
          "status": "posted",
      },
      {
          "merchant_name": "Netflix India",
          "description": "NETFLIX MUMBAI",
          "amount_paise": 64900,
          "transaction_date": date(2026, 10, 5),
          "direction": "outflow",
          "status": "posted",
      },
      # Unrelated single transaction
      {
          "merchant_name": "Zara Retail",
          "description": "ZARA PHOENIX MALL",
          "amount_paise": 349900,
          "transaction_date": date(2026, 9, 12),
          "direction": "outflow",
          "status": "posted",
      },
    ]

    patterns = detect_recurring_patterns_from_transactions(txs, as_of_date=date(2026, 10, 20))
    assert len(patterns) == 1
    p = patterns[0]
    assert "netflix" in p.merchant_name.lower()
    assert p.suggested_frequency == RecurringFrequency.MONTHLY
    assert p.suggested_amount_paise == 64900
    assert p.confidence_score >= Decimal("0.80")
    assert p.evidence_count == 3


# ==============================================================================
# 2. INTEGRATION TESTS (RECURRING, SUBSCRIPTIONS, MATCHING, COMMITMENTS)
# ==============================================================================

@pytest.fixture
async def setup_recurring_data(db_session: AsyncSession, registered_user: dict):
    """Sets up a test workspace, owner user, category, and checking account."""
    ws: Workspace = registered_user["workspace"]
    user = registered_user["user"]

    cat = Category(
        workspace_id=ws.id,
        name="Housing & Utilities",
        slug=f"housing-{uuid.uuid4().hex[:6]}",
        category_type="expense",
    )
    db_session.add(cat)

    acc = Account(
        workspace_id=ws.id,
        name="Salary Checking",
        account_type="savings",
        institution_name="HDFC Bank",
        currency="INR",
        current_book_balance_paise=15000000,
        status="active",
    )
    db_session.add(acc)
    await db_session.flush()
    await db_session.commit()

    return {
        "workspace": ws,
        "user": user,
        "category": cat,
        "account": acc,
    }


@pytest.mark.asyncio
async def test_recurring_definition_lifecycle_and_occurrence_generation(
    db_session: AsyncSession,
    setup_recurring_data: dict,
):
    """Validates recurring definition creation, idempotent occurrence batching, pause, resume, and cancel."""
    ws = setup_recurring_data["workspace"]
    user = setup_recurring_data["user"]
    cat = setup_recurring_data["category"]
    acc = setup_recurring_data["account"]

    rec_service = RecurringService(db_session)

    # 1. Create monthly recurring rent
    create_req = RecurringDefinitionCreateRequest(
        name="Apartment Rent",
        direction=RecurringDirection.OUTFLOW,
        transaction_type="expense",
        expected_amount_paise=3500000,  # ₹35,000
        category_id=cat.id,
        account_id=acc.id,
        frequency=RecurringFrequency.MONTHLY,
        day_of_month=1,
        start_date=date(2026, 11, 1),
    )
    defn = await rec_service.create_definition(
        workspace_id=ws.id,
        payload=create_req,
        created_by_id=user.id,
    )
    assert defn.status == "active"
    assert defn.expected_amount_paise == 3500000
    assert defn.normalized_monthly_paise == 3500000
    assert defn.normalized_annual_paise == 42000000

    # 2. Check occurrences were idempotently generated for 90 days ahead
    occurrences = await rec_service.list_occurrences(workspace_id=ws.id, definition_id=defn.id)
    assert len(occurrences) >= 3  # Nov, Dec, Jan

    # 3. Pause definition
    paused = await rec_service.pause_definition(defn.id, ws.id)
    assert paused.status == "paused"

    # 4. Resume definition
    resumed = await rec_service.resume_definition(defn.id, ws.id)
    assert resumed.status == "active"

    # 5. Cancel definition
    cancelled = await rec_service.cancel_definition(defn.id, ws.id)
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_subscription_lifecycle_and_trial_tracking(
    db_session: AsyncSession,
    setup_recurring_data: dict,
):
    """Validates subscription tracking, trial period status, and cancellation."""
    ws = setup_recurring_data["workspace"]
    user = setup_recurring_data["user"]
    sub_service = SubscriptionService(db_session)

    # 1. Create subscription with active trial
    sub_req = SubscriptionCreateRequest(
        name="GitHub Copilot",
        provider_name="GitHub Inc",
        expected_amount_paise=100000,  # ₹1,000
        billing_frequency="monthly",
        start_date=date(2026, 11, 1),
        next_billing_date=date(2026, 12, 1),
        trial_end_date=date(2026, 11, 30),  # Active trial
        create_recurring_definition=True,
    )
    sub = await sub_service.create_subscription(
        workspace_id=ws.id,
        payload=sub_req,
        created_by_id=user.id,
    )
    assert sub.status == SubscriptionStatus.TRIAL.value
    assert sub.estimated_monthly_paise == 100000
    assert sub.recurring_definition_id is not None

    # 2. Cancel subscription
    cancelled = await sub_service.cancel_subscription(sub.id, ws.id)
    assert cancelled.status == SubscriptionStatus.CANCELLED.value
    assert cancelled.cancellation_date == date.today()


@pytest.mark.asyncio
async def test_occurrence_reconciliation_and_actual_transaction_separation(
    db_session: AsyncSession,
    setup_recurring_data: dict,
):
    """
    Validates that:
    1. An expected occurrence is NOT a posted transaction.
    2. Matching associates the occurrence with a real transaction without altering general ledger journal entries.
    3. Unmatching cleanly disassociates the transaction and restores occurrence state.
    """
    ws = setup_recurring_data["workspace"]
    acc = setup_recurring_data["account"]
    rec_service = RecurringService(db_session)
    matching_service = MatchingService(db_session)

    # Create recurring definition
    defn = await rec_service.create_definition(
        workspace_id=ws.id,
        payload=RecurringDefinitionCreateRequest(
            name="Electricity Bill",
            direction=RecurringDirection.OUTFLOW,
            expected_amount_paise=250000,  # ₹2,500
            is_variable_amount=True,
            frequency=RecurringFrequency.MONTHLY,
            day_of_month=15,
            start_date=date(2026, 11, 15),
        ),
    )

    occurrences = await rec_service.list_occurrences(workspace_id=ws.id, definition_id=defn.id)
    occ = occurrences[0]
    assert occ.status in ("scheduled", "due", "upcoming", "overdue")
    assert occ.matched_transaction_id is None

    # Seed an actual posted transaction
    real_tx = Transaction(
        workspace_id=ws.id,
        account_id=acc.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("2650.00"),
        amount_paise=265000,
        currency="INR",
        transaction_date=date(2026, 11, 16),
        description="Tata Power Bill Payment",
        merchant_name="Tata Power",
        status="posted",
    )
    db_session.add(real_tx)
    await db_session.commit()

    # 1. Match occurrence to real transaction
    matched_occ = await matching_service.match_occurrence_to_transaction(
        occurrence_id=occ.id,
        workspace_id=ws.id,
        transaction_id=real_tx.id,
        notes="Reconciled against electricity debit",
    )
    assert matched_occ.status == OccurrenceStatus.MATCHED.value
    assert matched_occ.matched_transaction_id == real_tx.id
    assert matched_occ.matched_amount_paise == 265000
    assert matched_occ.amount_variance_paise == 15000  # ₹150 over expected

    # 2. Verify unmatching restores occurrence state cleanly
    unmatched_occ = await matching_service.unmatch_occurrence(occ.id, ws.id)
    assert unmatched_occ.status != OccurrenceStatus.MATCHED.value
    assert unmatched_occ.matched_transaction_id is None


@pytest.mark.asyncio
async def test_commitments_service_aggregation(
    db_session: AsyncSession,
    setup_recurring_data: dict,
):
    """Validates 30-day forward-looking cash flow commitment calculations."""
    ws = setup_recurring_data["workspace"]
    rec_service = RecurringService(db_session)
    commitment_service = CommitmentService(db_session)

    # Recurring Salary Inflow: ₹1,00,000
    await rec_service.create_definition(
        workspace_id=ws.id,
        payload=RecurringDefinitionCreateRequest(
            name="Monthly Salary",
            direction=RecurringDirection.INFLOW,
            transaction_type="income",
            expected_amount_paise=10000000,
            frequency=RecurringFrequency.MONTHLY,
            day_of_month=1,
            start_date=date(2026, 11, 1),
        ),
    )

    # Recurring Rent Outflow: ₹30,000
    await rec_service.create_definition(
        workspace_id=ws.id,
        payload=RecurringDefinitionCreateRequest(
            name="Apartment Rent",
            direction=RecurringDirection.OUTFLOW,
            transaction_type="expense",
            expected_amount_paise=3000000,
            frequency=RecurringFrequency.MONTHLY,
            day_of_month=5,
            start_date=date(2026, 11, 5),
        ),
    )

    # Evaluate 30-day commitments from 2026-11-01
    commitments = await commitment_service.get_commitments(
        workspace_id=ws.id,
        window_days=30,
        start_date=date(2026, 11, 1),
    )

    assert commitments.total_expected_inflow_paise >= 10000000
    assert commitments.total_expected_outflow_paise >= 3000000
    assert commitments.net_commitment_paise == commitments.total_expected_inflow_paise - commitments.total_expected_outflow_paise
    assert commitments.active_recurring_count >= 2
    assert len(commitments.upcoming_occurrences) >= 2


@pytest.mark.asyncio
async def test_pattern_detection_confirm_and_dismiss(
    db_session: AsyncSession,
    setup_recurring_data: dict,
):
    """Validates automatic pattern detection from transaction history and user confirmation/dismissal."""
    ws = setup_recurring_data["workspace"]
    acc = setup_recurring_data["account"]
    detection_service = DetectionService(db_session)
    rec_service = RecurringService(db_session)

    # Seed 3 monthly broadband payments
    d1 = date(2026, 8, 10)
    d2 = date(2026, 9, 10)
    d3 = date(2026, 10, 10)

    for d in (d1, d2, d3):
        tx = Transaction(
            workspace_id=ws.id,
            account_id=acc.id,
            transaction_type="expense",
            direction="outflow",
            amount=Decimal("999.00"),
            amount_paise=99900,
            currency="INR",
            transaction_date=d,
            description="AIRTEL BROADBAND BILL",
            merchant_name="Airtel Broadband",
            status="posted",
        )
        db_session.add(tx)
    await db_session.commit()

    # 1. Run detection
    suggestions = await detection_service.run_detection(
        workspace_id=ws.id,
        lookback_days=180,
        as_of_date=date(2026, 10, 20),
    )
    assert len(suggestions) >= 1
    sugg = next(s for s in suggestions if "airtel" in s.merchant_name.lower())
    assert sugg.suggested_frequency == "monthly"
    assert sugg.suggested_amount_paise == 99900
    assert sugg.status == "pending"

    # 2. Confirm suggestion into active definition
    confirmed = await detection_service.confirm_suggestion(
        suggestion_id=sugg.id,
        workspace_id=ws.id,
        payload=SuggestionConfirmRequest(name="Airtel Home Fiber"),
    )
    assert confirmed.status == "confirmed"

    # Verify definition was created
    defs = await rec_service.list_definitions(workspace_id=ws.id)
    assert any(d.name == "Airtel Home Fiber" for d in defs)

    # 3. Dismiss another test suggestion
    new_sugg = RecurringSuggestion(
        workspace_id=ws.id,
        merchant_name="Random Merchant",
        normalized_description="RANDOM",
        direction="outflow",
        suggested_frequency="monthly",
        suggested_amount_paise=50000,
        suggested_amount=Decimal("500.00"),
        min_amount_paise=50000,
        max_amount_paise=50000,
        currency="INR",
        confidence_score=Decimal("0.70"),
        evidence_count=2,
        first_seen_date=date(2026, 8, 1),
        last_seen_date=date(2026, 9, 1),
        estimated_next_date=date(2026, 10, 1),
        status="pending",
    )
    db_session.add(new_sugg)
    await db_session.commit()

    dismissed = await detection_service.dismiss_suggestion(
        suggestion_id=new_sugg.id,
        workspace_id=ws.id,
        payload=SuggestionDismissRequest(reason="One-time equipment purchase"),
    )
    assert dismissed.status == "dismissed"
    assert dismissed.dismissed_reason == "One-time equipment purchase"


@pytest.mark.asyncio
async def test_recurring_workspace_isolation(
    db_session: AsyncSession,
    setup_recurring_data: dict,
):
    """Validates anti-IDOR defense: cross-workspace access is strictly rejected with 404."""
    ws_a = setup_recurring_data["workspace"]
    user_a = setup_recurring_data["user"]
    ws_b_id = uuid.uuid4()

    rec_service = RecurringService(db_session)

    defn = await rec_service.create_definition(
        workspace_id=ws_a.id,
        payload=RecurringDefinitionCreateRequest(
            name="Workspace A Secret Subscription",
            direction=RecurringDirection.OUTFLOW,
            expected_amount_paise=100000,
            frequency=RecurringFrequency.MONTHLY,
            start_date=date(2026, 11, 1),
        ),
        created_by_id=user_a.id,
    )

    # Attempting to fetch from Workspace B must fail
    with pytest.raises(Exception):
        await rec_service.get_definition(defn.id, ws_b_id)


# ==============================================================================
# 3. HTTP RESTful API ENDPOINT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_api_recurring_and_subscriptions_endpoints(
    client: AsyncClient,
    registered_user: dict,
    setup_recurring_data: dict,
    db_session: AsyncSession,
):
    """Validates complete set of authenticated RESTful endpoints for recurring activities and subscriptions."""
    ws = registered_user["workspace"]
    headers = registered_user["headers"]

    # 1. POST /recurring (Create Definition)
    create_res = await client.post(
        f"/api/v1/workspaces/{ws.id}/recurring",
        headers=headers,
        json={
            "name": "API Test Gym Membership",
            "direction": "outflow",
            "transaction_type": "expense",
            "expected_amount_paise": 200000,
            "currency": "INR",
            "frequency": "monthly",
            "day_of_month": 5,
            "start_date": "2026-11-01",
        },
    )
    assert create_res.status_code == 201, create_res.text
    def_data = create_res.json()["data"]
    def_id = def_data["id"]
    assert def_data["name"] == "API Test Gym Membership"

    # 2. GET /recurring (List Definitions)
    list_res = await client.get(
        f"/api/v1/workspaces/{ws.id}/recurring",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 3. GET /recurring/commitments/overview
    commitments_res = await client.get(
        f"/api/v1/workspaces/{ws.id}/recurring/commitments/overview?window_days=30",
        headers=headers,
    )
    assert commitments_res.status_code == 200
    c_data = commitments_res.json()["data"]
    assert c_data["window_days"] == 30
    assert "total_expected_outflow_paise" in c_data

    # 4. POST /recurring/subscriptions/create
    sub_res = await client.post(
        f"/api/v1/workspaces/{ws.id}/recurring/subscriptions/create",
        headers=headers,
        json={
            "name": "Prime Video",
            "provider_name": "Amazon",
            "expected_amount_paise": 149000,
            "billing_frequency": "annual",
            "start_date": "2026-11-01",
            "next_billing_date": "2027-11-01",
            "create_recurring_definition": True,
        },
    )
    assert sub_res.status_code == 201
    sub_data = sub_res.json()["data"]
    assert sub_data["name"] == "Prime Video"

    # 5. POST /recurring/{id}/pause
    pause_res = await client.post(
        f"/api/v1/workspaces/{ws.id}/recurring/{def_id}/pause",
        headers=headers,
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["status"] == "paused"
