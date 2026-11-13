# ARTHSAVORA — 30-PROMPT DEVELOPMENT PROGRAMME TRACKER
**Document Reference:** `docs/DEVELOPMENT_PROGRESS.md`  
**Last Updated:** 2026-11-14  
**Project:** ARTHSAVORA  
**Market:** India-First (Commercial FinTech Ecosystem)  
**Repository:** https://github.com/Ashutosh2275/Arthsavora.git  
**Current Branch:** `main`  
**Starting Baseline Commit:** `6caa716456ec7cd9fff31ab16ee4a929b9f1d710`  
**Prompt 01 Commit Hash:** `dc139f365dac20bcc3e08985ed0dc7af4df62fec`  
**Prompt 02 Commit Hash:** `ef5581177aa0dbe9042b03fbdf7d1fc0d1ca26ef`  
**Prompt 03 Commit Hash:** `67717478061e86ae6be71e998db493be81a5e1cf`  
**Prompt 04 Commit Hash:** `76b444fb113a34a5df0bf6dd65b0145f18222ac9`  
**Prompt 05 Commit Hash:** `1bb05cee39cb012a67bc6477e0c46b95b778263f`  
**Prompt 06 Commit Hash:** `2ab11cdcfc1664cf51aafe7a1fae1c31278fce01`  
**Remote Push Verification:** Prompts 01, 02, 03, 04, and 05 pushed and verified on `origin/main`  

---

## 1. PROGRAMME STATUS OVERVIEW

- **Total Planned Prompts:** 30
- **Current Stage:** Stage 1 — Engineering Baseline & Core Architecture (Prompts 01–06)
- **Current Prompt:** Prompt 06 — Core Domain Layer, API Contracts and Service Architecture
- **Completed Prompts:** 6 of 30 (Stage 1 — Engineering Baseline, Architecture, Standards, Database, Backend, and Domain/Contracts Foundation fully established)
- **Prompt 06 Status:** COMPLETED & VERIFIED
- **Next Prompt:** Prompt 07 — Background Task Engine (Redis + Celery) & Async Workers (Stage 2)

---

## 2. 30-PROMPT PROGRAMME ROADMAP

| Prompt # | Stage | Title / Objective | Status | Commit Hash |
| :---: | :---: | :--- | :---: | :---: |
| **01** | Stage 1 | Complete Repository Audit and Engineering Baseline | **COMPLETED** | `dc139f3` |
| **02** | Stage 1 | Project Structure and Engineering Foundation | **COMPLETED** | `ef55811` |
| **03** | Stage 1 | Engineering Standards, Design System and Development Automation | **COMPLETED** | `6771747` |
| **04** | Stage 1 | Database Architecture and PostgreSQL Foundation | **COMPLETED** | `76b444f` |
| **05** | Stage 1 | Backend Architecture, API Foundation and Authentication | **COMPLETED** | `1bb05ce` |
| **06** | Stage 1 | Core Domain Layer, API Contracts and Service Architecture | **COMPLETED** | `2ab11cd` |
| **07** | Stage 2 | Background Task Engine (Redis + Celery) & Async Workers | UPCOMING | - |
| **08** | Stage 2 | Secure Document Storage (Supabase Signed URLs) & Robust OCR | UPCOMING | - |
| **09** | Stage 2 | Indian UPI SMS Ingestion Engine with Idempotency & Regex Verification | UPCOMING | - |
| **10** | Stage 2 | Core Financial Account Management (Bank, Credit Card, Cash, Wallets) | UPCOMING | - |
| **11** | Stage 3 | Personal & Household Multi-Account Dashboard & Cash Flow Tracker | UPCOMING | - |
| **12** | Stage 3 | Predictive Budgeting & ARIMA Forecasting Engine (Isolated Workers) | UPCOMING | - |
| **13** | Stage 3 | Milestone Goals & Real Ledger-Backed Savings Velocity Engine | UPCOMING | - |
| **14** | Stage 3 | Financial Anomaly & Fraud Risk Detection Engine | UPCOMING | - |
| **15** | Stage 3 | Indian Tax Intelligence (Old vs New Regime, 80C, 80D, Capital Gains) | UPCOMING | - |
| **16** | Stage 4 | Freelancer & Small Business Invoicing Engine with GST Compliance | UPCOMING | - |
| **17** | Stage 4 | Business Expense Categorization & Vendor Management | UPCOMING | - |
| **18** | Stage 4 | Cross-Platform Mobile Application Setup (React Native + Expo) | UPCOMING | - |
| **19** | Stage 4 | Mobile Native Financial Features (On-Device SMS Sync & Biometrics) | UPCOMING | - |
| **20** | Stage 4 | Multi-Currency Support & Automated FX Rate Ingestion | UPCOMING | - |
| **21** | Stage 5 | AI Financial Assistant (Official `google-genai` SDK + RAG Pipeline) | UPCOMING | - |
| **22** | Stage 5 | Financial Statement & Export Engine (CA-Ready PDF & Excel Reports) | UPCOMING | - |
| **23** | Stage 5 | Bank Statement Ingestion (PDF & CSV Parsers with Reconciliation) | UPCOMING | - |
| **24** | Stage 5 | Debt, Loan & EMI Amortization Schedule Engine | UPCOMING | - |
| **25** | Stage 6 | Premium Commercial FinTech UI/UX Polish & Design Token System | UPCOMING | - |
| **26** | Stage 6 | Comprehensive Security Hardening & Penetration Testing Remediation | UPCOMING | - |
| **27** | Stage 6 | Comprehensive End-to-End Testing (Playwright + Test Suites) | UPCOMING | - |
| **28** | Stage 6 | Observability, Structured Logging, APM & Sentry Integration | UPCOMING | - |
| **29** | Stage 6 | Production Deployment Engineering (Docker, Helm, Managed Cloud) | UPCOMING | - |
| **30** | Stage 6 | Final Production Verification, Documentation & Commercial Launch | UPCOMING | - |

