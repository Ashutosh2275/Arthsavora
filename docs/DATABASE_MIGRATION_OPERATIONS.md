# ARTHSAVORA — Database Migration Operations

## 1. Migration Runner Architecture

Database migrations are executed deterministically using `backend/scripts/run_migrations.py`. This script solves race conditions in multi-instance or auto-scaling clusters by wrapping Alembic migrations in an exclusive PostgreSQL session-level advisory lock.

```
                    [ run_migrations.py Execution ]
                                   |
                                   v
             [ Acquire Lock: SELECT pg_advisory_lock(987654321) ]
                                   |
                  +----------------+----------------+
                  |                                 |
           (Lock Acquired)                   (Lock Contended)
                  |                                 |
                  v                                 v
        [ Run Alembic Upgrade ]             [ Wait in Queue until ]
        - Executes upgrade to head          [ prior runner finishes]
        - Thread-isolated runner                    |
                  |                                 |
                  v                                 |
        [ Re-apply RLS Policies ]                   |
        - Calls generate_rls_sql()                  |
        - Synchronizes 46 tables                    |
                  |                                 |
                  v                                 |
       [ Release Advisory Lock ] <------------------+
       - SELECT pg_advisory_unlock(987654321)
                  |
                  v
         [ Migration Complete ]
```

## 2. PostgreSQL Advisory Lock Mechanics

- **Lock ID**: `987654321` (dedicated constant 64-bit integer identifier for ARTHSAVORA schema operations).
- **Behavior**:
  - `pg_advisory_lock(key)` blocks until the lock is acquired.
  - Guarantees that only ONE migration instance runs across the entire database cluster, even if multiple deployment workers are triggered simultaneously.
  - Locks are session-scoped; if the connection drops unexpectedly, PostgreSQL automatically releases the advisory lock.
- **Verification**: Verified via test `test_postgresql_advisory_lock_lifecycle` in `backend/tests/test_production_operational_readiness.py`.

## 3. Row-Level Security Synchronization

Following every Alembic upgrade, `run_migrations.py` automatically executes `generate_rls_sql()`. This guarantees:
1. Every newly created table is immediately locked down with `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
2. Tenant isolation policies (`USING (workspace_id = ...)` and `WITH CHECK (workspace_id = ...)`) are re-applied and verified.
3. No migration can accidentally leave a table unprotected.

## 4. Migration Execution Command Reference

```bash
# Production automated migration execution
python backend/scripts/run_migrations.py

# Check current revision status
uv run alembic current

# Inspect migration history
uv run alembic history --verbose

# Dry-run SQL generation (Offline Mode)
uv run alembic upgrade head --sql
```

## 5. Cross-Reference Links
- Production Database Operations: [PRODUCTION_DATABASE_OPERATIONS.md](file:///d:/Arthsavora/docs/PRODUCTION_DATABASE_OPERATIONS.md)
- Database Change Safety: [DATABASE_CHANGE_SAFETY.md](file:///d:/Arthsavora/docs/DATABASE_CHANGE_SAFETY.md)
- Deployment Pipeline: [DEPLOYMENT_PIPELINE.md](file:///d:/Arthsavora/docs/DEPLOYMENT_PIPELINE.md)
