# ARTHSAVORA — ENGINEERING STANDARDS & GOVERNANCE
**Document Reference:** `docs/ENGINEERING_STANDARDS.md`  
**Effective Date:** 2026-11-14  
**Applies To:** All 30 Development Prompts in the Arthsavora Programme  
**Authority:** Principal Software Architect & Financial Systems Engineer  

These engineering standards are mandatory and permanent. Every subsequent development prompt must strictly adhere to these specifications. No individual prompt may deviate from or dilute these requirements without explicit, documented architectural justification.

---

## 1. FINANCIAL CALCULATION RULES & ACCOUNTING INVARIANTS

Arthsavora is a commercial-grade financial technology platform. Financial correctness is paramount.

### 1.1 Absolute Prohibition of Floating-Point Money
- **Rule:** Under no circumstances shall floating-point types (`float`, `double`, IEEE 754 numbers) be used for storing, calculating, or mutating monetary values.
- **Backend Representation:**
  - In PostgreSQL schemas: Use `NUMERIC(18, 4)` for exact fixed-point amounts, or `BIGINT` representing minor currency units (paise for INR, cents for USD).
  - In Python domain logic: Always use `decimal.Decimal` with explicit rounding contexts (`ROUND_HALF_EVEN` / Bankers Rounding).
- **Frontend Representation:**
  - Pass monetary values over the API as exact strings (e.g. `"15400.50"`) or integer paise (`1540050`).
  - Convert to human-readable strings only at the presentation boundary using the Indian Rupee locale:
    ```typescript
    new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    }).format(amount);
    ```

### 1.2 Double-Entry Ledger Principles
- Every financial transaction must be recorded as an immutable set of balanced ledger lines.
- **The Accounting Equation Invariant:**
  $$\sum \text{Debits} = \sum \text{Credits}$$
- An unbalanced transaction must be rejected by the backend database transaction boundary.
- **No In-Place Modification of Posted Records:** Posted journal entries and transactions are immutable. Corrections, refunds, chargebacks, and reversals must be executed as distinct reversal journal entries linking to the original entry ID.

### 1.3 Ingestion & Mutation Idempotency
- Every financial mutation (transaction creation, payment, import, transfer) must require an `Idempotency-Key` header (UUIDv4) or derive a deterministic idempotency hash from upstream sources (e.g., bank statement UTR / reference number + timestamp + account ID).
- Submitting an identical idempotency key must return the original result without re-executing the financial mutation.

### 1.4 State Transitions for Financial Records
All financial entities must follow an explicit finite state machine:
```text
[ DRAFT ] ────────► [ PENDING ] ────────► [ POSTED ] ────────► [ RECONCILED ]
   │                     │                     │
   ▼                     ▼                     ▼
[ CANCELLED ]         [ FAILED ]          [ REVERSED ]
```

---

## 2. DATABASE & ORM CONVENTIONS

### 2.1 Technology Stack
- **Database Engine:** PostgreSQL 15+ (Single Financial Source of Truth).
- **ORM:** SQLAlchemy 2.0 with asynchronous driver (`asyncpg`).
- **Migrations:** Alembic with explicit upgrade/downgrade scripts.

### 2.2 Table Design & Field Standards
- **Primary Keys:** UUIDv7 or UUIDv4 (UUIDv7 preferred for sequential b-tree index performance).
- **Timestamps:** Every table must include timezone-aware timestamps:
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- **Soft Deletion:** Financial and user entities must never be physically purged with SQL `DELETE`. Include `deleted_at TIMESTAMPTZ NULL` and query via an active-only filter.
- **Multi-Tenancy:** Every user-facing domain model must include `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT`. All queries must filter by `workspace_id`.
- **Foreign Keys & Indices:** Every foreign key must have an index and explicit cascade rules (`RESTRICT` or `CASCADE`). Composite unique indexes must prevent duplicate accounts or transaction imports.

---

## 3. BACKEND ENGINEERING CONVENTIONS (PYTHON & FASTAPI)

### 3.1 Python Runtime & Dependencies
- **Python Version:** Python 3.11+.
- **Framework:** FastAPI with asynchronous route handlers (`async def`).
- **Data Validation:** Pydantic v2 (`BaseModel`, `ConfigDict`, `field_validator`).
- **Datetime Invariant:** Never use `datetime.utcnow()`. Always use `datetime.now(timezone.utc)`.

