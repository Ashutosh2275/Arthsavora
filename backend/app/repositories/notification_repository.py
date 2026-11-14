"""
Arthsavora Notification Repository
High-performance relational persistence for notifications, delivery tracking,
user preferences, templates, and push subscriptions with user-scoped anti-IDOR enforcement.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    PushSubscription,
)


class NotificationRepository:
    """Repository managing notifications, preferences, deliveries, and push subscriptions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # Notification Ingestion & Lifecycle
    # -------------------------------------------------------------------------

    async def create_notification(self, notification: Notification) -> Notification:
        """Persists a new notification record."""
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_by_id(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """Fetches a single notification scoped to the recipient user (Anti-IDOR)."""
        stmt = (
            select(Notification)
            .options(selectinload(Notification.deliveries))
            .where(
                Notification.id == notification_id,
                Notification.recipient_user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        """Lists user notifications with filtering, pagination, and total count."""
        conditions = [
            Notification.recipient_user_id == user_id,
            Notification.is_archived == is_archived,
        ]

        if workspace_id:
            conditions.append(
                (Notification.workspace_id == workspace_id) | (Notification.workspace_id.is_(None))
            )
        if category:
            conditions.append(Notification.category == category)
        if severity:
            conditions.append(Notification.severity == severity)
        if is_read is not None:
            conditions.append(Notification.is_read == is_read)

        # Count total matching
        count_stmt = select(func.count(Notification.id)).where(*conditions)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        # Query paginated rows
        stmt = (
            select(Notification)
            .options(selectinload(Notification.deliveries))
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    async def count_unread(
        self, user_id: UUID, workspace_id: Optional[UUID] = None
    ) -> int:
        """Calculates total unread, unarchived notifications for a user."""
        conditions = [
            Notification.recipient_user_id == user_id,
            Notification.is_read == False,  # noqa: E712
            Notification.is_archived == False,  # noqa: E712
        ]
        if workspace_id:
            conditions.append(
                (Notification.workspace_id == workspace_id) | (Notification.workspace_id.is_(None))
            )

        stmt = select(func.count(Notification.id)).where(*conditions)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def mark_as_read(
        self, notification_id: UUID, user_id: UUID
    ) -> Optional[Notification]:
        """Marks a notification as read."""
        notif = await self.get_by_id(notification_id, user_id)
        if not notif:
            return None
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        await self.session.flush()
        return notif

    async def mark_all_as_read(
        self,
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
        category: Optional[str] = None,
    ) -> int:
        """Batch marks all unread notifications as read for a user."""
        conditions = [
            Notification.recipient_user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        ]
        if workspace_id:
            conditions.append(
                (Notification.workspace_id == workspace_id) | (Notification.workspace_id.is_(None))
            )
        if category:
            conditions.append(Notification.category == category)

        stmt = (
            update(Notification)
            .where(*conditions)
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount

    async def archive_notification(
        self, notification_id: UUID, user_id: UUID
    ) -> Optional[Notification]:
        """Archives a notification, removing it from primary feeds."""
        notif = await self.get_by_id(notification_id, user_id)
        if not notif:
            return None
        notif.is_archived = True
        await self.session.flush()
        return notif

    async def delete_notification(
        self, notification_id: UUID, user_id: UUID
    ) -> bool:
        """Permanently deletes a notification."""
        notif = await self.get_by_id(notification_id, user_id)
        if not notif:
            return False
        await self.session.delete(notif)
        await self.session.flush()
        return True

    async def find_by_deduplication_key(
        self, user_id: UUID, deduplication_key: str
    ) -> Optional[Notification]:
        """Checks for existing notification with identical deduplication key."""
        stmt = select(Notification).where(
            Notification.recipient_user_id == user_id,
            Notification.deduplication_key == deduplication_key,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # Notification Delivery Tracking
    # -------------------------------------------------------------------------

    async def create_delivery(
        self, delivery: NotificationDelivery
    ) -> NotificationDelivery:
        """Records a new delivery attempt."""
        self.session.add(delivery)
        await self.session.flush()
        return delivery

    async def update_delivery_status(
        self,
        delivery_id: UUID,
        status: str,
        failure_reason: Optional[str] = None,
        provider_ref: Optional[str] = None,
        retry_at: Optional[datetime] = None,
    ) -> Optional[NotificationDelivery]:
        """Updates delivery lifecycle state."""
        stmt = select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        res = await self.session.execute(stmt)
        deliv = res.scalar_one_or_none()
        if not deliv:
            return None

        deliv.status = status
        deliv.last_attempt_at = datetime.now(timezone.utc)
        deliv.attempt_count += 1
        if status == "delivered":
            deliv.delivered_at = datetime.now(timezone.utc)
        if failure_reason:
            deliv.failure_reason = failure_reason
        if provider_ref:
            deliv.provider_message_reference = provider_ref
        if retry_at:
            deliv.retry_at = retry_at

        await self.session.flush()
        return deliv

    # -------------------------------------------------------------------------
    # Notification Preferences
    # -------------------------------------------------------------------------

    async def get_user_preferences(
        self, user_id: UUID
    ) -> List[NotificationPreference]:
        """Retrieves all notification preference entries for a user."""
        stmt = (
            select(NotificationPreference)
            .where(NotificationPreference.user_id == user_id)
            .order_by(NotificationPreference.category, NotificationPreference.channel)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def upsert_user_preference(
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
        """Inserts or updates a user preference row."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.category == category,
            NotificationPreference.channel == channel,
        )
        res = await self.session.execute(stmt)
        pref = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if pref:
            pref.is_enabled = is_enabled
            pref.min_severity = min_severity
            pref.quiet_hours_enabled = quiet_hours_enabled
            pref.quiet_hours_start = quiet_hours_start
            pref.quiet_hours_end = quiet_hours_end
            pref.timezone = timezone_name
            pref.frequency = frequency
            pref.updated_at = now
        else:
            pref = NotificationPreference(
                user_id=user_id,
                category=category,
                channel=channel,
                is_enabled=is_enabled,
                min_severity=min_severity,
                quiet_hours_enabled=quiet_hours_enabled,
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
                timezone=timezone_name,
                frequency=frequency,
                created_at=now,
                updated_at=now,
            )
            self.session.add(pref)

        await self.session.flush()
        return pref

    # -------------------------------------------------------------------------
    # Push Subscriptions (Web Push)
    # -------------------------------------------------------------------------

    async def save_push_subscription(
        self,
        user_id: UUID,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        user_agent: Optional[str] = None,
    ) -> PushSubscription:
        """Stores or reactivates a Web Push subscription."""
        stmt = select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
        res = await self.session.execute(stmt)
        sub = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if sub:
            sub.p256dh_key = p256dh_key
            sub.auth_key = auth_key
            sub.user_agent = user_agent
            sub.is_active = True
            sub.updated_at = now
        else:
            sub = PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh_key=p256dh_key,
                auth_key=auth_key,
                user_agent=user_agent,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self.session.add(sub)

        await self.session.flush()
        return sub

    async def get_user_push_subscriptions(
        self, user_id: UUID, active_only: bool = True
    ) -> List[PushSubscription]:
        """Gets registered push subscriptions for a user."""
        conditions = [PushSubscription.user_id == user_id]
        if active_only:
            conditions.append(PushSubscription.is_active == True)  # noqa: E712

        stmt = select(PushSubscription).where(*conditions)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def revoke_push_subscription(
        self, subscription_id: UUID, user_id: UUID
    ) -> bool:
        """Revokes an active push subscription."""
        stmt = select(PushSubscription).where(
            PushSubscription.id == subscription_id,
            PushSubscription.user_id == user_id,
        )
        res = await self.session.execute(stmt)
        sub = res.scalar_one_or_none()
        if not sub:
            return False
        sub.is_active = False
        await self.session.flush()
        return True

    # -------------------------------------------------------------------------
    # Notification Templates
    # -------------------------------------------------------------------------

    async def get_template(
        self, event_type: str, channel: str, locale: str = "en_IN"
    ) -> Optional[NotificationTemplate]:
        """Fetches active template for event type and channel."""
        stmt = (
            select(NotificationTemplate)
            .where(
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.channel == channel,
                NotificationTemplate.locale == locale,
                NotificationTemplate.is_active == True,  # noqa: E712
            )
            .order_by(NotificationTemplate.version.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