---

## 3. PROMPT 01 ACCEPTANCE CHECKLIST

- [x] Clone and inspect local repository without modifying Git history.
- [x] Verify remote identity against `https://github.com/Ashutosh2275/Arthsavora.git`.
- [x] Full filesystem traversal and module cataloging.
- [x] Complete frontend technology, quality, and UI/UX audit.
- [x] Complete backend technology, architecture, and code quality audit.
- [x] Comprehensive database and financial integrity audit.
- [x] Practical security assessment and vulnerability identification.
- [x] AI/ML and external integration audit.
- [x] Execute safe build and testing checks (npm ci, build, lint, py_compile, import).
- [x] Comprehensive architecture gap analysis (28 documented gaps).
- [x] Creation of `docs/REPOSITORY_AUDIT.md`.
- [x] Creation of `docs/EXISTING_IMPLEMENTATION_INVENTORY.md`.
- [x] Creation of `docs/ARCHITECTURE_GAP_REGISTER.md`.
- [x] Creation of `docs/DEVELOPMENT_PROGRESS.md`.
- [x] Creation of `docs/ENGINEERING_STANDARDS.md`.
- [ ] Review Git diff to ensure only audit documents and no unrelated changes are staged.
- [ ] Create meaningful commit for Prompt 01.
- [ ] Push commit to remote `main` branch and verify remote commit hash.
- [ ] Record final commit hash in this tracker.

---

## 4. CRITICAL ISSUES IDENTIFIED DURING PROMPT 01 AUDIT

1. **Database Mismatch:** MongoDB currently implemented; approved architecture mandates PostgreSQL + SQLAlchemy 2.0 + Alembic.
2. **Floating-Point Financial Data:** Currency stored as `float`, causing precision errors.
3. **Missing Relational Ledger:** No double-entry accounting ledger or transaction balancing.
4. **CORS Security Risk:** Wildcard origins combined with credential authorization in FastAPI `main.py`.
5. **Config Crash on Fresh Clone:** Backend cannot start or be imported without environment variables.
6. **Flawed Budget Calculation:** Budget aggregation counts all historical expenses across all time.
7. **Lack of Multi-Tenancy:** No workspace separation between personal, household, and business domains.
8. **Untracked / Tracked Bytecode:** 24 `.cpython-313.pyc` files accidentally committed in version control.
9. **Zero Test Coverage:** Exactly 0 automated tests in the repository.
10. **Frontend in JavaScript:** Frontend written in `.jsx` instead of mandated TypeScript (`.tsx`).

---

## 5. IMMEDIATE NEXT STEP FOR PROMPT 02 (COMPLETED)

Prompt 02 established the foundational monorepo, pnpm workspaces, TypeScript frontend migration, backend core restructuring, and initial test suites (Commit `ef55811`).

