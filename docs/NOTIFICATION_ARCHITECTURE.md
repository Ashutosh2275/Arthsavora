# Unified Notifications & Financial Alerts Architecture

## 1. System Overview

The Arthsavora Unified Notification & Communication System is a centralized, multi-channel alerting framework. It unifies financial activity updates across personal, family, and commercial business workspaces, delivering timely, verified, and non-alarmist communications via **In-App Notification Center**, **Transactional Email**, and **Web Push (W3C VAPID)**.

### Core Architectural Mandate
> **Notifications communicate verified events, scheduled expectations, or clearly labeled predictions.** They must **never** misrepresent an expected recurring commitment as a completed payment, nor label a statistical spending anomaly as confirmed fraud.

```
+───────────────────────────────────────────────────────────────────────────────────+
|                           FINANCIAL EVENT SOURCES                                 |
|  [Transactions]  [Budgets]  [Goals]  [Recurring]  [Forecasts]  [Anomalies]  ...   |
+─────────────────────────────────────────┬─────────────────────────────────────────+
                                          │
                                          ▼
                         [Notification Event Factory]
                      (Sanitization, Deduplication Keys)
                                          │
                                          ▼
                       [Deduplication & Cache Evaluation]
                         (Suppresses identical alerts)
                                          │
                                          ▼
                       [Notification Policy Evaluator]
                   (Category, Channel, Severity, Quiet Hours)
                                          │
                                          ▼
                    [Authoritative Database Persistence]
                        (notifications & deliveries)
                                          │
          ┌───────────────────────────────┼───────────────────────────────┐
          ▼                               ▼                               ▼
    [In-App Channel]               [Email Channel]                 [Push Channel]
   (Instant DB + SSE)             (HTML / PlainText)               (VAPID Web Push)
          │                               │                               │
          ▼                               ▼                               ▼
 [Notification Center]            [SMTP / Mock Log]              [Browser ServiceWorker]
```

---

## 2. Architectural Separation of Concerns

The notification system decomposes notification processing into ten decoupled lifecycle stages:

| Stage | Component | Responsibility |
|---|---|---|
| **1. Ingestion** | `NotificationService.dispatch_notification` | Receives domain `NotificationPayloadVO` with metadata. |
| **2. Deduplication** | `generate_deduplication_key` | Deterministic SHA-256 hash preventing duplicate spamming. |
| **3. Policy Evaluation** | `NotificationPolicyEvaluator` | Checks user category/channel preferences, min severity, and quiet-hours. |
| **4. Creation** | `NotificationRepository.create_notification` | Persists authoritative record in `notifications` table. |
| **5. Delivery Queuing** | `NotificationDelivery` | Creates tracked delivery records per eligible channel. |
| **6. Provider Dispatch** | `NotificationDeliveryEngine` | Coordinates physical dispatch via email, web push, and in-app. |
| **7. Real-Time Broadcast** | `subscribe_user_stream` | Live Server-Sent Events (SSE) push to active browser tabs. |
| **8. Delivery Tracking** | `update_delivery_status` | Records attempt count, provider references, and retry timestamps. |
| **9. User Interaction** | `mark_as_read`, `archive` | In-app notification center state mutations. |
| **10. Retry & Failure** | Exponential Backoff Engine | Bounded retries (max 3 attempts) with exponential delay. |

---

## 3. Relational Database Schema

```sql
-- 1. Master Notification Record
CREATE TABLE notifications (
    id UUID PRIMARY KEY,
    recipient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    category VARCHAR(32) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'info',
    related_resource_type VARCHAR(64),
    related_resource_id VARCHAR(64),
    action_url VARCHAR(512),
    metadata_json JSONB NOT NULL DEFAULT '{}',
    event_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    deduplication_key VARCHAR(128)
);

-- 2. Channel Delivery Logs
CREATE TABLE notification_deliveries (
    id UUID PRIMARY KEY,
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    channel VARCHAR(32) NOT NULL,
    provider VARCHAR(64) NOT NULL DEFAULT 'internal',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    attempt_count INT NOT NULL DEFAULT 0,
    provider_message_reference VARCHAR(255),
    last_attempt_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    retry_at TIMESTAMPTZ,
    failure_reason TEXT
);

-- 3. User Preferences & Quiet Hours
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(32) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    min_severity VARCHAR(16) NOT NULL DEFAULT 'info',
    quiet_hours_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    quiet_hours_start VARCHAR(8) DEFAULT '22:00',
    quiet_hours_end VARCHAR(8) DEFAULT '08:00',
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
    frequency VARCHAR(32) NOT NULL DEFAULT 'instant',
    CONSTRAINT uq_user_category_channel_pref UNIQUE (user_id, category, channel)
);

-- 4. Push Subscriptions
CREATE TABLE push_subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    user_agent VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_user_push_endpoint UNIQUE (user_id, endpoint)
);
```

---

## 4. Multi-Tenant & Anti-IDOR Authorization

All notification APIs enforce strict recipient scoping:
- Queries execute `where(Notification.recipient_user_id == current_user.id)`.
- If a user from Workspace A attempts to inspect, read, or archive a notification belonging to Workspace B or User B, the query returns `None` and raises an immediate `404 Not Found`.
- Workspace scoping is optional: user-specific alerts (e.g. security logins) span all workspaces, while financial alerts carry an optional `workspace_id` filter.

---

## 5. Related Documentation

- [Notification Event Catalog](file:///d:/Arthsavora/docs/NOTIFICATION_EVENT_CATALOG.md)
- [Notification Delivery Engine](file:///d:/Arthsavora/docs/NOTIFICATION_DELIVERY_ENGINE.md)
- [Notification Preferences & Quiet Hours](file:///d:/Arthsavora/docs/NOTIFICATION_PREFERENCES.md)
- [Email Provider Integration](file:///d:/Arthsavora/docs/EMAIL_PROVIDER_INTEGRATION.md)
- [Web Push Integration](file:///d:/Arthsavora/docs/WEB_PUSH_INTEGRATION.md)
