# Arthsavora — Financial Accounts API Reference

## 1. Overview & Base URLs

The Financial Accounts API allows client applications to create, list, manage, archive, and reconcile financial accounts within an authorized workspace context.

### Base Paths
All endpoints are available under two interchangeable RESTful path conventions:
1. **Header-Scoped Path:** `/api/v1/accounts/` (requires `X-Workspace-ID: <uuid>` header)
2. **Hierarchical Path:** `/api/v1/workspaces/{workspace_id}/accounts/`

---

## 2. Common Headers

| Header | Required | Type | Description |
| :--- | :--- | :--- | :--- |
| `Authorization` | Yes | `Bearer <JWT>` | Bearer access token issued by Arthsavora auth service. |
| `X-Workspace-ID` | Required for `/accounts/` | `UUID` | Active tenant workspace context identifier. |
| `X-Correlation-ID` / `X-Request-ID` | Optional | `string` | Distributed tracing correlation ID. Returned in all responses. |

---

## 3. Endpoints

### 3.1 List Accounts
Retrieves all accounts in the authorized workspace with optional filtering and bounded pagination.

- **Method:** `GET`
- **Path:** `/api/v1/accounts/` or `/api/v1/workspaces/{workspace_id}/accounts`
- **Query Parameters:**
  - `account_type` (`string`, optional): Filter by account type (`savings`, `credit_card`, `loan`, etc.).
  - `status` (`string`, optional): Filter by status (`active`, `archived`, `closed`).
  - `include_archived` (`boolean`, optional, default `false`): Include archived accounts.
  - `limit` (`integer`, optional, default `50`, max `100`): Page size.
  - `offset` (`integer`, optional, default `0`): Pagination offset.
- **Success Response:** `200 OK` (Array of `AccountResponse`)

```json
[
  {
    "id": "e4b2d189-826d-495c-9c71-3c829da422b1",
    "workspace_id": "9b97a884-d400-44da-8061-9a41e6e0be32",
    "name": "HDFC Salary Savings",
    "account_type": "savings",
    "account_subtype": "salary",
    "description": "Primary salary credit account",
    "currency": "INR",
    "institution_name": "HDFC Bank",
    "masked_identifier": "XX4321",
    "status": "active",
    "opening_date": "2026-01-01",
    "closing_date": null,
    "current_book_balance": "125000.50",
    "current_book_balance_paise": 12500050,
    "available_balance": "125000.50",
    "available_balance_paise": 12500050,
    "provider_reported_balance": "125000.50",
    "provider_reported_balance_paise": 12500050,
    "provider_reported_at": "2026-03-20T10:30:00Z",
    "outstanding_liability": null,
    "outstanding_liability_paise": null,
    "pending_amount": "0.00",
    "pending_amount_paise": 0,
    "credit_limit": null,
    "available_credit": null,
    "due_date": null,
    "interest_rate": null,
    "repayment_amount": null,
    "provider_name": "SetuAA",
    "connection_status": "connected",
    "last_synced_at": "2026-03-20T10:30:00Z",
    "balances": {
      "currency": "INR",
      "book_balance": "125000.50",
      "book_balance_paise": 12500050,
      "available_balance": "125000.50",
      "available_balance_paise": 12500050,
      "provider_reported_balance": "125000.50",
      "provider_reported_balance_paise": 12500050,
      "provider_reported_at": "2026-03-20T10:30:00Z",
      "outstanding_liability": null,
      "outstanding_liability_paise": null,
      "pending_amount": "0.00",
      "pending_amount_paise": 0,
      "opening_balance": "50000.00",
      "opening_balance_paise": 5000000,
      "opening_balance_date": "2026-01-01",
      "opening_balance_source": "manual",
      "credit_limit": null,
      "available_credit": null,
      "statement_balance": null,
      "minimum_due": null,
      "due_date": null,
      "original_principal": null,
      "outstanding_principal": null,
      "interest_rate": null,
      "repayment_amount": null
    },
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-03-20T10:30:00Z"
  }
]
```

---

### 3.2 Create Account
Provisions a new financial container, validates currency & tenancy type, and seeds an initial opening balance snapshot.

