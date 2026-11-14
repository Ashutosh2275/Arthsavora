# Arthsavora — Personal Budgeting & Spending Controls Architecture

## 1. Architectural Mission & Overview

The Personal Budgeting & Spending Controls engine in Arthsavora delivers institutional-grade financial discipline to individual and household users. It provides deterministic spending ceilings, transparent progress tracking, category allocations, linear period-end burn rate projections, and idempotent threshold alerting without relying on opaque machine-learning models or modifying underlying General Ledger records.

The budgeting engine adheres to strict commercial FinTech engineering principles:
1. **Separation of Accounting and Planning**: Budgets are forward-looking financial targets and spending boundaries. Creating, adjusting, or exceeding a budget never modifies double-entry general ledger journal entries or account balances.
2. **Deterministic Transaction Inclusion**: Spending progress is derived strictly from confirmed, posted, and eligible expenses. Internal transfers, credit card repayments, loan principal disbursements, and pending authorizations are eliminated to prevent turnover inflation and double-counting.
3. **Immutable Revision Audit Ledger**: Every modification to a budget's overall cap, period boundaries, or category allocation limits is permanently recorded in an append-only revision ledger (`budget_revisions`) with full before/after state diffs, user identity, and mandatory audit reasons.
4. **Idempotent Alert Engine**: Alert triggers are backed by PostgreSQL unique constraints preventing duplicate alert notifications when repeated evaluations occur within the same threshold tier (50%, 75%, 80%, 90%, 100%).
5. **Exact Minor Unit Precision**: All budget caps, allocations, actual expenses, and projections are calculated using 64-bit integer minor currency units (`paise`) and fixed-point `NUMERIC(18, 4)` in major units.

```
       ┌────────────────────────────────────────────────────────┐
       │              Workspace Boundary (Anti-IDOR)            │
       │                                                        │
       │   ┌──────────────────┐         1:N      ┌──────────┐   │
       │   │      Budget      │◄─────────────────┤Revisions │   │
       │   │  (Monthly/Custom)│                  └──────────┘   │
       │   └─────────┬────────┘                                 │
       │             │ 1:N                       ┌──────────┐   │
       │             ├──────────────────────────►│  Alerts  │   │
       │             ▼                           └──────────┘   │
       │   ┌──────────────────┐                                 │
       │   │BudgetAllocations │                                 │
       │   │(Category Ceilings│                                 │
       │   └─────────┬────────┘                                 │
       └─────────────┼──────────────────────────────────────────┘
                     │ Matches category_id & date range
                     ▼
       ┌────────────────────────────────────────────────────────┐
       │        Authoritative Transactions Engine (Prompt 09)   │
       │                                                        │
       │   • Status = 'posted' only (pending excluded)          │
       │   • Transfers & CC payments excluded                   │
       │   • Refunds netted against category expenses           │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Relational Database Models & Invariants

### 2.1 The `Budget` Model (`budgets`)
Defines the authoritative budget period, currency, overall allocated ceiling, and lifecycle status.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key | Universally unique budget identifier. |
| `workspace_id` | `UUID` | FK -> `workspaces.id` | Multi-tenant tenant boundary. |
| `name` | `VARCHAR(255)` | NOT NULL | Human-readable budget label. |
| `budget_type` | `VARCHAR(50)` | NOT NULL | `monthly`, `custom_period`, `category`, `annual`, `flexible`. |
| `currency` | `VARCHAR(3)` | NOT NULL | ISO 4217 3-letter currency code (default: `INR`). |
| `start_date` | `DATE` | NOT NULL | Beginning of the budget window. |
| `end_date` | `DATE` | NOT NULL | End of the budget window (`end_date >= start_date`). |
| `total_allocated_paise` | `BIGINT` | NOT NULL, `>= 0` | Total budget ceiling in integer minor units. |
| `total_allocated` | `NUMERIC(18, 4)` | NOT NULL | Major currency representation. |
| `recurrence_interval` | `VARCHAR(20)` | NOT NULL | `none`, `monthly`, `quarterly`, `annual`. |
| `status` | `VARCHAR(20)` | NOT NULL | `active`, `archived`, `closed`. |
| `created_by_id` | `UUID` | FK -> `users.id` | User provenance. |
| `settings` | `JSONB` | NOT NULL | Extensible configuration dictionary. |

### 2.2 The `BudgetAllocation` Model (`budget_allocations`)
Enforces category-specific ceilings within an overarching budget envelope.

- **Unique Category Constraint**: `uq_budget_category_allocation (budget_id, category_id)` guarantees that no category can be duplicated within the same budget.
- **Warning Threshold**: Configurable warning percentage (default: `80%`) triggering caution states.

### 2.3 The `BudgetRevision` Model (`budget_revisions`)
Append-only immutable audit trail capturing every structural change:
- `revision_type`: `created`, `budget_updated`, `allocation_added`, `allocation_updated`, `allocation_removed`, `budget_archived`.
- `previous_amount_paise` and `new_amount_paise`.
- `change_reason`: User-provided audit memo explaining the financial change.
- `changed_by_id`: User responsible for the revision.

### 2.4 The `BudgetAlert` Model (`budget_alerts`)
Stores idempotent alert notifications:
- **Unique Constraint**: `uq_budget_alert_threshold (budget_id, allocation_id, threshold_percentage)`.
- Eliminates redundant notifications when subsequent transactions are processed within the same threshold tier.

---

## 3. Service Layer Architecture

The service layer is encapsulated in `BudgetService` (`backend/app/services/budget/budget_service.py`):

1. **`create_budget(...)`**: Validates date order, non-negative amounts, inserts budget, creates initial revision, and flushes initial allocations.
2. **`update_budget(...)`**: Validates parameters, updates attributes, and records a structured revision.
3. **`add_allocation(...)` / `update_allocation(...)` / `remove_allocation(...)`**: Atomically adjusts category ceilings and appends revision entries.
4. **`get_budget_progress(...)`**: Queries PostgreSQL for actual spending, evaluates utilization, derives period progress, computes linear projections, and checks threshold alert crossings.
5. **`rollover_budget(...)`**: Clones budget parameters and category allocations into the subsequent period cycle idempotently.

---

## 4. Multi-Tenant Workspace Security & Anti-IDOR

All budget entities and queries are strictly scoped to the active `workspace_id`:
- FastAPI routes enforce permissions via `require_permission(Permission.VIEW_BUDGETS)` and `require_permission(Permission.MANAGE_BUDGETS)`.
- Data access methods verify both `id` and `workspace_id` in SQL `WHERE` clauses.
- Cross-workspace lookups return 404 to avoid information disclosure.

---

## 5. File References

- Implementation: [budget_service.py](file:///d:/Arthsavora/backend/app/services/budget/budget_service.py)
- Domain Models: [budget.py](file:///d:/Arthsavora/backend/app/domain/budget.py)
- Database Entities: [budget.py](file:///d:/Arthsavora/backend/app/infrastructure/database/models/budget.py)
- Repositories: [budget_repository.py](file:///d:/Arthsavora/backend/app/repositories/budget_repository.py)
- API Routes: [budget_routes.py](file:///d:/Arthsavora/backend/app/api/v1/budget_routes.py)
