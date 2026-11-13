# ARTHSAVORA TESTING STRATEGY
## Automated Quality Assurance, Test Automation & Coverage Protocol

---

## 1. Testing Philosophy & Pyramid

Arthsavora enforces a rigorous, multi-tiered testing strategy designed to guarantee financial accuracy, system reliability, accessibility, and high regression resistance.

```text
                  /\
                 /  \
                / E2E\            (Playwright: Golden Paths & User Journeys)
               /------\
              / Integr \          (Pytest: API Routes & DB Transactions)
             /----------\
            / Component  \        (Vitest + Testing Library: Design System UI)
           /--------------\
          /   Unit Tests   \      (Pytest + Vitest: Calculations & Validation)
         /------------------\
```

### Core Invariants
1. **Financial Precision Guarantee:** Every calculation service (tax calculations, loan amortizations, interest formulas, ledger balancing) must be validated with deterministic unit tests asserting zero floating-point discrepancies.
2. **Double-Entry Invariant:** Every ledger test must assert that $\sum \text{Debits} = \sum \text{Credits}$.
3. **Accessibility as a Quality Gate:** Foundational UI components must have automated unit tests verifying ARIA roles, focus behavior, and keyboard navigation.

---

## 2. Test Execution Architecture

### 2.1 Frontend Component & Unit Testing (Vitest + Testing Library)
- **Framework:** `vitest` with `jsdom` environment.
- **Library:** `@testing-library/react` and `@testing-library/jest-dom/vitest`.
- **Config:** `apps/web/vitest.config.ts` and setup at `apps/web/src/test/setup.ts`.
- **Scope:**
  - Component rendering under default, active, hover, disabled, and loading states.
  - User interaction simulation (clicks, typing, password toggle).
  - Keyboard navigation (Escape key dismissal, Tab indexing).
  - Indian currency formatting (`FinancialAmount`) and percentage display.
  - Dialog, modal, and confirmation flows (`Modal`, `ConfirmDialog`).
  - Error boundaries and empty states.

#### Execution Command
```bash
# Run all frontend tests
pnpm --filter @arthsavora/web test

# Run tests in watch mode
pnpm --filter @arthsavora/web test --watch
```

---

### 2.2 Backend Unit & Integration Testing (Pytest)
- **Framework:** `pytest` with `pytest-asyncio` (`asyncio_mode = auto`).
- **HTTP Test Client:** `httpx.AsyncClient` against FastAPI `app`.
- **Scope:**
  - Health checks and system status endpoints.
  - Configuration parsing and environment validation.
  - Security utilities (password hashing with bcrypt, timezone-aware JWT tokens).
  - Custom exception formatting and HTTP status mapping.
  - Double-entry ledger transaction posting and balance validation.
  - Multi-tenant workspace isolation.

#### Execution Command
```bash
# Run all backend tests
pytest backend/tests

# Run with test coverage
pytest --cov=backend/app backend/tests
```

---

### 2.3 End-to-End Testing (Playwright - Scheduled for Stage 6)
- **Scope:** End-to-end browser verification of critical golden paths:
  1. User Registration & Sign In.
  2. Manual Expense Logging & Category Tagging.
  3. SMS Paste & AI Transaction Extraction.
  4. Budget Creation & Alert Threshold Triggering.
  5. Goal Progress Update & Savings Allocation.

---

## 3. Quality Gates & Definition of Done

Every pull request and prompt completion must pass:

| Check | Tool | Command | Pass Criteria |
|:---|:---|:---|:---|
| **TypeScript Compilation** | `tsc` | `pnpm -r run typecheck` | 0 errors across all 5 workspace projects |
| **Frontend Code Quality** | `eslint` | `pnpm --filter @arthsavora/web lint` | 0 errors, 0 warnings (`--max-warnings 0`) |
| **Frontend Component Tests** | `vitest` | `pnpm --filter @arthsavora/web test` | 100% test pass rate |
| **Frontend Production Build** | `vite` | `pnpm --filter @arthsavora/web build` | Successful bundle generation |
| **Backend Unit Tests** | `pytest` | `pytest backend/tests` | 100% test pass rate |
| **Backend App Initialization**| `python` | `python -c "from app.main import app"` | Clean boot with zero unhandled exceptions |
