"""
Arthsavora Notification Delivery Engine
Executes multi-channel outbound delivery with retry policies, exponential backoff,
and delivery state tracking.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
from uuid import UUID

from app.domain.notification import (
    DeliveryStatus,
    NotificationChannel,
    NotificationPayloadVO,
)
from app.infrastructure.database.models.notification import (
    Notification,
    NotificationDelivery,
)
from app.infrastructure.database.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.services.notification.channels.email import (
    BaseEmailProvider,
    MockEmailProvider,
    render_financial_email_template,
)
from app.services.notification.channels.web_push import (
    BasePushProvider,
    MockPushProvider,
)

logger = logging.getLogger(__name__)


class NotificationDeliveryEngine:
    """Coordinates physical dispatch across email, push, and in-app channels."""

    MAX_RETRIES = 3
    INITIAL_BACKOFF_SECONDS = 30

    def __init__(
        self,
        repository: NotificationRepository,
        email_provider: Optional[BaseEmailProvider] = None,
        push_provider: Optional[BasePushProvider] = None,
    ):
        self.repository = repository
        self.email_provider = email_provider or MockEmailProvider()
        self.push_provider = push_provider or MockPushProvider()

    async def execute_delivery(
        self,
        notification: Notification,
        delivery: NotificationDelivery,
        recipient_user: Optional[User] = None,
    ) -> NotificationDelivery:
        """Executes a single channel delivery attempt."""
        channel = delivery.channel

        try:
            if channel == NotificationChannel.IN_APP.value:
                # In-app notifications are delivered instantaneously upon database persistence
                return await self.repository.update_delivery_status(
                    delivery_id=delivery.id,
                    status=DeliveryStatus.DELIVERED.value,
                    provider_ref=f"in_app_{delivery.id.hex[:8]}",
                )

            elif channel == NotificationChannel.EMAIL.value:
                if not recipient_user or not recipient_user.email:
                    return await self.repository.update_delivery_status(
                        delivery_id=delivery.id,
                        status=DeliveryStatus.FAILED.value,
                        failure_reason="Recipient has no verified email address",
                    )

                html_body, text_body = render_financial_email_template(
                    title=notification.title,
                    message=notification.message,
                    severity=notification.severity,
                    action_url=notification.action_url,
                    metadata=notification.metadata_json,
                )

                success, ref, error_msg = await self.email_provider.send_email(
                    to_email=recipient_user.email,
                    subject=f"Arthsavora: {notification.title}",
                    html_body=html_body,
                    text_body=text_body,
                )

                if success:
                    return await self.repository.update_delivery_status(
                        delivery_id=delivery.id,
                        status=DeliveryStatus.DELIVERED.value,
                        provider_ref=ref,
                    )
                else:
                    return await self._handle_delivery_failure(delivery, error_msg or "Email delivery failed")

            elif channel == NotificationChannel.WEB_PUSH.value:
                subscriptions = await self.repository.get_user_push_subscriptions(notification.recipient_user_id)
                if not subscriptions:
                    # User has enabled push in prefs but has not yet registered an active browser token
                    return await self.repository.update_delivery_status(
                        delivery_id=delivery.id,
                        status=DeliveryStatus.CANCELLED.value,
                        failure_reason="No active browser push subscription registered",
                    )

                all_succeeded = True
                last_ref = None
                last_err = None

                for sub in subscriptions:
                    ok, ref, err = await self.push_provider.send_push(
                        subscription=sub,
                        title=notification.title,
                        body=notification.message,
                        data={"url": notification.action_url, "id": str(notification.id)},
                    )
                    if ok:
                        last_ref = ref
                    else:
                        all_succeeded = False
                        last_err = err

                if all_succeeded:
                    return await self.repository.update_delivery_status(
                        delivery_id=delivery.id,
                        status=DeliveryStatus.DELIVERED.value,
                        provider_ref=last_ref,
                    )
                else:
                    return await self._handle_delivery_failure(delivery, last_err or "Push delivery failed")

            elif channel == NotificationChannel.MOBILE_PUSH.value:
                # Mobile push abstraction placeholder for future React Native/Expo integration
                return await self.repository.update_delivery_status(
                    delivery_id=delivery.id,
                    status=DeliveryStatus.DELIVERED.value,
                    provider_ref=f"mobile_push_{delivery.id.hex[:8]}",
                )

            else:
                return await self.repository.update_delivery_status(
                    delivery_id=delivery.id,
                    status=DeliveryStatus.FAILED.value,
                    failure_reason=f"Unsupported notification channel: {channel}",
                )

        except Exception as exc:
            logger.error(f"[DeliveryEngine] Exception executing {channel} delivery: {exc}")
            return await self._handle_delivery_failure(delivery, str(exc))

    async def _handle_delivery_failure(
        self, delivery: NotificationDelivery, error_msg: str
    ) -> NotificationDelivery:
        """Evaluates retry eligibility using exponential backoff."""
        next_attempt = delivery.attempt_count + 1
        if next_attempt <= self.MAX_RETRIES:
            backoff_sec = self.INITIAL_BACKOFF_SECONDS * (2 ** (next_attempt - 1))
            retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_sec)
            return await self.repository.update_delivery_status(
                delivery_id=delivery.id,
                status=DeliveryStatus.RETRY_SCHEDULED.value,
                failure_reason=error_msg,
                retry_at=retry_at,
            )
        else:
            return await self.repository.update_delivery_status(
                delivery_id=delivery.id,
                status=DeliveryStatus.FAILED.value,
                failure_reason=f"Exceeded max retries ({self.MAX_RETRIES}). Final error: {error_msg}",
            )
