# Transactional Email Provider Integration & Template Engine

## 1. Overview

The Email Notification Channel in Arthsavora provides institutional-grade, transactional messaging for budget breaches, upcoming loan/recurring payments, account anomalies, and critical security notices.

The integration implemented in [email.py](file:///d:/Arthsavora/backend/app/services/notification/channels/email.py) utilizes a provider-independent interface that supports development, offline testing, and production SMTP relays without modifying business logic.

---

## 2. Provider Abstraction Architecture

```python
class BaseEmailProvider(ABC):
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Dispatches email to recipient.
        Returns: (success: bool, provider_message_id: Optional[str], error_message: Optional[str])
        """
        pass
```

### 2.1 Supported Adapters
1. **`MockEmailProvider`**:
   - Stores dispatched emails in memory (`self.sent_emails`).
   - Generates deterministic message identifiers: `mock_mail_{uuid[:12]}`.
   - Default provider during unit/integration tests and development environments without SMTP credentials.
2. **`SmtpEmailProvider`**:
   - Production SMTP client with `STARTTLS` transport encryption.
   - Authenticates via environment configuration (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`).
   - Generates unique reference tokens upon `SMTP.sendmail` completion.

---

## 3. Financial Email Template System

### 3.1 Design Principles
Financial emails require an authoritative, minimalist, and accessible visual hierarchy:
- **Dark-Theme Aesthetics**: Styled with slate foundations (`#090d16`, `#0f172a`, `#1e293b`) mirroring the web application.
- **Severity Color Borders**:
  - `info`: Blue (`#3b82f6`)
  - `success`: Emerald (`#10b981`)
  - `warning`: Amber (`#f59e0b`)
  - `critical`: Red (`#ef4444`)
- **Direct Action Buttons**: Single-click deep links navigating to relevant resources (`/budgets`, `/transactions`, `/anomalies`).

### 3.2 HTML Injection Defenses
All user-generated strings (transaction descriptions, custom budget names, merchant titles) pass through Python's `html.escape()` prior to string interpolation, eliminating Cross-Site Scripting (XSS) and email client injection vulnerabilities.

### 3.3 Plain-Text Fallback
Every outgoing message attaches both `text/html` and `text/plain` multipart MIME parts, guaranteeing readability across legacy clients, terminal email readers (e.g., Mutt), and assistive screen readers.

---

## 4. Configuration Reference

```bash
# Production SMTP Environment Variables
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your_actual_key
SMTP_FROM_EMAIL=notifications@arthsavora.com
FRONTEND_URL=https://app.arthsavora.com
```

---

## 5. Related Documentation

- [Notification Architecture](file:///d:/Arthsavora/docs/NOTIFICATION_ARCHITECTURE.md)
- [Notification Delivery Engine](file:///d:/Arthsavora/docs/NOTIFICATION_DELIVERY_ENGINE.md)
- [Notification Security & Privacy](file:///d:/Arthsavora/docs/NOTIFICATION_SECURITY.md)
