# ARTHSAVORA Notification Deduplication & Alert Fatigue Prevention

## 1. Executive Overview

Financial platforms run the risk of overwhelming users with redundant alerts—such as repeated threshold alerts when spending hovers around 90%, multiple notifications for the same recurring payment schedule, or duplicate alerts triggered by asynchronous background workers.

ARTHSAVORA implements a deterministic, cryptographically keyed notification deduplication engine that guarantees idempotent alert delivery across all channels (In-App, Email, Web Push, and Mobile Push) while preventing notification storming.

---

## 2. Core Deduplication Key Architecture

Every notification event evaluated by the `NotificationService` generates or receives an authoritative deduplication key (`deduplication_key`).

### 2.1 Key Derivation Formula

The deduplication key is calculated using a deterministic SHA-256 hash across four contextual components:

```python
def generate_deduplication_key(
    recipient_user_id: UUID,
    event_type: NotificationEventType,
    resource_id: Optional[str] = None,
    period_token: Optional[str] = None,
) -> str:
    elements = [
        str(recipient_user_id),
        event_type.value,
        str(resource_id or "global"),
        str(period_token or "instant"),
    ]
    raw = ":".join(elements)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"dedup:{event_type.value}:{digest}"
```

### 2.2 Key Components

| Component | Description | Example |
| :--- | :--- | :--- |
| `recipient_user_id` | Scopes deduplication strictly to the affected user. | `3fa85f64-5717-4562-b3fc-2c963f66afa6` |
| `event_type` | Granular event type from `NotificationEventType`. | `budget.threshold_reached` |
| `resource_id` | Identifier of the entity generating the event. | `bgt-9812-rent` |
| `period_token` | Time window token restricting re-issuance. | `2026-11` or `2026-W46` or `2026-11-14` |

---

## 3. Category-Specific Deduplication Strategies

### 3.1 Budget Threshold Crossing Suppression
When user spending crosses a budget threshold (e.g., 80%, 90%, 100%), micro-transactions in quick succession could trigger back-to-back alerts.
- **Resource ID:** Budget ID + Threshold Percentile (`{budget_id}:{threshold_pct}`)
- **Period Token:** Fiscal period (`YYYY-MM`)
- **Behavior:** Once the 90% alert is issued for November 2026, subsequent transactions within the same month will not fire another 90% alert for that budget.

### 3.2 Recurring Commitment & Bill Reminders
Upcoming payment reminders for utility bills, rent, and subscriptions:
- **Resource ID:** Commitment Schedule ID or Recurring Rule ID (`{rule_id}`)
- **Period Token:** Target payment due date (`YYYY-MM-DD`)
- **Behavior:** Ensures only one reminder per scheduled bill occurrence is dispatched, even if background scheduler tasks run repeatedly.

### 3.3 Financial Anomaly & Risk Alerts
When anomalous transactions or spikes are flagged:
- **Resource ID:** Transaction ID (`{transaction_id}`)
- **Period Token:** `instant` or detection scan batch ID
- **Behavior:** Multiple anomaly detection runs over historical transactions never re-alert the user for the same flagged transaction.

### 3.4 Cash-Flow Forecast Alerts
Forecast predictions regarding projected balances or budget exhaustion:
- **Resource ID:** Projection horizon type (`projected_exhaustion`)
- **Period Token:** Calendar week (`YYYY-Www`)
- **Behavior:** Forecast adjustments update dashboard metrics in place rather than issuing repetitive alerts unless there is a material variance shift.

---

## 4. Concurrency & Race Condition Protection

To prevent concurrent background worker threads from dispatching duplicate notifications:
1. **Unique Index:** The `notifications` table maintains a database index on `(recipient_user_id, deduplication_key)`.
2. **Lookup Before Create:** The `NotificationRepository.get_by_deduplication_key` checks for prior issuance within the event's deduplication horizon.
3. **Graceful Idempotency:** If a duplicate key is detected, the dispatch operation logs the collision and returns the existing notification without creating a new record or triggering channel providers.

---

## 5. Verification & Testing Evidence

The deduplication engine is rigorously tested in `backend/tests/test_notifications.py`:
- `test_notification_deduplication_key_generation`: Verifies deterministic key generation and matching hashes for identical inputs.
- `test_deduplication_suppression`: Verifies that re-dispatching with the same deduplication key suppresses secondary outbound delivery.
