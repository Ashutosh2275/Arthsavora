# Integration Failure Handling and Resilience

## 1. Principles of Resilience

FinTech integration failures (bank timeout, OCR parsing failure, webhook dropped, database disconnect) must never leave financial records in an indeterminate, corrupted, or unrecoverable state.

ARTHSAVORA enforces four resilience principles:
1. **Atomic Commits with Savepoints**: Operations spanning multiple tables or services commit atomically or rollback completely.
2. **Circuit Breakers for External Providers**: Third-party APIs (AA gateways, SMS parsers, OCR endpoints) are guarded by circuit breakers to prevent thread exhaustion during outages.
3. **Idempotent Webhooks & Retries**: All external inbound webhooks require idempotency keys and cryptographic signature verification.
4. **Graceful UI Degradation**: Network or provider failures render informative, non-blocking error banners while maintaining read access to local cached records.

---

## 2. Failure Recovery Matrix

| Failure Mode | Detection Mechanism | Immediate System Action | Recovery Mechanism | User Impact |
|---|---|---|---|---|
| **Database Connection Drop** | Pool heartbeat ping failure | Request aborted with HTTP 503; active transaction rolled back | Automatic connection pool recycling | User presented with retry banner |
| **Unbalanced Journal Submission** | `LedgerService` validation check | Rejects transaction with `UnbalancedJournalError` | Transaction not persisted; diagnostic logged | User sees descriptive validation error |
| **Account Aggregator Timeout** | 10-second gateway HTTP timeout | Sync job marked `FAILED_RETRYABLE`; circuit tripped | Exponential backoff retry (1m, 5m, 15m) | User informed sync is running in background |
| **MIME / Magic Bytes Mismatch** | `python-magic` file header inspection | Upload rejected with HTTP 422 | Temporary file deleted immediately | Error message: "File content does not match extension" |
| **Cross-Tenant IDOR Attempt** | Row-Level Security / Workspace check | Request rejected with HTTP 404 (Not Found) | Security alert logged to audit log | User receives 404 resource not found |

---

## 3. Circuit Breaker Configuration

```python
CIRCUIT_BREAKER_CONFIG = {
    "account_aggregator": {
        "failure_threshold": 5,        # Trip after 5 consecutive failures
        "recovery_timeout_seconds": 60,# Half-open after 60 seconds
        "expected_exceptions": [GatewayTimeoutError, ConnectionRefusedError]
    },
    "ocr_provider": {
        "failure_threshold": 3,
        "recovery_timeout_seconds": 120,
        "expected_exceptions": [ProviderUnavailableError]
    }
}
```
