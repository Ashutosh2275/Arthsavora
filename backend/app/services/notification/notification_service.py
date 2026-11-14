"""
Arthsavora Unified Notification Application Service
Orchestrates event ingestion, deduplication, policy evaluation, multi-channel dispatch,
real-time SSE streaming, and user state management.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notification import (
    DeliveryStatus,
    NotificationCategory,
    NotificationChannel,
    NotificationPayloadVO,
    NotificationSeverity,
)
from app.infrastructure.database.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    PushSubscription,
)
from app.infrastructure.database.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.services.notification.channels.email import BaseEmailProvider
from app.services.notification.channels.web_push import BasePushProvider
from app.services.notification.delivery_engine import NotificationDeliveryEngine
from app.services.notification.policy import NotificationPolicyEvaluator

logger = logging.getLogger(__name__)


# Global in-memory broadcast bus for Server-Sent Events (SSE)
# Maps user_id -> set of asyncio.Queue
_active_user_streams: Dict[UUID, Set[asyncio.Queue]] = {}


class NotificationService:
    """Primary application service for notifications across personal, family, and business workspaces."""

    def __init__(
        self,
        session: AsyncSession,
        repository: Optional[NotificationRepository] = None,
        email_provider: Optional[BaseEmailProvider] = None,
        push_provider: Optional[BasePushProvider] = None,
    ):
        self.session = session
        self.repository = repository or NotificationRepository(session)
        self.delivery_engine = NotificationDeliveryEngine(
            repository=self.repository,
            email_provider=email_provider,
            push_provider=push_provider,
        )

    # -------------------------------------------------------------------------
    # Ingestion & Dispatch
    # -------------------------------------------------------------------------

    async def dispatch_notification(
        self,
        payload: NotificationPayloadVO,
        now_utc: Optional[datetime] = None,
    ) -> Notification:
        """
        Ingests a domain event payload, evaluates deduplication, policies,
        persists the notification record, and executes outbound channel delivery.
        """
        now = now_utc or datetime.now(timezone.utc)

        # 1. Deduplication Check
        if payload.deduplication_key:
            existing = await self.repository.find_by_deduplication_key(
                user_id=payload.recipient_user_id,
                deduplication_key=payload.deduplication_key,
            )
            if existing:
                logger.info(
                    f"[NotificationService] Suppressing duplicate notification {payload.deduplication_key} for user {payload.recipient_user_id}"
                )
                return existing

        # 2. Retrieve User & Preferences
        user_res = await self.session.execute(
            select(User).where(User.id == payload.recipient_user_id)
        )
        recipient_user = user_res.scalar_one_or_none()

        user_prefs = await self.repository.get_user_preferences(payload.recipient_user_id)

        # 3. Policy Evaluation: determine allowed channels
        allowed_channels = NotificationPolicyEvaluator.evaluate_channels_for_recipient(
            payload=payload,
            preferences=user_prefs,
            now_utc=now,
        )

        # 4. Create Authoritative Notification Record
        notification = Notification(
            recipient_user_id=payload.recipient_user_id,
            workspace_id=payload.workspace_id,
            category=payload.category.value,
            event_type=payload.event_type.value,
            title=payload.title,
            message=payload.message,
            severity=payload.severity.value,
            related_resource_type=payload.related_resource_type,
            related_resource_id=payload.related_resource_id,
            action_url=payload.action_url,
            metadata_json=payload.metadata,
            event_timestamp=payload.event_timestamp or now,
            created_at=now,
            expires_at=payload.expires_at,
            is_read=False,
            is_archived=False,
            deduplication_key=payload.deduplication_key,
        )
        await self.repository.create_notification(notification)

        # 5. Create Deliveries & Execute Dispatch
        deliveries: List[NotificationDelivery] = []
        for channel in allowed_channels:
            delivery = NotificationDelivery(
                notification_id=notification.id,
                channel=channel.value,
                provider="internal" if channel == NotificationChannel.IN_APP else "configured_provider",
                status=DeliveryStatus.PENDING.value,
                created_at=now,
            )
            created_deliv = await self.repository.create_delivery(delivery)
            deliveries.append(created_deliv)

        # Execute channel delivery asynchronously
        for deliv in deliveries:
            await self.delivery_engine.execute_delivery(
                notification=notification,
                delivery=deliv,
                recipient_user=recipient_user,
            )

        # 6. Real-Time Broadcast to In-App SSE subscribers
        self._broadcast_sse_event(payload.recipient_user_id, notification)

        return notification

    def _broadcast_sse_event(self, user_id: UUID, notification: Notification) -> None:
        """Pushes event payload to active user SSE connections."""
        queues = _active_user_streams.get(user_id)
        if queues:
            event_data = {
                "id": str(notification.id),
                "category": notification.category,
                "event_type": notification.event_type,
                "title": notification.title,
                "message": notification.message,
                "severity": notification.severity,
                "action_url": notification.action_url,
                "created_at": notification.created_at.isoformat(),
            }
            for q in list(queues):
                try:
                    q.put_nowait(event_data)
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Notification Queries & User State
    # -------------------------------------------------------------------------

    async def list_notifications(
        self,
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Notification], int]:
        """Returns paginated notifications with total count."""
        return await self.repository.list_notifications(
            user_id=user_id,
            workspace_id=workspace_id,
            category=category,
            severity=severity,
            is_read=is_read,
            is_archived=is_archived,
            limit=limit,
            offset=offset,
        )

    async def get_unread_count(
        self, user_id: UUID, workspace_id: Optional[UUID] = None
    ) -> int:
        """Returns instantaneous unread notification count."""
        return await self.repository.count_unread(user_id=user_id, workspace_id=workspace_id)

    async def get_notification_by_id(
        self, notification_id: UUID, user_id: UUID
    ) -> Optional[Notification]:
        """Gets single notification scoped to user."""
        return await self.repository.get_by_id(notification_id, user_id)

    async def mark_as_read(
        self, notification_id: UUID, user_id: UUID
    ) -> Optional[Notification]:
        """Marks notification as read."""
        return await self.repository.mark_as_read(notification_id, user_id)

    async def mark_all_as_read(
        self,
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
        category: Optional[str] = None,
    ) -> int:
        """Batch marks all unread notifications as read."""
        return await self.repository.mark_all_as_read(user_id, workspace_id, category)

    async def archive_notification(
        self, notification_id: UUID, user_id: UUID
    ) -> Optional[Notification]:
        """Archives a notification."""
        return await self.repository.archive_notification(notification_id, user_id)

    async def delete_notification(
        self, notification_id: UUID, user_id: UUID
    ) -> bool:
        """Permanently deletes a notification."""
        return await self.repository.delete_notification(notification_id, user_id)

    # -------------------------------------------------------------------------
    # Preferences Management
    # -------------------------------------------------------------------------

    async def get_user_preferences(
        self, user_id: UUID
    ) -> List[NotificationPreference]:
        """Gets all user preferences."""
        return await self.repository.get_user_preferences(user_id)

    async def update_user_preference(
        self,
        user_id: UUID,
        category: str,
        channel: str,
        is_enabled: bool,
        min_severity: str = "info",
        quiet_hours_enabled: bool = False,
        quiet_hours_start: Optional[str] = "22:00",
        quiet_hours_end: Optional[str] = "08:00",
        timezone_name: str = "Asia/Kolkata",
        frequency: str = "instant",
    ) -> NotificationPreference:
        """Updates or creates a user notification preference."""
        return await self.repository.upsert_user_preference(
            user_id=user_id,
            category=category,
            channel=channel,
            is_enabled=is_enabled,
            min_severity=min_severity,
            quiet_hours_enabled=quiet_hours_enabled,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            timezone_name=timezone_name,
            frequency=frequency,
        )

    # -------------------------------------------------------------------------
    # Push Subscriptions
    # -------------------------------------------------------------------------

    async def register_push_subscription(
        self,
        user_id: UUID,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        user_agent: Optional[str] = None,
    ) -> PushSubscription:
        """Registers a browser push subscription for Web Push."""
        return await self.repository.save_push_subscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            user_agent=user_agent,
        )

    async def list_push_subscriptions(
        self, user_id: UUID
    ) -> List[PushSubscription]:
        """Lists active browser push subscriptions for user."""
        return await self.repository.get_user_push_subscriptions(user_id)

    async def revoke_push_subscription(
        self, subscription_id: UUID, user_id: UUID
    ) -> bool:
        """Revokes a push subscription."""
        return await self.repository.revoke_push_subscription(subscription_id, user_id)

    # -------------------------------------------------------------------------
    # Server-Sent Events (SSE) Stream
    # -------------------------------------------------------------------------

    async def subscribe_user_stream(
        self, user_id: UUID
    ) -> AsyncGenerator[str, None]:
        """Subscribes client to live Server-Sent Events for user notifications."""
        q = asyncio.Queue()
        if user_id not in _active_user_streams:
            _active_user_streams[user_id] = set()
        _active_user_streams[user_id].add(q)

        # Initial ping
        yield f"event: connect\ndata: {json.dumps({'status': 'connected', 'user_id': str(user_id)})}\n\n"

        try:
            while True:
                # Wait for next event or heartbeat
                try:
                    event_data = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"event: notification\ndata: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat comment
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if user_id in _active_user_streams and q in _active_user_streams[user_id]:
                _active_user_streams[user_id].remove(q)
                if not _active_user_streams[user_id]:
                    del _active_user_streams[user_id]
