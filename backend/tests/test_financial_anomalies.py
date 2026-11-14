"""
Arthsavora Financial Anomaly Detection, Fraud Signals & Risk Intelligence Test Suite
Validates deterministic rules, statistical outlier detection (MAD/IQR),
unsupervised ML Isolation Forest inference, hybrid risk scoring, whitelist exceptions,
user review workflows, workspace isolation, and HTTP API endpoints.
"""

import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List
import uuid

import httpx
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.anomaly import (
    AnomalyCategory,
    AnomalyEvidenceVO,
    AnomalySeverity,
    AnomalyStatus,
    CandidateTransactionVO,
    DEFAULT_SYSTEM_RULES,
    DetectionMethod,
    calculate_iqr,
    calculate_median_and_mad,
    detect_category_spike_anomaly,
    detect_merchant_amount_anomaly,
    detect_ml_isolation_forest,
    evaluate_deterministic_rules,
    extract_ml_feature_vector,
    matches_detection_exception,
    synthesize_hybrid_anomaly,
)
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.anomaly import AnomalyDetection, DetectionException, DetectionRule
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.merchant import Merchant
from app.infrastructure.database.models.recurring import RecurringDefinition, RecurringOccurrence
from app.infrastructure.database.models.transaction import Transaction
from app.infrastructure.database.models.workspace import Workspace
from app.repositories.anomaly_repository import AnomalyRepository
from app.schemas.anomaly_schema import (
    AnomalyReviewRequest,
    DetectionExceptionCreateRequest,
    DetectionRuleUpdateRequest,
)
from app.services.anomaly.detection_service import AnomalyDetectionService
from app.services.anomaly.review_service import AnomalyReviewService


# -----------------------------------------------------------------------------
# 1. Pure Domain Unit Tests
# -----------------------------------------------------------------------------

def test_deterministic_rule_high_amount():
    """Validates that transactions exceeding high-value threshold trigger RULE_HIGH_AMOUNT."""
    tx_normal = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        amount_paise=150000,  # ₹1,500
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=datetime.utcnow(),
        description="Grocery Store",
    )
    evidences_normal = evaluate_deterministic_rules(tx_normal, DEFAULT_SYSTEM_RULES)
    assert not any(e.rule_code == "RULE_HIGH_AMOUNT" for e in evidences_normal)

    tx_high = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        amount_paise=7500000,  # ₹75,000 (Exceeds ₹50,000 threshold)
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=datetime.utcnow(),
        description="Jewelry Store",
    )
    evidences_high = evaluate_deterministic_rules(tx_high, DEFAULT_SYSTEM_RULES)
    high_ev = next((e for e in evidences_high if e.rule_code == "RULE_HIGH_AMOUNT"), None)
    assert high_ev is not None
    assert high_ev.severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL)
    assert high_ev.risk_score >= 65
    assert "₹75,000.00 exceeds" in high_ev.explanation


def test_deterministic_rule_frequency_burst():
    """Validates that multiple payments to the same merchant within 30 minutes trigger RULE_FREQUENCY_BURST."""
    ws_id = uuid.uuid4()
    now = datetime.utcnow()

    prior_tx1 = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=25000,
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=now - timedelta(minutes=10),
        description="Fast Food Corner",
        merchant_name="Fast Food Corner",
    )
    prior_tx2 = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=25000,
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=now - timedelta(minutes=5),
        description="Fast Food Corner",
        merchant_name="Fast Food Corner",
    )

    current_tx = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=25000,
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=now,
        description="Fast Food Corner",
        merchant_name="Fast Food Corner",
    )

    evidences = evaluate_deterministic_rules(
        current_tx,
        DEFAULT_SYSTEM_RULES,
        recent_transactions=[prior_tx1, prior_tx2],
    )
    burst_ev = next((e for e in evidences if e.rule_code == "RULE_FREQUENCY_BURST"), None)
    assert burst_ev is not None
    assert burst_ev.severity == AnomalySeverity.HIGH
    assert burst_ev.risk_score == 75
    assert "3 transactions recorded at 'Fast Food Corner'" in burst_ev.explanation


