# ARTHSAVORA DATABASE ARCHITECTURE
## PostgreSQL Relational Foundation, Multi-Tenant Domain Models & Double-Entry Accounting Ledger

---

## 1. Executive Summary & Authoritative Source of Truth

PostgreSQL 15+ serves as the single, authoritative, relational financial source of truth for **ARTHSAVORA**. The database architecture is engineered to provide absolute mathematical precision, tamper-resistant auditability, multi-tenant isolation, and scalable commercial fintech operations in India.

### Core Architectural Invariants
1. **PostgreSQL as Source of Truth:** All user balances, accounts, transactions, invoices, and accounting ledger lines reside in PostgreSQL. No external document store (e.g. MongoDB) or transient cache may serve as authoritative financial state.
2. **Absolute Prohibition of Floating-Point Storage:** All currency and monetary fields enforce `NUMERIC(18, 4)` or minor unit integers. Floating-point types (`float`, `double precision`) are strictly prohibited to prevent IEEE 754 precision drift.
3. **Explicit Multi-Tenant Workspace Scoping:** Every user-facing financial record belongs to an explicit `workspace_id`. Cross-workspace queries and foreign key associations are strictly prevented.
4. **Double-Entry General Ledger Balance:** Every financial transaction translates into a balanced journal entry where $\sum \text{Debits} = \sum \text{Credits}$. Posted journal entries are strictly immutable.
5. **Idempotency & Deduplication:** External bank statement imports and UPI SMS records are uniquely indexed by `(workspace_id, external_transaction_id)` to ensure repeated imports produce zero duplicate records.

---

## 2. Entity Relationship Diagram (ERD)

```text
       ┌──────────────┐
       │    users     │◄───────────────────┐
       └──────┬───────┘                    │
              │ 1:1                        │
              ▼                            │ owner_id / created_by
       ┌──────────────┐             ┌──────┴───────┐
       │user_profiles │             │  workspaces  │
       └──────────────┘             └──────┬───────┘
                                           │
         ┌───────────────────┬─────────────┼────────────────────┐
         │ 1:N               │ 1:N         │ 1:N                │ 1:N
         ▼                   ▼             ▼                    ▼
┌─────────────────┐   ┌─────────────┐ ┌──────────────┐   ┌──────────────┐
│workspace_members│   │  accounts   │ │  categories  │   │ data_sources │
└─────────────────┘   └──────┬──────┘ └──────┬───────┘   └──────┬───────┘
                             │               │                  │ 1:N
                             │ 1:N           │ 1:N              ▼
                             ▼               ▼           ┌──────────────┐
                      ┌──────────────────────────────┐   │ consent_recs │
                      │         transactions         │   ├──────────────┤
                      └──────────────┬───────────────┘   │ import_jobs  │
                                     │                   └──────┬───────┘
                                     │ source_id                │ 1:N
                                     ▼                          ▼
                              ┌──────────────┐           ┌──────────────┐
                              │journal_entries           │ import_files │
                              └──────┬───────┘           └──────────────┘
                                     │ 1:N
                                     ▼
                              ┌──────────────┐       ┌──────────────┐
                              │journal_lines │◄──────┤ledger_account│
                              └──────────────┘       └──────────────┘
```

---

## 3. Domain Modules & Relational Schema

### 3.1 Identity & User Profiles
- **`users`:** Authoritative user account table supporting both local credentials and delegated authentication providers (Supabase Auth, Google OAuth). Tracks active status, verification, security stamps, and audit timestamps.
- **`user_profiles`:** Encapsulates locale preferences, default currency (`INR`), timezone (`Asia/Kolkata`), theme (`dark`), and notification settings.

### 3.2 Multi-Tenant Workspaces & RBAC
- **`workspaces`:** Top-level multi-tenant boundary. Categorized into `personal`, `family`, and `business`. Holds default currency, timezone, operational status, and extensible JSONB settings.
- **`workspace_members`:** Junction table binding users to workspaces with granular roles:
  - **Personal:** `owner`
  - **Family:** `owner`, `admin`, `member`, `viewer`
  - **Business:** `owner`, `admin`, `accountant`, `approver`, `staff`, `viewer`
  - Enforces `UNIQUE(workspace_id, user_id)` and preserves historical attribution upon revocation.

