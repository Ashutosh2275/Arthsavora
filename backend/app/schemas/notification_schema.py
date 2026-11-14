"""
Arthsavora Notification Pydantic Schemas & DTOs
Request/Response contracts for notifications, preferences, push subscriptions, and unread counts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class NotificationDeliveryResponse(BaseModel):
    """Outbound delivery log across channels."""
    id: UUID
    channel: str
    provider: str
    status: str
    attempt_count: int
    provider_message_reference: Optional[str] = None
    last_attempt_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Complete notification DTO presented in in-app notification centers."""
    id: UUID
    recipient_user_id: UUID
    workspace_id: Optional[UUID] = None
    category: str
    event_type: str
    title: str
    message: str
    severity: str
    related_resource_type: Optional[str] = None
    related_resource_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    event_timestamp: datetime
    created_at: datetime
    is_read: bool
    read_at: Optional[datetime] = None
    is_archived: bool
    deliveries: List[NotificationDeliveryResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated collection of notifications with total count and unread count."""
    items: List[NotificationResponse]
    total: int
    limit: int
    offset: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Fast indexed unread count response."""
    unread_count: int


class MarkReadResponse(BaseModel):
    """Response returned upon read-state mutation."""
    success: bool
    affected_count: int


class NotificationPreferenceResponse(BaseModel):
    """User notification preference settings."""
    id: UUID
    user_id: UUID
    category: str
    channel: str
    is_enabled: bool
    min_severity: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"
    timezone: str
    frequency: str
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationPreferenceUpdateRequest(BaseModel):
    """Payload to create or update a user preference."""
    category: str
    channel: str
    is_enabled: bool
    min_severity: Optional[str] = "info"
    quiet_hours_enabled: Optional[bool] = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"
    timezone: Optional[str] = "Asia/Kolkata"
    frequency: Optional[str] = "instant"


class PushSubscriptionCreateRequest(BaseModel):
    """Payload to register a Web Push browser subscription."""
    endpoint: str
    p256dh_key: str
    auth_key: str
    user_agent: Optional[str] = None


class PushSubscriptionResponse(BaseModel):
    """Web Push subscription record."""
    id: UUID
    endpoint: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TestNotificationRequest(BaseModel):
    """Payload for triggering a simulated notification in development."""
    category: str = "transaction"
    title: str = "Test Financial Alert"
    message: str = "This is a simulated verification notification from ARTHSAVORA."
    severity: str = "info"
    action_url: Optional[str] = "/notifications"
