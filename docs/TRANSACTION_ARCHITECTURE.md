# Arthsavora — Transaction Engine Architecture

## 1. Executive Summary & Core Principles

The transaction engine in **Arthsavora** serves as the authoritative ledger for every monetary movement within personal, family, and business workspaces. Because subsequent financial intelligence, double-entry accounting, budgeting, cash flow forecasting, and AI advisory features depend directly on the integrity of transaction records, the engine is designed under five immutable engineering principles:

1. **Exact Monetary Precision (Paise-Native Arithmetic):** Floating-point data types are strictly prohibited in database persistence and business calculations. All financial amounts are stored as integer paise (`amount_paise`, `BIGINT`) and accompanied by a canonical high-precision decimal column (`amount`, `NUMERIC(18, 4)`) for international and multi-currency reporting.
2. **Immutability of Posted Financial Facts:** A transaction with status `posted` represents a real-world financial occurrence that has altered an account's ledger balance. Its financial parameters—amount, currency, account reference, transaction date, and direction—are permanently immutable. Corrections and cancellations must be effected via formal compensating reversals or refunds.
3. **Strict Workspace Isolation & Multi-Tenancy:** Transactions are bound to a single workspace (`workspace_id`). Every repository query and service mutation enforces workspace boundaries, returning `404 Not Found` for cross-workspace identifier references to eliminate insecure direct object reference (IDOR) vulnerabilities.
4. **Dual Balance Synchronization:** When transactions transition between lifecycle states (e.g., from `pending` to `posted` or `reversed`), balance mutations are applied atomically to the parent `FinancialAccount`. The system synchronizes `current_book_balance_paise`, `available_balance_paise`, and `outstanding_liability_paise` within the same database transaction.
5. **Multi-Source Provenance & Auditability:** Every transaction records its origin (`source_type`: `manual`, `bank_sync`, `csv_import`, `sms_parsed`, `ocr_receipt`, `recurring_rule`, `api`, `system`), full ingestion metadata (`source_provenance`), and the authenticated user identity (`created_by_id`).

---

## 2. High-Level Engine Architecture

The transaction architecture follows a clean modular-monolith design within FastAPI and SQLAlchemy, strictly separating presentation, application services, domain business rules, and infrastructure persistence:

```
+-----------------------------------------------------------------------------------+
|                               Presentation Layer                                  |
|   /api/v1/workspaces/{workspace_id}/transactions  |  /api/v1/transactions        |
|   /api/v1/workspaces/{workspace_id}/transfers     |  /api/v1/transfers           |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Application Service Layer                                  |
|                       (TransactionService)                                        |
|   - Request validation & Money parsing                                           |
|   - Workspace permission checks (RBAC)                                            |
|   - Deduplication verification (External Reference & Idempotency)                 |
|   - Lifecycle state machine execution                                             |
|   - Paired transfer coordination                                                  |
|   - Cumulative refund validation                                                  |
|   - Compensating reversal creation                                                |
|   - Atomic balance synchronization with FinancialAccount                          |
|   - Domain event dispatching                                                      |
+-----------------------------------------+-----------------------------------------+
                                          |
                   +----------------------+----------------------+
                   |                                             |
                   v                                             v
+--------------------------------------+   +---------------------------------------+
|            Domain Layer              |   |          Infrastructure Layer         |
|  - Value Objects: Money, Currency    |   |  - TransactionRepository              |
|  - Taxonomy: TransactionType         |   |  - AccountRepository                  |
|  - Direction: TransactionDirection   |   |  - SQLAlchemy ORM: Transaction,       |
|  - Lifecycle: TransactionStatus      |   |    FinancialAccount, Workspace        |
|  - State Transition Matrix           |   |  - PostgreSQL Database                |
|  - Domain Events                     |   |  - Alembic Migrations                 |
+--------------------------------------+   +---------------------------------------+
```

---

## 3. Data Model & Dual Monetary Precision

### 3.1 Schema Definition
The `transactions` table is defined in PostgreSQL with exact precision, foreign key constraints, and specialized partial indexes:

