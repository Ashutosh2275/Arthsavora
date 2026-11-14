"""
Arthsavora Unified Notifications & Financial Alerts Comprehensive Test Suite
Verifies event catalog generation, deduplication keys, policy evaluation,
quiet-hours windows (including midnight-crossing and timezone adjustments),
email template rendering & mock delivery, Web Push subscriptions,
in-app lifecycle (unread count, read/archive/delete), and anti-IDOR security.
"""

from datetime import datetime, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.security import create_access_token
from app.domain.notification import (
    DeliveryStatus,
    NotificationCategory,
    NotificationChannel,
    NotificationEventType,
    NotificationPayloadVO,
    NotificationSeverity,
    generate_deduplication_key,
    is_in_quiet_hours,
    mask_sensitive_financial_payload,
)
from app.infrastructure.database.models import User, Workspace, WorkspaceMember, WorkspaceRole
from app.infrastructure.database.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    PushSubscription,
)
from app.repositories.notification_repository import NotificationRepository
from app.services.notification.channels.email import (
    MockEmailProvider,
    render_financial_email_template,
)
from app.services.notification.channels.web_push import MockPushProvider
from app.services.notification.delivery_engine import NotificationDeliveryEngine
from app.services.notification.event_catalog import NotificationEventFactory
from app.services.notification.notification_service import NotificationService
from app.services.notification.policy import NotificationPolicyEvaluator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def setup_test_user(db_session: AsyncSession):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"notif_user_{user_id.hex[:6]}@arthsavora.com",
        full_name="Notification Test User",
        is_active=True,
    )
    db_session.add(user)

    ws_id = uuid.uuid4()
    workspace = Workspace(
        id=ws_id,
        name="Personal Test Workspace",
        slug=f"personal-test-{ws_id.hex[:6]}",
        type="personal",
        owner_id=user_id,
    )
    db_session.add(workspace)

    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        user_id=user_id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)

    await db_session.commit()
    return user, workspace


# ---------------------------------------------------------------------------
# 1. Event Catalog Factory Tests
# ---------------------------------------------------------------------------

def test_domain_event_factory_creation():
    uid = uuid.uuid4()
    wid = uuid.uuid4()

    # Transaction Recorded
    tx_event = NotificationEventFactory.transaction_recorded(
        user_id=uid,
        workspace_id=wid,
        transaction_id=uuid.uuid4(),
        amount_paise=150000,
        merchant_name="Swiggy",
    )
    assert tx_event.category == NotificationCategory.TRANSACTION
    assert "₹1500.00" in tx_event.title
    assert tx_event.deduplication_key is not None

    # Budget Threshold Reached
    bg_event = NotificationEventFactory.budget_threshold_reached(
        user_id=uid,
        workspace_id=wid,
        budget_id=uuid.uuid4(),
        category_name="Groceries",
        percentage_spent=95.5,
        period_str="Nov 2026",
    )
    assert bg_event.category == NotificationCategory.BUDGET
    assert bg_event.severity == NotificationSeverity.WARNING

    # Goal Milestone
    goal_event = NotificationEventFactory.goal_milestone_reached(
        user_id=uid,
        workspace_id=wid,
        goal_id=uuid.uuid4(),
        goal_name="Emergency Fund",
        percentage_saved=50.0,
    )
    assert goal_event.severity == NotificationSeverity.SUCCESS

    # Forecast Exhaustion (Explicit Estimate Label)
    fc_event = NotificationEventFactory.forecast_budget_exhaustion(
        user_id=uid,
        workspace_id=wid,
        category_name="Dining",
        projected_exhaustion_date="2026-11-25",
    )
    assert "[Estimate]" in fc_event.title
    assert "informational forecast" in fc_event.message

    # Anomaly Detected (Non-Alarmist Phrasing)
    anom_event = NotificationEventFactory.anomaly_detected(
        user_id=uid,
        workspace_id=wid,
        anomaly_id=uuid.uuid4(),
        merchant_or_category="Amazon India",
        amount_paise=4999900,
        detection_reason="Amount exceeds 3.5x standard deviation",
    )
    assert "Unusual Activity Noted" in anom_event.title
    assert "not automatically unauthorized" in anom_event.message


# ---------------------------------------------------------------------------
# 2. Deduplication Determinism & Suppression
# ---------------------------------------------------------------------------

