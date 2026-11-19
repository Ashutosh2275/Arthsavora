# PostgreSQL Row-Level Security (RLS) Runtime Verification Report

## 1. Executive Summary

- **Verification Timestamp**: 2026-11-19T14:21:55.459582+00:00
- **Database Engine**: PostgreSQL 18.1 (x86_64-pc-windows-msvc)
- **Target Environment**: Local PostgreSQL Production Replica (`localhost:5433/arthsavora`)
- **Catalog Verification**: **69 / 69 tables PASS** (100.0%)
- **Multi-Tenant Isolation Tests**: **7 / 7 tests PASS** (100.0%)
- **Overall RLS Status**: **FULLY SECURED & ENFORCED AT RUNTIME**

---

## 2. Multi-Tenant Live Isolation Verification

| Test Case | Expected Behavior | Actual Empirical Result | Verdict |
|---|---|---|:---:|
| **Workspace A Context Read Isolation** | Only Account A visible (1 row) | `1 row(s): ['HDFC Current Alpha']` | **PASS** |
| **Workspace B Context Read Isolation** | Only Account B visible (1 row) | `1 row(s): ['ICICI Savings Beta']` | **PASS** |
| **Empty Context Fail-Closed Enforcement** | 0 rows visible (access denied by default) | `0 row(s) returned` | **PASS** |
| **Cross-Tenant Mutation (UPDATE) Prevention** | 0 rows updated (silent denial) | `0 row(s) updated` | **PASS** |
| **Cross-Tenant Mutation (DELETE) Prevention** | 0 rows deleted (silent denial) | `0 row(s) deleted` | **PASS** |
| **Planning & Budgets Table RLS Isolation** | Workspace A budget invisible to Workspace B | `Visible: False` | **PASS** |
| **SET LOCAL Transaction Hygiene (Pool Safety)** | Tenant context purged automatically upon transaction end | `Inside: 'b97262a9-4895-481e-aba0-1dcf6f52fa9e', Outside: ''` | **PASS** |

---

## 3. PostgreSQL Catalog Verification Matrix (All 69 Tenant Tables)

All tables below enforce both `relrowsecurity = true` (`ENABLE ROW LEVEL SECURITY`) and `relforcerowsecurity = true` (`FORCE ROW LEVEL SECURITY`), with tenant isolation policies filtering by `workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid`.

