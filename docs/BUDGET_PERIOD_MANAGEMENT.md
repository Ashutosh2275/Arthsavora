# Arthsavora — Budget Period Management & Rollover Lifecycle

## 1. Overview & Time Horizons

Arthsavora provides flexible, robust budget period definitions accommodating varied personal financial rhythms:

| Budget Type | Description | Recurrence Interval Options | Typical Use Case |
|---|---|---|---|
| `monthly` | Standard calendar month (e.g. 1 Nov – 30 Nov). | `monthly` | Salaried household monthly expense planning. |
| `custom_period` | User-defined start and end dates. | `none`, `monthly`, `quarterly`, `annual` | Project-based, trip, or wedding budgets. |
| `annual` | Full calendar or fiscal year. | `annual` | Annual insurance, property tax, and education budgets. |
| `category` | Dedicated budget envelope for a single domain. | `monthly`, `quarterly`, `annual` | Specialized vehicle maintenance or dining out limits. |
| `flexible` | Dynamic rolling window. | `monthly`, `quarterly` | Freelancer or irregular income households. |

---

## 2. Automatic Period Generation & Rollovers

When a budget reaches its period end, or when a user requests a proactive rollover, Arthsavora's `generate_next_period_bounds` computes the exact subsequent dates.

### 2.1 Next Period Bound Formulas

1. **Monthly Recurrence (`monthly`)**:
   - $\text{Next Start} = \text{First day of next calendar month}$.
   - $\text{Next End} = \text{Last day of next calendar month}$ (handling 28, 29, 30, and 31 days).
   - If current is Nov 2026: $\rightarrow$ 1 Dec 2026 to 31 Dec 2026.
2. **Quarterly Recurrence (`quarterly`)**:
   - Period advances by exactly 3 months (e.g. Q4 2026 $\rightarrow$ Q1 2027).
3. **Annual Recurrence (`annual`)**:
   - Advances year by +1 (e.g. 1 Jan 2026 – 31 Dec 2026 $\rightarrow$ 1 Jan 2027 – 31 Dec 2027).
4. **India Financial Year (1 April – 31 March)**:
   - Preserves standard Indian fiscal cadence across multi-year cycles.

---

## 3. The Rollover Execution Lifecycle

When `rollover_budget` is invoked via `POST /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/rollover`:

```
       ┌────────────────────────────────────────────────────────┐
       │                Active Budget (e.g. Nov 2026)          │
       │                                                        │
       │  • Total Cap: ₹50,000                                  │
       │  • Groceries: ₹20,000 (80% threshold)                  │
       │  • Utilities: ₹10,000 (80% threshold)                  │
       │  • Status: Active / Expiring                           │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
                   POST /budgets/{id}/rollover
                   (Optional adjustment & dates)
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │               New Budget (e.g. Dec 2026)               │
       │                                                        │
       │  • Cloned from parent budget                           │
       │  • Carries forward all category ceilings & thresholds  │
       │  • Initialized with revision #1 ("Initial created")    │
       │  • Fresh spending baseline against Dec transactions    │
       │  • Prior Nov records remain permanently intact         │
       └────────────────────────────────────────────────────────┘
```

### 3.1 Preservation of Historical Records
- **Zero Loss of History**: Rollover **never** overwrites, truncates, or resets the parent budget.
- The parent budget retains its historical spent totals, audit revisions, and triggered alerts for historical review.
- The new budget receives a fresh UUID and begins tracking expenses against transactions matching its new date window.

---

## 4. File References

- Period Calculations: [budget.py](file:///d:/Arthsavora/backend/app/domain/budget.py)
- Rollover Logic: [budget_service.py](file:///d:/Arthsavora/backend/app/services/budget/budget_service.py)
- API Routes: [budget_routes.py](file:///d:/Arthsavora/backend/app/api/v1/budget_routes.py)