def test_deterministic_rule_recurring_hike_and_cancelled():
    """Validates unexpected price hike and charge on cancelled subscription."""
    ws_id = uuid.uuid4()
    now = datetime.utcnow()

    # 1. Price hike on active subscription (>15% increase and >= ₹500 increase)
    tx_hike = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=180000,  # ₹1,800 (Scheduled was ₹1,000, hike is ₹800 = 80,000 paise)
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=now,
        description="Cloud Storage",
    )
    recurring_active = {
        "is_recurring": True,
        "definition_id": uuid.uuid4(),
        "name": "Cloud Storage",
        "expected_amount_paise": 100000,  # ₹1,000
        "status": "active",
    }
    ev_hike = evaluate_deterministic_rules(tx_hike, DEFAULT_SYSTEM_RULES, recurring_info=recurring_active)
    hike_res = next((e for e in ev_hike if e.rule_code == "RULE_RECURRING_HIKE"), None)
    assert hike_res is not None
    assert hike_res.severity == AnomalySeverity.MEDIUM
    assert hike_res.metadata["percentage_increase"] > 15.0

    # 2. Charge on cancelled subscription
    tx_cancelled = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=150000,
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=now,
        description="Gym Membership",
    )
    recurring_cancelled = {
        "is_recurring": True,
        "definition_id": uuid.uuid4(),
        "name": "Gym Membership",
        "expected_amount_paise": 150000,
        "status": "cancelled",
    }
    ev_cancelled = evaluate_deterministic_rules(tx_cancelled, DEFAULT_SYSTEM_RULES, recurring_info=recurring_cancelled)
    cancel_res = next((e for e in ev_cancelled if e.rule_code == "RULE_CANCELLED_RECURRING"), None)
    assert cancel_res is not None
    assert cancel_res.severity == AnomalySeverity.CRITICAL
    assert cancel_res.risk_score == 90
    assert "previously marked as cancelled" in cancel_res.explanation


def test_deterministic_rule_duplicate_candidate():
    """Validates duplicate payment candidate detection within 48h."""
    ws_id = uuid.uuid4()
    now = datetime.utcnow()
    m_name = "Electricity Board"

    tx1 = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=345000,  # ₹3,450
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=now - timedelta(hours=2),
        description=m_name,
        merchant_name=m_name,
    )

    tx2 = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=345000,  # Exact same amount
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=now,
        description=m_name,
        merchant_name=m_name,
    )

    evidences = evaluate_deterministic_rules(tx2, DEFAULT_SYSTEM_RULES, recent_transactions=[tx1])
    dup_res = next((e for e in evidences if e.rule_code == "RULE_DUPLICATE_CANDIDATE"), None)
    assert dup_res is not None
    assert dup_res.severity == AnomalySeverity.MEDIUM
    assert dup_res.risk_score == 65
    assert str(tx1.id) == dup_res.metadata["duplicate_transaction_id"]


def test_statistical_mad_merchant_outlier():
    """Validates robust Median Absolute Deviation (MAD) on skewed merchant expenditures."""
    # Historical payments at Coffee Shop: ₹150, ₹180, ₹200, ₹220, ₹190, ₹210 (Median ~₹195, MAD ~₹15)
    hist = [15000, 18000, 20000, 22000, 19000, 21000]
    med, mad = calculate_median_and_mad(hist)
    assert med == 19500.0
    assert mad > 0

    tx_normal = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        amount_paise=25000,  # ₹250 (Typical variance)
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=datetime.utcnow(),
        description="Coffee Shop",
        merchant_name="Coffee Shop",
    )
    ev_norm = detect_merchant_amount_anomaly(tx_normal, hist, min_observations=5)
    assert ev_norm is None

    # Anomaly: ₹6,500 at Coffee Shop (Extreme outlier, >30x normal coffee)
    tx_outlier = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        amount_paise=650000,  # ₹6,500
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=datetime.utcnow(),
        description="Coffee Shop",
        merchant_name="Coffee Shop",
    )
    ev_outlier = detect_merchant_amount_anomaly(tx_outlier, hist, min_observations=5)
    assert ev_outlier is not None
    assert ev_outlier.category == AnomalyCategory.MERCHANT
    assert ev_outlier.method == DetectionMethod.STATISTICAL_MAD
    assert ev_outlier.risk_score >= 70
    assert ev_outlier.metadata["modified_z_score"] >= 3.5