### 3.2 Architectural Layering (Modular Monolith)
Backend code must follow strict separation of concerns:
```text
app/
├── api/          # Transport layer: HTTP routes, request parsing, status codes
├── services/     # Domain business logic: Pure Python services, validation
├── repositories/ # Data access layer: SQLAlchemy queries and persistence
├── models/       # Relational models (SQLAlchemy) and Pydantic schemas
├── workers/      # Asynchronous background tasks (Celery)
└── core/         # Cross-cutting concerns: Config, security, database session
```
- **Rule:** Route handlers must not contain raw SQL queries or business logic. They must delegate directly to domain services.
- **Rule:** Database sessions must be injected using FastAPI dependencies (`Depends(get_db)`) with automatic commit on success and rollback on exception.

### 3.3 Asynchronous Execution & Event-Loop Protection
- **Rule:** Never execute CPU-heavy computations (ARIMA model fitting, scikit-learn training, PDF document generation, image OCR) directly within the async web server thread.
- Heavy operations must be dispatched to **Celery workers backed by Redis**.

---

## 4. FRONTEND ENGINEERING CONVENTIONS (REACT & TYPESCRIPT)

### 4.1 Technology Stack
- **Framework:** React 18+ / React 19 with Vite.
- **Language:** TypeScript 5.0+ in strict mode (`"strict": true`).
- **Styling:** Tailwind CSS with CSS variables for design tokens.
- **Icons:** `lucide-react`.
- **State Management:** Zustand for client UI state; `@tanstack/react-query` for server state and caching.
- **Form Handling:** `react-hook-form` paired with `zod` for type-safe validation schemas.

### 4.2 TypeScript Standards
- **Zero `any`:** The use of `any` is strictly prohibited. Use `unknown` with type narrowing, generics, or explicit interfaces.
- **Shared Types:** All API request bodies and response shapes must have matching TypeScript interfaces.
- **Null Safety:** Explicitly model nullability (`string | null`). Avoid non-null assertion operators (`!`).

### 4.3 Component Architecture
- Components must be functional and stateless where possible.
- Separate presentational UI components from data-fetching container hooks.
- Every async component must gracefully handle four distinct states:
  1. **Loading:** Accessible skeleton loaders matching the component geometry (no full-screen blocking spinners).
  2. **Error:** Helpful error messages with actionable retry actions.
  3. **Empty:** Purposeful empty state illustration and clear call-to-action.
  4. **Success:** High-density, polished data display.

---

## 5. UI/UX STANDARDS (COMMERCIAL FINTECH GRADE)

Arthsavora must look and behave like an institutional-grade financial product.

### 5.1 Visual Language
- **Aesthetic:** Clean, minimal, high-trust, and institutional.
- **Palette:** Deep neutral slates (`#0b0f1a`, `#0f172a`, `#1e293b`), crisp pure whites for critical numbers, and muted semantic colors:
  - **Positive / Income:** Emerald (`#10b981`).
  - **Negative / Outflow:** Rose / Amber (`#f43f5e` / `#f59e0b`).
  - **Primary Interactive:** Refined Indigo (`#4f46e5`).
  - **Neutral / Borders:** Slate 800 (`#1e293b`).
- **Restraint:** Prohibit gimmicky neon glows, cartoonish illustrations, excessive blur blobs, and playful emojis.
- **Card Radii:** Standardize on consistent border radii (`rounded-xl` / 12px for small cards, `rounded-2xl` / 16px for main containers). Avoid inconsistent 40px rounded corners.

### 5.2 User Feedback & Notifications
- **Prohibition of `window.alert()`:** Under no circumstances shall native browser alerts (`alert()`, `confirm()`, `prompt()`) be used.
- Use accessible, non-blocking toast notifications (e.g. Sonner) for operational feedback.
- Destructive actions (e.g., deleting a category or cancelling a subscription) require explicit modal confirmation dialogs.

---

## 6. SECURITY STANDARDS

### 6.1 Authentication & Session Handling
- Use Supabase Auth or secure server-issued session cookies (`HttpOnly`, `Secure`, `SameSite=Strict`).
- Never store sensitive JWTs or credentials in browser `localStorage`.
- Implement automatic token refresh before expiration.

### 6.2 Authorization & Tenant Isolation
- **Backend Enforcement:** Never rely on frontend routing for security. Every API endpoint must enforce authorization on the server.
- **Workspace Security:** Every database operation must verify that the authenticated user is an active member of the target `workspace_id`. Cross-workspace data leaks represent a critical security vulnerability.

