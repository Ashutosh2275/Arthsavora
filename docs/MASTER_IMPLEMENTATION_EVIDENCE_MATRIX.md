# Master Implementation Evidence Matrix

## 1. Overview

This matrix provides comprehensive, direct traceability between every functional domain of ARTHSAVORA, its concrete source implementation files, and the automated tests proving its correctness.

---

## 2. Domain-by-Domain Implementation & Test Evidence

### 2.1 Workspace Multi-Tenancy & Authorization
- **Domain Models:** `backend/app/domain/workspace.py`
- **Database Models:** `backend/app/infrastructure/database/models.py` (`Workspace`, `WorkspaceMember`, `User`)
- **Service Layer:** `backend/app/services/workspace_service.py`
- **API Endpoints:** `backend/app/api/v1/workspaces.py`
- **Security Enforcement:** `backend/app/core/dependencies.py` (`get_current_workspace`, `require_workspace_role`)
- **Automated Tests:**
  - `backend/tests/test_workspace_service.py`
  - `backend/tests/test_security_hardening.py`
  - `backend/tests/test_system_integration_e2e_qa.py::test_cross_tenant_idor_protection_returns_404`

### 2.2 Identity & Session Authentication
- **Service Layer:** `backend/app/services/auth_service.py` (Argon2id hashing, sliding session, token revocation)
- **Security Utilities:** `backend/app/core/security.py` (JWT issuance, verification, password hashing)
- **API Endpoints:** `backend/app/api/v1/auth.py` (`/register`, `/login`, `/refresh`, `/logout`, `/me`)
- **Frontend Store:** `apps/web/src/stores/useAuthStore.ts`
- **Automated Tests:**
  - `backend/tests/test_auth_service.py`
  - `backend/tests/test_security.py`
  - `apps/web/src/pages/__tests__/Login.test.tsx`

### 2.3 Financial Accounts Management & Lifecycle
- **Domain Models:** `backend/app/domain/account.py` (Account types: `SAVINGS`, `CURRENT`, `CREDIT_CARD`, `LOAN`, `INVESTMENT`)
- **Service Layer:** `backend/app/services/account_service.py` (IFSC validation, account lifecycle)
- **API Endpoints:** `backend/app/api/v1/accounts.py`
- **Frontend UI:** `apps/web/src/pages/Accounts.tsx`, `apps/web/src/components/accounts/`
- **Automated Tests:**
  - `backend/tests/test_account_service.py`
  - `apps/web/src/pages/__tests__/Accounts.test.tsx`

### 2.4 Transaction Engine & Deduplication
- **Domain Models:** `backend/app/domain/transaction.py` (`PENDING`, `CLEARED`, `RECONCILED`)
- **Service Layer:** `backend/app/services/transaction_service.py` (hash deduplication, transaction linking)
- **API Endpoints:** `backend/app/api/v1/transactions.py`
- **Frontend UI:** `apps/web/src/pages/Transactions.tsx`, `apps/web/src/components/transactions/`
- **Automated Tests:**
  - `backend/tests/test_transaction_service.py`
  - `apps/web/src/pages/__tests__/Transactions.test.tsx`

### 2.5 Double-Entry General Ledger & Balance Derivation
- **Domain Models:** `backend/app/domain/ledger.py` (`JournalEntry`, `JournalLine`, `AccountType`, `DebitCredit`)
- **Service Layer:** `backend/app/services/ledger/ledger_service.py` ($\sum D == \sum C$ validation, posting, balance derivation)
- **Database Triggers:** PostgreSQL trigger enforcing zero-sum line totals
- **API Endpoints:** `backend/app/api/v1/ledger.py`
- **Automated Tests:**
  - `backend/tests/test_ledger_service.py`
  - `backend/tests/test_financial_integrity.py`
  - `backend/tests/test_system_integration_e2e_qa.py::test_unbalanced_journal_post_rejected_by_service`

