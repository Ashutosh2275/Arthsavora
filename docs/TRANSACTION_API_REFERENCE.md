# Arthsavora — Transaction Management API Reference

## 1. Overview & URL Mounting Convention

Arthsavora provides dual URL routing for all transaction endpoints to support both multi-workspace path nesting and standard default-workspace header resolution:
1. **Workspace-Scoped Paths (Recommended):**
   * `/api/v1/workspaces/{workspace_id}/transactions`
   * `/api/v1/workspaces/{workspace_id}/transfers`
2. **Context-Header / Default Workspace Paths:**
   * `/api/v1/transactions` (resolves workspace from active profile or `X-Workspace-Id` header)
   * `/api/v1/transfers`

All endpoints require an authenticated user bearer token (`Authorization: Bearer <jwt_token>`).

---

## 2. RBAC Permissions Matrix

Permissions are validated on every request against the user's role in the specified workspace:

| Operation | Method & Route Pattern | Required Permission | Allowed Roles |
| :--- | :--- | :--- | :--- |
| **List Transactions** | `GET /workspaces/{w_id}/transactions` | `transaction:read` | Owner, Admin, Member, Viewer, Accountant |
| **Get Transaction** | `GET /workspaces/{w_id}/transactions/{id}` | `transaction:read` | Owner, Admin, Member, Viewer, Accountant |
| **Create Transaction** | `POST /workspaces/{w_id}/transactions` | `transaction:write` | Owner, Admin, Member, Accountant |
| **Update Metadata** | `PATCH /workspaces/{w_id}/transactions/{id}`| `transaction:write` | Owner, Admin, Member, Accountant |
| **Post / Settle** | `POST /workspaces/{w_id}/transactions/{id}/post` | `transaction:write` | Owner, Admin, Member, Accountant |
| **Cancel Pending** | `POST /workspaces/{w_id}/transactions/{id}/cancel` | `transaction:write` | Owner, Admin, Member |
| **Reverse Transaction**| `POST /workspaces/{w_id}/transactions/{id}/reverse` | `transaction:reverse` | Owner, Admin, Accountant |
| **Refund Transaction** | `POST /workspaces/{w_id}/transactions/{id}/refund` | `transaction:write` | Owner, Admin, Member, Accountant |
| **Create Transfer** | `POST /workspaces/{w_id}/transfers` | `transaction:write` | Owner, Admin, Member |
| **Get Transfer Pair** | `GET /workspaces/{w_id}/transfers/{transfer_id}` | `transaction:read` | Owner, Admin, Member, Viewer, Accountant |
| **View Audit History**| `GET /workspaces/{w_id}/transactions/{id}/history` | `transaction:read` | Owner, Admin, Accountant |

---

## 3. Endpoints Documentation

### 3.1 List Transactions
`GET /api/v1/workspaces/{workspace_id}/transactions`

#### Query Parameters:
- `limit` (int, default: 50, max: 200): Maximum records to return.
- `offset` (int, default: 0): Records to skip for pagination.
- `account_id` (UUID, optional): Filter transactions by account.
- `category_id` (UUID, optional): Filter by category.
- `status` (string, optional): Filter by lifecycle state (`pending`, `posted`, `failed`, `cancelled`, `reversed`).
- `transaction_type` (string, optional): Filter by transaction taxonomy type.
- `direction` (string, optional): Filter by `inflow`, `outflow`, or `neutral`.
- `start_date` (ISO-8601 string, optional): Inclusive lower bound for `transaction_date`.
- `end_date` (ISO-8601 string, optional): Inclusive upper bound for `transaction_date`.
- `search` (string, optional): Free-text substring match on `description` and `merchant_name`.
- `order_by` (string, default: `transaction_date`): Sort column (`transaction_date`, `amount`, `created_at`).
- `order_dir` (string, default: `desc`): Sort direction (`asc` or `desc`).