def test_deduplication_keys_determinism():
    uid = uuid.uuid4()
    res_id = "bg-123"

    key1 = generate_deduplication_key(uid, NotificationEventType.BUDGET_THRESHOLD_REACHED, res_id, "2026-11")
    key2 = generate_deduplication_key(uid, NotificationEventType.BUDGET_THRESHOLD_REACHED, res_id, "2026-11")
    key3 = generate_deduplication_key(uid, NotificationEventType.BUDGET_THRESHOLD_REACHED, res_id, "2026-12")

    assert key1 == key2
    assert key1 != key3


@pytest.mark.asyncio
async def test_deduplication_suppresses_duplicate_notifications(db_session: AsyncSession, setup_test_user):
    user, workspace = setup_test_user
    service = NotificationService(session=db_session)

    bg_id = uuid.uuid4()
    event1 = NotificationEventFactory.budget_threshold_reached(
        user_id=user.id,
        workspace_id=workspace.id,
        budget_id=bg_id,
        category_name="Travel",
        percentage_spent=90.0,
        period_str="2026-11",
    )
    notif1 = await service.dispatch_notification(event1)
    await db_session.commit()

    # Attempt to dispatch the identical event again
    event2 = NotificationEventFactory.budget_threshold_reached(
        user_id=user.id,
        workspace_id=workspace.id,
        budget_id=bg_id,
        category_name="Travel",
        percentage_spent=90.0,
        period_str="2026-11",
    )
    notif2 = await service.dispatch_notification(event2)
    await db_session.commit()

    assert notif1.id == notif2.id

    # Verify repository only has 1 record
    items, total = await service.list_notifications(user_id=user.id, category="budget")
    assert total == 1


# ---------------------------------------------------------------------------
# 3. Quiet Hours & Timezone Evaluation
# ---------------------------------------------------------------------------

def test_quiet_hours_calculation():
    # 23:30 in Asia/Kolkata -> Inside quiet hours (22:00 to 08:00)
    dt_quiet_kolkata = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc) # 18:00 UTC = 23:30 IST
    assert is_in_quiet_hours(
        now_utc=dt_quiet_kolkata,
        tz_name="Asia/Kolkata",
        quiet_start_str="22:00",
        quiet_end_str="08:00",
    ) is True

    # 14:00 in Asia/Kolkata -> Outside quiet hours
    dt_active_kolkata = datetime(2026, 11, 14, 8, 30, tzinfo=timezone.utc) # 08:30 UTC = 14:00 IST
    assert is_in_quiet_hours(
        now_utc=dt_active_kolkata,
        tz_name="Asia/Kolkata",
        quiet_start_str="22:00",
        quiet_end_str="08:00",
    ) is False

    # Midnight crossing in America/New_York (UTC-5)
    # 23:00 EST = 04:00 UTC next day
    dt_ny_night = datetime(2026, 11, 15, 4, 0, tzinfo=timezone.utc)
    assert is_in_quiet_hours(
        now_utc=dt_ny_night,
        tz_name="America/New_York",
        quiet_start_str="22:00",
        quiet_end_str="07:00",
    ) is True


def test_mandatory_security_bypasses_quiet_hours():
    uid = uuid.uuid4()
    # User pref has quiet hours enabled
    pref = NotificationPreference(
        user_id=uid,
        category="*",
        channel="email",
        is_enabled=True,
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        timezone="Asia/Kolkata",
    )

    now_quiet = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc) # 23:30 IST

    # Ordinary budget notification -> email should be suppressed
    ordinary_payload = NotificationPayloadVO(
        recipient_user_id=uid,
        category=NotificationCategory.BUDGET,
        event_type=NotificationEventType.BUDGET_THRESHOLD_REACHED,
        title="Budget Alert",
        message="80% limit reached",
        severity=NotificationSeverity.INFO,
    )
    channels_ordinary = NotificationPolicyEvaluator.evaluate_channels_for_recipient(
        payload=ordinary_payload,
        preferences=[pref],
        now_utc=now_quiet,
    )
    assert NotificationChannel.EMAIL not in channels_ordinary
    assert NotificationChannel.IN_APP in channels_ordinary

    # Critical security notification -> email MUST bypass quiet hours
    security_payload = NotificationPayloadVO(
        recipient_user_id=uid,
        category=NotificationCategory.SECURITY,
        event_type=NotificationEventType.SECURITY_AUTH_EVENT,
        title="New Login from Unknown Device",
        message="A new login was recorded.",
        severity=NotificationSeverity.CRITICAL,
    )
    channels_sec = NotificationPolicyEvaluator.evaluate_channels_for_recipient(
        payload=security_payload,
        preferences=[pref],
        now_utc=now_quiet,
    )
    assert NotificationChannel.EMAIL in channels_sec
    assert NotificationChannel.IN_APP in channels_sec


