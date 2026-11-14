# ARTHSAVORA — General Ledger & Accounting API Reference

## 1. Overview & Dual Route Pattern

The Accounting & General Ledger API is exposed under both workspace-scoped and top-level RESTful routes:
- `/api/v1/workspaces/{workspace_id}/ledger/...` (Canonical hierarchical format)
- `/api/v1/ledger/...` (Convenience route defaulting to active workspace via header/query/cookie)

All endpoints require active user authentication and workspace role-based authorization (`VIEW_LEDGER`, `MANAGE_LEDGER`, `POST_JOURNAL`, `REVERSE_JOURNAL`, `MANAGE_PERIODS`).

---

## 2. Endpoints Summary

| Method | Endpoint | Description | Required Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/workspaces/{workspace_id}/ledger/accounts` | List chart of accounts with hierarchical codes | `VIEW_LEDGER` |
| `POST` | `/workspaces/{workspace_id}/ledger/accounts` | Create a custom ledger account | `MANAGE_LEDGER` |
| `GET` | `/workspaces/{workspace_id}/ledger/accounts/{id}/balance`| Get derived net debit/credit balance of an account | `VIEW_LEDGER` |
| `GET` | `/workspaces/{workspace_id}/ledger/periods` | List all accounting periods | `VIEW_LEDGER` |
| `POST` | `/workspaces/{workspace_id}/ledger/periods` | Create a new accounting period | `MANAGE_PERIODS` |
| `POST` | `/workspaces/{workspace_id}/ledger/periods/{id}/close` | Close an accounting period (locks postings) | `MANAGE_PERIODS` |
| `POST` | `/workspaces/{workspace_id}/ledger/periods/{id}/reopen` | Reopen an accounting period | `MANAGE_PERIODS` |
| `GET` | `/workspaces/{workspace_id}/ledger/journals` | List journal entries with filters and pagination | `VIEW_LEDGER` |
| `POST` | `/workspaces/{workspace_id}/ledger/journals` | Create a new draft journal entry | `MANAGE_LEDGER` |
| `GET` | `/workspaces/{workspace_id}/ledger/journals/{id}` | Get single journal entry with line items | `VIEW_LEDGER` |
| `POST` | `/workspaces/{workspace_id}/ledger/journals/{id}/post` | Post a draft journal entry (validates balance) | `POST_JOURNAL` |
| `POST` | `/workspaces/{workspace_id}/ledger/journals/{id}/reverse` | Create a compensating reversal entry | `REVERSE_JOURNAL` |
| `GET` | `/workspaces/{workspace_id}/ledger/trial-balance` | Generate Trial Balance report | `VIEW_LEDGER` |

---

## 3. Request & Response Payloads

### 3.1 Create Draft Journal Entry
`POST /api/v1/workspaces/{workspace_id}/ledger/journals`

**Request Body:**
```json
{
  "entry_number": "JE-2026-000105",
  "entry_date": "2026-11-14",
  "description": "Monthly Office Rent Payment",
  "source_type": "manual",
  "lines": [
    {
      "ledger_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "entry_type": "debit",
      "amount": "45000.0000",
      "description": "Office rent for Nov 2026",
      "counterparty_name": "DLF Cybercity Landlords"
    },
    {
      "ledger_account_id": "8bb12345-5717-4562-b3fc-2c963f66afb7",
      "entry_type": "credit",
      "amount": "45000.0000",
      "description": "Paid via HDFC Bank Current Account"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "id": "e9b21f3a-96df-4a92-b05b-b9f44b20ec92",
  "workspace_id": "0d207ec1-8d07-4bf6-a681-432857476839",
  "entry_number": "JE-2026-000105",
  "entry_date": "2026-11-14",
  "status": "draft",
  "source_type": "manual",
  "description": "Monthly Office Rent Payment",
  "lines": [
    {
      "id": "11111111-2222-3333-4444-555555555555",
      "ledger_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "entry_type": "debit",
      "amount": "45000.0000",
      "amount_paise": 4500000,
      "counterparty_name": "DLF Cybercity Landlords"
    },
    {
      "id": "66666666-7777-8888-9999-000000000000",
      "ledger_account_id": "8bb12345-5717-4562-b3fc-2c963f66afb7",
      "entry_type": "credit",
      "amount": "45000.0000",
      "amount_paise": 4500000
    }
  ]
}
```

### 3.2 Post Journal Entry
`POST /api/v1/workspaces/{workspace_id}/ledger/journals/{id}/post`

**Response (200 OK):**
```json
{
  "id": "e9b21f3a-96df-4a92-b05b-b9f44b20ec92",
  "entry_number": "JE-2026-000105",
  "status": "posted",
  "posted_at": "2026-11-14T06:30:00Z",
  "posted_by_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```

### 3.3 Reverse Journal Entry
`POST /api/v1/workspaces/{workspace_id}/ledger/journals/{id}/reverse`

**Request Body:**
```json
{
  "reversal_reason": "Landlord refunded rent invoice due to contract renewal credit",
  "reversal_number": "REV-2026-000042"
}
```

**Response (200 OK):**
Returns newly created compensating `JournalEntry` with status `posted` and lines inverted.

### 3.4 Trial Balance Report
`GET /api/v1/workspaces/{workspace_id}/ledger/trial-balance?as_of_date=2026-11-14`

**Response (200 OK):**
```json
{
  "workspace_id": "0d207ec1-8d07-4bf6-a681-432857476839",
  "as_of_date": "2026-11-14",
  "total_debits": "650000.0000",
  "total_credits": "650000.0000",
  "total_debits_paise": 65000000,
  "total_credits_paise": 65000000,
  "difference": "0.0000",
  "difference_paise": 0,
  "is_balanced": true,
  "accounts": [
    {
      "account_id": "8bb12345-5717-4562-b3fc-2c963f66afb7",
      "code": "1020",
      "name": "Bank Accounts",
      "type": "asset",
      "normal_balance": "debit",
      "debit_balance": "575000.0000",
      "credit_balance": "0.0000",
      "debit_balance_paise": 57500000,
      "credit_balance_paise": 0
    },
    {
      "account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "code": "5010",
      "name": "Housing & Rent",
      "type": "expense",
      "normal_balance": "debit",
      "debit_balance": "60000.0000",
      "credit_balance": "0.0000",
      "debit_balance_paise": 6000000,
      "credit_balance_paise": 0
    },
    {
      "account_id": "7aa99999-5717-4562-b3fc-2c963f66afc9",
      "code": "3010",
      "name": "Owner's Equity / Initial Capital",
      "type": "equity",
      "normal_balance": "credit",
      "debit_balance": "0.0000",
      "credit_balance": "500000.0000",
      "debit_balance_paise": 0,
      "credit_balance_paise": 50000000
    }
  ]
}
```
