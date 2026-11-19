# ARTHSAVORA — API Security Standard & Gateway Hardening

## 1. Overview & Policy

All ARTHSAVORA RESTful endpoints conform to this API Security Standard. Security is enforced through global ASGI middleware, centralized exception formatting, Pydantic v2 input validation, explicit CORS origin allowlisting, and rate limiting.

---

## 2. Global Security Headers

Every HTTP response from the ARTHSAVORA API engine includes hardened security headers configured in `app.api.middleware.security_headers`:

| Header Name | Value | Purpose |
| :--- | :--- | :--- |
| `X-Content-Type-Options` | `nosniff` | Prevents browsers from MIME-sniffing the response away from the declared content-type. |
| `X-Frame-Options` | `DENY` | Prevents clickjacking and UI redressing by forbidding embedding within `<iframe>` elements. |
| `X-XSS-Protection` | `0` | Disables legacy buggy XSS auditors in older browsers in favor of modern CSP. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Protects privacy by omitting URL path and query parameters when navigating cross-origin. |
| `Permissions-Policy` | `accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()` | Forbids access to sensitive hardware sensors and device APIs. |
| `X-Permitted-Cross-Domain-Policies` | `none` | Prevents Adobe Flash and PDF viewers from loading cross-domain policy documents. |
| `Cache-Control` | `no-store, no-cache, must-revalidate, max-age=0` (on `/api/*`) | Prevents intermediary proxies and browser disks from caching sensitive financial data. |
| `Pragma` | `no-cache` (on `/api/*`) | HTTP/1.0 backwards-compatible cache prohibition. |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` (on `/api/*`) | Strictly disallows script execution or framing for all API JSON payloads. |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` (when enabled) | Forces HTTPS connections for 1 year, including subdomains. |

---

## 3. Standardized Error Response Schema

API responses never leak internal tracebacks, SQL statements, or infrastructure paths. All exceptions are caught by `setup_exception_handlers` and formatted according to the RFC 7807-compliant JSON schema:

```json
{
  "error": {
    "code": "STANDARD_ERROR_CODE",
    "message": "Human-readable sanitized explanation.",
    "request_id": "uuid-correlation-id",
    "details": []
  }
}
```

### Error Code Taxonomy
- `400`: `BAD_REQUEST`, `VALIDATION_ERROR`
- `401`: `UNAUTHORIZED`, `AUTHENTICATION_REQUIRED`, `INVALID_CREDENTIALS`, `INVALID_TOKEN`, `TOKEN_EXPIRED`
- `403`: `FORBIDDEN`, `INSUFFICIENT_PERMISSIONS`, `MEMBERSHIP_INACTIVE`, `WORKSPACE_SUSPENDED`
- `404`: `NOT_FOUND`
- `409`: `CONFLICT`, `EMAIL_ALREADY_REGISTERED`, `JOURNAL_ALREADY_POSTED`
- `422`: `REQUEST_VALIDATION_ERROR`
- `429`: `RATE_LIMIT_EXCEEDED`
- `500`: `INTERNAL_SERVER_ERROR`

---

## 4. Input Validation & Typed Schemas

1. **Pydantic v2 Parsing:** Every API endpoint defines strict Pydantic v2 request schemas. Extra unexpected fields are rejected or ignored.
2. **Numeric Precision:** Monetary inputs require positive decimal numbers with valid currency codes.
3. **Safe Pagination:** List endpoints enforce bounded pagination: `limit: int = Query(50, ge=1, le=100)` and `offset: int = Query(0, ge=0)`. Unbounded queries (`limit=ALL`) are prohibited.
4. **UUID Parsing:** All entity IDs (`workspace_id`, `account_id`, `transaction_id`, etc.) are validated as cryptographic UUIDs. Invalid strings return 422 validation errors before hitting the database.

---

## 5. Rate Limiting Policy

Rate limiting is governed by SlowAPI and keyed by authenticated user ID (or client IP for unauthenticated routes):

| Route Group | Limit | Key Func | Purpose |
| :--- | :--- | :--- | :--- |
| **Authentication (`/auth/login`, `/auth/register`)** | `5/minute` | Remote IP | Brute force and credential stuffing defense |
| **Document Upload (`/documents/upload`)** | `30/minute` | User ID / IP | Resource exhaustion & disk protection |
| **AI Assistant (`/assistant/chat`)** | `20/minute` | User ID / IP | LLM token usage and cost bounds |
| **General Financial APIs (`/api/v1/*`)** | `120/minute` | User ID / IP | Abuse prevention and availability protection |
| **Health Probes (`/health`, `/api/v1/health/*`)** | `300/minute` | Remote IP | Kubernetes / monitoring uptime headroom |

---

## 6. CORS Configuration

- Configured explicitly via `setup_cors(app)`.
- Disallows wildcard origins with credentials (`Access-Control-Allow-Origin: *` + `Allow-Credentials: true` is forbidden by W3C and blocked by the server).
- Allowed origins are restricted to configured client applications (`localhost:5173`, `localhost:3000`, and authorized production domains).
- Production startup validator aborts with `ValueError` if `*` is detected in `settings.CORS_ORIGINS`.