### 3.3 Financial Accounts
- **`accounts`:** Represents real-world financial endpoints: `cash`, `bank`, `savings`, `current`, `credit_card`, `loan`, `investment`, `wallet`.
  - Captures masked account identifiers (`XX4092`), institutional names (e.g. HDFC Bank, ICICI Bank), currency, and lifecycle dates.
  - Full card numbers, CVVs, and banking passwords are never stored.

### 3.4 Financial Data Acquisition & Consents
- **`data_sources`:** External origin connection tracking (`manual`, `upi_sms`, `statement_upload`, `aa_consent`).
- **`consent_records`:** Comprehensive consent governance tracking purpose, data categories, recipient, consent timestamp, expiry, and revocation state.
- **`import_jobs`:** Manages batch ingestion jobs with real-time counters (`total_records`, `success_records`, `failed_records`) and error summaries.
- **`import_files`:** Tracks uploaded statement documents, storage URIs, and cryptographic SHA-256 hashes (`file_hash`) for idempotent file deduplication.

### 3.5 Categorization
- **`categories`:** Hierarchical classification tree supporting parent-child subcategories (`parent_id`).
  - Supports universal system-default categories (`workspace_id IS NULL`) and workspace-custom categories (`workspace_id = UUID`).
  - Enforces `UNIQUE(workspace_id, slug)`.

### 3.6 Financial Transactions
- **`transactions`:** Authoritative record for all operational cash movements.
  - Supports types: `income`, `expense`, `transfer`, `refund`, `reversal`, `loan_disbursal`, `loan_repayment`, `credit_card_purchase`, `credit_card_payment`, `investment`, `withdrawal`, `deposit`, `interest`, `fee`, `tax`, `cash`, `pending`, `unknown`.
  - Stores exact decimal amounts in `NUMERIC(18, 4)`.
  - Enforces `UNIQUE(workspace_id, external_transaction_id) WHERE external_transaction_id IS NOT NULL` to prevent duplicate ingestion.
  - Flags AI-predicted classifications with `is_ai_predicted` and `ai_confidence` score.

### 3.7 Double-Entry General Ledger
- **`ledger_accounts` (Chart of Accounts):** Standardized accounting classes (`asset`, `liability`, `equity`, `revenue`, `expense`) with normal balance designation (`debit` or `credit`).
- **`journal_entries`:** Immutable transaction container with sequential `entry_number`, `entry_date`, and posting status (`draft`, `posted`, `reversed`).
- **`journal_lines`:** Balanced legs of the journal entry. Each line carries `line_number`, `entry_type` (`debit` or `credit`), and exact positive amount `NUMERIC(18, 4)`.
- **Invariants:**
  - Posting requires $\sum \text{Debits} = \sum \text{Credits}$.
  - Posted entries are strictly immutable. Corrections require formal reversal entries (`reverse_journal_entry()`).

### 3.8 Audit Trail
- **`audit_logs`:** Append-oriented immutable ledger capturing actor, action (`CREATE`, `UPDATE`, `DELETE`, `POST_JOURNAL`, `REVERSE_JOURNAL`), entity, correlation ID (`X-Request-ID`), IP address, and sanitized state snapshots.
- Survives member revocation to ensure permanent regulatory audit compliance.

---

## 4. Multi-Tenant Isolation & Row-Level Security (RLS)

Arthsavora employs a dual-layer defense-in-depth security model:
1. **Application-Layer Authorization (Primary):** FastAPI dependency injection verifies that the authenticated user holds an active membership in the requested `workspace_id`.
2. **PostgreSQL Row-Level Security (Defense-in-Depth):**
   - Tables carry `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
   - Security policy filters: `workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid`.
   - The application manages context using `SET LOCAL app.current_workspace_id = '...'` inside transactional blocks, guaranteeing that connection pooling cannot leak tenant context across requests.
