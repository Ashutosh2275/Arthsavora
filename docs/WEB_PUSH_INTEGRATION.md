# Web Push & PWA Notification Integration (VAPID)

## 1. Executive Summary

Arthsavora provides browser-level Web Push notifications conforming to W3C standards and RFC 8292 Voluntary Application Server Identification (VAPID). This enables users on modern desktop browsers (Chrome, Edge, Firefox, Safari 16+) to receive real-time financial alerts even when the application tab is closed.

Implemented in [web_push.py](file:///d:/Arthsavora/backend/app/services/notification/channels/web_push.py) and [useNotificationStore.ts](file:///d:/Arthsavora/apps/web/src/store/useNotificationStore.ts).

---

## 2. Web Push Architecture Flow

```
[User Clicks "Enable Push"]
           │
           ▼
[Browser Permission Prompt] ──(Denied)──> [Permission State: 'denied' (Stop)]
           │ (Granted)
           ▼
[ServiceWorker Registration]
           │
           ▼
[PushManager.subscribe(VAPID_PUBLIC_KEY)]
           │
           ▼
[Obtain PushSubscription (endpoint, p256dh, auth)]
           │
           ▼
[POST /api/v1/notifications/push-subscriptions]
           │
           ▼
[Stored in PostgreSQL: push_subscriptions]
           │
           ▼
[Outbound Event Dispatched]
           │
           ▼
[WebPushProvider: Encrypt Payload & Transmit to Browser Push Service]
```

---

## 3. Provider Abstraction

```python
class BasePushProvider(ABC):
    @abstractmethod
    async def send_push(
        self,
        subscription: PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        pass
```

### 3.1 Implementations
1. **`MockPushProvider`**:
   - Records outbound pushes in memory (`self.dispatched_pushes`).
   - Generates deterministic message references: `mock_vapid_{hash}`.
   - Enforces payload sanitization during testing.
2. **`WebPushProvider`**:
   - Production adapter integrating with `pywebpush`.
   - Uses VAPID ECDSA prime256v1 private keys and claims subject.
   - Handles HTTP 410 Gone responses by deactivating expired subscriptions.

---

## 4. Lock-Screen Privacy Safeguards

Push notifications display on lock screens and system notifications banners where bystanders could view sensitive information.

The push channel actively scrubs sensitive data:
- **Card Numbers**: Replaced with masked representation (`**** **** **** 1234`).
- **CVVs and Passwords**: Actively redacted.
- **Account Balances**: Titles focus on category names and percentages (e.g., "Budget Alert: Dining at 90%") rather than raw account balance amounts where possible.

---

## 5. Subscription Lifecycle Management

- **Registration**: `POST /api/v1/notifications/push-subscriptions`
  - Validates `endpoint`, `p256dh_key`, and `auth_key`.
  - Upserts subscription row mapped to `current_user.id`.
- **Listing**: `GET /api/v1/notifications/push-subscriptions`
- **Revocation**: `DELETE /api/v1/notifications/push-subscriptions/{subscription_id}`
  - Soft-deactivates the subscription record (`is_active = False`).

---

## 6. Related Documentation

- [Notification Architecture](file:///d:/Arthsavora/docs/NOTIFICATION_ARCHITECTURE.md)
- [Notification Delivery Engine](file:///d:/Arthsavora/docs/NOTIFICATION_DELIVERY_ENGINE.md)
- [Notification Security & Privacy](file:///d:/Arthsavora/docs/NOTIFICATION_SECURITY.md)