#### Success Response (`200 OK`):
```json
{
  "items": [
    {
      "id": "7f8b91a2-3c4d-5e6f-a7b8-c9d0e1f2a3b4",
      "workspace_id": "414851b4-2b9b-4cc9-b64e-1dd302cefa0a",
      "account_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "transaction_type": "expense",
      "direction": "outflow",
      "status": "posted",
      "amount": "1499.00",
      "amount_paise": 149900,
      "currency": "INR",
      "transaction_date": "2026-11-14T05:30:00Z",
      "description": "Monthly Cloud Hosting Subscription",
      "merchant_name": "DigitalOcean",
      "category_id": null,
      "tags": ["cloud", "infrastructure", "tax_deductible"],
      "source_type": "manual",
      "source_provenance": {},
      "external_reference": null,
      "transfer_id": null,
      "related_transaction_id": null,
      "reversal_reason": null,
      "created_by_id": "b3c4d5e6-f7a8-9b0c-1d2e-3f4a5b6c7d8e",
      "metadata": {
        "invoice_number": "INV-2026-11"
      },
      "created_at": "2026-11-14T05:31:00Z",
      "updated_at": "2026-11-14T05:31:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### 3.2 Create / Intake Transaction
`POST /api/v1/workspaces/{workspace_id}/transactions`

#### Request Body:
```json
{
  "account_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "transaction_type": "expense",
  "amount": "2499.50",
  "currency": "INR",
  "transaction_date": "2026-11-14T08:00:00Z",
  "description": "Office Supplies & Paper",
  "merchant_name": "Staples India",
  "status": "posted",
  "source_type": "manual",
  "tags": ["office", "stationery"],
  "external_reference": "MAN-TX-20261114-001",
  "metadata": {
    "store_location": "Bangalore"
  }
}
```

#### Success Response (`201 Created`): Returns the complete `TransactionResponse` entity.

---

### 3.3 Create Paired Account Transfer
`POST /api/v1/workspaces/{workspace_id}/transfers`

#### Request Body:
```json
{
  "source_account_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "destination_account_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
  "amount": "15000.00",
  "currency": "INR",
  "transaction_date": "2026-11-14T09:00:00Z",
  "description": "Savings to Investment Fund transfer",
  "metadata": {
    "transfer_channel": "IMPS"
  }
}
```

#### Success Response (`201 Created`):
```json
{
  "transfer_id": "9a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
  "source_transaction": {
    "id": "c1f7a8b4-9e32-4d51-87ab-893cf1a02931",
    "account_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "transaction_type": "transfer_out",
    "direction": "outflow",
    "amount": "15000.00",
    "amount_paise": 1500000,
    "status": "posted",
    "transfer_id": "9a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
    "related_transaction_id": "d2a8b9c5-0f43-5e62-98bc-904da2b13042"
  },
  "destination_transaction": {
    "id": "d2a8b9c5-0f43-5e62-98bc-904da2b13042",
    "account_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
    "transaction_type": "transfer_in",
    "direction": "inflow",
    "amount": "15000.00",
    "amount_paise": 1500000,
    "status": "posted",
    "transfer_id": "9a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
    "related_transaction_id": "c1f7a8b4-9e32-4d51-87ab-893cf1a02931"
  }
}
```

---

### 3.4 Compensating Reversal
`POST /api/v1/workspaces/{workspace_id}/transactions/{transaction_id}/reverse`

#### Request Body:
```json
{
  "reversal_reason": "Duplicate charge verified with merchant billing department"
}
```

#### Success Response (`200 OK`):
Returns the updated original transaction with `status = "reversed"`, `reversal_reason`, and inverted account balance mutations committed.

---

### 3.5 Record Refund
`POST /api/v1/workspaces/{workspace_id}/transactions/{transaction_id}/refund`

#### Request Body:
```json
{
  "amount": "1200.00",
  "description": "Partial refund for returned damaged goods",
  "transaction_date": "2026-11-14T10:00:00Z"
}
```

#### Validation:
Returns `400 Bad Request` with `MAX_REFUND_EXCEEDED` if cumulative refunds exceed the original transaction amount.
