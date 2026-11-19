# ARTHSAVORA — Database Change Safety and Evolution Guidelines

## 1. Zero-Downtime Schema Evolution Principles

In an institutional financial system, table locks or backward-incompatible schema changes risk downtime, uncommitted ledger posts, and user transaction failures. All schema changes in ARTHSAVORA must follow the **Expand / Contract Pattern**.

## 2. The Expand / Contract Pattern

```
 PHASE 1: EXPAND                  PHASE 2: DUAL WRITE / COMPAT        PHASE 3: CONTRACT
 [ Schema Migration ]             [ Code Update ]                    [ Cleanup Migration ]
 Add new column as nullable       Backend reads from new column;      Drop deprecated column
 or with default value.           falls back to old column.           or old table after all
 Old code continues running.      Writes to both or new column.       instances are upgraded.
```

### Prohibited Operations in a Single Release
1. **Never `ALTER TABLE ... DROP COLUMN`** without prior deprecation release.
2. **Never `ALTER TABLE ... RENAME COLUMN`** directly (replaces with Add New + Migrate + Drop Old).
3. **Never add a `NOT NULL` constraint without a DEFAULT value** on existing tables with data (causes table rewrite and exclusive table locks).
4. **Never create an index without `CONCURRENTLY`** in production:
   ```sql
   -- Prohibited:
   CREATE INDEX idx_trans_date ON transactions (transaction_date);

   -- Mandatory in PostgreSQL:
   CREATE INDEX CONCURRENTLY idx_trans_date ON transactions (transaction_date);
   ```

## 3. Safe Schema Evolution Playbook

### 3.1 Adding a Required Field
1. **Migration 1 (Expand)**: Add column as nullable:
   ```sql
   ALTER TABLE invoices ADD COLUMN payment_reference VARCHAR(100) DEFAULT NULL;
   ```
2. **Application Release 1**: Code starts populating `payment_reference` for all new rows.
3. **Data Backfill Job**: Background migration script backfills historical rows.
4. **Migration 2 (Contract)**: Add `NOT NULL` constraint:
   ```sql
   ALTER TABLE invoices ALTER COLUMN payment_reference SET NOT NULL;
   ```

### 3.2 Renaming a Field
1. **Migration 1**: Add new column `new_field`.
2. **Application Release 1**: Write to both `old_field` and `new_field`; read from `new_field` if present, else fallback.
3. **Backfill**: Copy data from `old_field` to `new_field`.
4. **Application Release 2**: Read and write exclusively to `new_field`.
5. **Migration 2**: Drop `old_field`.

## 4. Multi-Tenancy Invariant Verification

Any schema change adding a tenant-scoped table MUST include:
- `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`.
- Entry in `RLS_TABLES` tuple in `backend/app/services/rls_service.py`.
- Re-run of `test_rls_ddl_generation_covers_all_tenant_tables`.

## 5. Cross-Reference Links
- Database Migration Operations: [DATABASE_MIGRATION_OPERATIONS.md](file:///d:/Arthsavora/docs/DATABASE_MIGRATION_OPERATIONS.md)
- Production Database Operations: [PRODUCTION_DATABASE_OPERATIONS.md](file:///d:/Arthsavora/docs/PRODUCTION_DATABASE_OPERATIONS.md)