---

## 6. PROMPT 03 ACCEPTANCE & VERIFICATION RECORDS

- [x] Design token system established in `packages/design-tokens` (Color, Typography, Spacing, Radii, Shadows, Breakpoints, Z-Index, Motion).
- [x] High-contrast Light Theme & Institutional Dark Theme foundations functional via CSS custom properties.
- [x] Reusable component foundation created and refined:
  - Interactive: `Button` (primary, secondary, outline, ghost, destructive, icon-only, loading state).
  - Form Controls: `Input` (password toggle, search, error state, helper text), `Textarea`, `Select`, `Checkbox`, `RadioGroup`, `Switch`.
  - Layout: `PageContainer`, `SectionHeader`, `Stack`, `Grid`, `Card` (with Header, Title, Content, Footer), `Divider`.
  - Feedback: `Alert`, `Modal`, `ConfirmDialog`, `Skeleton`, `EmptyState`, `ErrorBoundary`.
  - Financial Data: `FinancialAmount` (INR formatting, tabular numbers, credit/debit semantics, privacy masking), `PercentageDisplay`, `StatusBadge` (icons + text, AI prediction indicator), `Table`.
- [x] Accessibility verified: WCAG 2.2 AA compliant contrast, keyboard navigation, focus management, color independence, reduced-motion media query.
- [x] Observability foundation: Correlation IDs (`X-Request-ID`), structured logging with sensitive data redaction, Sentry-ready `apps/web/src/lib/observability.ts`.
- [x] Automated testing: Vitest component test suites (7 test files, 24 unit/component tests passing).
- [x] CI/CD pipeline updated in `.github/workflows/ci.yml` with component tests.
- [x] Documentation created: `docs/DESIGN_SYSTEM.md`, `docs/COMPONENT_GUIDELINES.md`, `docs/ACCESSIBILITY_STANDARD.md`, `docs/TESTING_STRATEGY.md`, `docs/CI_CD_STANDARD.md`, and updated `docs/ENGINEERING_STANDARDS.md`.
- [x] Verification commands: `typecheck:all` (0 errors), `lint:web` (0 warnings), `build:web` (passed in 4.8s), `test:web` (24 passed), `pytest` (10 passed).
- [x] Existing application routes and pages preserved intact.

---

## 7. PROMPT 04 ACCEPTANCE & VERIFICATION RECORDS

- [x] **PostgreSQL Authoritative Relational Database:** Configured PostgreSQL 15+ engine via SQLAlchemy 2.0 async engine and `asyncpg` driver on host port 5433 (`arthsavora` and `arthsavora_test`).
- [x] **Domain Models Established (15 Tables across 8 Modules):**
  - Identity & Profile: `users` (external auth UID, security stamp, soft delete) and `user_profiles` (currency, timezone, theme, notification preferences).
  - Workspace Tenancy: `workspaces` (personal, family, business) and `workspace_members` (owner, admin, member, accountant, viewer with unique constraints).
  - Financial Accounts: `accounts` (bank, savings, current, credit card, cash, wallet, loan with masked identifiers `XX4092`).
  - Categories: `categories` (hierarchical parent-child, system default vs workspace-custom with unique slug per workspace).
  - Operational Transactions: `transactions` with exact `NUMERIC(18, 4)` precision, transaction types, source tracing, AI prediction flags, and partial unique index `(workspace_id, external_transaction_id) WHERE external_transaction_id IS NOT NULL` for idempotent deduplication.
  - Double-Entry General Ledger: `ledger_accounts` (chart of accounts with debit/credit normal balance), `journal_entries` (entry number, posting date, draft/posted/reversed status, reversal reference), and `journal_lines` (entry type, exact `NUMERIC(18, 4)` amount with `CHECK (amount > 0)`).
  - Ingestion & Consent: `data_sources`, `consent_records` (expiry and revocation audit), `import_jobs` (counters for total/success/failed), and `import_files` (SHA-256 deduplication hash).
  - Immutable Audit: `audit_logs` (actor, action, entity, correlation ID `X-Request-ID`, before/after JSONB state snapshots).
