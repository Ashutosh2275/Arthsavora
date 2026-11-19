# ARTHSAVORA — Production Database Operations

## 1. Relational Database Authority

PostgreSQL 18 is the **sole authoritative financial system of record** for ARTHSAVORA. It holds user profiles, workspaces, double-entry general ledger entries, account records, transactions, family allocations, small-business invoicing, GST classifications, and audit journals.

## 2. Multi-Tenancy and Row-Level Security (RLS)

All 46 tenant-scoped tables enforce Row-Level Security. Tenancy is bound on every transaction via `SET LOCAL app.current_workspace_id = '...'`:

```sql
-- Enforcement policy standard across all workspace-scoped tables
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts FORCE ROW LEVEL SECURITY;

CREATE POLICY accounts_workspace_isolation_policy ON accounts
    FOR ALL
    USING (workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid)
    WITH CHECK (workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid);
```

### Verified RLS Protection
In `backend/app/services/rls_service.py`, `generate_rls_sql()` synchronizes policies across the entire schema. The test `test_rls_ddl_generation_covers_all_tenant_tables` validates that all 46 tables receive strict RLS policies.

## 3. Connection Pooling and Concurrency Management

- **Database Engine**: SQLAlchemy 2.0 Async with `asyncpg` driver.
- **Pool Size**: `pool_size = 20`, `max_overflow = 10`, `pool_timeout = 30.0` seconds.
- **Connection Recycler**: `pool_recycle = 1800` (connections recycled every 30 minutes to prevent stale TCP half-open states).
- **External Proxy (Optional at scale)**: AWS RDS Proxy or PgBouncer configured in `transaction` pooling mode for connection consolidation.

## 4. Routine Maintenance and Performance Tuning

| Task | Frequency | Execution Window | Impact |
| :--- | :--- | :--- | :--- |
| **Autovacuum Tuning** | Continuous | Automatic background daemon | Dead tuple reclamation; vacuum scale factor = 0.05 |
| **ANALYZE Statistics**| Daily | 02:00 IST | Updates planner index selectivity statistics |
| **Index Bloat Inspection** | Weekly | Sundays 03:00 IST | Evaluates `pgstattuple` on high-churn ledger tables |
| **REINDEX CONCURRENTLY**| Monthly | Maintenance window | Rebuilds btree indexes without table locks |

## 5. Slow Query Logging & Guardrails

- `log_min_duration_statement = 250ms`: All queries exceeding 250 milliseconds are captured to AWS CloudWatch Logs.
- `statement_timeout = 10000ms`: Prevents runaway queries from consuming database worker threads.
- `idle_in_transaction_session_timeout = 30000ms`: Aborts uncommitted transactions holding row locks.

## 6. Cross-Reference Links
- Database Migration Operations: [DATABASE_MIGRATION_OPERATIONS.md](file:///d:/Arthsavora/docs/DATABASE_MIGRATION_OPERATIONS.md)
- Database Change Safety: [DATABASE_CHANGE_SAFETY.md](file:///d:/Arthsavora/docs/DATABASE_CHANGE_SAFETY.md)
- Backup Operations: [BACKUP_OPERATIONS.md](file:///d:/Arthsavora/docs/BACKUP_OPERATIONS.md)
