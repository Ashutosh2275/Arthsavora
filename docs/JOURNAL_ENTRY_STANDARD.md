# ARTHSAVORA — Journal Entry Standard & Data Model

## 1. Introduction

A Journal Entry is the atomic transaction record of the double-entry accounting engine. Every financial transaction affecting a workspace's balance sheet or income statement is captured as a structured `JournalEntry` containing two or more `JournalLine` items.

---

## 2. Journal Entry Header Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` (PK) | Unique entry identifier |
| `workspace_id` | `UUID` (FK) | Workspace isolation scope |
| `entry_number` | `VARCHAR(32)` | Sequential reference identifier (e.g. `JE-2026-000001`) |
| `entry_date` | `DATE` | Accounting effective date (defaults to UTC today) |
| `status` | `VARCHAR(20)` | `draft` \| `posted` \| `reversed` |
| `source_type` | `VARCHAR(32)` | `manual` \| `transaction` \| `reversal` \| `closing` |
| `source_id` | `UUID` (Nullable) | Link to originating operational transaction or entity |
| `accounting_period_id` | `UUID` (Nullable FK)| Link to active `AccountingPeriod` |
| `description` | `TEXT` | Human-readable explanation / narrative |
| `reversal_of_id` | `UUID` (Nullable FK) | Reference to original entry if this is a compensating reversal |
| `reversal_reason` | `TEXT` (Nullable) | Mandatory justification for reversal entries |
| `posted_at` | `TIMESTAMPTZ` (Nullable)| Timestamp when entry transitioned to `posted` |
| `posted_by_id` | `UUID` (Nullable FK) | User who executed the posting |
| `created_at` | `TIMESTAMPTZ` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | Record update timestamp |

---

## 3. Journal Line Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` (PK) | Unique line identifier |
| `journal_entry_id` | `UUID` (FK) | Parent journal entry reference (Cascade on draft delete) |
| `ledger_account_id` | `UUID` (FK) | Target general ledger account |
| `entry_type` | `VARCHAR(10)` | `debit` or `credit` |
| `amount` | `NUMERIC(18, 4)` | High-precision decimal monetary value ($> 0$) |
| `amount_paise` | `BIGINT` | Integer currency value in Indian paise ($100 \times \text{amount}$) |
| `currency` | `VARCHAR(3)` | ISO 4217 currency code (default: `INR`) |
| `description` | `TEXT` (Nullable) | Line-specific memo or line note |
| `financial_account_id`| `UUID` (Nullable FK)| Link to operational `financial_accounts` record |
| `counterparty_name` | `VARCHAR(255)` (Null)| Counterparty name (merchant, vendor, employer, lender) |
| `source_metadata` | `JSONB` | Flexible payload storing transaction tags, reference IDs |

---

## 4. Fundamental Invariants & Constraints

1. **Dual Representation:** Every line has positive `amount` and positive `amount_paise`. Negative lines are forbidden (`CHECK (amount > 0 AND amount_paise > 0)`).
2. **Debit-Credit Balance on Post:**
   $$\sum_{\text{lines with entry\_type='debit'}} \text{amount} = \sum_{\text{lines with entry\_type='credit'}} \text{amount}$$
   $$\sum_{\text{lines with entry\_type='debit'}} \text{amount\_paise} = \sum_{\text{lines with entry\_type='credit'}} \text{amount\_paise}$$
3. **Minimum Line Count:** Every posted journal entry must contain at least 2 lines ($\ge 2$).
4. **Audit Trail Completeness:** Reversals require both `reversal_of_id` and non-empty `reversal_reason`.
