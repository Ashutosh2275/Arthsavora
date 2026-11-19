# ARTHSAVORA — Frontend State Management Architecture

**Document Reference:** `docs/FRONTEND_STATE_MANAGEMENT.md`  
**Authoritative Standard:** Stage 5/6 State Management & Data Hydration  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. State Architecture & Technology Selection

ARTHSAVORA uses **Zustand** as its primary client-side state manager. Zustand was selected over Redux or Context API for several critical reasons:
1. **Zero Boilerplate:** Avoids complex reducers, action types, and dispatch overhead.
2. **Selector-Based Performance:** Granular subscription selectors prevent unnecessary component re-renders when unrelated store properties change.
3. **Decoupled Stores:** Domain modules (Ledger, Transactions, Budgets, Forecasts, Reports) maintain isolated stores, avoiding a bloated monolithic state tree.
4. **Clean Async Integration:** Supports direct async/await action execution without secondary middleware (e.g., redux-thunk, redux-saga).

---

## 2. Store Catalog & Domain Breakdown

The frontend state is partitioned into specialized stores located in `apps/web/src/store/`:

| Store File | Domain Responsibility | Invalidation Trigger |
| :--- | :--- | :--- |
| `useThemeStore.ts` | Theme preference ('light', 'dark', 'system') & DOM sync | User preference |
| `useWorkspaceStore.ts` | Active workspace, workspace list, members, invitations | Workspace switch |
| `useAccountStore.ts` | Bank accounts, balances, credit limits, account types | Workspace switch, transaction post |
| `useTransactionStore.ts`| Authoritative transactions, search filters, pagination | Workspace switch, new posting |
| `useLedgerStore.ts` | Journal entries, ledger accounts, trial balances | Workspace switch, manual journal |
| `useBudgetStore.ts` | Category budgets, period progress, spending thresholds | Workspace switch, new expense |
| `useGoalStore.ts` | Savings goals, target dates, ledger contributions | Workspace switch, goal deposit |
| `useRecurringStore.ts` | Subscriptions, recurring bills, commitment calendars | Workspace switch, renewal |
| `useForecastStore.ts` | Cash-flow predictions, Monte Carlo simulations | Workspace switch, scenario toggle |
| `useAnomalyStore.ts` | Fraud signals, risk scores, review status | Workspace switch, anomaly review |
| `useDocumentStore.ts` | Receipt OCR batches, line-item drafts, match status | Workspace switch, document post |
| `useAssistantStore.ts` | Chat conversation messages, active tool invocations | Session reset, new chat |
| `useNotificationStore.ts`| Live alerts, unread counts, notification preferences | Workspace switch, alert poll |
| `useFinancialReportStore.ts`| Statements (P&L, Cash Flow, BS), Tax summaries, GST | Workspace switch, period change |
| `useBusinessStore.ts` | Clients, vendors, invoices, AR/AP ledgers | Workspace switch, invoice issue |

---

## 3. Store Implementation Patterns

### 3.1 Immutable State Updates
Stores utilize standard spread operations to ensure state immutability:
```typescript
set((state) => ({
  accounts: [...state.accounts, newAccount],
  isLoading: false,
}));
```

### 3.2 Granular Selectors
Components extract only the exact slices of state they require:
```typescript
// Prevents re-rendering when other properties on useAccountStore change
const accounts = useAccountStore((state) => state.accounts);
const fetchAccounts = useAccountStore((state) => state.fetchAccounts);
```

### 3.3 Loading & Error Semantics
Every async store adheres to a standardized lifecycle contract:
- `isLoading: boolean` — Tracks in-flight API requests.
- `error: string | null` — Captures localized error messages for user-friendly UI display.

---

## 4. Theme State Synchronization (`useThemeStore.ts`)

Theme state is managed through `useThemeStore.ts`:
- Supports `'light' | 'dark' | 'system'`.
- Synchronizes with system preference via `window.matchMedia('(prefers-color-scheme: dark)')`.
- Toggles the `dark` class on the root `document.documentElement` element to drive Tailwind's `class` dark mode strategy.
- Persists user preference across browser restarts via `localStorage`.