- **Method:** `POST`
- **Path:** `/api/v1/accounts/` or `/api/v1/workspaces/{workspace_id}/accounts`
- **Request Body (`AccountCreateRequest`):**

```json
{
  "name": "Amazon Pay ICICI Card",
  "account_type": "credit_card",
  "currency": "INR",
  "institution_name": "ICICI Bank",
  "masked_identifier": "XX2040",
  "credit_limit": "250000.00",
  "outstanding_liability": "14200.00",
  "statement_balance": "14200.00",
  "minimum_due": "750.00",
  "due_date": "2026-04-12"
}
```

- **Success Response:** `201 Created` (`AccountResponse`)
- **Error Responses:**
  - `409 Conflict`: If an external provider connection with same `provider_name` & `provider_account_id` already exists.
  - `422 Unprocessable Entity`: If `currency` or `account_type` is invalid for the workspace tenancy model.

---

### 3.3 Get Account Details
- **Method:** `GET`
- **Path:** `/api/v1/accounts/{id}` or `/api/v1/workspaces/{workspace_id}/accounts/{id}`
- **Success Response:** `200 OK` (`AccountResponse`)
- **Error Response:** `404 Not Found` if account does not exist or belongs to another workspace.

---

### 3.4 Update Account Metadata
Updates user-modifiable fields (name, subtype, notes, masked number).

- **Method:** `PATCH`
- **Path:** `/api/v1/accounts/{id}`
- **Request Body (`AccountUpdateRequest`):**
```json
{
  "name": "Primary ICICI Credit Card",
  "description": "Used for online shopping and bill payments"
}
```
- **Success Response:** `200 OK` (`AccountResponse`)
- **Error Response:** `422 Unprocessable Entity` if account is currently in `archived` or `closed` state.

---

### 3.5 Archive Account
Transitions an account from `active` to `archived`.

- **Method:** `POST`
- **Path:** `/api/v1/accounts/{id}/archive`
- **Success Response:** `200 OK` (`AccountResponse` with `status: "archived"`)

---

### 3.6 Restore Account
Reinstates an archived account back to `active`.

- **Method:** `POST`
- **Path:** `/api/v1/accounts/{id}/restore`
- **Success Response:** `200 OK` (`AccountResponse` with `status: "active"`)

---

### 3.7 Close Account
Permanently closes an account with a verified effective closing date.

- **Method:** `POST`
- **Path:** `/api/v1/accounts/{id}/close`
- **Request Body (`AccountCloseRequest`):**
```json
{
  "closing_date": "2026-03-31",
  "closing_notes": "Closed account at bank branch"
}
```
- **Success Response:** `200 OK` (`AccountResponse` with `status: "closed"`, `closing_date: "2026-03-31"`)
- **Error Response:** `422 Unprocessable Entity` if `closing_date` precedes `opening_date`.

---

### 3.8 Get Account Balances
Returns detailed balance breakdown for an account.

- **Method:** `GET`
- **Path:** `/api/v1/accounts/{id}/balances`
- **Success Response:** `200 OK` (`BalanceBreakdown`)

---

### 3.9 Record Balance Snapshot
Appends an immutable point-in-time snapshot to the account's history and updates the account's fast-read pointer.

- **Method:** `POST`
- **Path:** `/api/v1/accounts/{id}/balances/snapshot`
- **Request Body (`AccountBalanceSnapshotCreateRequest`):**
```json
{
  "balance_type": "provider_reported",
  "balance_amount": "142500.75",
  "currency": "INR",
  "source": "account_aggregator",
  "source_reference": "sync_batch_7781"
}
```
- **Success Response:** `201 Created` (`AccountBalanceSnapshotResponse`)

---

### 3.10 List Balance History
Retrieves chronological point-in-time balance snapshot history for the account.

- **Method:** `GET`
- **Path:** `/api/v1/accounts/{id}/balance-history`
- **Query Parameters:**
  - `balance_type` (`string`, optional): Filter by type (`book`, `available`, `provider_reported`, `liability`, `opening`).
  - `limit` (`integer`, optional, default `50`): Page size.
  - `offset` (`integer`, optional, default `0`): Pagination offset.
- **Success Response:** `200 OK` (Array of `AccountBalanceSnapshotResponse`)
