# ARTHSAVORA DATABASE SECURITY & ACCESS CONTROL
## Least-Privilege Roles, Row-Level Security (RLS) & AI Query Governance

---

## 1. Least-Privilege Role Hierarchy

In production environments, database connections must operate under strictly separated PostgreSQL roles rather than a shared superuser:

```text
                  [ Superuser / DBA ]
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
[ arthsavora_migrator ]  [ arthsavora_app ]  [ arthsavora_reader ]
 (DDL on public schema)   (DML: CRUD on data)  (SELECT only on data)
```

| Role | Permitted Actions | Prohibited Actions | Usage Context |
|:---|:---|:---|:---|
| **`arthsavora_app`** | `SELECT`, `INSERT`, `UPDATE`, `DELETE` on all tables | `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE` | Primary web backend and Celery worker connection pool |
| **`arthsavora_migrator`** | Full DDL on `public` schema | Modifying users/roles outside `public` | Automated CI/CD deployment pipeline running `alembic upgrade` |
| **`arthsavora_reader`** | `SELECT` on financial tables | Any mutation (`INSERT`, `UPDATE`, `DELETE`, DDL) | Analytical reporting, read replicas, and BI dashboards |

---

## 2. PostgreSQL Row-Level Security (RLS) Specification

Arthsavora provides native defense-in-depth tenant isolation through PostgreSQL Row-Level Security (RLS):

### 2.1 Activation DDL
```sql
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts FORCE ROW LEVEL SECURITY;

CREATE POLICY accounts_tenant_isolation ON accounts
FOR ALL USING (
    workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid
);
```

### 2.2 Connection Pool Safety Invariant
To prevent tenant context leakage across pooled connections:
- The backend executes `SET LOCAL app.current_workspace_id = '...'` strictly inside active database transactions (`backend/app/infrastructure/database/rls.py`).
- Because `SET LOCAL` is used, the context is automatically cleared upon transaction `COMMIT` or `ROLLBACK`.
- Explicit call to `reset_tenant_context()` is executed in session teardown.

---

## 3. AI & LLM Service Query Governance

To protect financial records from prompt injection and arbitrary database tampering:

1. **Zero Direct SQL Generation:** LLMs and generative AI models (Gemini) are strictly prohibited from generating raw SQL queries executed against the database.
2. **Schema-Constrained Interfacing:** AI features interface with the database strictly through strongly-typed Pydantic schemas and deterministic Python services.
3. **No Financial Mutations Without Human Approval:** AI categorization proposals are flagged with `is_ai_predicted = TRUE` and require human verification before being marked as finalized.
4. **Credential Isolation:** The AI service layer possesses zero direct credentials to PostgreSQL. It accesses data exclusively through authorized application service abstractions.
