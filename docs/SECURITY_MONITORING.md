# ARTHSAVORA — Security Monitoring & Telemetry Architecture

## 1. Overview & Objectives

Security monitoring provides real-time visibility into application health, access control events, authentication anomalies, and infrastructure threats.

The monitoring architecture is designed to:
- Detect unauthorized access attempts and privilege escalation immediately.
- Correlate distributed API requests using unique request tracking IDs.
- Sanitize sensitive data from log files (zero passwords, tokens, or PII in logs).
- Maintain audit integrity for statutory compliance and incident investigation.

---

## 2. Structured Telemetry & Correlation IDs

Every inbound HTTP request is assigned a unique correlation ID via `setup_audit_middleware`:
```python
correlation_id = (
    request.headers.get("X-Request-ID")
    or request.headers.get("X-Correlation-ID")
    or str(uuid.uuid4())
)
request.state.correlation_id = correlation_id
```

The correlation ID is:
1. Injected into response headers (`X-Request-ID`).
2. Included in all application log statements.
3. Attached to RFC 7807 error responses for client-side support traceability.
4. Stored in relational audit log records (`AuditLog.correlation_id`).

---

## 3. Log Sanitization & Sensitive Data Redaction

Logging sensitive credentials compromises confidentiality. ARTHSAVORA enforces strict log sanitization:
1. **Query Parameter Scrubbing:** Query strings containing `"password"`, `"token"`, or `"secret"` are redacted to `?[QUERY_REDACTED]`.
2. **Body Filtering:** Request bodies containing passwords, tokens, or bank account numbers are never logged in plaintext.
3. **Zero Credentials in Access Logs:** `audit_request_middleware` logs:
   ```
   HTTP {method} {safe_path} - Status: {status_code} - Latency: {duration_ms}ms - Client: {client_host} - RequestId: {correlation_id}
   ```

---

## 4. Security Event Taxonomy

The platform records security events across four severity classifications:

| Event Type | Trigger | Severity | Action / Alert |
| :--- | :--- | :--- | :--- |
| **AUTH_FAILURE** | Invalid password or unverified user credentials | Warning | Monitored for brute-force thresholds (>5/min triggers 429) |
| **TOKEN_REVOKED_ACCESS** | Attempt to use revoked JWT token | Warning | Session rejected; logged with client IP |
| **IDOR_ATTEMPT** | User attempts to access resource in unauthorized workspace | Warning | Returns 404; security metric incremented |
| **PRIVILEGE_ESCALATION** | Member attempts administrative action (role update, deletion) | High | Returns 403; alert dispatched to workspace owner |
| **MIME_SPOOF_UPLOAD** | Upload payload header does not match magic bytes | High | Upload blocked; file discarded |
| **PROMPT_INJECTION** | User chat query contains adversarial system instructions | Warning | Neutralized; flagged in `assistant_usage_logs` |
| **UNBALANCED_JOURNAL** | Programmatic attempt to post unbalanced debits/credits | Critical | Transaction aborted; integrity alert raised |
| **RATE_LIMIT_EXCEEDED** | Request rate exceeds configured SlowAPI limits | Warning | Returns 429; retry-after header returned |

---

## 5. Centralized Log Retention & CERT-In Alignment

- **Local Development:** Formatted standard output stream via Python `logging`.
- **Production Deployment:** Structured JSON formatted logs streamed to stdout and ingested by cloud log aggregators (AWS CloudWatch, Datadog, or Grafana Loki).
- **Retention Period:** 180 days minimum in Indian cloud data regions (aligned with CERT-In directions of April 2022).
