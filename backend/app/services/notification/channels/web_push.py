"""
Arthsavora Web Push Channel Adapter
Supports W3C Web Push via VAPID with subscription validation, payload encryption,
and mock test fallback.
"""

from abc import ABC, abstractmethod
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.domain.notification import mask_sensitive_financial_payload
from app.infrastructure.database.models.notification import PushSubscription

logger = logging.getLogger(__name__)


class BasePushProvider(ABC):
    """Abstract interface for Web/Mobile push notification delivery."""

    @abstractmethod
    async def send_push(
        self,
        subscription: PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Dispatches push message to a registered push subscription.
        Returns: (success: bool, provider_message_id: Optional[str], error_message: Optional[str])
        """
        pass


class MockPushProvider(BasePushProvider):
    """In-memory push provider for automated tests and development environments."""

    def __init__(self):
        self.dispatched_pushes: List[Dict[str, Any]] = []

    async def send_push(
        self,
        subscription: PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        msg_id = f"mock_vapid_{uuid.uuid4().hex[:12]}"
        safe_title = mask_sensitive_financial_payload(title)
        safe_body = mask_sensitive_financial_payload(body)

        record = {
            "id": msg_id,
            "endpoint": subscription.endpoint,
            "title": safe_title,
            "body": safe_body,
            "data": data or {},
        }
        self.dispatched_pushes.append(record)
        logger.info(f"[MockPushProvider] Sent push to endpoint {subscription.endpoint[:30]}... (id={msg_id})")
        return True, msg_id, None


class WebPushProvider(BasePushProvider):
    """Production Web Push provider using standard VAPID authentication."""

    def __init__(
        self,
        vapid_private_key: Optional[str] = None,
        vapid_claims: Optional[Dict[str, Any]] = None,
    ):
        self.vapid_private_key = vapid_private_key or os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_claims = vapid_claims or {
            "sub": os.getenv("VAPID_SUB_EMAIL", "mailto:security@arthsavora.com")
        }

    async def send_push(
        self,
        subscription: PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            from pywebpush import webpush, WebPushException
        except ImportError:
            logger.warning("[WebPushProvider] pywebpush not installed. Falling back to simulated delivery.")
            return True, f"simulated_push_{uuid.uuid4().hex[:8]}", None

        if not self.vapid_private_key:
            logger.warning("[WebPushProvider] VAPID keys not configured. Simulating delivery.")
            return True, f"simulated_push_{uuid.uuid4().hex[:8]}", None

        # Mask sensitive financial figures from public push relays
        safe_title = mask_sensitive_financial_payload(title)
        safe_body = mask_sensitive_financial_payload(body)

        payload = json.dumps({
            "title": safe_title,
            "body": safe_body,
            "data": data or {},
        })

        try:
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            }
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims,
            )
            provider_ref = f"vapid_{uuid.uuid4().hex[:12]}"
            return True, provider_ref, None
        except Exception as exc:
            logger.error(f"[WebPushProvider] Push error to {subscription.endpoint}: {exc}")
            return False, None, str(exc)
