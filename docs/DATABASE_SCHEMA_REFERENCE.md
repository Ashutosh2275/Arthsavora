# ARTHSAVORA DATABASE SCHEMA REFERENCE
## Comprehensive Table Specifications, Column Data Types, Indexes & Constraints

---

## 1. Relational Table Specifications

### 1.1 `users`
Authoritative user registry.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `UUID` | `PRIMARY KEY`, Default `gen_random_uuid()` | Immutable user identifier |
| `email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE`, Indexed | Primary login and communication handle |
| `full_name` | `VARCHAR(255)` | `NOT NULL` | User legal / display name |
| `hashed_password`| `VARCHAR(255)` | `NULLABLE` | Bcrypt hash (null for delegated OAuth users) |
| `auth_provider` | `VARCHAR(50)` | `NOT NULL`, Default `'local'` | Authentication source (`local`, `supabase`, `google`) |
| `auth_provider_id`| `VARCHAR(255)`| `NULLABLE`, Indexed | Provider subject / UID |
| `phone_number` | `VARCHAR(20)` | `NULLABLE` | Contact telephone number |
| `is_active` | `BOOLEAN` | `NOT NULL`, Default `TRUE` | Account active flag |
| `is_verified` | `BOOLEAN` | `NOT NULL`, Default `FALSE` | Email verification flag |
| `last_login_at` | `TIMESTAMPTZ` | `NULLABLE` | Last successful login timestamp |
| `security_stamp`| `VARCHAR(64)` | `NULLABLE` | Invalidation stamp for revoking sessions |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, Default `CURRENT_TIMESTAMP` | Record creation timestamp (UTC) |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL`, Default `CURRENT_TIMESTAMP` | Record last modification timestamp (UTC) |
| `is_deleted` | `BOOLEAN` | `NOT NULL`, Default `FALSE` | Soft delete flag |
| `deleted_at` | `TIMESTAMPTZ` | `NULLABLE` | Soft delete timestamp (UTC) |

---

### 1.2 `user_profiles`
User preferences and locale settings.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `UUID` | `PRIMARY KEY` | Profile identifier |
| `user_id` | `UUID` | `NOT NULL`, `UNIQUE`, `FK users(id) ON DELETE CASCADE` | Associated user reference |
| `default_currency`| `VARCHAR(3)` | `NOT NULL`, Default `'INR'` | ISO 4217 currency code |
| `timezone` | `VARCHAR(50)` | `NOT NULL`, Default `'Asia/Kolkata'` | IANA timezone identifier |
| `locale` | `VARCHAR(10)` | `NOT NULL`, Default `'en-IN'` | BCP 47 locale tag |
| `theme` | `VARCHAR(20)` | `NOT NULL`, Default `'dark'` | UI theme preference |
| `notification_preferences`| `JSONB`| `NOT NULL`, Default `'{}'` | Granular email/SMS notification settings |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | Update timestamp |

---

### 1.3 `workspaces`
Tenant boundary for personal, household, and commercial finance.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `UUID` | `PRIMARY KEY` | Workspace identifier |
| `name` | `VARCHAR(255)` | `NOT NULL` | Workspace title |
| `slug` | `VARCHAR(100)` | `NOT NULL`, `UNIQUE`, Indexed | URL-safe workspace slug |
| `type` | `VARCHAR(20)` | `NOT NULL` | Workspace type (`personal`, `family`, `business`) |
| `owner_id` | `UUID` | `NOT NULL`, `FK users(id) ON DELETE RESTRICT` | Primary workspace owner |
| `default_currency`| `VARCHAR(3)` | `NOT NULL`, Default `'INR'` | Workspace operating currency |
| `timezone` | `VARCHAR(50)` | `NOT NULL`, Default `'Asia/Kolkata'` | Default timezone |
| `status` | `VARCHAR(30)` | `NOT NULL`, Default `'active'` | Lifecycle status (`active`, `suspended`, `archived`) |
| `settings` | `JSONB` | `NOT NULL`, Default `'{}'` | Custom workspace configuration |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | Update timestamp |
| `is_deleted` | `BOOLEAN` | `NOT NULL`, Default `FALSE` | Soft delete flag |
| `deleted_at` | `TIMESTAMPTZ` | `NULLABLE` | Soft delete timestamp |

---

### 1.4 `workspace_members`
User memberships and role assignments.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `UUID` | `PRIMARY KEY` | Membership identifier |
| `workspace_id` | `UUID` | `NOT NULL`, `FK workspaces(id) ON DELETE CASCADE` | Target workspace |
| `user_id` | `UUID` | `NOT NULL`, `FK users(id) ON DELETE CASCADE` | Target user |
| `role` | `VARCHAR(30)` | `NOT NULL` | Assigned role (`owner`, `admin`, `member`, `accountant`, `viewer`) |
| `status` | `VARCHAR(20)` | `NOT NULL`, Default `'active'` | Membership status (`active`, `invited`, `revoked`) |
| `invitation_token`| `VARCHAR(100)`| `NULLABLE`, Indexed | Pending invite token |
| `joined_at` | `TIMESTAMPTZ` | `NOT NULL` | Membership acceptance timestamp |
| `revoked_at` | `TIMESTAMPTZ` | `NULLABLE` | Access revocation timestamp |
| **Constraint** | `UNIQUE(workspace_id, user_id)` | Enforces single membership per user per workspace |

---

### 1.5 `accounts`
Financial bank accounts, wallets, cash boxes, and credit cards.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `UUID` | `PRIMARY KEY` | Account identifier |
| `workspace_id` | `UUID` | `NOT NULL`, `FK workspaces(id) ON DELETE CASCADE`, Indexed | Owning workspace |
| `name` | `VARCHAR(255)` | `NOT NULL` | Account name (e.g. "HDFC Salary Account") |
| `account_type` | `VARCHAR(30)` | `NOT NULL` | Type (`bank`, `savings`, `current`, `credit_card`, `cash`, `wallet`) |
| `currency` | `VARCHAR(3)` | `NOT NULL`, Default `'INR'` | Operating currency |
| `institution_name`| `VARCHAR(255)`| `NULLABLE` | Bank / NBFC name |
| `masked_identifier`| `VARCHAR(50)`| `NULLABLE` | Masked identifier (e.g. "XX4092") |
| `status` | `VARCHAR(20)` | `NOT NULL`, Default `'active'` | Status (`active`, `frozen`, `closed`) |
| `opening_date` | `DATE` | `NULLABLE` | Opening date |
| `closing_date` | `DATE` | `NULLABLE` | Closing date |
| `source_metadata`| `JSONB` | `NOT NULL`, Default `'{}'` | Provider and connection metadata |

---

### 1.6 `transactions`
Operational financial ledger transactions.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `UUID` | `PRIMARY KEY` | Transaction identifier |
| `workspace_id` | `UUID` | `NOT NULL`, `FK workspaces(id) ON DELETE CASCADE`, Indexed | Owning workspace |
| `account_id` | `UUID` | `NOT NULL`, `FK accounts(id) ON DELETE RESTRICT`, Indexed | Associated account |
| `transaction_type`| `VARCHAR(30)` | `NOT NULL` | Transaction class (`income`, `expense`, `transfer`, `refund`, etc.) |
| `amount` | `NUMERIC(18, 4)` | `NOT NULL` | Exact fixed-point monetary value |
| `currency` | `VARCHAR(3)` | `NOT NULL`, Default `'INR'` | ISO 4217 currency |
| `transaction_date`| `DATE` | `NOT NULL`, Indexed | Date transaction occurred |
| `settlement_date` | `DATE` | `NULLABLE` | Value / bank clearance date |
| `description` | `VARCHAR(512)` | `NOT NULL` | Transaction narration |
| `merchant_name` | `VARCHAR(255)` | `NULLABLE`, Indexed | Normalized merchant name |
| `category_id` | `UUID` | `NULLABLE`, `FK categories(id) ON DELETE SET NULL`, Indexed | Category classification |
| `status` | `VARCHAR(20)` | `NOT NULL`, Default `'cleared'` | Status (`pending`, `cleared`, `reconciled`, `failed`) |
| `source_reference`| `VARCHAR(255)`| `NULLABLE` | Statement / SMS source reference |
| `external_transaction_id`| `VARCHAR(255)`| `NULLABLE` | External reference ID (Bank UTR, UPI Ref) |
| `original_transaction_id`| `UUID` | `NULLABLE`, `FK transactions(id) ON DELETE SET NULL` | Reversal / refund link |
| `is_ai_predicted`| `BOOLEAN` | `NOT NULL`, Default `FALSE` | AI categorization flag |
| `ai_confidence` | `NUMERIC(5, 4)` | `NULLABLE` | Classification confidence (0.0000 - 1.0000) |
| `metadata` | `JSONB` | `NOT NULL`, Default `'{}'` | Flexible source payload |
| **Index** | `UNIQUE(workspace_id, external_transaction_id) WHERE external_transaction_id IS NOT NULL` | Idempotent import deduplication |

---

### 1.7 Double-Entry General Ledger

#### `ledger_accounts` (Chart of Accounts)
- Columns: `id`, `workspace_id`, `code` (`UNIQUE` per workspace), `name`, `account_type` (`asset`, `liability`, `equity`, `revenue`, `expense`), `normal_balance` (`debit`, `credit`), `linked_account_id`, `is_active`.

#### `journal_entries`
- Columns: `id`, `workspace_id`, `entry_number` (`UNIQUE` per workspace), `entry_date`, `posting_date`, `status` (`draft`, `posted`, `reversed`), `description`, `source_type`, `source_id`, `reversal_of_entry_id`, `created_by`.

#### `journal_lines`
- Columns: `id`, `journal_entry_id` (`FK CASCADE`), `ledger_account_id` (`FK RESTRICT`), `line_number`, `entry_type` (`debit` or `credit`), `amount` (`NUMERIC(18, 4)` with `CHECK (amount > 0)`), `currency`, `description`.

---

### 1.8 `audit_logs`
Append-oriented immutable system audit trail.

| Column | Type | Description |
|:---|:---|:---|
| `id` | `UUID` | Audit record primary key |
| `workspace_id` | `UUID` | Owning workspace context (nullable for global actions) |
| `actor_id` | `UUID` | User ID who initiated the operation |
| `action` | `VARCHAR(100)` | Operation performed (`CREATE`, `UPDATE`, `DELETE`, `POST_JOURNAL`) |
| `entity_type` | `VARCHAR(100)` | Target entity name (`transaction`, `account`, `journal_entry`) |
| `entity_id` | `UUID` | Target record UUID |
| `correlation_id`| `VARCHAR(64)` | `X-Request-ID` linking HTTP request to log entry |
| `before_state` | `JSONB` | Sanitized snapshot prior to modification |
| `after_state` | `JSONB` | Sanitized snapshot following modification |
| `ip_address` | `VARCHAR(45)` | Client IP address |
| `user_agent` | `VARCHAR(255)` | Client user-agent string |
| `timestamp` | `TIMESTAMPTZ` | Timestamp of event (UTC) |