# ---------------------------------------------------------------------------
# 4. Sensitive Payload Masking
# ---------------------------------------------------------------------------

def test_sensitive_payload_masking():
    raw_text = "Card 4111 2222 3333 4444 used with CVV: 789 and OTP: 123456"
    scrubbed = mask_sensitive_financial_payload(raw_text)
    assert "4111" not in scrubbed
    assert "**** **** **** 4444" in scrubbed
    assert "CVV: ***" in scrubbed
    assert "OTP: ******" in scrubbed


# ---------------------------------------------------------------------------
# 5. Email Template Rendering & Mock Delivery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_email_template_rendering_and_mock_delivery():
    html_out, text_out = render_financial_email_template(
        title="Payment Due: Reliance Jio (₹399.00)",
        message="Upcoming mobile recharge scheduled for tomorrow.",
        severity="warning",
        action_url="/recurring",
    )
    assert "ARTHSAVORA" in html_out
    assert "Reliance Jio" in html_out
    assert "Upcoming mobile recharge" in text_out

    mock_email = MockEmailProvider()
    ok, ref, err = await mock_email.send_email(
        to_email="customer@example.com",
        subject="Arthsavora: Payment Due",
        html_body=html_out,
        text_body=text_out,
    )
    assert ok is True
    assert ref.startswith("mock_mail_")
    assert len(mock_email.sent_emails) == 1


# ---------------------------------------------------------------------------
# 6. Web Push Provider Mock
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_web_push_provider_mock():
    mock_push = MockPushProvider()
    sub = PushSubscription(
        user_id=uuid.uuid4(),
        endpoint="https://fcm.googleapis.com/fcm/send/fake-token",
        p256dh_key="fake-p256dh",
        auth_key="fake-auth",
    )
    ok, ref, err = await mock_push.send_push(
        subscription=sub,
        title="Unusual Spend: ₹45,000.00",
        body="Card 4111-2222-3333-1234 charged.",
    )
    assert ok is True
    assert ref.startswith("mock_vapid_")
    assert len(mock_push.dispatched_pushes) == 1
    # Verify masking inside mock provider
    assert "**** **** **** 1234" in mock_push.dispatched_pushes[0]["body"]


