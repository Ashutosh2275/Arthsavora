"""
Arthsavora Notification & Communication API Endpoints
RESTful endpoints for notification listing, unread counts, status mutations,
user preferences, Web Push subscriptions, and real-time Server-Sent Events (SSE).
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException
from app.domain.notification import (
    NotificationCategory,
    NotificationEventType,
    NotificationPayloadVO,
    NotificationSeverity,
)
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db_session
from app.schemas.notification_schema import (
    MarkReadResponse,
    NotificationDeliveryResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
    PushSubscriptionCreateRequest,
    PushSubscriptionResponse,
    TestNotificationRequest,
    UnreadCountResponse,
)
from app.services.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Unified Notifications & Financial Alerts"])


def _to_delivery_response(deliv) -> NotificationDeliveryResponse:
    return NotificationDeliveryResponse(
        id=deliv.id,
        channel=deliv.channel,
        provider=deliv.provider,
        status=deliv.status,
        attempt_count=deliv.attempt_count,
        provider_message_reference=deliv.provider_message_reference,
        last_attempt_at=deliv.last_attempt_at,
        delivered_at=deliv.delivered_at,
        failure_reason=deliv.failure_reason,
    )


def _to_notification_response(notif) -> NotificationResponse:
    deliveries = []
    try:
        raw_delivs = getattr(notif, "deliveries", None)
        if raw_delivs:
            deliveries = [_to_delivery_response(d) for d in raw_delivs]
    except Exception:
        deliveries = []
    return NotificationResponse(
        id=notif.id,
        recipient_user_id=notif.recipient_user_id,
        workspace_id=notif.workspace_id,
        category=notif.category,
        event_type=notif.event_type,
        title=notif.title,
        message=notif.message,
        severity=notif.severity,
        related_resource_type=notif.related_resource_type,
        related_resource_id=notif.related_resource_id,
        action_url=notif.action_url,
        metadata_json=notif.metadata_json or {},
        event_timestamp=notif.event_timestamp,
        created_at=notif.created_at,
        is_read=notif.is_read,
        read_at=notif.read_at,
        is_archived=notif.is_archived,
        deliveries=deliveries,
    )


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List recipient notifications with filtering and pagination",
)
async def list_notifications(
    workspace_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    is_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    items, total = await service.list_notifications(
        user_id=current_user.id,
        workspace_id=workspace_id,
        category=category,
        severity=severity,
        is_read=is_read,
        is_archived=is_archived,
        limit=limit,
        offset=offset,
    )
    unread_count = await service.get_unread_count(user_id=current_user.id, workspace_id=workspace_id)
    return NotificationListResponse(
        items=[_to_notification_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        unread_count=unread_count,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
)
async def get_unread_count(
    workspace_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    count = await service.get_unread_count(user_id=current_user.id, workspace_id=workspace_id)
    return UnreadCountResponse(unread_count=count)


@router.get(
    "/stream",
    summary="Subscribe to real-time notification Server-Sent Events (SSE)",
)
async def stream_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    return StreamingResponse(
        service.subscribe_user_stream(user_id=current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/preferences",
    response_model=list[NotificationPreferenceResponse],
    summary="Get user notification delivery preferences",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    prefs = await service.get_user_preferences(user_id=current_user.id)
    return [NotificationPreferenceResponse.model_validate(p) for p in prefs]


@router.patch(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Create or update user notification preference",
)
async def update_preference(
    payload: NotificationPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    pref = await service.update_user_preference(
        user_id=current_user.id,
        category=payload.category,
        channel=payload.channel,
        is_enabled=payload.is_enabled,
        min_severity=payload.min_severity or "info",
        quiet_hours_enabled=payload.quiet_hours_enabled or False,
        quiet_hours_start=payload.quiet_hours_start or "22:00",
        quiet_hours_end=payload.quiet_hours_end or "08:00",
        timezone_name=payload.timezone or "Asia/Kolkata",
        frequency=payload.frequency or "instant",
    )
    await session.commit()
    return NotificationPreferenceResponse.model_validate(pref)


@router.post(
    "/push-subscriptions",
    response_model=PushSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register browser Web Push subscription",
)
async def register_push_subscription(
    payload: PushSubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    sub = await service.register_push_subscription(
        user_id=current_user.id,
        endpoint=payload.endpoint,
        p256dh_key=payload.p256dh_key,
        auth_key=payload.auth_key,
        user_agent=payload.user_agent,
    )
    await session.commit()
    return PushSubscriptionResponse.model_validate(sub)


@router.get(
    "/push-subscriptions",
    response_model=list[PushSubscriptionResponse],
    summary="List active Web Push subscriptions",
)
async def list_push_subscriptions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    subs = await service.list_push_subscriptions(user_id=current_user.id)
    return [PushSubscriptionResponse.model_validate(s) for s in subs]


@router.delete(
    "/push-subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Web Push subscription",
)
async def revoke_push_subscription(
    subscription_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    revoked = await service.revoke_push_subscription(subscription_id=subscription_id, user_id=current_user.id)
    if not revoked:
        raise NotFoundException(message="Push subscription not found", code="SUBSCRIPTION_NOT_FOUND")
    await session.commit()


@router.post(
    "/read-all",
    response_model=MarkReadResponse,
    summary="Mark all unread notifications as read",
)
async def mark_all_read(
    workspace_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    affected = await service.mark_all_as_read(
        user_id=current_user.id,
        workspace_id=workspace_id,
        category=category,
    )
    await session.commit()
    return MarkReadResponse(success=True, affected_count=affected)


@router.post(
    "/test",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a simulated notification for verification",
)
async def trigger_test_notification(
    payload: TestNotificationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    try:
        cat = NotificationCategory(payload.category)
    except ValueError:
        cat = NotificationCategory.SYSTEM

    try:
        sev = NotificationSeverity(payload.severity)
    except ValueError:
        sev = NotificationSeverity.INFO

    notif_payload = NotificationPayloadVO(
        recipient_user_id=current_user.id,
        category=cat,
        event_type=NotificationEventType.TRANSACTION_RECORDED,
        title=payload.title,
        message=payload.message,
        severity=sev,
        action_url=payload.action_url,
    )
    notif = await service.dispatch_notification(notif_payload)
    await session.commit()
    fresh = await service.get_notification_by_id(notif.id, current_user.id)
    return _to_notification_response(fresh or notif)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get single notification details",
)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    notif = await service.get_notification_by_id(notification_id=notification_id, user_id=current_user.id)
    if not notif:
        raise NotFoundException(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    return _to_notification_response(notif)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark single notification as read",
)
async def mark_single_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    notif = await service.mark_as_read(notification_id=notification_id, user_id=current_user.id)
    if not notif:
        raise NotFoundException(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    await session.commit()
    return _to_notification_response(notif)


@router.post(
    "/{notification_id}/archive",
    response_model=NotificationResponse,
    summary="Archive a notification",
)
async def archive_single_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    notif = await service.archive_notification(notification_id=notification_id, user_id=current_user.id)
    if not notif:
        raise NotFoundException(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    await session.commit()
    return _to_notification_response(notif)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification permanently",
)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(session=session)
    deleted = await service.delete_notification(notification_id=notification_id, user_id=current_user.id)
    if not deleted:
        raise NotFoundException(message="Notification not found", code="NOTIFICATION_NOT_FOUND")
    await session.commit()
