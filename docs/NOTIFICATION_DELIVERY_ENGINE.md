# Notification Delivery Engine & Outbound Dispatch Architecture

## 1. Executive Summary

The Notification Delivery Engine ([delivery_engine.py](file:///d:/Arthsavora/backend/app/services/notification/delivery_engine.py)) coordinates outbound communication across email, Web Push, and in-app channels.

### Delivery State Invariant
> **Notification creation is strictly decoupled from delivery confirmation.** A notification may be successfully recorded in the PostgreSQL database but fail to reach an external mail transfer agent (MTA) or push service relay. These lifecycle phases are tracked independently.

```
                      [Notification Created]
                                │
                                ▼
                       [Delivery Queued]
                                │
                                ▼
                       [Delivery Sending]
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
    [Provider Delivers]                  [Provider Fails]
              │                                   │
              ▼                                   ▼
      [Status: DELIVERED]                 (Attempts < MAX_RETRIES)
                                            ├── Yes ──> [Status: RETRY_SCHEDULED]
                                            └── No  ──> [Status: FAILED]
```

---

## 2. Delivery Lifecycle State Machine

| State | Definition | Next Permissible States |
|---|---|---|
| `PENDING` | Channel delivery created, waiting for worker execution | `QUEUED`, `SENDING`, `CANCELLED` |
| `QUEUED` | Placed on internal async worker queue | `SENDING`, `CANCELLED` |
| `SENDING` | Socket or HTTP request to external provider active | `DELIVERED`, `RETRY_SCHEDULED`, `FAILED` |
| `DELIVERED` | Provider returned definitive acknowledgement (e.g. SMTP 250 OK or VAPID 201 Created) | Terminal |
| `RETRY_SCHEDULED` | Temporary failure; backoff timer queued | `SENDING`, `CANCELLED` |
| `FAILED` | Terminal failure after exceeding maximum retry attempts | Terminal |
| `CANCELLED` | Delivery aborted (e.g. user revoked push token or quiet hours override) | Terminal |

---

## 3. Exponential Backoff Retry Policy

Network hiccups, provider rate limits (e.g. SMTP 421 / 450), and mobile relay timeouts are handled with exponential backoff:

### 3.1 Mathematical Formula
For attempt number $k \in \{1, 2, 3\}$:

$$\text{Delay}_k = \text{Initial Backoff} \times 2^{k-1}$$

With `INITIAL_BACKOFF_SECONDS = 30`:
- **Attempt 1 Failure**: Retry scheduled in $30 \times 2^0 = 30\text{ seconds}$.
- **Attempt 2 Failure**: Retry scheduled in $30 \times 2^1 = 60\text{ seconds}$.
- **Attempt 3 Failure**: Retry scheduled in $30 \times 2^2 = 120\text{ seconds}$.
- **Subsequent Failure**: Marked `FAILED` with `failure_reason = "Exceeded max retries (3)"`.

---

## 4. Multi-Channel Provider Interfaces

### 4.1 In-App Channel (`in_app`)
- **Latency**: Instantaneous.
- **Provider Ref**: `in_app_{delivery_id}`.
- **Delivery**: Written directly to PostgreSQL and broadcast via the in-memory Server-Sent Events (SSE) bus to all connected client tabs.

### 4.2 Email Channel (`email`)
- **Latency**: Sub-second to 3 seconds.
- **Provider Ref**: SMTP message ID or `mock_mail_{hash}` in test environments.
- **Fallback**: Both multipart HTML and plain-text alternatives rendered per recipient.

### 4.3 Web Push Channel (`web_push`)
- **Protocol**: W3C Push API over RFC 8292 VAPID.
- **Payload Privacy**: Critical account numbers and security pins are masked prior to encryption.

### 4.4 Mobile Push Channel (`mobile_push`)
- **Status**: Platform interface prepared for future React Native and Expo push integration.

---

## 5. Related Documentation

- [Notification Architecture](file:///d:/Arthsavora/docs/NOTIFICATION_ARCHITECTURE.md)
- [Email Provider Integration](file:///d:/Arthsavora/docs/EMAIL_PROVIDER_INTEGRATION.md)
- [Web Push Integration](file:///d:/Arthsavora/docs/WEB_PUSH_INTEGRATION.md)
- [Notification Deduplication](file:///d:/Arthsavora/docs/NOTIFICATION_DEDUPLICATION.md)
