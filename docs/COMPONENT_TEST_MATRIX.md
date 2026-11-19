# Component Testing Matrix [Post-Audit QA]

## 1. Overview

This matrix inventories every component across categories A through U, mapping test items to specific test modules, asserting expected behavior, and recording actual verification outcomes.

---

## 2. Exhaustive Component Testing Matrix

### Category A: Identity and Authentication

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| User Registration | `test_auth_api.py`, `test_identity_and_profiles.py` | New user created with hashed password, personal workspace initialized | User created, default workspace seeded with chart of accounts | **PASS** |
| User Login | `test_auth_api.py` | Valid credentials return JWT access + refresh tokens | Tokens returned in standard envelope with user profile | **PASS** |
| Invalid Credentials | `test_auth_api.py` | Wrong password returns HTTP 401 Unauthorized | Returns 401 with `INVALID_CREDENTIALS` error code | **PASS** |
| Password Hashing | `test_security.py` | Argon2id memory-hard parameters ($m=65536, t=3, p=4$) | Verified Argon2id format `$argon2id$v=19$m=65536...` | **PASS** |
| Access Token Expiry | `test_security.py` | Expired token rejected with HTTP 401 | `TokenExpiredException` raised and handled | **PASS** |
| Refresh Token Rotation | `test_auth_api.py` | Refreshing issues new access token; old token revoked | New access token issued; sliding window updated | **PASS** |
| Token Revocation | `test_security.py` | JTI blacklisted in Redis; subsequent calls rejected | Blacklisted JTI immediately rejected | **PASS** |
| User Logout | `test_auth_api.py` | Session invalidated; refresh token revoked | JTI added to blacklist; cookies cleared | **PASS** |
| Suspended Users | `test_auth_api.py` | `is_active=False` blocks login and API access | Returns HTTP 403 `ACCOUNT_INACTIVE` | **PASS** |
| Deleted Users | `test_identity_and_profiles.py` | Soft-deleted users cannot authenticate | Queries filter out soft-deleted users | **PASS** |
| Session Restoration | `test_auth_api.py` | Valid refresh token restores active session | Returns active user and current workspace context | **PASS** |
| Rate Limiting | `test_auth_api.py` | Burst requests trigger HTTP 429 Too Many Requests | SlowAPI limits burst authentication attempts | **PASS** |

### Category B: Workspace and Multi-Tenancy

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Personal Workspace Creation | `test_workspace_management.py` | Default personal workspace provisioned on signup | Personal workspace created with OWNER role | **PASS** |
| Family Workspace Creation | `test_family_finance.py` | Family workspace with shared budget support | Provisioned with household member invitations | **PASS** |
| Business Workspace Creation | `test_business_finance.py` | Business workspace with GST configuration | Provisioned with B2B invoicing and ledger accounts | **PASS** |
| Workspace Switching | `test_workspace_management.py` | User context switches workspace; data prunes | Session updates active workspace ID | **PASS** |
| Membership Lifecycle | `test_memberships_and_invitations.py` | Member invited, accepted, and roles assigned | State transitions: `invited` $\rightarrow$ `active` | **PASS** |
| Role Permissions (RBAC) | `test_authorization.py` | VIEWER cannot mutate; ADMIN/OWNER can mutate | 403 Forbidden raised for unauthorized mutation | **PASS** |
| Cross-Workspace IDOR | `test_system_integration_e2e_qa.py` | Requesting foreign workspace entity returns HTTP 404 | Returns 404 Not Found (Zero entity discovery) | **PASS** |
| PostgreSQL Kernel RLS | `test_security_hardening.py` | `SET LOCAL app.current_workspace_id` isolates rows | Raw SQL queries return 0 rows for other tenants | **PASS** |
| Connection Pool Isolation | `test_security_hardening.py` | Resetting context prevents cross-request leakage | `SET LOCAL` automatically cleared on commit | **PASS** |

### Category C: Accounts and Transactions

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Account Creation | `test_financial_accounts.py` | Create savings/current/card account with IFSC validation | Account created with validated IFSC bank metadata | **PASS** |
| Opening Balances | `test_financial_accounts.py` | Opening balance credited as integer paise | Stored as exact integer paise in `opening_balance_paise` | **PASS** |
| Income Transactions | `test_financial_transactions.py` | Inflow transactions increase available balance | Stored with `direction="inflow"`; balance incremented | **PASS** |
| Expense Transactions | `test_financial_transactions.py` | Outflow transactions decrease available balance | Stored with `direction="outflow"`; balance decremented | **PASS** |
| Account Transfers | `test_financial_transactions.py` | Dual transactions created and linked via `transfer_id` | Source debited, destination credited atomically | **PASS** |
| Transaction Reversals | `test_financial_transactions.py` | Reversal entry offsets original without mutation | Status set to `reversed`; offsetting entry posted | **PASS** |
| Duplicate Detection | `test_financial_transactions.py` | Identical hash within 5 minutes flagged as duplicate | Duplicate rejected with HTTP 409 Conflict | **PASS** |
| Transaction Ownership | `test_financial_transactions.py` | Transactions belong strictly to workspace | Cross-tenant access blocked with HTTP 404 | **PASS** |

