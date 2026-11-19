# Provider Failure and Boundary Error Tests

## 1. Provider Outage Simulation

External provider APIs inevitably experience intermittent outages, rate limits (HTTP 429), gateway timeouts (HTTP 504), and malformed payloads.

ARTHSAVORA was tested under simulated fault conditions across all external integration adapters.

---

## 2. Test Scenarios and Results

| Test ID | Provider | Simulated Fault Condition | System Response & Handling | Recovery Verification | Status |
|---|---|---|---|---|---|
| **FAIL-01** | Account Aggregator | HTTP 504 Gateway Timeout during sync | Background job logs failure; schedules exponential backoff retry at $t+60\text{s}$. | Transaction state untouched; user alerted. | **PASS** |
| **FAIL-02** | Account Aggregator | HTTP 401 Consent Expired or Revoked | Sync marked as `REVOKED`; no further retries scheduled. | UI displays "Consent Expired — Reconnect Bank". | **PASS** |
| **FAIL-03** | OCR Provider | HTTP 429 Rate Limit Exceeded | Circuit breaker enters half-open state; queue switches to local fallback parser. | Upload accepted; processed with fallback heuristics. | **PASS** |
| **FAIL-04** | OCR Provider | Corrupt / Unreadable Image Payload | Service returns HTTP 422 with message "Unable to detect receipt boundaries". | User prompted to upload clearer document. | **PASS** |
| **FAIL-05** | LLM Gateway | Model Timeout (> 15s) | Assistant service terminates request with friendly fallback summary. | UI displays rule-based financial summary. | **PASS** |

---

## 3. Resilience Guarantees

1. **Zero Thread Pool Exhaustion**: All outbound HTTP requests utilize explicit timeouts (`connect=3s`, `read=10s`).
2. **Zero Orphaned Transactions**: Failure to fetch or parse external data never generates partial or half-posted double-entry journal transactions.