### 6.3 CORS & API Hardening
- CORS origins must be explicitly enumerated based on environment configuration. Never combine `allow_origins=["*"]` with `allow_credentials=True`.
- Enforce strict Content Security Policy (CSP) headers and rate limiting across sensitive endpoints (auth, SMS parse, OCR, and AI chat).

### 6.4 File Upload Security
- Enforce maximum file size limits (5MB for receipt images).
- Verify file magic bytes on the backend (e.g., verifying `FF D8 FF` for JPEG) rather than trusting client-provided `Content-Type` headers.
- Never store confidential receipts in publicly accessible storage buckets. Use short-lived presigned URLs.

---

## 7. AI/ML INTEGRATION & SAFETY STANDARDS

### 7.1 SDK & Model Modernization
- Use the modern official `google-genai` SDK. Deprecated `google.generativeai` must not be used.
- Pin model versions to stable releases (`gemini-2.5-flash`).

### 7.2 Deterministic Financial Protection
- **No AI Financial Decisions:** AI and LLMs must never directly mutate financial balances or execute bank transfers without human confirmation.
- **Deterministic Math:** Financial calculations (tax owed, savings velocity, surplus, balances) must always be computed using deterministic Python code, never generated or estimated by an LLM.
- **Prompt Injection Defense:** Strict separation between system instructions and untrusted user queries using structured API inputs and parameter boundaries.

---

## 8. TESTING & QUALITY ASSURANCE

### 8.1 Required Testing Infrastructure
- **Backend:** `pytest` with `pytest-asyncio`, `pytest-cov`, and an in-memory SQLite or test PostgreSQL database.
- **Frontend:** `vitest`, `@testing-library/react`, and `@testing-library/user-event`.
- **E2E:** `playwright` for critical golden paths (signup, login, add transaction, view ledger).

### 8.2 Test-First Discipline
- For every new feature or bugfix, write unit tests validating expected behavior and edge cases before declaring the task complete.
- Minimum 85% branch coverage required for financial calculation services and double-entry ledger logic.

---

## 9. GIT CONVENTIONS & WORKFLOW GOVERNANCE

### 9.1 Non-Destructive Principles
- Never use destructive Git commands: `git reset --hard`, `git clean -fd`, `git push --force`.
- Preserve existing commit history and untracked user files.

### 9.2 Commit Standards
- Use Conventional Commits formatting:
  `feat(module): description`, `fix(module): description`, `docs(audit): description`.
- Stage only intended files. Never commit `.env`, credentials, local caches, `.pyc` files, or build artifacts (`dist/`, `node_modules/`, `venv/`).

---

## 11. OBSERVABILITY, CORRELATION IDS & DISTRIBUTED TRACING

### 11.1 Correlation IDs
- Every HTTP request passing through the FastAPI gateway must carry or be assigned an `X-Request-ID` (UUIDv4) via `backend/app/api/middleware/audit.py`.
- The correlation ID must be bound to request state (`request.state.correlation_id`), logged with all structured server log entries, and returned in the HTTP response headers.
- The frontend Axios client (`apps/web/src/lib/axios.ts`) and observability layer (`apps/web/src/lib/observability.ts`) must capture and report this ID when reporting client-side errors.

### 11.2 Structured Logging & Redaction
- All application logs must be structured and human/machine-readable.
- **Strict Data Sanitization Invariant:** Under no circumstances shall passwords, bearer tokens, card numbers, CVVs, or Indian tax identifiers (PAN, Aadhaar) be emitted in logs, query strings, or exception messages.

### 11.3 Error Boundaries & Sentry Readiness
- All major views must be wrapped in `ErrorBoundary` components.
- Errors must never present raw stack traces or internal server error messages to users. Instead, display an actionable message with an incident reference ID (`errorId`).
- Prepare interfaces for Sentry SDK (`initObservability`, `captureException`) to ensure seamless plug-and-play APM instrumentation.

A development prompt in the Arthsavora programme is considered complete only when:
1. **Requirements Satisfied:** All requirements specified in the prompt scope are fully implemented without shortcuts.
2. **Type Safety Verified:** Backend passes strict typing and Pydantic validation; frontend passes `tsc --noEmit` with zero errors.
3. **Tests Pass:** All automated unit and integration tests execute successfully.
4. **Code Quality:** Linting passes with zero errors; no dead or placeholder code introduced.
5. **Security Enforced:** No secrets committed, tenant isolation enforced, inputs sanitized.
6. **Git Synchronized:** Changes committed with conventional commit message, pushed to remote `main`, and remote commit hash verified.
7. **Documentation Updated:** Progress recorded in `docs/DEVELOPMENT_PROGRESS.md`.