def test_statistical_iqr_and_category_spike():
    """Validates IQR calculations and category-level monthly volume spikes."""
    vals = [100, 150, 200, 250, 300, 350, 400, 450]
    q1, q3, iqr = calculate_iqr(vals)
    assert q1 > 0
    assert q3 > q1
    assert iqr == q3 - q1

    # Historical 90-day daily spend in 'Dining': ₹200/day -> ₹6,087/month
    daily_hist = [20000] * 30
    current_month_spike = 2500000  # ₹25,000 this month (>4x normal baseline)

    tx = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        amount_paise=500000,
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=datetime.utcnow(),
        description="Fine Dining Restaurant",
        category_name="Dining Out",
    )

    ev_spike = detect_category_spike_anomaly(tx, daily_hist, current_month_spike, min_days=14)
    assert ev_spike is not None
    assert ev_spike.category == AnomalyCategory.CATEGORY
    assert ev_spike.metadata["ratio"] >= 2.5


def test_ml_isolation_forest_multivariate():
    """Validates unsupervised Isolation Forest inference and graceful fallback on insufficient data."""
    tx = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        amount_paise=15000000,  # ₹1,50,000
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=datetime.utcnow(),
        description="Luxury Electronics",
        merchant_name="Flagship Tech Store",
    )
    cand_vec = extract_ml_feature_vector(tx)
    assert len(cand_vec) == 5

    # 1. Insufficient training samples (<30) must safely return None
    small_matrix = [[5.0, 1.0, 24.0, 0.5, 0.0] for _ in range(15)]
    res_small = detect_ml_isolation_forest(tx, small_matrix, cand_vec, min_training_samples=30)
    assert res_small is None

    # 2. Sufficient training samples: train on baseline cluster, test on extreme outlier
    normal_cluster = [
        [math.log1p(200.0), 1.0, 12.0, 0.4, 0.0]
        for _ in range(50)
    ]
    # Extreme candidate: huge amount, 10x ratio, 0 delta
    extreme_vec = [math.log1p(150000.0), 10.0, 0.1, 0.9, 1.0]
    res_ml = detect_ml_isolation_forest(tx, normal_cluster, extreme_vec, min_training_samples=30)
    assert res_ml is not None
    assert res_ml.method == DetectionMethod.ML_ISOLATION_FOREST
    assert res_ml.risk_score >= 60


def test_exception_whitelist_matching():
    """Validates that whitelist exceptions match merchant patterns, categories, ceilings, and expiries."""
    ws_id = uuid.uuid4()
    m_id = uuid.uuid4()

    tx = CandidateTransactionVO(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        amount_paise=500000,  # ₹5,000
        currency="INR",
        direction="outflow",
        transaction_date=date.today(),
        created_at=datetime.utcnow(),
        description="Bescom Electric Utility",
        merchant_id=m_id,
        merchant_name="Bescom Electricity",
    )

    # 1. Matching unexpired exception
    exc_valid = [{
        "id": uuid.uuid4(),
        "merchant_name_pattern": "bescom",
        "max_amount_paise": 1000000,  # ₹10,000 ceiling
        "expires_at": date.today() + timedelta(days=30),
    }]
    matched = matches_detection_exception(tx, exc_valid, as_of_date=date.today())
    assert matched is not None

    # 2. Expired exception should not match
    exc_expired = [{
        "id": uuid.uuid4(),
        "merchant_name_pattern": "bescom",
        "expires_at": date.today() - timedelta(days=1),
    }]
    assert matches_detection_exception(tx, exc_expired, as_of_date=date.today()) is None

    # 3. Amount exceeding ceiling should not match
    exc_ceiling_exceeded = [{
        "id": uuid.uuid4(),
        "merchant_name_pattern": "bescom",
        "max_amount_paise": 200000,  # ₹2,000 ceiling < ₹5,000 tx
    }]
    assert matches_detection_exception(tx, exc_ceiling_exceeded, as_of_date=date.today()) is None


