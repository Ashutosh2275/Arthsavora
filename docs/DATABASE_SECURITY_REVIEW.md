# ARTHSAVORA — Database Security & PostgreSQL RLS Review

## 1. Overview

ARTHSAVORA uses PostgreSQL 18 as its primary relational financial store and single source of truth for all accounting, identity, document, and transactional data.

Database security is enforced via:
- Multi-tenant Row-Level Security (RLS) policies.
- Transaction-scoped connection session variables (`SET LOCAL`).
- Parameterized async SQLAlchemy queries (SQL injection elimination).
- Least-privilege application database roles.
- Strict relational foreign-key integrity constraints and fixed-point numeric types.

---

## 2. Row-Level Security (RLS) Architecture

### 2.1. Isolation Mechanism
Every multi-tenant table enforces PostgreSQL Row-Level Security:
```sql
ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table_name> FORCE ROW LEVEL SECURITY;

CREATE POLICY <table_name>_tenant_isolation ON <table_name>
FOR ALL USING (workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid);
```

`FORCE ROW LEVEL SECURITY` ensures that even table owners or application connection roles are subject to the tenant isolation policy unless operating with explicit `BYPASSRLS` privileges.

### 2.2. Connection Pooling & Context Isolation
A critical vulnerability in multi-tenant connection pools is session leakage, where a connection returned to the pool retains the previous tenant's session variable.

ARTHSAVORA prevents this by using transaction-scoped settings:
```python
async def set_tenant_context(session: AsyncSession, workspace_id: uuid.UUID) -> None:
    # Uses SET LOCAL so the setting is discarded on COMMIT or ROLLBACK
    stmt = text(f"SET LOCAL app.current_workspace_id = '{workspace_id}'")
    await session.execute(stmt)
```

Because `SET LOCAL` is bound strictly to the active database transaction:
1. When the transaction commits, the setting resets.
2. When the transaction rolls back, the setting resets.
3. If an uncaught exception occurs, connection context is automatically sanitized before returning to the pool.

---

## 3. Comprehensive RLS Table Coverage

Row-Level Security is configured and enforced across all 46 workspace-scoped tables in the system:

| Domain | Covered Tables |
| :--- | :--- |
| **Core Financial & Banking** | `accounts`, `transactions`, `account_balance_snapshots`, `categories`, `merchants`, `classification_rules`, `transaction_classifications`, `user_classification_feedback` |
| **Double-Entry General Ledger** | `ledger_accounts`, `journal_entries`, `accounting_periods` |
| **Data Acquisition & Consent** | `data_sources`, `consent_records`, `import_jobs`, `import_batches`, `import_candidates` |
| **Planning & Goals** | `budgets`, `budget_allocations`, `budget_revisions`, `budget_alerts`, `financial_goals`, `goal_activities` |
| **Recurring & Subscriptions** | `recurring_definitions`, `recurring_occurrences`, `recurring_reminders`, `recurring_suggestions`, `subscriptions` |
| **Forecasting & Scenarios** | `forecast_runs`, `forecast_points`, `forecast_evaluations`, `financial_scenarios` |
| **Anomalies & Fraud Signals** | `anomaly_detections`, `anomaly_reviews`, `detection_rules`, `detection_exceptions` |
| **AI Financial Assistant** | `assistant_conversations`, `assistant_messages`, `assistant_action_drafts`, `assistant_usage_logs` |
| **Documents & OCR Extractions** | `financial_documents`, `document_extractions`, `document_reviews`, `document_transaction_associations` |
| **Notifications & Comms** | `notifications` |
| **Family Collaborative Finance** | `family_profiles`, `family_activities`, `family_expense_allocations`, `family_member_contributions` |
| **Small Business Commercial** | `business_profiles`, `business_activities`, `business_clients`, `business_vendors`, `business_invoices`, `business_invoice_payments`, `business_payables`, `business_payable_payments` |
| **Account Aggregator & Connections** | `financial_connections`, `financial_consents`, `sync_jobs`, `external_account_references`, `connection_audit_events`, `reconciliation_records` |
| **Financial Reporting & Tax** | `generated_reports`, `report_validation_findings`, `tax_classification_records`, `tax_estimate_snapshots` |
| **Auditing & Workspace** | `audit_logs`, `workspace_members`, `workspace_invitations` |

---

## 4. SQL Injection Elimination

- **Parameterized Queries:** All relational database operations use SQLAlchemy 2.0 async select/insert/update expressions with typed parameters. Raw SQL string concatenation is strictly prohibited across the entire codebase.
- **Static Analysis:** Automated code scanning confirms zero unsafe string interpolation into database statements.
- **Type Safety:** All IDs are validated as UUID objects before query compilation.

---

## 5. Audit & Compliance

- **Append-Only Audit Trail:** `audit_logs` records the actor, entity, operation, correlation ID, and state changes.
- **Attribution Preservation:** Verified in `test_audit_log_survives_member_revocation`. If a user is removed or their role revoked, historical audit log entries retain full user attribution for forensic investigation.
- **Automated Verification:** Verified in `test_rls_ddl_generation_covers_all_tenant_tables` and `test_tenant_context_transaction_isolation`.
