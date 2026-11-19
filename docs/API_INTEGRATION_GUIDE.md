# ARTHSAVORA — Frontend API Integration Guide

**Document Reference:** `docs/API_INTEGRATION_GUIDE.md`  
**Authoritative Standard:** Stage 5/6 API Client & Gateway Architecture  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Overview & Gateway Architecture

The ARTHSAVORA web application interfaces with the backend REST API hosted at `/api/v1` via a centralized Axios instance configured in `apps/web/src/lib/api.ts`. The gateway manages:
1. Base URL configuration (environment-driven).
2. Request header injection (`Authorization`, `X-Workspace-ID`, `X-Request-ID`).
3. Global response error normalization and session expiration handling.
4. Paired data-type synchronization via `@arthsavora/contracts`.

---

## 2. Request Lifecycle & Interceptors

```
[UI Component / Store Action]
               │
               ▼
       apiClient.get/post(...)
               │
               ▼
    [Request Interceptor]
    • Attach Bearer Token (if authenticated)
    • Attach X-Workspace-ID (from useWorkspaceStore)
    • Attach Content-Type: application/json
               │
               ▼
       [Network Transport]
               │
               ▼
    [Response Interceptor]
    • Success (2xx) -> Return response.data
    • 401 Unauthorized -> Trigger useAuthStore.logout() & redirect
    • 403 Forbidden -> Surface permission error
    • 422 Validation Error -> Parse Pydantic field errors
    • 500 Server Error -> Generic fallback alert
```

---

## 3. Endpoints Catalog by Domain

| Domain | Base Route | Key Operations |
| :--- | :--- | :--- |
| **Authentication & Users**| `/api/v1/auth`, `/api/v1/users` | Login, Register, Refresh, Profile update |
| **Workspaces** | `/api/v1/workspaces` | CRUD workspaces, member management, invite |
| **Accounts** | `/api/v1/accounts` | Fetch accounts, create account, sync balances |
| **Transactions** | `/api/v1/transactions` | Query transactions, post transaction, categorize |
| **General Ledger** | `/api/v1/ledger` | Journal entries, posting rules, trial balances |
| **Import & Statement** | `/api/v1/import` | Upload CSV/PDF statements, parse batches, commit |
| **Budgets & Goals** | `/api/v1/budgets`, `/api/v1/goals` | Set limits, track progress, record deposits |
| **Recurring Commitments** | `/api/v1/recurring` | Subscriptions, scheduled payments, renewals |
| **Forecasting & Scenarios**| `/api/v1/forecast` | Cash flow projections, scenario simulations |
| **Anomaly Intelligence** | `/api/v1/anomalies` | Detected anomalies, review signals, feedback |
| **Document OCR** | `/api/v1/documents` | Upload receipts, extract fields, match txs |
| **AI Assistant** | `/api/v1/assistant` | Conversation threads, query chat, tool calls |
| **Financial Reports** | `/api/v1/reports`, `/api/v1/tax` | P&L, Cash Flow, Balance Sheet, GST summaries |
| **Bank Connections (AA)** | `/api/v1/connections` | Consent requests, account aggregation sync |
| **Business Operations** | `/api/v1/business` | Invoices, client/vendor directories, AR/AP |
| **Notifications** | `/api/v1/notifications` | Feed alerts, mark read, delivery preferences |

---

## 4. Contract-Driven Typing

Frontend requests and responses are strictly typed using shared schemas from `@arthsavora/contracts`:

```typescript
import type { 
  TransactionResponse, 
  CreateTransactionRequest, 
  WorkspaceResponse 
} from '@arthsavora/contracts';

// Strictly typed API interaction
export async function createTransaction(payload: CreateTransactionRequest): Promise<TransactionResponse> {
  const response = await apiClient.post<TransactionResponse>('/api/v1/transactions', payload);
  return response.data;
}
```

This ensures that backend schema alterations are caught immediately during monorepo compilation (`pnpm -r run typecheck`).