| # | Table Name | RLS Enabled (`relrowsecurity`) | RLS Forced (`relforcerowsecurity`) | Active Policy | Command Scope | Verdict |
|:---:|---|:---:|:---:|---|:---:|:---:|
| 1 | `accounts` | `true` | `true` | `accounts_tenant_isolation` | `b'*'` | **PASS** |
| 2 | `transactions` | `true` | `true` | `transactions_tenant_isolation` | `b'*'` | **PASS** |
| 3 | `ledger_accounts` | `true` | `true` | `ledger_accounts_tenant_isolation` | `b'*'` | **PASS** |
| 4 | `journal_entries` | `true` | `true` | `journal_entries_tenant_isolation` | `b'*'` | **PASS** |
| 5 | `accounting_periods` | `true` | `true` | `accounting_periods_tenant_isolation` | `b'*'` | **PASS** |
| 6 | `account_balance_snapshots` | `true` | `true` | `account_balance_snapshots_tenant_isolation` | `b'*'` | **PASS** |
| 7 | `categories` | `true` | `true` | `categories_tenant_isolation` | `b'*'` | **PASS** |
| 8 | `merchants` | `true` | `true` | `merchants_tenant_isolation` | `b'*'` | **PASS** |
| 9 | `classification_rules` | `true` | `true` | `classification_rules_tenant_isolation` | `b'*'` | **PASS** |
| 10 | `transaction_classifications` | `true` | `true` | `transaction_classifications_tenant_isolation` | `b'*'` | **PASS** |
| 11 | `user_classification_feedback` | `true` | `true` | `user_classification_feedback_tenant_isolation` | `b'*'` | **PASS** |
| 12 | `data_sources` | `true` | `true` | `data_sources_tenant_isolation` | `b'*'` | **PASS** |
| 13 | `consent_records` | `true` | `true` | `consent_records_tenant_isolation` | `b'*'` | **PASS** |
| 14 | `import_jobs` | `true` | `true` | `import_jobs_tenant_isolation` | `b'*'` | **PASS** |
| 15 | `import_batches` | `true` | `true` | `import_batches_tenant_isolation` | `b'*'` | **PASS** |
| 16 | `import_candidates` | `true` | `true` | `import_candidates_tenant_isolation` | `b'*'` | **PASS** |
| 17 | `audit_logs` | `true` | `true` | `audit_logs_tenant_isolation` | `b'*'` | **PASS** |
| 18 | `budgets` | `true` | `true` | `budgets_tenant_isolation` | `b'*'` | **PASS** |
| 19 | `budget_allocations` | `true` | `true` | `budget_allocations_tenant_isolation` | `b'*'` | **PASS** |
| 20 | `budget_revisions` | `true` | `true` | `budget_revisions_tenant_isolation` | `b'*'` | **PASS** |
| 21 | `budget_alerts` | `true` | `true` | `budget_alerts_tenant_isolation` | `b'*'` | **PASS** |
| 22 | `financial_goals` | `true` | `true` | `financial_goals_tenant_isolation` | `b'*'` | **PASS** |
| 23 | `goal_activities` | `true` | `true` | `goal_activities_tenant_isolation` | `b'*'` | **PASS** |
| 24 | `recurring_definitions` | `true` | `true` | `recurring_definitions_tenant_isolation` | `b'*'` | **PASS** |
| 25 | `recurring_occurrences` | `true` | `true` | `recurring_occurrences_tenant_isolation` | `b'*'` | **PASS** |
| 26 | `recurring_reminders` | `true` | `true` | `recurring_reminders_tenant_isolation` | `b'*'` | **PASS** |
| 27 | `recurring_suggestions` | `true` | `true` | `recurring_suggestions_tenant_isolation` | `b'*'` | **PASS** |
| 28 | `subscriptions` | `true` | `true` | `subscriptions_tenant_isolation` | `b'*'` | **PASS** |
| 29 | `forecast_runs` | `true` | `true` | `forecast_runs_tenant_isolation` | `b'*'` | **PASS** |
| 30 | `forecast_points` | `true` | `true` | `forecast_points_tenant_isolation` | `b'*'` | **PASS** |
| 31 | `forecast_evaluations` | `true` | `true` | `forecast_evaluations_tenant_isolation` | `b'*'` | **PASS** |
| 32 | `financial_scenarios` | `true` | `true` | `financial_scenarios_tenant_isolation` | `b'*'` | **PASS** |
| 33 | `anomaly_detections` | `true` | `true` | `anomaly_detections_tenant_isolation` | `b'*'` | **PASS** |
| 34 | `anomaly_reviews` | `true` | `true` | `anomaly_reviews_tenant_isolation` | `b'*'` | **PASS** |
| 35 | `detection_rules` | `true` | `true` | `detection_rules_tenant_isolation` | `b'*'` | **PASS** |
| 36 | `detection_exceptions` | `true` | `true` | `detection_exceptions_tenant_isolation` | `b'*'` | **PASS** |
| 37 | `assistant_conversations` | `true` | `true` | `assistant_conversations_tenant_isolation` | `b'*'` | **PASS** |
| 38 | `assistant_messages` | `true` | `true` | `assistant_messages_tenant_isolation` | `b'*'` | **PASS** |
| 39 | `assistant_action_drafts` | `true` | `true` | `assistant_action_drafts_tenant_isolation` | `b'*'` | **PASS** |
| 40 | `assistant_usage_logs` | `true` | `true` | `assistant_usage_logs_tenant_isolation` | `b'*'` | **PASS** |
| 41 | `financial_documents` | `true` | `true` | `financial_documents_tenant_isolation` | `b'*'` | **PASS** |
| 42 | `document_extractions` | `true` | `true` | `document_extractions_tenant_isolation` | `b'*'` | **PASS** |
| 43 | `document_reviews` | `true` | `true` | `document_reviews_tenant_isolation` | `b'*'` | **PASS** |
| 44 | `document_transaction_associations` | `true` | `true` | `document_transaction_associations_tenant_isolation` | `b'*'` | **PASS** |
| 45 | `notifications` | `true` | `true` | `notifications_tenant_isolation` | `b'*'` | **PASS** |
| 46 | `family_profiles` | `true` | `true` | `family_profiles_tenant_isolation` | `b'*'` | **PASS** |
| 47 | `family_activities` | `true` | `true` | `family_activities_tenant_isolation` | `b'*'` | **PASS** |
| 48 | `family_expense_allocations` | `true` | `true` | `family_expense_allocations_tenant_isolation` | `b'*'` | **PASS** |
| 49 | `family_member_contributions` | `true` | `true` | `family_member_contributions_tenant_isolation` | `b'*'` | **PASS** |
| 50 | `business_profiles` | `true` | `true` | `business_profiles_tenant_isolation` | `b'*'` | **PASS** |
| 51 | `business_activities` | `true` | `true` | `business_activities_tenant_isolation` | `b'*'` | **PASS** |
| 52 | `business_clients` | `true` | `true` | `business_clients_tenant_isolation` | `b'*'` | **PASS** |
| 53 | `business_vendors` | `true` | `true` | `business_vendors_tenant_isolation` | `b'*'` | **PASS** |
| 54 | `business_invoices` | `true` | `true` | `business_invoices_tenant_isolation` | `b'*'` | **PASS** |
| 55 | `business_invoice_payments` | `true` | `true` | `business_invoice_payments_tenant_isolation` | `b'*'` | **PASS** |
| 56 | `business_payables` | `true` | `true` | `business_payables_tenant_isolation` | `b'*'` | **PASS** |
| 57 | `business_payable_payments` | `true` | `true` | `business_payable_payments_tenant_isolation` | `b'*'` | **PASS** |
| 58 | `financial_connections` | `true` | `true` | `financial_connections_tenant_isolation` | `b'*'` | **PASS** |
| 59 | `financial_consents` | `true` | `true` | `financial_consents_tenant_isolation` | `b'*'` | **PASS** |
| 60 | `sync_jobs` | `true` | `true` | `sync_jobs_tenant_isolation` | `b'*'` | **PASS** |
| 61 | `external_account_references` | `true` | `true` | `external_account_references_tenant_isolation` | `b'*'` | **PASS** |
| 62 | `connection_audit_events` | `true` | `true` | `connection_audit_events_tenant_isolation` | `b'*'` | **PASS** |
| 63 | `reconciliation_records` | `true` | `true` | `reconciliation_records_tenant_isolation` | `b'*'` | **PASS** |
| 64 | `generated_reports` | `true` | `true` | `generated_reports_tenant_isolation` | `b'*'` | **PASS** |
| 65 | `report_validation_findings` | `true` | `true` | `report_validation_findings_tenant_isolation` | `b'*'` | **PASS** |
| 66 | `tax_classification_records` | `true` | `true` | `tax_classification_records_tenant_isolation` | `b'*'` | **PASS** |
| 67 | `tax_estimate_snapshots` | `true` | `true` | `tax_estimate_snapshots_tenant_isolation` | `b'*'` | **PASS** |
| 68 | `workspace_members` | `true` | `true` | `workspace_members_tenant_isolation` | `b'*'` | **PASS** |
| 69 | `workspace_invitations` | `true` | `true` | `workspace_invitations_tenant_isolation` | `b'*'` | **PASS** |

---

## 4. Key Architectural Guarantees Established

1. **Fail-Closed by Default**: When `app.current_workspace_id` is empty, unset, or malformed, PostgreSQL policies evaluate `workspace_id = NULL`, which matches zero records and returns an empty result set.
2. **FORCE ROW LEVEL SECURITY**: Applied to every tenant-scoped table, guaranteeing that RLS is enforced uniformly even when running as table owner, service accounts, or administrative migration roles.
3. **Zero Connection Pool Leakage**: Context setting uses `SET LOCAL app.current_workspace_id = ...`, binding the parameter strictly to the active transaction block. Upon `COMMIT` or `ROLLBACK`, PostgreSQL automatically purges the setting.
4. **Cross-Tenant Mutation Defense**: Direct `UPDATE` and `DELETE` queries targeting out-of-workspace record IDs result in `0 rows affected`, preventing both data tampering and IDOR leakage.

---
*Report generated automatically by `backend/scripts/verify_rls_runtime.py`.*