### 2.6 Bank Statement Parsing & Ingestion Pipeline
- **Parsers:** `backend/app/services/importers/` (HDFC, ICICI, SBI statement parsers, CSV/XLSX)
- **Service Layer:** `backend/app/services/import_service.py` (file mapping, fuzzy deduplication, batch staging)
- **API Endpoints:** `backend/app/api/v1/imports.py`
- **Frontend UI:** `apps/web/src/pages/Import.tsx`
- **Automated Tests:**
  - `backend/tests/test_import_service.py`
  - `apps/web/src/pages/__tests__/Import.test.tsx`

### 2.7 Categorization Engine & Merchant Intelligence
- **Rule Engine:** `backend/app/services/intelligence/rule_engine.py` (UPI VPA, POS pattern matching)
- **ML Classifier:** `backend/app/services/intelligence/ml_classifier.py` (TF-IDF + Logistic Regression)
- **Service Layer:** `backend/app/services/intelligence/categorization_service.py`
- **API Endpoints:** `backend/app/api/v1/categorization.py`
- **Automated Tests:**
  - `backend/tests/test_categorization_service.py`
  - `backend/tests/test_merchant_intelligence.py`

### 2.8 Budgeting, Goal Tracking & Threshold Alerts
- **Domain Models:** `backend/app/domain/budget.py`, `backend/app/domain/goal.py`
- **Service Layer:** `backend/app/services/budget/budget_service.py`, `backend/app/services/budget/goal_service.py`
- **Alert Dispatch:** Automated notifications when consumption reaches 80% and 100%
- **API Endpoints:** `backend/app/api/v1/budgets.py`, `backend/app/api/v1/goals.py`
- **Frontend UI:** `apps/web/src/pages/Budgets.tsx`, `apps/web/src/pages/Goals.tsx`
- **Automated Tests:**
  - `backend/tests/test_budget_service.py`
  - `apps/web/src/pages/__tests__/Budgets.test.tsx`
  - `apps/web/src/pages/__tests__/Goals.test.tsx`

### 2.9 Recurring Commitments & Subscription Calendar
- **Domain Models:** `backend/app/domain/recurring.py` (frequencies, leap-day logic, status)
- **Service Layer:** `backend/app/services/recurring/recurring_service.py`, `backend/app/services/recurring/recurrence_engine.py`
- **API Endpoints:** `backend/app/api/v1/recurring.py`
- **Frontend UI:** `apps/web/src/pages/Recurring.tsx`
- **Automated Tests:**
  - `backend/tests/test_recurring_service.py`
  - `backend/tests/test_recurrence_engine.py`
  - `apps/web/src/pages/__tests__/Recurring.test.tsx`

### 2.10 Cash Flow Forecasting & Analytics
- **Forecasting Engine:** `backend/app/services/forecasting/forecasting_service.py` (Holt-Winters exponential smoothing)
- **Analytics Service:** `backend/app/services/analytics/analytics_service.py` (cash flow velocity, burn rate, net worth)
- **API Endpoints:** `backend/app/api/v1/forecasting.py`, `backend/app/api/v1/analytics.py`
- **Frontend UI:** `apps/web/src/pages/Forecast.tsx`, `apps/web/src/pages/Analytics.tsx`
- **Automated Tests:**
  - `backend/tests/test_forecast_service.py`
  - `backend/tests/test_analytics_service.py`
  - `apps/web/src/pages/__tests__/Forecast.test.tsx`

### 2.11 Anomaly Detection & Financial Risk Intelligence
- **Statistical Model:** `backend/app/services/anomaly/detection_service.py` (Z-score and IQR outliers, velocity anomalies)
- **API Endpoints:** `backend/app/api/v1/anomalies.py`
- **Frontend UI:** `apps/web/src/pages/Anomalies.tsx`
- **Automated Tests:**
  - `backend/tests/test_anomaly_service.py`
  - `apps/web/src/pages/__tests__/Anomalies.test.tsx`

### 2.12 Financial AI Assistant & Tool Sandboxing
- **Assistant Service:** `backend/app/services/assistant/assistant_service.py`
- **Tool Sandbox:** `backend/app/services/assistant/tool_registry.py`, `tool_executor.py`
- **Prompt Sanitizer:** `backend/app/services/assistant/sanitizer.py` (injection detection, PII redacting)
- **API Endpoints:** `backend/app/api/v1/assistant.py`
- **Frontend UI:** `apps/web/src/pages/Assistant.tsx`, `apps/web/src/components/assistant/`
- **Automated Tests:**
  - `backend/tests/test_assistant_service.py`
  - `apps/web/src/pages/__tests__/Assistant.test.tsx`