def test_hybrid_synthesis_and_deduplication():
    """Validates that multiple overlapping signals do not duplicate and receive multi-detector boost."""
    ev1 = AnomalyEvidenceVO(
        category=AnomalyCategory.AMOUNT,
        method=DetectionMethod.DETERMINISTIC_RULE,
        severity=AnomalySeverity.HIGH,
        risk_score=75,
        rule_code="RULE_HIGH_AMOUNT",
        explanation="High value purchase",
    )
    ev2 = AnomalyEvidenceVO(
        category=AnomalyCategory.MERCHANT,
        method=DetectionMethod.STATISTICAL_MAD,
        severity=AnomalySeverity.HIGH,
        risk_score=78,
        rule_code="STAT_MERCHANT_AMOUNT_MAD",
        explanation="3.5x higher than merchant median",
    )

    res = synthesize_hybrid_anomaly([ev1, ev2])
    assert res.is_anomalous is True
    assert res.risk_score == 83  # 78 base + 5 multi-detector reinforcement boost
    assert res.severity == AnomalySeverity.HIGH
    assert len(res.evidence_metadata["methods_triggered"]) == 2


# -----------------------------------------------------------------------------
# 2. Database & Service Integration Tests
# -----------------------------------------------------------------------------

@pytest.fixture
async def setup_anomaly_data(db_session: AsyncSession, registered_user: dict):
    """Sets up workspace, liquid account, category, merchant, and transactions for anomaly testing."""
    ws: Workspace = registered_user["workspace"]
    user = registered_user["user"]

    acc = Account(
        workspace_id=ws.id,
        name="Main Savings",
        account_type="savings",
        currency="INR",
        current_book_balance_paise=10000000,
        status="active",
    )
    db_session.add(acc)

    cat = Category(
        workspace_id=ws.id,
        name="Dining Out",
        slug=f"dining-{uuid.uuid4().hex[:6]}",
        category_type="expense",
    )
    db_session.add(cat)

    merch = Merchant(
        canonical_name="Artisan Cafe",
        slug=f"artisan-cafe-{uuid.uuid4().hex[:6]}",
        status="active",
        is_verified=True,
    )
    db_session.add(merch)
    await db_session.flush()

    # Seed 10 baseline historical transactions at Artisan Cafe (Median ~₹250 = 25,000 paise)
    base_date = date.today() - timedelta(days=20)
    for i in range(10):
        t = Transaction(
            workspace_id=ws.id,
            account_id=acc.id,
            category_id=cat.id,
            merchant_name="Artisan Cafe",
            amount_paise=25000 + (i * 1000),  # ₹250 to ₹340
            amount=Decimal(250 + (i * 10)),
            currency="INR",
            direction="outflow",
            transaction_type="expense",
            status="posted",
            transaction_date=base_date + timedelta(days=i),
            description="Artisan Cafe Lunch",
        )
        db_session.add(t)

    # Seed an anomalous high-value transaction (₹12,000 vs ₹250 median)
    anomaly_tx = Transaction(
        workspace_id=ws.id,
        account_id=acc.id,
        category_id=cat.id,
        merchant_name="Artisan Cafe",
        amount_paise=1200000,  # ₹12,000
        amount=Decimal("12000.0000"),
        currency="INR",
        direction="outflow",
        transaction_type="expense",
        status="posted",
        transaction_date=date.today(),
        description="Artisan Cafe Catering Order",
    )
    db_session.add(anomaly_tx)

    await db_session.flush()
    await db_session.commit()

    return {
        "workspace": ws,
        "user": user,
        "account": acc,
        "category": cat,
        "merchant": merch,
        "anomaly_tx": anomaly_tx,
    }


@pytest.mark.asyncio
async def test_anomaly_detection_service_lifecycle(db_session: AsyncSession, setup_anomaly_data: dict):
    """Validates single transaction evaluation, persistent anomaly creation, and idempotency."""
    ws = setup_anomaly_data["workspace"]
    tx = setup_anomaly_data["anomaly_tx"]

    service = AnomalyDetectionService(db_session)
    detection = await service.evaluate_transaction(
        workspace_id=ws.id,
        transaction_id=tx.id,
        persist=True,
    )
    assert detection is not None
    assert detection.workspace_id == ws.id
    assert detection.transaction_id == tx.id
    assert detection.risk_score >= 60
    assert detection.status == "new"
    assert "Artisan Cafe" in detection.explanation

    # Idempotent re-check: must return existing record without creating duplicate
    rechecked = await service.evaluate_transaction(
        workspace_id=ws.id,
        transaction_id=tx.id,
        persist=True,
    )
    assert rechecked.id == detection.id