- [x] **Double-Entry Ledger Domain Service:** Built `backend/app/infrastructure/database/ledger.py` with strict balance validation ($\sum \text{Debits} = \sum \text{Credits}$), posting immutability enforcement, and reversible journal entries with inverted line items.
- [x] **Multi-Tenant Row-Level Security (RLS):** Implemented transaction-local tenant context isolation via `set_tenant_context` (`SET LOCAL app.current_workspace_id = '...'`) and generated PostgreSQL RLS policies ensuring zero connection pool state leakage.
- [x] **Alembic Async Migrations:** Initialized `alembic.ini` and `backend/migrations/env.py`, generated migration `a0735f358f00_initial_schema_postgresql_foundation.py`. Verified `alembic upgrade head`, `alembic downgrade base`, and re-upgrade `alembic upgrade head` with 100% schema fidelity.
- [x] **Automated Database Test Suite:** Implemented 8 real PostgreSQL tests in `backend/tests/test_database.py` covering workspace isolation, exact numeric precision, partial index idempotency, double-entry balancing and rejection, posted entry immutability and reversal, audit log preservation across member revocation, and RLS tenant context scoping.
- [x] **All Tests Passing:** Total backend test suite: 18 passed in 1.24s. Web test suite: 24 passed in 2.2s.
- [x] **Documentation Delivered:**
  - `docs/DATABASE_ARCHITECTURE.md`
  - `docs/DATABASE_SCHEMA_REFERENCE.md`
  - `docs/DATABASE_MIGRATION_GUIDE.md`
  - `docs/DATABASE_SECURITY.md`
  - `docs/DATABASE_BACKUP_RECOVERY.md`

---

## 8. PROMPT 05 ACCEPTANCE & VERIFICATION RECORDS

- [x] **Modular Monolith Backend Architecture:** Strict separation between Routing (`api/v1/`), Request/Response Schemas (`schemas/`), Application Services (`services/`), Domain Logic (`ledger.py`, `models/`), Persistence (`infrastructure/database/`), and Security/Authorization (`core/`).
- [x] **FastAPI Application Lifecycle & Factory:** Created `create_app()` factory with async lifespan verifying PostgreSQL connection pool health, environment safety assertions, and clean connection pool disposal without automatic table creation or unreviewed migrations.
- [x] **Authentication Engine:** Built `AuthService` handling PostgreSQL-backed registration, bcrypt password hashing, automatic personal workspace and profile bootstrapping, credential validation, 24-hour access tokens, 30-day refresh tokens, and suspended/soft-deleted account rejection.
- [x] **Cryptographic Token Verification:** Implemented `decode_token()` in `app.core.security` with strict signature integrity, expiration checking, token-type isolation (`access` vs `refresh`), and dual verification support for internal and Supabase-issued JWTs.
- [x] **Server-Side Authorization & Anti-IDOR:** Implemented `get_workspace_context_resolver` and `require_role()` supporting Personal, Family, and Business workspace role matrices (`owner`, `admin`, `member`, `accountant`, `viewer`). Enforced anti-IDOR cloaking (returns 404 on unauthorized workspace access) and injected transaction-local `SET LOCAL app.current_workspace_id` for PostgreSQL RLS.
- [x] **API Design Standards & Foundation Endpoints:**
  - Standard error format with `code`, `message`, `request_id`, and `details`.
  - Canonical V1 route hierarchy mounted at `/api/v1/*` (`health/live`, `health/ready`, `auth/register`, `auth/login`, `auth/me`, `auth/refresh`, `auth/logout`, `workspaces/`, `workspaces/{id}`, `workspaces/{id}/members`).
  - Standard pagination schema with 1-indexed page, max 100 page size, and offset calculation.
  - Correlation ID tracking: `X-Request-ID` extracted or generated, injected into responses and logs.
- [x] **Abuse Protection, Security Headers & Idempotency:**
  - SlowAPI rate limiter: 5 req/min on login, 120 req/min general, 300 req/min health probes.
  - Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 0`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Cache-Control: no-store` on API responses.
  - Request idempotency engine (`app.core.idempotency`) with in-flight lock detection (409 Conflict) and SHA-256 fingerprint matching.
  - Masking of passwords, tokens, and authorization credentials in access logs.
