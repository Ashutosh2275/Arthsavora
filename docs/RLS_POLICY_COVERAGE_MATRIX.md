# Row-Level Security (RLS) Policy Coverage Matrix

## 1. Overview

Row-Level Security (RLS) is PostgreSQL's kernel-level access control mechanism. In ARTHSAVORA, RLS guarantees that even if application logic were to emit an un-scoped `SELECT * FROM table`, the database kernel itself filters records strictly by the active tenant workspace.

This matrix documents all **69 PostgreSQL tables** protected by Row-Level Security in `backend/app/infrastructure/database/rls.py`.

---

## 2. Global RLS Policy Definition

Each tenant-scoped table is configured with the following deterministic DDL pattern:

```sql
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name};

CREATE POLICY {table_name}_tenant_isolation ON {table_name}
    FOR ALL
    USING (workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid);
```

> **Note on `FORCE ROW LEVEL SECURITY`:** PostgreSQL by default bypasses RLS for table owners. Applying `FORCE ROW LEVEL SECURITY` ensures that even queries executed by the database application user are strictly subject to RLS filtering.

---

## 3. Comprehensive 69-Table Coverage Inventory

### 3.1 Core Financial & Identity Subsystem (17 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 1 | `accounts` | `workspace_id (UUID)` | `accounts_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 2 | `transactions` | `workspace_id (UUID)` | `transactions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 3 | `ledger_accounts` | `workspace_id (UUID)` | `ledger_accounts_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 4 | `journal_entries` | `workspace_id (UUID)` | `journal_entries_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 5 | `accounting_periods` | `workspace_id (UUID)` | `accounting_periods_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 6 | `account_balance_snapshots` | `workspace_id (UUID)` | `account_balance_snapshots_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 7 | `categories` | `workspace_id (UUID)` | `categories_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 8 | `merchants` | `workspace_id (UUID)` | `merchants_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 9 | `classification_rules` | `workspace_id (UUID)` | `classification_rules_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 10 | `transaction_classifications` | `workspace_id (UUID)` | `transaction_classifications_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 11 | `user_classification_feedback` | `workspace_id (UUID)` | `user_classification_feedback_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 12 | `data_sources` | `workspace_id (UUID)` | `data_sources_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 13 | `consent_records` | `workspace_id (UUID)` | `consent_records_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 14 | `import_jobs` | `workspace_id (UUID)` | `import_jobs_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 15 | `import_batches` | `workspace_id (UUID)` | `import_batches_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 16 | `import_candidates` | `workspace_id (UUID)` | `import_candidates_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 17 | `audit_logs` | `workspace_id (UUID)` | `audit_logs_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.2 Planning, Budgeting & Foresight Subsystem (15 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 18 | `budgets` | `workspace_id (UUID)` | `budgets_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 19 | `budget_allocations` | `workspace_id (UUID)` | `budget_allocations_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 20 | `budget_revisions` | `workspace_id (UUID)` | `budget_revisions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 21 | `budget_alerts` | `workspace_id (UUID)` | `budget_alerts_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 22 | `financial_goals` | `workspace_id (UUID)` | `financial_goals_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 23 | `goal_activities` | `workspace_id (UUID)` | `goal_activities_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 24 | `recurring_definitions` | `workspace_id (UUID)` | `recurring_definitions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 25 | `recurring_occurrences` | `workspace_id (UUID)` | `recurring_occurrences_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 26 | `recurring_reminders` | `workspace_id (UUID)` | `recurring_reminders_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 27 | `recurring_suggestions` | `workspace_id (UUID)` | `recurring_suggestions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 28 | `subscriptions` | `workspace_id (UUID)` | `subscriptions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 29 | `forecast_runs` | `workspace_id (UUID)` | `forecast_runs_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 30 | `forecast_points` | `workspace_id (UUID)` | `forecast_points_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 31 | `forecast_evaluations` | `workspace_id (UUID)` | `forecast_evaluations_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 32 | `financial_scenarios` | `workspace_id (UUID)` | `financial_scenarios_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.3 Anomaly & Risk Intelligence Subsystem (4 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 33 | `anomaly_detections` | `workspace_id (UUID)` | `anomaly_detections_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 34 | `anomaly_reviews` | `workspace_id (UUID)` | `anomaly_reviews_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 35 | `detection_rules` | `workspace_id (UUID)` | `detection_rules_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 36 | `detection_exceptions` | `workspace_id (UUID)` | `detection_exceptions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.4 Conversational AI Assistant Subsystem (4 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 37 | `assistant_conversations` | `workspace_id (UUID)` | `assistant_conversations_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 38 | `assistant_messages` | `workspace_id (UUID)` | `assistant_messages_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 39 | `assistant_action_drafts` | `workspace_id (UUID)` | `assistant_action_drafts_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 40 | `assistant_usage_logs` | `workspace_id (UUID)` | `assistant_usage_logs_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.5 Document Processing & OCR Subsystem (4 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 41 | `financial_documents` | `workspace_id (UUID)` | `financial_documents_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 42 | `document_extractions` | `workspace_id (UUID)` | `document_extractions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 43 | `document_reviews` | `workspace_id (UUID)` | `document_reviews_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 44 | `document_transaction_associations` | `workspace_id (UUID)` | `document_transaction_associations_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.6 Notifications Subsystem (1 Table)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 45 | `notifications` | `workspace_id (UUID)` | `notifications_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.7 Family Finance Subsystem (4 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 46 | `family_profiles` | `workspace_id (UUID)` | `family_profiles_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 47 | `family_activities` | `workspace_id (UUID)` | `family_activities_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 48 | `family_expense_allocations` | `workspace_id (UUID)` | `family_expense_allocations_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 49 | `family_member_contributions` | `workspace_id (UUID)` | `family_member_contributions_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.8 Small Business Finance Subsystem (8 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 50 | `business_profiles` | `workspace_id (UUID)` | `business_profiles_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 51 | `business_activities` | `workspace_id (UUID)` | `business_activities_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 52 | `business_clients` | `workspace_id (UUID)` | `business_clients_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 53 | `business_vendors` | `workspace_id (UUID)` | `business_vendors_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 54 | `business_invoices` | `workspace_id (UUID)` | `business_invoices_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 55 | `business_invoice_payments` | `workspace_id (UUID)` | `business_invoice_payments_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 56 | `business_payables` | `workspace_id (UUID)` | `business_payables_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 57 | `business_payable_payments` | `workspace_id (UUID)` | `business_payable_payments_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.9 Financial Connectivity & Account Aggregation Subsystem (6 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 58 | `financial_connections` | `workspace_id (UUID)` | `financial_connections_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 59 | `financial_consents` | `workspace_id (UUID)` | `financial_consents_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 60 | `sync_jobs` | `workspace_id (UUID)` | `sync_jobs_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 61 | `external_account_references` | `workspace_id (UUID)` | `external_account_references_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 62 | `connection_audit_events` | `workspace_id (UUID)` | `connection_audit_events_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 63 | `reconciliation_records` | `workspace_id (UUID)` | `reconciliation_records_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.10 Financial Reporting & Tax Intelligence Subsystem (4 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 64 | `generated_reports` | `workspace_id (UUID)` | `generated_reports_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 65 | `report_validation_findings` | `workspace_id (UUID)` | `report_validation_findings_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 66 | `tax_classification_records` | `workspace_id (UUID)` | `tax_classification_records_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 67 | `tax_estimate_snapshots` | `workspace_id (UUID)` | `tax_estimate_snapshots_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

### 3.11 Workspace Membership Subsystem (2 Tables)

| # | Table Name | Tenant Scoping Key | Policy Name | Enforcement Mode | Verified Status |
|:---:|---|---|---|---|:---:|
| 68 | `workspace_members` | `workspace_id (UUID)` | `workspace_members_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |
| 69 | `workspace_invitations` | `workspace_id (UUID)` | `workspace_invitations_tenant_isolation` | ENABLE + FORCE | **VERIFIED** |

---

## 4. Verification & Testing

Every migration cycle and test run verifies RLS via `backend/scripts/run_migrations.py` and `backend/tests/test_security_hardening.py`. RLS coverage is 100% across all 69 multi-tenant tables.