@pytest.mark.asyncio
async def test_anomaly_scan_recent_transactions(db_session: AsyncSession, setup_anomaly_data: dict):
    """Validates scanning recent transactions in workspace."""
    ws = setup_anomaly_data["workspace"]
    service = AnomalyDetectionService(db_session)

    detections = await service.scan_recent_transactions(
        workspace_id=ws.id,
        lookback_days=7,
        force_recheck=False,
    )
    assert len(detections) >= 1
    assert any(d.transaction_id == setup_anomaly_data["anomaly_tx"].id for d in detections)


@pytest.mark.asyncio
async def test_anomaly_review_workflow_and_exception_creation(db_session: AsyncSession, setup_anomaly_data: dict):
    """Validates user review actions (acknowledge, mark expected, dismiss) and whitelist exception creation."""
    ws = setup_anomaly_data["workspace"]
    user = setup_anomaly_data["user"]
    tx = setup_anomaly_data["anomaly_tx"]

    det_service = AnomalyDetectionService(db_session)
    detection = await det_service.evaluate_transaction(workspace_id=ws.id, transaction_id=tx.id, persist=True)

    review_service = AnomalyReviewService(db_session)

    # 1. Acknowledge Action
    ack_req = AnomalyReviewRequest(action="acknowledge", notes="Checking with family member")
    res_ack = await review_service.review_anomaly(
        anomaly_id=detection.id,
        workspace_id=ws.id,
        reviewer_id=user.id,
        request=ack_req,
    )
    assert res_ack.status == "acknowledged"

    # 2. Mark Expected + Create Whitelist Exception
    exp_req = AnomalyReviewRequest(
        action="mark_expected",
        reason="Office party catering",
        create_exception=True,
        exception_expires_in_days=90,
    )
    res_exp = await review_service.review_anomaly(
        anomaly_id=detection.id,
        workspace_id=ws.id,
        reviewer_id=user.id,
        request=exp_req,
    )
    assert res_exp.status == "expected_activity"

    # Verify whitelist exception was created
    repo = AnomalyRepository(db_session)
    exceptions = await repo.list_exceptions(ws.id)
    assert len(exceptions) >= 1
    created_exc = exceptions[0]
    assert created_exc.merchant_name_pattern == tx.merchant_name
    assert created_exc.expires_at is not None


@pytest.mark.asyncio
async def test_rules_customization_and_workspace_override(db_session: AsyncSession, setup_anomaly_data: dict):
    """Validates detection rules listing and workspace override customization."""
    ws = setup_anomaly_data["workspace"]
    repo = AnomalyRepository(db_session)

    rules = await repo.get_rules(ws.id)
    assert len(rules) >= 5

    # Update threshold for RULE_HIGH_AMOUNT to ₹1,00,000 (10,000,000 paise)
    target_rule = next(r for r in rules if r.rule_code == "RULE_HIGH_AMOUNT")
    review_service = AnomalyReviewService(db_session)
    update_req = DetectionRuleUpdateRequest(
        threshold_config={"threshold_paise": 10000000},
        severity="critical",
    )
    updated = await review_service.update_rule(
        rule_id=target_rule.id,
        workspace_id=ws.id,
        request=update_req,
    )
    assert updated.rule_code == "RULE_HIGH_AMOUNT"
    assert updated.threshold_config["threshold_paise"] == 10000000
    assert updated.severity == "critical"


