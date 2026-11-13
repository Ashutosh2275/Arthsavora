# ARTHSAVORA DATABASE MIGRATION GUIDE
## Schema Version Control, Alembic Workflow & Reversible Migration Protocols

---

## 1. Migration Architecture

Database schema evolution is managed via **Alembic** paired with SQLAlchemy 2.0 asynchronous execution:
- **Configuration File:** [backend/alembic.ini](file:///d:/Arthsavora/backend/alembic.ini)
- **Environment Script:** [backend/migrations/env.py](file:///d:/Arthsavora/backend/migrations/env.py)
- **Migration Scripts Directory:** [backend/migrations/versions/](file:///d:/Arthsavora/backend/migrations/versions/)

### Core Principles
1. **Never Modify Database Directly:** Direct DDL modifications outside Alembic are strictly prohibited.
2. **Reversible Migrations:** Every migration script must implement fully functional and tested `upgrade()` and `downgrade()` functions.
3. **Transactional DDL:** PostgreSQL executes DDL inside transactions. If any statement in a migration fails, the entire migration rolls back automatically.
4. **Zero Accidental Data Loss:** Destructive operations (`DROP TABLE`, `DROP COLUMN`) require explicit review and data migration scripts prior to execution.

---

## 2. Common Migration Commands

All commands should be executed from the `backend/` directory:

```bash
# Check current migration status
alembic current

# View complete migration history
alembic history --verbose

# Generate a new migration automatically from SQLAlchemy models
alembic revision --autogenerate -m "descriptive_migration_name"

# Apply all pending migrations to database head
alembic upgrade head

# Roll back exactly one migration step
alembic downgrade -1

# Roll back all migrations to base (disposable test databases only)
alembic downgrade base
```

---

## 3. Active Initial Migration

- **Revision Identifier:** `a0735f358f00`
- **File:** `backend/migrations/versions/a0735f358f00_initial_schema_postgresql_foundation.py`
- **Scope:**
  - Creates 15 foundational tables (`users`, `user_profiles`, `workspaces`, `workspace_members`, `accounts`, `categories`, `transactions`, `ledger_accounts`, `journal_entries`, `journal_lines`, `data_sources`, `consent_records`, `import_jobs`, `import_files`, `audit_logs`).
  - Creates all foreign key cascades and constraints.
  - Builds unique constraints (`uq_workspace_member`, `uq_workspace_ledger_code`, `uq_workspace_entry_number`).
  - Builds partial unique index for idempotent import deduplication (`uq_workspace_external_tx`).
  - Full downgrade verified: cleanly drops all indexes and tables in reverse dependency order.

---

## 4. Production Deployment Protocol

When deploying schema updates to staging or production:
1. **Pre-Deployment Migration:** Run non-destructive additive changes (`CREATE TABLE`, `ADD COLUMN NULLABLE`) before deploying new application pods.
2. **Post-Deployment Migration:** Remove obsolete columns only after old application versions have been fully phased out.
