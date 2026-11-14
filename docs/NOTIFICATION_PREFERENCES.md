# User Notification Preferences, Quiet Hours and Timezone Policy

## 1. Overview

Users maintain fine-grained, self-service control over how and when they receive financial alerts. Implemented in [policy.py](file:///d:/Arthsavora/backend/app/services/notification/policy.py) and [notification_repository.py](file:///d:/Arthsavora/backend/app/repositories/notification_repository.py), the preference engine reconciles user settings before any outbound channel dispatch occurs.

---

## 2. Granular Preference Matrix

Users configure preferences across three orthogonal dimensions:

```
                  ┌──────────────────────┐
                  │ Notification Category│ (Transaction, Budget, Goal, etc.)
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Delivery Channel    │ (In-App, Email, Web Push)
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Minimum Severity   │ (Info, Warning, Critical)
                  └──────────────────────┘
```

### 2.1 Default Policy State
When a new user joins a workspace, the system initializes permissive, non-intrusive defaults:
- **In-App**: Enabled for all categories at `INFO` severity.
- **Email**: Enabled for high-significance categories (`BUDGET`, `RECURRING`, `ANOMALY`, `SECURITY`).
- **Web Push**: Disabled by default until the user explicitly opts in via browser permissions.

---

## 3. Configurable Quiet Hours & Timezones

### 3.1 Motivation
Financial anxiety increases when notifications awaken users during late-night or early-morning hours. Quiet hours allow users to specify rest periods during which noisy external channels (emails and push notifications) are suppressed.

### 3.2 Timezone Normalization
All timestamps in the PostgreSQL database are recorded in UTC (`TIMESTAMPTZ`). When evaluating quiet hours:
1. The user's configured timezone (e.g., `Asia/Kolkata`, `America/New_York`, `Europe/London`) is loaded from preferences.
2. The current UTC time is converted to the user's localized wall-clock time using Python's `zoneinfo.ZoneInfo`.
3. The localized time is checked against the configured quiet window.

### 3.3 Midnight-Crossing Algorithm
Quiet hour intervals frequently cross midnight (e.g., 10:00 PM to 7:00 AM):
```python
if start_time <= end_time:
    # Standard daytime window (e.g., 13:00 to 14:00)
    in_quiet = start_time <= local_time < end_time
else:
    # Midnight-crossing window (e.g., 22:00 to 07:00)
    in_quiet = local_time >= start_time or local_time < end_time
```

### 3.4 In-App Persistence During Quiet Hours
Quiet hours **only suppress outbound external interruptions** (Email and Web Push). In-app notifications are still persisted to the `notifications` table and will be visible in the user's Notification Center when they next open the application.

---

## 4. Mandatory Security Notification Policy

### The Safety Invariant
> **Critical account-security alerts strictly bypass quiet hours and user channel silencers.**

The following events cannot be disabled by user preferences:
- `security.new_login`: Login detected from an unrecognized IP, device, or geographical location.
- `security.password_changed`: Password or primary authentication credentials modified.
- `security.auth_event`: Account lockout or critical permission escalation.

**Rationale**: Immediate delivery of security alerts is vital for incident response (e.g., allowing a user to immediately revoke compromised sessions before unauthorized ledger transactions occur).

---

## 5. REST API Reference

- **Get Preferences**: `GET /api/v1/notifications/preferences`
- **Update Preference**: `PATCH /api/v1/notifications/preferences`
  ```json
  {
    "category": "budget",
    "channel": "email",
    "is_enabled": true,
    "min_severity": "warning",
    "quiet_hours_enabled": true,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    "timezone": "Asia/Kolkata",
    "frequency": "instant"
  }
  ```

---

## 6. Related Documentation

- [Notification Architecture](file:///d:/Arthsavora/docs/NOTIFICATION_ARCHITECTURE.md)
- [Notification Delivery Engine](file:///d:/Arthsavora/docs/NOTIFICATION_DELIVERY_ENGINE.md)
- [Notification Security & Privacy](file:///d:/Arthsavora/docs/NOTIFICATION_SECURITY.md)
