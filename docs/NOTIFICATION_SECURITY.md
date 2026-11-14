# ARTHSAVORA Notification Security, Privacy & Anti-IDOR Architecture

## 1. Executive Summary

Financial notifications carry sensitive information regarding account activity, balances, transaction parties, and security events. If misconfigured, notification systems can become attack vectors for Insecure Direct Object References (IDOR), credential leakage, cross-site scripting (XSS), or lock-screen privacy violations.

ARTHSAVORA enforces strict security invariants across the entire notification lifecycle:
1. Complete anti-IDOR isolation at the repository and routing layers.
2. Zero credential storage and automated payload masking.
3. Strict HTML escaping in email and template rendering engines.
4. Privacy-preserving lock-screen push payloads.
5. High-priority security bypass for non-silenceable account protection events.

---

## 2. Anti-IDOR & User Scoping Protections

### 2.1 Repository-Level Scoping
All notification retrieval, modification, batch marking as read, and deletion operations mandate the authenticated user's ID (`recipient_user_id`):

```python
# In NotificationRepository
async def get_by_id(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
    stmt = (
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
        )
    )
    result = await self.db.execute(stmt)
    return result.scalars().first()
```

Users can never view, mark as read, or modify notification records belonging to another user or workspace member without explicit authorization.

### 2.2 Role-Based Access Control (RBAC)
Two dedicated permissions govern notification interactions:
- `notifications:view`: Grants permission to view the notification inbox, unread counts, and stream events via SSE.
- `notifications:manage`: Grants permission to update notification preferences, register push subscriptions, and dismiss/archive alerts.

These permissions are mapped across all platform roles (`viewer`, `member`, `admin`, `owner`) in personal, family, and business workspaces in `backend/app/core/permissions.py`.

---

## 3. Data Sanitization & Credential Protection

### 3.1 Zero Credential Policy
ARTHSAVORA strictly prohibits the transmission, logging, or storage of:
- Full Primary Account Numbers (PANs) / Credit card numbers.
- Card Verification Values (CVV / CVC).
- One-Time Passwords (OTPs) and PINs.
- Plaintext account passwords or authentication tokens.

### 3.2 Defensive Regex Scrubber
The domain model includes `mask_sensitive_financial_payload`, which scrub outbound notification titles and bodies before storage and transmission:

```python
def mask_sensitive_financial_payload(text: str) -> str:
    # Mask 16-digit card patterns -> **** **** **** 1234
    text = re.sub(r"\b([0-9]{4})[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})\b", r"**** **** **** \4", text)
    # Mask CVV mentions
    text = re.sub(r"\bCVV[\s\:\=]*[0-9]{3,4}\b", "CVV: ***", text, flags=re.IGNORECASE)
    # Mask OTP / PIN
    text = re.sub(r"\b(OTP|PIN|MPIN)[\s\:\=]*[0-9]{4,6}\b", r"\1: ******", text, flags=re.IGNORECASE)
    return text
```

---

## 4. Email Security & Template Sanitization

### 4.1 HTML Injection & XSS Prevention
When rendering transactional HTML emails in `backend/app/services/notification/channels/email.py`:
- All user-supplied text (such as transaction notes, merchant names, or budget labels) is passed through `html.escape()` prior to string interpolation.
- No dynamic `eval()` or unconstrained template execution is permitted.

### 4.2 Transport Security & Authentication
Outbound SMTP deliveries mandate:
- TLS 1.3 / STARTTLS encryption.
- Verification of SPF, DKIM, and DMARC aligned sender domains.
- Unsubscribe headers (`List-Unsubscribe`) for non-critical notification types.

---

## 5. Web Push & Lock-Screen Privacy

### 5.1 RFC 8292 / VAPID Compliance
Web push messages use end-to-end payload encryption following RFC 8291 / RFC 8292 with user-specific `p256dh` public keys and `auth` secrets. Push payloads are encrypted before dispatching to browser push services (e.g., Google FCM, Apple Push Notification service, Mozilla Push Service).

### 5.2 Lock-Screen Privacy Defense
Push notifications displayed on locked device screens could inadvertently expose sensitive account balances to shoulder-surfing bystanders.
- **Push Preview Sanitization:** Push payloads contain high-level actionable alerts (e.g., *"Unusual spending detected on your card"*) without displaying account balances or net worth figures on the lock screen.
- Deep-links (`action_url`) route the user to authenticate before revealing granular financial breakdowns in the web or mobile app.

---

## 6. Security Alert Invariants

Security-related notifications (`NotificationCategory.SECURITY` and `NotificationEventType.SECURITY_*`):
1. **Never Silenced:** Bypass all user-defined quiet-hour schedules.
2. **Mandatory Delivery:** Dispatched immediately across In-App and Email channels regardless of channel preference silencers.
3. **Audit Trail:** Retained permanently in the security audit ledger to support forensics and incident response.