@pytest.mark.asyncio
async def test_anomaly_workspace_isolation(db_session: AsyncSession, registered_user: dict, setup_anomaly_data: dict):
    """Enforces multi-tenant isolation: Workspace B cannot view or review Workspace A's anomalies."""
    from app.infrastructure.database.models.workspace import Workspace
    from app.core.exceptions import NotFoundException

    ws1 = setup_anomaly_data["workspace"]
    user1 = setup_anomaly_data["user"]
    tx1 = setup_anomaly_data["anomaly_tx"]

    # Create distinct Workspace 2
    ws2 = Workspace(
        name="Isolation Workspace 2",
        slug=f"iso-ws2-{uuid.uuid4().hex[:6]}",
        type="personal",
        owner_id=user1.id,
        status="active",
    )
    db_session.add(ws2)
    await db_session.flush()

    det_service = AnomalyDetectionService(db_session)
    d1 = await det_service.evaluate_transaction(workspace_id=ws1.id, transaction_id=tx1.id, persist=True)

    repo = AnomalyRepository(db_session)
    # Listing from WS2 should not include d1
    ws2_list, _ = await repo.list_detections(workspace_id=ws2.id)
    assert not any(d.id == d1.id for d in ws2_list)

    # Direct query scoped to WS2 should return None
    assert await repo.get_detection(d1.id, ws2.id) is None

    # Reviewing from WS2 should raise NotFoundException
    review_service = AnomalyReviewService(db_session)
    with pytest.raises(NotFoundException):
        await review_service.review_anomaly(
            anomaly_id=d1.id,
            workspace_id=ws2.id,
            reviewer_id=user1.id,
            request=AnomalyReviewRequest(action="dismiss"),
        )


@pytest.mark.asyncio
async def test_api_anomaly_routes(
    client: AsyncClient,
    registered_user: dict,
    setup_anomaly_data: dict,
):
    """Validates all authenticated REST API endpoints for anomalies, reviews, rules, and exceptions."""
    token = registered_user["token"]
    ws_id = str(setup_anomaly_data["workspace"].id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. POST /workspaces/{ws_id}/anomalies/scan
    scan_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/anomalies/scan",
        json={"lookback_days": 14, "force_recheck": False},
        headers=headers,
    )
    assert scan_res.status_code == 200
    detections = scan_res.json()["data"]
    assert len(detections) >= 1
    anom_id = detections[0]["id"]

    # 2. GET /workspaces/{ws_id}/anomalies
    list_res = await client.get(f"/api/v1/workspaces/{ws_id}/anomalies", headers=headers)
    assert list_res.status_code == 200
    assert any(d["id"] == anom_id for d in list_res.json()["data"])

    # 3. GET /workspaces/{ws_id}/anomalies/summary
    sum_res = await client.get(f"/api/v1/workspaces/{ws_id}/anomalies/summary", headers=headers)
    assert sum_res.status_code == 200
    assert sum_res.json()["data"]["total_detections"] >= 1

    # 4. GET /workspaces/{ws_id}/anomalies/trends
    trends_res = await client.get(f"/api/v1/workspaces/{ws_id}/anomalies/trends?lookback_days=30", headers=headers)
    assert trends_res.status_code == 200

    # 5. GET /workspaces/{ws_id}/anomalies/{anomaly_id}
    detail_res = await client.get(f"/api/v1/workspaces/{ws_id}/anomalies/{anom_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == anom_id

    # 6. POST /workspaces/{ws_id}/anomalies/{anomaly_id}/acknowledge
    ack_res = await client.post(f"/api/v1/workspaces/{ws_id}/anomalies/{anom_id}/acknowledge", headers=headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["data"]["status"] == "acknowledged"

    # 7. POST /workspaces/{ws_id}/anomalies/{anomaly_id}/review (Mark expected + Exception)
    rev_payload = {
        "action": "mark_expected",
        "reason": "Business client lunch",
        "create_exception": True,
        "exception_expires_in_days": 60,
    }
    rev_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/anomalies/{anom_id}/review",
        json=rev_payload,
        headers=headers,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["status"] == "expected_activity"

    # 8. GET /workspaces/{ws_id}/anomalies/rules/list
    rules_res = await client.get(f"/api/v1/workspaces/{ws_id}/anomalies/rules/list", headers=headers)
    assert rules_res.status_code == 200
    assert len(rules_res.json()["data"]) >= 5

    # 9. GET /workspaces/{ws_id}/anomalies/exceptions/list
    exc_res = await client.get(f"/api/v1/workspaces/{ws_id}/anomalies/exceptions/list", headers=headers)
    assert exc_res.status_code == 200
    assert len(exc_res.json()["data"]) >= 1
