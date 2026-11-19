# ARTHSAVORA — Frontend Testing Strategy & Quality Assurance

**Document Reference:** `docs/FRONTEND_TESTING.md`  
**Authoritative Standard:** Stage 5/6 Quality Engineering & Test Execution  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Testing Philosophy & Standards

Frontend testing in ARTHSAVORA adheres strictly to the **User-Centric Testing Paradigm**:
- **Test User Behavior, Not Implementation Details:** Tests query elements through accessible roles, labels, and text rather than internal component state or arbitrary CSS classes.
- **Deterministic Mocking:** All network requests and backend endpoints are intercepted using structured Vitest mocks that mirror `@arthsavora/contracts` schemas.
- **Zero Test Flakiness:** Asynchronous UI transitions use `waitFor` and `findByRole` rather than arbitrary timers or `sleep` calls.

---

## 2. Test Execution Environment & Tooling

| Tool | Purpose | Configuration |
| :--- | :--- | :--- |
| **Vitest** | Test runner & assertion library | Configured with `environment: 'jsdom'` |
| **React Testing Library** | Component rendering & interaction | Strict accessibility queries (`getByRole`, `getByLabelText`) |
| **Jest DOM** | DOM matchers | `toBeInTheDocument()`, `toBeDisabled()`, `toHaveValue()` |
| **TypeScript Typecheck** | Compile-time validation | `pnpm -r run typecheck` across all monorepo packages |

---

## 3. Test Coverage & Verified Suites

As of Prompt 25, the frontend test suite achieves **100% pass rate** across all 29 test files and 138 tests:

```
Test Files  29 passed (29)
     Tests  138 passed (138)
  Duration  27.66s
```

### Key Test Suite Breakdown:
- **`AppLayout.test.tsx` (3 tests):**
  - Brand identity rendering & skip-to-content accessibility link.
  - Desktop sidebar and TopBar integration.
  - Mobile menu toggle open/close lifecycle.
- **`WorkspaceSwitcher.test.tsx` (4 tests):**
  - Active workspace badge and entity icon rendering.
  - Dropdown workspace list population.
  - Multi-tenant workspace selection and listener triggering.
  - Create Workspace modal opening and form submission.
- **`GlobalSearch.test.tsx` (5 tests):**
  - Search trigger button with `Ctrl+K` shortcut indicator.
  - Modal opening via trigger click and keyboard `Ctrl+K` shortcut.
  - Search query filtering across pages, accounts, and transactions.
  - Keyboard navigation (`ArrowDown`, `ArrowUp`, `Enter`, `Escape`).
  - Empty state message rendering when query matches no records.
- **`Settings.test.tsx` (5 tests):**
  - Settings page header and 4 navigation tabs (Profile, Workspace, Members, Platform).
  - Workspace configuration update form submission.
  - Workspace members list and role badges.
  - Invite Collaborator modal opening and invitation submission.
  - Platform preferences toggle.
- **Feature Suites (25 files):**
  - `Dashboard.test.tsx`, `Accounts.test.tsx`, `Transactions.test.tsx`, `Ledger.test.tsx`, `Budgets.test.tsx`, `Goals.test.tsx`, `Recurring.test.tsx`, `Forecast.test.tsx`, `Categories.test.tsx`, `Anomalies.test.tsx`, `Documents.test.tsx`, `Assistant.test.tsx`, `FinancialReports.test.tsx`, `FinancialConnections.test.tsx`, `Family.test.tsx`, `Business.test.tsx`, `Notifications.test.tsx`, `Import.test.tsx`.
- **UI Atomic Suites:**
  - `Button.test.tsx`, `Input.test.tsx`, `Modal.test.tsx`, `Alert.test.tsx`, `StatusBadge.test.tsx`, `EmptyState.test.tsx`, `FinancialAmount.test.tsx`.

---

## 4. Running Frontend Tests

```bash
# Run all web tests synchronously
pnpm --filter @arthsavora/web test -- --run

# Run a specific test file
pnpm --filter @arthsavora/web test src/components/__tests__/AppLayout.test.tsx --run

# Run full monorepo typecheck
pnpm -r run typecheck
```
