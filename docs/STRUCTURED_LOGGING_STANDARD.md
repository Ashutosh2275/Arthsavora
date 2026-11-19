# ARTHSAVORA — Structured Logging Standard and PII Sanitization

## 1. Specification and Schema

In staging and production environments, ARTHSAVORA emits single-line JSON log objects formatted by `StructuredJsonFormatter` in `backend/app/core/logging.py`.

```json
{
  "timestamp": "2026-11-19T10:12:20.123456+00:00",
  "level": "INFO",
  "service": "ARTHSAVORA",
  "environment": "production",
  "logger": "ARTHSAVORA",
  "message": "HTTP POST /api/v1/transactions - Status: 201 - Latency: 24.50ms - Client: 10.0.1.25 - RequestId: c3b91a27-7f41-4882-9cf1-2292fca3b302",
  "module": "audit",
  "line": 42,
  "request_id": "c3b91a27-7f41-4882-9cf1-2292fca3b302",
  "workspace_id": "8f7e2c91-1234-4567-890a-bcdef0123456"
}
```

## 2. Automated PII & Credential Scrubbing Engine

In accordance with the Indian Digital Personal Data Protection (DPDP) Act 2023 and RBI cybersecurity guidelines, sensitive financial information must NEVER appear in application logs.

The `sanitize_value` utility in `backend/app/core/logging.py` intercepts log payloads and redacts:

1. **Explicit Key Matching**: Any dictionary key matching the following triggers replacement with `[REDACTED]`:
   - `password`, `secret`, `token`, `access_token`, `refresh_token`, `api_key`
   - `authorization`, `cookie`, `pan`, `aadhaar`, `cvv`, `card_number`, `account_number`
2. **Regex Pattern Matching**:
   - Authorization Bearer tokens: `Bearer eyJ...` -> `Bearer [REDACTED]`
   - Payment Card PANs: 16-digit card numbers -> `****-****-****-****`
3. **Query Parameter Scrubbing**:
   - `request.url.query` containing sensitive keys is scrubbed into `?[QUERY_REDACTED]`.

## 3. Log Levels and Retention Policy

| Log Level | Purpose | Target Destinations | Retention Period |
| :--- | :--- | :--- | :--- |
| **DEBUG** | Local development diagnostics | Stdout (Disabled in Prod) | 0 Days |
| **INFO** | HTTP requests, state transitions, job completions | CloudWatch / Datadog | 30 Days |
| **WARNING** | Retries, degraded external services, rate limit hits | CloudWatch / Datadog | 90 Days |
| **ERROR** | Unhandled exceptions, 5xx responses, DB timeouts | CloudWatch / Sentry | 180 Days |
| **AUDIT** | Security events, login, permission changes, ledger posts | Dedicated WORM S3 Bucket | 7 Years (Compliance) |

## 4. Cross-Reference Links
- Observability Architecture: [OBSERVABILITY_ARCHITECTURE.md](file:///d:/Arthsavora/docs/OBSERVABILITY_ARCHITECTURE.md)
- Alerting and Escalation: [ALERTING_AND_ESCALATION.md](file:///d:/Arthsavora/docs/ALERTING_AND_ESCALATION.md)