- [x] **OpenAPI Specification Generator:** Created reproducible offline generator `backend/scripts/generate_openapi.py` producing `docs/openapi.json` (29 paths, 26 schema components, OpenAPI 3.1.0).
- [x] **Comprehensive Test Suite:** 49 automated backend tests passing in 8.29s across 10 test modules (including 11 auth tests, 7 authorization tests, 7 API standards tests, 8 PostgreSQL integration tests, 3 health/readiness tests, 3 idempotency tests). Web test suite: 24 passed in 8.4s. Monorepo typecheck: 0 errors.
- [x] **Documentation Delivered:**
  - `docs/BACKEND_ARCHITECTURE.md`
  - `docs/API_DESIGN_STANDARD.md`
  - `docs/AUTHENTICATION_AUTHORIZATION.md`
  - `docs/SECURITY_IMPLEMENTATION.md`
  - `docs/BACKEND_TESTING.md`
  - `docs/API_CONTRACT_WORKFLOW.md`
  - `docs/openapi.json`

---

## 9. PROMPT 06 ACCEPTANCE & VERIFICATION RECORDS

- [x] **Pure Domain Layer Architecture:** Implemented `backend/app/domain/` strictly decoupled from FastAPI, HTTP status codes, Celery, or external AI providers. Pure domain exceptions (`DomainError`, `DomainValidationError`, `CurrencyMismatchError`, `BusinessRuleViolationError`, `EntityNotFoundError`, `UnauthorizedDomainActionError`).
- [x] **Exact Financial Money Value Object:** Built immutable `Money` dataclass (`backend/app/domain/money.py`) using `Decimal` arithmetic exclusively, Bankers Rounding (`ROUND_HALF_EVEN`), 4-decimal internal ledger quantization, ISO 4217 currency precisions, minor unit conversion (`paise` integer methods `to_minor_units` and `from_minor_units`), and strict `CurrencyMismatchError` enforcement.
- [x] **Domain Events & Transactional Outbox Collector:** Implemented immutable `DomainEvent` dataclass with correlation and actor tracking, standard factory functions (`workspace.created`, `workspace.member_joined`, `account.created`, `transaction.created`, `accounting.journal_posted`), and `DomainEventCollector` for atomic outbox staging and rollback flushing.
- [x] **Domain Invariants & Financial Rules:** Defined business rule validators (`backend/app/domain/rules.py`) enforcing non-identical transfer accounts, positive non-zero transfer amounts, refund limits, and AI prediction confidence score transparency ($0.0 \le \text{confidence} \le 1.0$).
- [x] **Repository Pattern & Anti-IDOR Enforcement:**
  - `BaseRepository[T]`: Generic CRUD persistence methods.
  - `WorkspaceScopedRepository[T]`: Atomic `where(id == ..., workspace_id == ...)` anti-IDOR checks with zero resource existence leakage, and bounded pagination (`limit <= 100`).
  - `WorkspaceRepository`: Workspace lookup and membership management.
  - `AccountRepository`: Bank, cash, and card account persistence and filtering.
  - `TransactionRepository`: Operational transaction persistence and `get_by_external_id` for idempotent deduplication.
- [x] **Application Services Layer:**
  - `AccountService`: Provisions accounts, validates currencies via `Money`, and emits `account.created` events.
  - `TransactionService`: Intakes transactions, validates exact Money, enforces AI transparency rules, performs idempotent deduplication via `external_transaction_id`, and emits `transaction.created` events.
- [x] **API Route Handlers & Monorepo Synchronization:**
  - Registered `/api/v1/accounts/` and `/api/v1/transactions/` in `app/api/v1/router.py`.
  - Exported OpenAPI 3.1.0 schema (`docs/openapi.json`) with 31 paths and 31 schema components.
  - Synchronized TypeScript contracts (`packages/contracts/src/index.ts`) with `AccountCreateRequest`, `AccountResponse`, `TransactionCreateRequest`, `TransactionResponse`.
  - Configured frontend Axios client (`apps/web/src/lib/axios.ts`) to inject `X-Request-ID` and `X-Workspace-ID` on all requests.
- [x] **Comprehensive Test Suites:** 77 passing backend tests across 14 test files (including 11 Money value object tests, 3 domain event tests, 4 repository tests, 5 service tests, and 5 API integration tests). 24 passing web tests. Monorepo typecheck: 0 errors.
- [x] **Documentation Delivered:**
  - `docs/DOMAIN_ARCHITECTURE.md`
  - `docs/DOMAIN_MODEL_CONVENTIONS.md`
  - `docs/APPLICATION_SERVICE_GUIDELINES.md`
  - `docs/REPOSITORY_PATTERN.md`
  - `docs/API_CONTRACT_STANDARD.md`
  - `docs/DOMAIN_EVENTS.md`




