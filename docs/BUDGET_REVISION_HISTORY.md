# Arthsavora — Budget Revision History & Audit Ledger

## 1. Objective & Compliance Integrity

In commercial FinTech, budgeting adjustments must be auditable and traceable. Users frequently adjust category spending limits, expand total caps, or change period boundaries. Without an immutable changelog, prior budget states cannot be reconstructed, leading to confusion when reviewing historical spending discipline.

Arthsavora enforces a **first-class append-only revision ledger** (`budget_revisions`) that records every structural change to a budget throughout its lifecycle.

---

## 2. Relational Schema (`budget_revisions`)

| Column | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary key of the revision record. |
| `budget_id` | `UUID` | Foreign key referencing the parent budget. |
| `workspace_id` | `UUID` | Workspace tenant isolation boundary. |
| `allocation_id` | `UUID \| NULL` | Null if overall budget change; populated if category allocation change. |
| `category_id` | `UUID \| NULL` | Target category if category limit changed. |
| `revision_type` | `VARCHAR(50)` | Change classification (see taxonomy below). |
| `previous_amount_paise` | `BIGINT \| NULL` | Previous ceiling in paise (`NULL` for initial creation). |
| `new_amount_paise` | `BIGINT \| NULL` | Updated ceiling in paise (`0` if deleted). |
| `change_reason` | `VARCHAR(500) \| NULL` | User-provided or system-generated explanation. |
| `changed_by_id` | `UUID \| NULL` | User identifier who authorized the change. |
| `created_at` | `TIMESTAMPTZ` | Immutable UTC timestamp. |

---

## 3. Revision Type Taxonomy

The system standardizes change classifications:

1. `created`: Initial establishment of the budget.
2. `budget_updated`: Overall ceiling, dates, or recurrence modified.
3. `budget_archived`: Budget soft-deleted / archived by user.
4. `allocation_created`: Initial category limit created during budget onboarding.
5. `allocation_added`: New category limit added to an active budget.
6. `allocation_updated`: Existing category limit adjusted (amount or threshold).
7. `allocation_removed`: Category allocation ceiling removed from budget.

---

## 4. Audit Trail Retrieval & Presentation

The revision log is queried via `GET /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/revisions`.

The API returns chronologically indexed entries:
```json
{
  "id": "7f8b9c2a-...",
  "budget_id": "2a1c4b8e-...",
  "revision_number": 3,
  "change_type": "allocation_updated",
  "previous_state": { "amount_paise": 1500000 },
  "new_state": { "amount_paise": 2000000 },
  "reason": "Higher fuel price this month / family event",
  "changed_by_id": "5f6e7d8c-...",
  "created_at": "2026-11-14T08:00:00Z"
}
```

In the frontend UI ([Budgets.tsx](file:///d:/Arthsavora/apps/web/src/pages/Budgets.tsx)), clicking **"Revisions"** launches an audit drawer displaying the complete chronological chain of custody.

---

## 5. File References

- Model Definition: [budget.py](file:///d:/Arthsavora/backend/app/infrastructure/database/models/budget.py)
- Repository Methods: [budget_repository.py](file:///d:/Arthsavora/backend/app/repositories/budget_repository.py)
- Web UI Drawer: [Budgets.tsx](file:///d:/Arthsavora/apps/web/src/pages/Budgets.tsx)
