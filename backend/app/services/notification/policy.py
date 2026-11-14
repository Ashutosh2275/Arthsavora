"""
Arthsavora Notification Policy Evaluator
Evaluates user delivery preferences, category permissions, channel routing,
severity filtering, and quiet-hours rules.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set
from uuid import UUID

from app.domain.notification import (
    NotificationCategory,
    NotificationChannel,
    NotificationPayloadVO,
    NotificationSeverity,
    SEVERITY_WEIGHTS,
    is_in_quiet_hours,
)
from app.infrastructure.database.models.notification import NotificationPreference

logger = logging.getLogger(__name__)


class NotificationPolicyEvaluator:
    """Evaluates whether an event payload should be delivered on specific channels."""

    # Channels always allowed unless explicitly disabled
    DEFAULT_ENABLED_CHANNELS = {
        NotificationChannel.IN_APP,
        NotificationChannel.EMAIL,
    }

    # Categories that are mandatory and bypass user silencing for critical security
    MANDATORY_SECURITY_CATEGORIES = {
        NotificationCategory.SECURITY,
    }

    @classmethod
    def evaluate_channels_for_recipient(
        cls,
        payload: NotificationPayloadVO,
        preferences: List[NotificationPreference],
        now_utc: Optional[datetime] = None,
    ) -> Set[NotificationChannel]:
        """
        Determines the exact set of channels permitted for delivering `payload`.
        Takes user preferences, minimum severity, and quiet-hours into account.
        """
        now = now_utc or datetime.now(timezone.utc)
        eligible_channels: Set[NotificationChannel] = set()

        # Build index of user preferences by channel
        # Category matches exact category or wildcard "*"
        pref_by_channel: Dict[NotificationChannel, NotificationPreference] = {}
        for pref in preferences:
            try:
                chan = NotificationChannel(pref.channel)
            except ValueError:
                continue

            if pref.category == payload.category.value:
                pref_by_channel[chan] = pref
            elif pref.category == "*" and chan not in pref_by_channel:
                pref_by_channel[chan] = pref

        # Security events always dispatch to in_app and email regardless of quiet hours
        is_critical_security = (
            payload.category in cls.MANDATORY_SECURITY_CATEGORIES
            or payload.severity == NotificationSeverity.CRITICAL
        )

        for channel in [NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.WEB_PUSH]:
            pref = pref_by_channel.get(channel)

            # Check 1: Is channel enabled?
            if pref:
                if not pref.is_enabled and not is_critical_security:
                    continue

                # Check 2: Minimum severity threshold
                try:
                    pref_min_sev = NotificationSeverity(pref.min_severity)
                    if SEVERITY_WEIGHTS[payload.severity] < SEVERITY_WEIGHTS[pref_min_sev]:
                        if not is_critical_security:
                            continue
                except ValueError:
                    pass

                # Check 3: Quiet Hours check (only applies to noisy outbound channels, not in_app)
                if pref.quiet_hours_enabled and channel != NotificationChannel.IN_APP:
                    in_quiet = is_in_quiet_hours(
                        now_utc=now,
                        tz_name=pref.timezone or "Asia/Kolkata",
                        quiet_start_str=pref.quiet_hours_start or "22:00",
                        quiet_end_str=pref.quiet_hours_end or "08:00",
                    )
                    if in_quiet and not is_critical_security:
                        logger.info(
                            f"[NotificationPolicy] Suppressing {channel.value} for {payload.event_type.value} during quiet hours."
                        )
                        continue

            eligible_channels.add(channel)

        # In-App is always delivered so the user has an authoritative record in the notification center
        eligible_channels.add(NotificationChannel.IN_APP)

        return eligible_channels