### Category D: Double-Entry General Ledger

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Balanced Posting | `test_double_entry_ledger.py` | Postings with $\sum D == \sum C$ post successfully | Status transitions from `draft` to `posted` | **PASS** |
| Unbalanced Posting Rejection | `test_system_integration_e2e_qa.py` | Postings where $\sum D \neq \sum C$ rejected | `UnbalancedJournalError` raised; commit rolled back | **PASS** |
| Immutability Protocol | `test_double_entry_ledger.py` | Posted journals cannot be edited or deleted | `ImmutableJournalError` raised on modification attempt | **PASS** |
| Reversing Entries | `test_double_entry_ledger.py` | Reversals post inverted debits/credits linked to parent | Offsetting lines posted; original marked `reversed` | **PASS** |
| Trial Balance Invariant | `test_double_entry_ledger.py` | Net sum of all debit and credit balances equals 0 | Sum of debits minus credits equals `Decimal("0.0000")` | **PASS** |
| Closed Period Guard | `test_double_entry_ledger.py` | Posting to closed accounting periods rejected | `PeriodClosedError` raised; ledger history protected | **PASS** |

### Category E: Import and Statement Processing

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| CSV Statement Import | `test_import_and_data_acquisition.py` | Parse Indian bank CSVs (HDFC, ICICI, SBI) | Columns mapped; candidate transactions staged | **PASS** |
| Excel Statement Import | `test_import_and_data_acquisition.py` | Parse `.xlsx` statement files via `openpyxl` | Rows extracted, sanitized, and staged | **PASS** |
| Native Vector PDF Ingestion | `test_document_intelligence.py` | Extract digital text via `pypdf` / `pdfplumber` | High-confidence text extracted from invoice PDFs | **PASS** |
| Invalid File Rejection | `test_import_and_data_acquisition.py` | Corrupted files or wrong MIME rejected with 422 | `ValidationException` raised with clear diagnostic | **PASS** |
| Statement Deduplication | `test_import_and_data_acquisition.py` | Re-importing identical statement skips duplicates | Existing entries identified by sha256 hash | **PASS** |

### Category F: Categorization and Merchant Intelligence

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Rule-Based Categorization | `test_categorization_and_merchant_intelligence.py` | Tenant regex rules match known patterns | Custom user category applied with confidence 1.0 | **PASS** |
| ML Classification (TF-IDF) | `test_categorization_and_merchant_intelligence.py` | Predicts category from description tokens | Predicted category assigned with confidence band | **PASS** |
| Merchant Normalization | `test_categorization_and_merchant_intelligence.py` | Strips UPI IDs, terminal codes, bank noise | "UPI/123/SWIGGY" $\rightarrow$ "Swiggy" | **PASS** |
| User Feedback Correction | `test_categorization_and_merchant_intelligence.py` | User override stored for model adaptation | Feedback logged in `user_classification_feedback` | **PASS** |

### Category G: Analytics and Net Worth

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Net Worth Calculation | `test_financial_analytics.py` | Assets minus Liabilities across all accounts | Net worth computed in exact integer paise | **PASS** |
| Historical Cash Flow | `test_financial_analytics.py` | Inflows vs outflows aggregated across date bounds | Periodic totals match ledger transaction sums | **PASS** |
| Category Breakdowns | `test_financial_analytics.py` | Spending aggregated per category slug | Sum of category percentages equals 100% | **PASS** |
| Indian Financial Year Bounds | `test_system_integration_e2e_qa.py` | April 1 to March 31 bounds calculated | Correct FY assignment (e.g. FY 2026-27) | **PASS** |

### Category H: Budgets and Goals

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Monthly Category Budgets | `test_personal_budgeting_and_goals.py` | Monthly limit allocated per expense category | Allocation recorded; utilization tracked | **PASS** |
| Threshold Notifications | `test_personal_budgeting_and_goals.py` | Alerts dispatched at 80% and 100% consumption | Alerts created in `budget_alerts` table | **PASS** |
| Milestone Savings Goals | `test_personal_budgeting_and_goals.py` | Goal target, saved amount, and velocity tracked | Progress percentage computed accurately | **PASS** |

### Category I: Recurring Finance

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Frequencies & Scheduling | `test_recurring_and_subscriptions.py` | Daily, weekly, monthly, quarterly recurrences | Next occurrence dates computed accurately | **PASS** |
| Leap-Year Pinning | `test_recurring_and_subscriptions.py` | Feb 29 pins to Feb 28 in non-leap years | Verified leap-year safe calculations | **PASS** |
| Transaction Matching | `test_recurring_and_subscriptions.py` | Cleared transaction matched to scheduled occurrence | Occurrence marked `fulfilled`; no duplicate posting | **PASS** |

### Category J: Forecasting and Anomaly Detection

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Cash Flow Projections | `test_financial_forecasting.py` | Holt-Winters smoothing projects future balances | Projected curves output with 80%/95% intervals | **PASS** |
| Anomaly Scoring | `test_financial_anomalies.py` | Z-score / IQR flags unusual spending amounts | Severity assigned (`LOW`, `MEDIUM`, `HIGH`) | **PASS** |
| False Positive Handling | `test_financial_anomalies.py` | Expected recurring bills not flagged as anomalies | Recurring definitions exempt from outlier scoring | **PASS** |