```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES financial_accounts(id) ON DELETE RESTRICT,
    transaction_type VARCHAR(50) NOT NULL,
    direction VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'posted',
    amount NUMERIC(18, 4) NOT NULL,
    amount_paise BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    transaction_date TIMESTAMPTZ NOT NULL,
    description TEXT NOT NULL,
    merchant_name VARCHAR(255),
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_type VARCHAR(50) NOT NULL DEFAULT 'manual',
    source_provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    external_reference VARCHAR(255),
    idempotency_key VARCHAR(255),
    transfer_id UUID,
    related_transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    reversal_reason TEXT,
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- Indices
CREATE INDEX ix_transactions_workspace_date ON transactions(workspace_id, transaction_date DESC);
CREATE INDEX ix_transactions_account_date ON transactions(account_id, transaction_date DESC);
CREATE INDEX ix_transactions_category ON transactions(category_id) WHERE category_id IS NOT NULL;
CREATE INDEX ix_transactions_status ON transactions(status);
CREATE INDEX ix_transactions_transfer_id ON transactions(transfer_id) WHERE transfer_id IS NOT NULL;
CREATE INDEX ix_transactions_related_id ON transactions(related_transaction_id) WHERE related_transaction_id IS NOT NULL;
CREATE UNIQUE INDEX uq_workspace_external_tx ON transactions(workspace_id, source_type, external_reference) 
    WHERE external_reference IS NOT NULL;
CREATE INDEX ix_transactions_idempotency ON transactions(workspace_id, idempotency_key) 
    WHERE idempotency_key IS NOT NULL;
```

### 3.2 Dual Precision Rationale
- **Integer Paise (`amount_paise` BIGINT):** Stores minor units ($1 \text{ INR} = 100 \text{ paise}$). Storing values as integers guarantees $0.10 + 0.20 = 0.30$ without IEEE-754 binary floating-point rounding errors. This column is the foundation for all balance calculations, reconciliation algorithms, and ledger queries.
- **Decimal Amount (`amount` NUMERIC(18, 4)):** Stores human-readable major currency units with 4 decimal places. This supports fractional currency units, foreign exchange rates (e.g., USD/INR conversions), and institutional reporting.
- **Validation Constraint:** The domain layer guarantees that `amount_paise == round(amount * 100)`.

---

## 4. Direction Taxonomy & Balance Mutation Pipeline

### 4.1 Canonical Directions
Every transaction is categorized into one of three canonical directions:
1. `inflow`: Increases asset book balance or decreases loan liability (money arriving into the user's possession).
2. `outflow`: Decreases asset book balance or increases credit liability (money leaving the user's possession).
3. `neutral`: Balance-neutral transactions (e.g., memo adjustments or informational entries that do not alter monetary balances).

### 4.2 Account Balance Mutations
When a transaction is `posted`, its direction and the account's classification determine which account balance is updated:

| Account Classification | Inflow Effect | Outflow Effect |
| :--- | :--- | :--- |
| **Asset Accounts** (Savings, Current, Cash, Wallet, Investment) | `current_book_balance += amount_paise`<br>`available_balance += amount_paise` | `current_book_balance -= amount_paise`<br>`available_balance -= amount_paise` |
| **Liability Accounts** (Credit Card) | `outstanding_liability -= amount_paise`<br>`available_balance += amount_paise` | `outstanding_liability += amount_paise`<br>`available_balance -= amount_paise` |
| **Liability Accounts** (Personal Loan, Home Loan, Business Loan) | `outstanding_liability -= amount_paise` (Principal repayment) | `outstanding_liability += amount_paise` (Borrowing / disbursement) |

When a transaction is `pending`, asset accounts hold the funds in reserve:
- `available_balance -= amount_paise` (for outflow)
- `current_book_balance` remains unchanged until the transaction is confirmed as `posted`.

---

## 5. Provenance & Audit Trail Architecture

Arthsavora enforces full traceability for every financial entry:
- **`source_type`:** Classifies the capture channel (`manual`, `bank_sync`, `csv_import`, `sms_parsed`, `ocr_receipt`, `recurring_rule`, `api`, `system`).
- **`source_provenance`:** A structured JSON object containing channel-specific audit attributes:
  * Bank Sync: `{ "aggregator": "setu", "institution_id": "HDFC", "account_mask": "1234", "raw_ref": "UPI/4123..." }`
  * SMS Parsing: `{ "parser_version": "1.2", "sender": "VM-HDFCBK", "raw_hash": "a1b2c3...", "confidence": 0.98 }`
  * Receipt OCR: `{ "ocr_engine": "tesseract-5", "receipt_id": "uuid", "confidence_score": 0.94 }`
  * API / Import: `{ "file_name": "statement_oct2026.csv", "row_number": 42, "batch_id": "uuid" }`
- **`created_by_id`:** Records the exact authenticated user who initiated or authorized the transaction.
- **Audit Logs:** Every lifecycle event publishes an audit event to the `audit_logs` table containing the previous state, new state, client IP, user agent, and timestamp.