### 2.13 Document Processing, OCR & Spoofing Defense
- **Service Layer:** `backend/app/services/document/document_service.py`
- **Magic Bytes Validator:** Binary signature validation (PDF, PNG, JPEG, TIFF)
- **Extractor:** `backend/app/services/document/field_extractor.py` (GSTIN, total amount, date)
- **API Endpoints:** `backend/app/api/v1/documents.py`
- **Frontend UI:** `apps/web/src/pages/Documents.tsx`
- **Automated Tests:**
  - `backend/tests/test_document_service.py`
  - `apps/web/src/pages/__tests__/Documents.test.tsx`

### 2.14 Unified Notification Engine
- **Service Layer:** `backend/app/services/notification/notification_service.py`
- **Preference Center:** `backend/app/services/notification/preference_service.py`
- **API Endpoints:** `backend/app/api/v1/notifications.py`
- **Frontend UI:** `apps/web/src/pages/Notifications.tsx`
- **Automated Tests:**
  - `backend/tests/test_notification_service.py`
  - `apps/web/src/pages/__tests__/Notifications.test.tsx`

### 2.15 Family Collaborative Household Finance
- **Service Layer:** `backend/app/services/family_service.py` (shared budgets, split tracking, individual account privacy)
- **API Endpoints:** `backend/app/api/v1/family.py`
- **Frontend UI:** `apps/web/src/pages/Family.tsx`
- **Automated Tests:**
  - `backend/tests/test_family_finance_service.py`
  - `apps/web/src/pages/__tests__/Family.test.tsx`

### 2.16 Small Business Invoicing & GST Operations
- **Service Layer:** `backend/app/services/business_service.py` (B2B client management, invoice generation, GST calculation)
- **API Endpoints:** `backend/app/api/v1/business.py`
- **Frontend UI:** `apps/web/src/pages/Business.tsx`
- **Automated Tests:**
  - `backend/tests/test_business_service.py`
  - `apps/web/src/pages/__tests__/Business.test.tsx`

### 2.17 Account Aggregator (ReBIT Adapter Architecture)
- **Client & Adapters:** `backend/app/services/financial_providers/` (`AccountAggregatorAdapter`, `MockAccountAggregatorAdapter`)
- **Service Layer:** `backend/app/services/financial_connection_service.py`
- **API Endpoints:** `backend/app/api/v1/financial_connections.py`
- **Frontend UI:** `apps/web/src/pages/FinancialConnections.tsx`
- **Automated Tests:**
  - `backend/tests/test_aa_service.py`
  - `apps/web/src/pages/__tests__/FinancialConnections.test.tsx`

### 2.18 Financial Reporting & Indian Tax Intelligence (Sec 115BAC)
- **Service Layer:** `backend/app/services/financial_reporting_service.py` (P&L, Balance Sheet, Cash Flow, Tax Slabs)
- **API Endpoints:** `backend/app/api/v1/financial_reports.py`
- **Frontend UI:** `apps/web/src/pages/FinancialReports.tsx`
- **Automated Tests:**
  - `backend/tests/test_financial_reporting.py`
  - `apps/web/src/pages/__tests__/FinancialReports.test.tsx`

### 2.19 Progressive Web App & Offline Experience
- **Manifest:** `apps/web/public/manifest.json`
- **Service Worker:** `apps/web/src/pwa/` (`registerSW.ts`, `sw.ts`)
- **State Store:** `apps/web/src/stores/usePwaStore.ts`
- **UI Components:** `apps/web/src/components/pwa/OfflineBanner.tsx`, `InstallPromptModal.tsx`
- **Automated Tests:**
  - `apps/web/src/stores/__tests__/usePwaStore.test.ts`
  - `apps/web/src/components/pwa/__tests__/InstallPromptModal.test.tsx`
