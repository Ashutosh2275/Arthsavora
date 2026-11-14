"""
Arthsavora Unified Notifications Relational Database Models
PostgreSQL source of truth for in-app notifications, delivery logs, user preferences,
templates, and Web Push subscriptions.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authoritative notification record representing an event dispatched to a recipient."""
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "recipient_user_id", "is_read", "is_archived"),
        Index("ix_notifications_user_category", "recipient_user_id", "category"),
        Index("ix_notifications_dedup", "recipient_user_id", "deduplication_key"),
        Index("ix_notifications_workspace", "workspace_id"),
    )

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    related_resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deduplication_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_user_id])
    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
        order_by="NotificationDelivery.created_at.desc()",
        lazy="selectin",
    )


class NotificationDelivery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks delivery attempts across channels (in_app, email, web_push, mobile_push)."""
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        Index("ix_notification_deliveries_status", "status"),
        Index("ix_notification_deliveries_channel", "channel"),
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="internal", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_message_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    notification: Mapped["Notification"] = relationship("Notification", back_populates="deliveries")


class NotificationPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User-level delivery preferences by category, channel, and quiet-hours."""
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "channel", name="uq_user_category_channel_pref"),
        Index("ix_notif_pref_user", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "transaction", "budget", "*"
    channel: Mapped[str] = mapped_column(String(32), nullable=False)   # "in_app", "email", "web_push"
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_severity: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(8), default="22:00", nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(8), default="08:00", nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), default="instant", nullable=False)

    user = relationship("User", foreign_keys=[user_id])


class NotificationTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Multi-channel localized message templates."""
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint("event_type", "channel", "locale", "version", name="uq_template_event_chan_ver"),
        Index("ix_notif_template_event", "event_type", "channel"),
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en_IN", nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PushSubscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Web Push VAPID credentials registered for a user browser instance."""
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        Index("ix_push_subs_user", "user_id"),
        UniqueConstraint("user_id", "endpoint", name="uq_user_push_endpoint"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False)
    auth_key: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
