# ARTHSAVORA — API CONTRACT STANDARD & FRONTEND SYNCHRONIZATION

## 1. Objective

This specification details the end-to-end API contract standard for Arthsavora. It outlines the schema architecture, synchronization mechanisms between FastAPI and the TypeScript frontend, correlation header propagation, and RFC 7807 error envelopes.

---

## 2. API Contract Architecture

```
┌─────────────────────────────────┐
│     Backend FastAPI Schemas     │  (Pydantic v2 Models in backend/app/schemas/)
└────────────────┬────────────────┘
                 │
                 │ 1. python backend/scripts/generate_openapi.py
                 ▼
┌─────────────────────────────────┐
│        docs/openapi.json        │  (OpenAPI 3.1.0 JSON Specification)
└────────────────┬────────────────┘
                 │
                 │ 2. TypeScript Contract Package Synchronization
                 ▼
┌─────────────────────────────────┐
│    packages/contracts/src/      │  (Shared TypeScript Types & Interfaces)
└────────────────┬────────────────┘
                 │
                 │ 3. Workspace Monorepo Dependency
                 ▼
┌─────────────────────────────────┐
│            apps/web/            │  (React 19 + Axios Client in apps/web/)
└─────────────────────────────────┘
```

---

## 3. OpenAPI 3.1.0 Generation Pipeline

The OpenAPI schema is automatically exported via `backend/scripts/generate_openapi.py`:
- Root schema file: `docs/openapi.json`
- Includes all routes under `/api/v1` (Auth, Workspaces, Accounts, Transactions, Health).
- Total endpoints documented: **31 API routes**.
- Total schema definitions: **31 components**.

To regenerate the schema:
```bash
python backend/scripts/generate_openapi.py
```

---

## 4. TypeScript Contract Models (`packages/contracts/src/index.ts`)

The shared TypeScript package mirrors the backend Pydantic schemas:

```typescript
export interface AccountCreateRequest {
  name: string;
  account_type: string;
  currency?: string;
  institution_name?: string;
  masked_identifier?: string;
}

export interface AccountResponse {
  id: string;
  workspace_id: string;
  name: string;
  account_type: string;
  currency: string;
  institution_name: string | null;
  masked_identifier: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreateRequest {
  account_id: string;
  amount: string;
  currency?: string;
  transaction_type: 'income' | 'expense' | 'transfer' | 'refund' | 'repayment' | 'adjustment';
  transaction_date: string;
  description: string;
  merchant_name?: string;
  category_id?: string;
  external_transaction_id?: string;
  is_ai_predicted?: boolean;
  ai_confidence?: number;
}

export interface TransactionResponse {
  id: string;
  workspace_id: string;
  account_id: string;
  amount: string;
  currency: string;
  transaction_type: string;
  transaction_date: string;
  settlement_date: string | null;
  description: string;
  merchant_name: string | null;
  category_id: string | null;
  external_transaction_id: string | null;
  is_ai_predicted: boolean;
  ai_confidence: number | null;
  created_at: string;
  updated_at: string;
}
```

---

## 5. HTTP Client Middleware & Context Headers (`apps/web/src/lib/axios.ts`)

The frontend Axios client automatically injects required context headers for every outgoing request:
1. **`X-Request-ID`:** A unique UUIDv4 generated per request for distributed tracing and log correlation.
2. **`X-Workspace-ID`:** The active workspace UUID retrieved from local storage / session state.
3. **`Authorization`:** Bearer JWT access token.

```typescript
apiClient.interceptors.request.use((config) => {
  if (!config.headers['X-Request-ID']) {
    config.headers['X-Request-ID'] = crypto.randomUUID();
  }
  const workspaceId = getActiveWorkspaceId();
  if (workspaceId && !config.headers['X-Workspace-ID']) {
    config.headers['X-Workspace-ID'] = workspaceId;
  }
  return config;
});
```

---

## 6. Standard Error Envelope (RFC 7807)

All non-2xx responses adhere to the standard JSON error schema:
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Transaction amount cannot be zero.",
  "request_id": "da1948c8-4dd4-4310-bb8c-2408e4bd5025",
  "timestamp": "2026-11-14T04:44:51.123456Z",
  "details": [
    {
      "field": "amount",
      "issue": "ZERO_AMOUNT_PROHIBITED"
    }
  ]
}
```
Client code normalizes errors using the `ApiError` TypeScript interface.