### Category K: AI Financial Assistant

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Intent Recognition | `test_ai_assistant.py` | Natural language parsed to structured query intent | Intent mapped to analytical tool calls | **PASS** |
| Prompt Sanitization | `test_ai_assistant.py` | Injection attacks stripped; PII redacted | Jailbreak patterns stripped; PAN/Aadhaar masked | **PASS** |
| Zero Ledger Mutation | `test_ai_assistant.py` | Assistant has strictly read-only capabilities | No ledger write endpoints exposed to assistant | **PASS** |

### Category L: Receipt and Document Intelligence

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Binary Magic Bytes Check | `test_document_intelligence.py` | Validates leading binary signatures (PDF/PNG/JPEG) | Spoofed extensions rejected with HTTP 422 | **PASS** |
| GSTIN & Field Extraction | `test_document_intelligence.py` | Extracts Indian GSTIN and line amounts | Extracted fields structured into `StructuredReceiptDataVO` | **PASS** |
| Human Confirmation Gate | `test_document_intelligence.py` | OCR never posts transactions without user review | User confirmation required to create transaction | **PASS** |

### Category M: Unified Notification Engine

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| In-App Notification Center | `test_notifications.py` | Real-time security, budget, and system alerts | Alerts stored in `notifications` table | **PASS** |
| User Preferences | `test_notifications.py` | Respects channel and category toggle settings | Muted categories do not generate alerts | **PASS** |

### Category N: Family Finance

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Household Creation | `test_family_finance.py` | Shared family workspace with household members | Provisioned with collaborative budgeting | **PASS** |
| Private Account Isolation | `test_family_privacy.py` | Private bank accounts concealed from other members | Cross-member query returns HTTP 404 | **PASS** |
| Expense Split Settlement | `test_family_finance.py` | Shared expenses tracked and settled among members | Settlement ledger tracks peer balances | **PASS** |

### Category O: Small Business Finance

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| B2B Invoicing & AR | `test_business_finance.py` | Generate GST invoice with sequential numbering | Invoices created, PDF rendered, AR tracked | **PASS** |
| CGST / SGST / IGST Math | `test_business_finance.py` | Accurate 18% tax calculation and ledger posting | Intra-state (9%+9%) and Inter-state (18%) verified | **PASS** |

### Category P: Account Aggregator (AA)

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| ReBIT Adapter Architecture | `test_financial_connections.py` | Consent artifact lifecycle and synthetic sync | Mock adapter exercises consent and data fetch | **PASS** |
| Live Bank Sync | Manual / Production | Production NBFC-AA digital certificate exchange | Requires commercial contract with licensed NBFC | **BLOCKED (OPERATIONAL)** |

### Category Q: Reporting and Tax Intelligence

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Section 115BAC Income Tax | `test_financial_reports.py` | New Tax Regime slabs, ₹75k deduction, Sec 87A | Tax computed in exact integer paise | **PASS** |
| Financial Statements | `test_financial_reports.py` | P&L, Balance Sheet, and Trial Balance generation | Reconciled against double-entry general ledger | **PASS** |

### Category R: Frontend Component Library

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| UI Components (Button, Modal, Input, Tables, StatusBadge, etc.) | `apps/web/src/components/__tests__/*.test.tsx` (16 test files) | Accessible rendering, ARIA attributes, focus states | 48 component tests pass cleanly | **PASS** |

### Category S: Frontend Application Pages

| Component / Functionality | Test File | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| All 17 Pages (Dashboard, Accounts, Transactions, Ledger, Budgets, Business, Family, etc.) | `apps/web/src/pages/__tests__/*.test.tsx` (17 test files) | Complete view rendering, modal triggers, API hooks | 110 page tests pass cleanly | **PASS** |

### Category T: PWA & Responsive Viewports

| Component / Functionality | Test File / Tool | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Service Worker & Offline Banner | `usePwaStore.test.ts`, `OfflineBanner.test.tsx` | Precaches assets, displays offline warning banner | Caching active; offline write guards functional | **PASS** |
| Responsive Viewports (360px – 1440px) | `agent-browser` (Chromium 157) | Layout adapts cleanly across all 6 breakpoint widths | Verified at 360, 390, 430, 768, 1024, 1440px | **PASS** |

### Category U: Infrastructure and Operational Testing

| Component / Functionality | Test File / Verification | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| Dockerfile Security | `test_production_operational_readiness.py` | Multi-stage, non-root user (UID 10001) | Non-root `arthsavora` user verified | **PASS** |
| Migration Advisory Lock | `test_production_operational_readiness.py` | `pg_advisory_lock(987654321)` prevents race | Lock acquired and released in `finally` | **PASS** |
| Health Probes | `test_production_operational_readiness.py` | `/health/live` and `/health/ready` return 200 OK | Process and database readiness probes verified | **PASS** |
