"""
Arthsavora Email Notification Channel Adapter
Provider-independent email delivery with HTML template rendering, plain-text fallback,
and deterministic mock adapter for test suites.
"""

from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html
import logging
import os
import smtplib
from typing import Any, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class BaseEmailProvider(ABC):
    """Abstract contract for transactional email delivery."""

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


class MockEmailProvider(BaseEmailProvider):
    """Deterministic, in-memory email provider for testing and environments without SMTP."""

    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        msg_id = f"mock_mail_{uuid.uuid4().hex[:12]}"
        self.sent_emails.append({
            "id": msg_id,
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "text": text_body,
        })
        logger.info(f"[MockEmailProvider] Dispatched email '{subject}' to '{to_email}' (ref={msg_id})")
        return True, msg_id, None


class SmtpEmailProvider(BaseEmailProvider):
    """Production SMTP adapter with TLS/SSL."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.host = host or os.getenv("SMTP_HOST", "localhost")
        self.port = int(port or os.getenv("SMTP_PORT", 587))
        self.username = username or os.getenv("SMTP_USER")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("SMTP_FROM_EMAIL", "notifications@arthsavora.com")
        self.use_tls = use_tls

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())

            provider_ref = f"smtp_{uuid.uuid4().hex[:12]}"
            return True, provider_ref, None
        except Exception as exc:
            logger.error(f"[SmtpEmailProvider] Failed to send email to {to_email}: {exc}")
            return False, None, str(exc)


def render_financial_email_template(
    title: str,
    message: str,
    severity: str = "info",
    action_url: Optional[str] = None,
    action_label: Optional[str] = "View in Arthsavora",
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Renders safe, accessible, branded HTML email and matching plain-text fallback.
    Scrubs HTML injection vulnerabilities from user text.
    """
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    app_url = os.getenv("FRONTEND_URL", "https://app.arthsavora.com")
    full_action_url = f"{app_url}{action_url}" if action_url else app_url

    # Severity border colors
    severity_colors = {
        "info": "#3b82f6",
        "success": "#10b981",
        "warning": "#f59e0b",
        "critical": "#ef4444",
    }
    accent_color = severity_colors.get(severity.lower(), "#3b82f6")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #090d16; color: #f8fafc;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #0f172a; border-radius: 12px; border: 1px solid #1e293b; overflow: hidden;">
    <tr>
      <td style="padding: 24px; border-bottom: 2px solid {accent_color};">
        <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.02em;">ARTHSAVORA</h1>
        <p style="margin: 4px 0 0; font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Commercial Financial Intelligence</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 28px 24px;">
        <h2 style="margin: 0 0 16px; font-size: 18px; font-weight: 600; color: #f8fafc;">{safe_title}</h2>
        <div style="font-size: 14px; line-height: 1.6; color: #cbd5e1; margin-bottom: 24px;">
          {safe_message}
        </div>
        <table border="0" cellspacing="0" cellpadding="0">
          <tr>
            <td align="center" style="border-radius: 8px; background-color: #4f46e5;">
              <a href="{full_action_url}" target="_blank" style="font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; display: inline-block;">
                {html.escape(action_label)} &rarr;
              </a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    <tr>
      <td style="padding: 20px 24px; background-color: #0b1120; border-top: 1px solid #1e293b; font-size: 12px; color: #64748b; line-height: 1.5;">
        <p style="margin: 0 0 8px;">This is an automated notification from ARTHSAVORA. Please do not reply directly to this email.</p>
        <p style="margin: 0;">Manage your notification preferences anytime from your workspace settings.</p>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    text_content = f"""ARTHSAVORA — FINANCIAL UPDATE
--------------------------------------------------
{title}

{message}

Action: {full_action_url}

--------------------------------------------------
Manage your notification preferences from your workspace settings.
"""

    return html_content, text_content
