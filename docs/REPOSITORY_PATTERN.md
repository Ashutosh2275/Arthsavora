# ARTHSAVORA — REPOSITORY PATTERN ARCHITECTURE

## 1. Purpose and Philosophy

The Repository Pattern separates the domain and service layers from direct database access logic. It provides an in-memory collection-like interface for accessing persistent domain entities.

In Arthsavora, repositories serve two critical functions:
1. **Encapsulate Query Mechanics:** Encapsulate SQLAlchemy 2.0 async query syntax (`select`, `join`, `where`).
2. **Enforce Tenant Isolation (Anti-IDOR):** Guarantee that every query is partitioned by `workspace_id` to prevent cross-tenant data leakage.

---

## 2. Class Hierarchy

```
┌────────────────────────────────────────────────────────┐
│                   BaseRepository[T]                    │
│   - Generic CRUD methods: get_by_id, add, flush        │
│   - Bound to AsyncSession and Model class              │
└───────────────────────────┬────────────────────────────┘
                            │ extends
                            ▼
┌────────────────────────────────────────────────────────┐
│             WorkspaceScopedRepository[T]               │
│   - get_by_id_scoped(entity_id, workspace_id)         │
│   - list_scoped(workspace_id, limit, offset)           │
│   - count_scoped(workspace_id)                         │
│   - Bounded pagination enforcement (limit <= 100)      │
└───────────────┬──────────────────────────┬─────────────┘
                │                          │
        extends │                  extends │
                ▼                          ▼
┌───────────────────────────┐  ┌───────────────────────────┐
│     AccountRepository     │  │   TransactionRepository   │
│ - list_by_workspace       │  │ - get_by_external_id      │
│ - create                  │  │ - list_paginated          │
└───────────────────────────┘  └───────────────────────────┘
```

---

## 3. Anti-IDOR (Insecure Direct Object Reference) Query Defense

A standard security flaw in multi-tenant SaaS occurs when an entity is retrieved by its primary key `id` without verifying tenant ownership in the same atomic SQL query:

```sql
-- DANGEROUS PATTERN (VULNERABLE TO IDOR & TIMING ATTACKS)
SELECT * FROM accounts WHERE id = '...';
-- then verifying account.workspace_id == current_workspace in Python
```

In Arthsavora, all queries in `WorkspaceScopedRepository` enforce composite atomic evaluation:
```python
stmt = select(self.model_class).where(
    self.model_class.id == entity_id,
    self.model_class.workspace_id == workspace_id,
)
result = await self.session.execute(stmt)
return result.scalar_one_or_none()
```
### Security Guarantees:
- If a malicious user attempts to query an `account_id` belonging to a rival workspace, the database returns `None`.
- The application responds with `404 Not Found`, revealing zero information about whether that resource ID exists elsewhere.

---

## 4. Bounded Pagination Conventions

Unbounded pagination queries (`SELECT * FROM transactions`) cause memory exhaustion and denial-of-service in large databases.

All repository pagination methods enforce defensive upper bounds:
```python
safe_limit = max(1, min(limit, 100))
safe_offset = max(0, offset)
```
- Maximum allowable page size is **100 records**.
- Requests for `limit > 100` are silently capped to 100.
- Negative offsets or limits are normalized safely.

---

## 5. Domain-Specific Repositories

### 5.1 `AccountRepository`
- `list_by_workspace(workspace_id, account_type=None)`: Queries active accounts ordered by creation date descending.
- `create(workspace_id, name, account_type, currency, ...)`: Schedules creation of an account entity.

### 5.2 `TransactionRepository`
- `get_by_external_id(workspace_id, external_id)`: Provides single-query lookup for bank statement and UPI deduplication.
- `list_transactions_paginated(...)`: Implements composite filtering (account, date range, type) and returns `(items, total_count)`.

### 5.3 `WorkspaceRepository`
- `get_by_id(workspace_id)`: Retrieves workspace metadata.
- `get_by_slug(slug)`: Resolves public/vanity URLs.
- `get_membership(workspace_id, user_id)`: Checks active user role and status within a workspace.
- `list_members_with_user(workspace_id)`: Fetches active members joined with profile data.