# ---------------------------------------------------------------------------
# 7. Delivery Retry & Backoff Handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delivery_retry_and_backoff(db_session: AsyncSession, setup_test_user):
    user, workspace = setup_test_user
    repo = NotificationRepository(db_session)

    notif = Notification(
        recipient_user_id=user.id,
        category="transaction",
        event_type="transaction.recorded",
        title="Test Transaction",
        message="A transaction was recorded",
        severity="info",
        created_at=datetime.now(timezone.utc),
    )
    await repo.create_notification(notif)

    deliv = NotificationDelivery(
        notification_id=notif.id,
        channel="email",
        provider="failing_provider",
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    await repo.create_delivery(deliv)

    # Mock failing email provider
    class FailingEmailProvider(MockEmailProvider):
        async def send_email(self, *args, **kwargs):
            return False, None, "SMTP Connection Timed Out"

    delivery_engine = NotificationDeliveryEngine(
        repository=repo,
        email_provider=FailingEmailProvider(),
    )

    # Attempt 1
    res1 = await delivery_engine.execute_delivery(notif, deliv, recipient_user=user)
    assert res1.status == DeliveryStatus.RETRY_SCHEDULED.value
    assert res1.attempt_count == 1
    assert res1.retry_at is not None


# ---------------------------------------------------------------------------
# 8. Notification Service Lifecycle (Read, Archive, Delete, Unread Count)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notification_service_crud_lifecycle(db_session: AsyncSession, setup_test_user):
    user, workspace = setup_test_user
    service = NotificationService(session=db_session)

    # Ingest 2 notifications
    payload1 = NotificationEventFactory.transaction_recorded(
        user_id=user.id,
        workspace_id=workspace.id,
        transaction_id=uuid.uuid4(),
        amount_paise=50000,
        merchant_name="Zomato",
    )
    payload2 = NotificationEventFactory.goal_milestone_reached(
        user_id=user.id,
        workspace_id=workspace.id,
        goal_id=uuid.uuid4(),
        goal_name="Vacation Fund",
        percentage_saved=75.0,
    )
    n1 = await service.dispatch_notification(payload1)
    n2 = await service.dispatch_notification(payload2)
    await db_session.commit()

    # Verify unread count is 2
    unread = await service.get_unread_count(user_id=user.id)
    assert unread == 2

    # Mark n1 as read
    marked = await service.mark_as_read(notification_id=n1.id, user_id=user.id)
    assert marked.is_read is True
    assert marked.read_at is not None
    await db_session.commit()

    # Unread count should now be 1
    unread = await service.get_unread_count(user_id=user.id)
    assert unread == 1

    # Mark all read
    affected = await service.mark_all_as_read(user_id=user.id)
    assert affected == 1
    await db_session.commit()

    unread = await service.get_unread_count(user_id=user.id)
    assert unread == 0

    # Archive n1
    archived = await service.archive_notification(notification_id=n1.id, user_id=user.id)
    assert archived.is_archived is True
    await db_session.commit()

    # List unarchived should only contain n2
    items, total = await service.list_notifications(user_id=user.id, is_archived=False)
    assert total == 1
    assert items[0].id == n2.id

    # Delete n2
    deleted = await service.delete_notification(notification_id=n2.id, user_id=user.id)
    assert deleted is True
    await db_session.commit()


# ---------------------------------------------------------------------------
# 9. Push Subscription Registration & Revocation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_push_subscription_registration(db_session: AsyncSession, setup_test_user):
    user, _ = setup_test_user
    service = NotificationService(session=db_session)

    sub = await service.register_push_subscription(
        user_id=user.id,
        endpoint="https://updates.push.services.mozilla.com/wpush/v2/test-endpoint",
        p256dh_key="test-p256dh",
        auth_key="test-auth",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    )
    await db_session.commit()
    assert sub.is_active is True

    subs = await service.list_push_subscriptions(user_id=user.id)
    assert len(subs) == 1
    assert subs[0].endpoint == sub.endpoint

    # Revoke
    revoked = await service.revoke_push_subscription(subscription_id=sub.id, user_id=user.id)
    assert revoked is True
    await db_session.commit()

    subs = await service.list_push_subscriptions(user_id=user.id)
    assert len(subs) == 0


# ---------------------------------------------------------------------------
# 10. REST API Endpoints Verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_notification_endpoints(client: AsyncClient, db_session: AsyncSession, setup_test_user):
    user, workspace = setup_test_user
    token = create_access_token(subject=str(user.id), email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trigger test alert
    resp = await client.post(
        "/api/v1/notifications/test",
        json={"category": "budget", "title": "API Test Alert", "message": "Test Message", "severity": "warning"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    notif_data = resp.json()
    notif_id = notif_data["id"]
    assert notif_data["title"] == "API Test Alert"

    # 2. Get unread count
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] >= 1

    # 3. List notifications
    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    list_data = resp.json()
    assert list_data["total"] >= 1
    assert any(n["id"] == notif_id for n in list_data["items"])

    # 4. Mark single read
    resp = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True

    # 5. Preferences patch
    patch_pref = {
        "category": "budget",
        "channel": "email",
        "is_enabled": False,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "07:00",
        "timezone": "Asia/Kolkata",
    }
    resp = await client.patch("/api/v1/notifications/preferences", json=patch_pref, headers=headers)
    assert resp.status_code == 200
    pref_data = resp.json()
    assert pref_data["category"] == "budget"
    assert pref_data["is_enabled"] is False

    # 6. Delete notification
    resp = await client.delete(f"/api/v1/notifications/{notif_id}", headers=headers)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# 11. Workspace and User Isolation (Anti-IDOR)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notification_anti_idor_isolation(client: AsyncClient, db_session: AsyncSession, setup_test_user):
    user_a, _ = setup_test_user

    # Create User B
    user_b_id = uuid.uuid4()
    user_b = User(
        id=user_b_id,
        email=f"user_b_{user_b_id.hex[:6]}@arthsavora.com",
        full_name="User B",
        is_active=True,
    )
    db_session.add(user_b)
    await db_session.commit()

    # User A creates a notification
    service = NotificationService(session=db_session)
    notif_a = await service.dispatch_notification(
        NotificationEventFactory.security_alert(
            user_id=user_a.id,
            title="User A Secret Alert",
            message="Private account details",
        )
    )
    await db_session.commit()

    # User B authenticates and attempts to read User A's notification
    token_b = create_access_token(subject=str(user_b.id), email=user_b.email)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Should return 404 Not Found (Zero cross-user leakage)
    resp = await client.get(f"/api/v1/notifications/{notif_a.id}", headers=headers_b)
    assert resp.status_code == 404

    # User B attempts to mark User A's notification as read
    resp = await client.post(f"/api/v1/notifications/{notif_a.id}/read", headers=headers_b)
    assert resp.status_code == 404
