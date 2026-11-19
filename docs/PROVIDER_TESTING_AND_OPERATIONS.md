# ARTHSAVORA Financial Provider Testing & Operations Runbook

## 1. Test Suite Architecture

The financial connection and aggregation subsystem is covered by automated unit, integration, RBAC security, AI tool, and frontend test suites.

### 1.1 Backend Test Matrix (`backend/tests/test_financial_connections.py`)
1. **`test_pure_domain_account_masking`**: Verifies masking logic across various input formats, strings, and lengths.
2. **`test_pure_domain_normalize_direction`**: Verifies conversion of diverse debit/credit labels into canonical `inflow` / `outflow` directions and positive paise amounts.
3. **`test_pure_domain_reconciliation_variance`**: Validates variance calculation, status thresholds (`matched`, `variance_detected`, `critical_discrepancy`), and Indian currency formatting.
4. **`test_pure_domain_connection_health`**: Verifies health transitions based on failure counts, elapsed days, and consent expiration.
5. **`test_pure_domain_consent_validity`**: Verifies active window evaluation against UTC boundaries.
6. **`test_provider_registry`**: Verifies provider registration, catalog retrieval, and singleton adapter resolution.
7. **`test_mock_sandbox_adapter_flow`**: Validates complete mock sandbox lifecycle without database dependencies.
8. **`test_financial_connection_full_lifecycle`**: End-to-end integration test against live PostgreSQL test database: initiate -> authorize -> discover -> link -> sync -> idempotent repeat sync -> reconcile -> revoke -> disconnect.
9. **`test_financial_connections_api_and_rbac`**: Validates all FastAPI endpoints with JWT authentication, tenant headers, and RBAC permission checks.
10. **`test_ai_assistant_connection_tools`**: Verifies that the AI Assistant can query live connection overviews, health statuses, and reconciliation summaries via registered tools.

### 1.2 Frontend Test Matrix (`apps/web/src/pages/__tests__/FinancialConnections.test.tsx`)
1. Page header and summary KPI metrics rendering.
2. Connected account cards with health badges and balances.
3. Empty state handling when no accounts are connected.
4. Tab navigation between Accounts, Providers, Details, History, and Reconciliation.
5. Modal workflows: Connect Institution, Link Discovered Account, Disconnect Confirmation.
6. Action triggers: Manual Sync dispatch.

---

## 2. Operational Monitoring & Health Indicators

Operators should monitor the following telemetry baselines:
- **`sync_failure_count`**: Alert if any connection exceeds 3 consecutive failures.
- **Provider API Latency**: Normal P95 latency is < 800ms for Account Aggregator handoffs.
- **Critical Discrepancy Rate**: Flag if more than 5% of reconciliations report `critical_discrepancy` (indicates upstream feed drift or unmapped transaction types).
- **Consent Expiration Rate**: Automated email reminders are dispatched at $T-14$ days and $T-3$ days prior to `expires_at`.

---

## 3. Production Onboarding & Provider Deployment Checklist

Before enabling live Account Aggregator feeds in production:
- [ ] Complete commercial and regulatory agreement with authorized TSP / NBFC-AA (e.g. Setu, OneMoney).
- [ ] Provision production Mutual TLS (mTLS) client certificates and upload to ARTHSAVORA secure secret store (never in Git).
- [ ] Set `ARTHSAVORA_AA_CLIENT_ID` and `ARTHSAVORA_AA_CLIENT_SECRET` environment variables.
- [ ] Update `FinancialProvider.status` from `unconfigured` to `active` in production database.
- [ ] Configure webhook listener URL in provider portal to receive real-time consent approval callbacks.
- [ ] Verify Diffie-Hellman / ECDH decryption keys for inbound encrypted FI payloads.
