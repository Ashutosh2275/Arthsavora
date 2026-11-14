# Arthsavora — Recurring Financial Activity Architecture

## 1. Executive Summary & Core Mission

The Recurring Financial Activity Management module in Arthsavora provides institutional-grade tracking, scheduling, anticipation, and reconciliation of regular cash-flow commitments across personal, family, and business workspaces. It encompasses scheduled income (salaries, dividends, stipends), recurring expenses (rent, utilities, insurance, loan EMIs), subscription memberships (SaaS, media, fitness), and forward-looking commitments.

Crucially, this system operates under a fundamental financial invariant:
> **An expected recurring occurrence is strictly an anticipation of a financial event and NEVER proof that funds were moved.**

Scheduled payments, subscription renewal dates, and expected occurrences do not automatically generate General Ledger journal entries, do not modify financial account balances, and do not execute bank transfers. They only reconcile against authoritative financial records when real, verified transactions are imported or posted.

```
       ┌────────────────────────────────────────────────────────┐
       │             Workspace Boundary (Anti-IDOR)             │
       │                                                        │
       │   ┌───────────────────────────┐                        │
       │   │   RecurringDefinition     │                        │
       │   │ (Rent, Salary, EMI, SaaS) │                        │
       │   └─────────────┬─────────────┘                        │
       │                 │ 1:1 or 1:0..1                        │
       │                 ▼                                      │
       │   ┌───────────────────────────┐                        │
       │   │       Subscription        │                        │
       │   │ (Trials, Cycles, Deadlines│                        │
       │   └─────────────┬─────────────┘                        │
       │                 │                                      │
       │                 │ 1:N Idempotent Schedule Generation   │
       │                 ▼                                      │
       │   ┌───────────────────────────┐                        │
       │   │    RecurringOccurrence    │                        │
       │   │ (Scheduled / Due / Matched│                        │
       │   └─────────────┬─────────────┘                        │
       └─────────────────┼──────────────────────────────────────┘
                         │ 
                         │ Reconciled / Matched (Optional 1:1)
                         ▼
       ┌────────────────────────────────────────────────────────┐
       │        Authoritative Transactions Engine (Prompt 09)   │
       │                                                        │
       │   • Status = 'posted' actual bank transaction          │
       │   • Preserves General Ledger balance immutability      │
       │   • Exact reconciliation without balance fabrication   │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Institutional Engineering Principles

1. **Strict Separation of Expectation and Reality**:
   - `recurring_definitions` and `recurring_occurrences` model planned or anticipated cash events.
   - `transactions` and `journal_entries` represent immutable historical accounting facts.
   - Reconciling an occurrence links `matched_transaction_id` but never alters double-entry ledger postings.

2. **Deterministic Date Math & Non-Drifting Schedules**:
   - Monthly and multi-month recurrences preserve initial user intent via `day_of_month` pinning.
   - Clamping to month ends (e.g. Jan 31 -> Feb 28) never permanently shifts subsequent cycles to the 28th; the recurrence engine springs back to Mar 31 and Apr 30 deterministically.
   - Leap years (Feb 29) are fully evaluated using Gregorian calendar rules.

3. **Idempotent Occurrence Generation**:
   - Unique relational constraints `(recurring_definition_id, expected_date)` prevent duplicate occurrence records even when generation algorithms run concurrently or repeatedly.
   - Forward generation windows default to 90 days, dynamically backfilled as time advances.

4. **Exact Monetary Precision**:
   - All expected amounts, matched amounts, normalized monthly costs, and commitments are calculated in 64-bit integer minor currency units (`paise`) and mapped to `NUMERIC(18, 4)` in major units.
   - Zero floating-point rounding errors are permitted.

5. **Multi-Tenant Workspace Isolation**:
   - Every definition, occurrence, subscription, suggestion, and reminder contains a mandatory, foreign-keyed `workspace_id`.
   - All repository queries filter by `workspace_id` to enforce strict anti-IDOR protection.

6. **Explainable Pattern Detection**:
   - Historical transaction clusters are scanned to discover recurring patterns (e.g., Netflix, utility bills, rent).
   - Inferred recurring suggestions are never silently activated; they require explicit human confirmation or dismissal.

---

## 3. Relational Schema Architecture

The module introduces five dedicated relational tables in PostgreSQL:

| Table Name | Primary Responsibility | Key Invariants |
|---|---|---|
| `recurring_definitions` | Canonical definition of recurring rules, cadence, direction, and amount. | `interval >= 1`, `day_of_month BETWEEN 1 AND 31`, `expected_amount_paise >= 0`. |
| `recurring_occurrences` | Individual scheduled instances of an expected event. | `UNIQUE(recurring_definition_id, expected_date)`, lifecycle state machine. |
| `subscriptions` | Metadata for recurring services, trial periods, and cancellation workflows. | Links 1:1 with `recurring_definition_id`. |
| `recurring_reminders` | Scheduled notifications prior to occurrence due dates. | `days_before >= 0`, `status IN ('pending', 'sent', 'dismissed')`. |
| `recurring_suggestions` | Heuristically detected recurring patterns awaiting user confirmation. | `confidence_score BETWEEN 0.0 AND 1.0`, `status IN ('pending', 'confirmed', 'dismissed')`. |

---

## 4. Subsystem Interactions

### 4.1 Budgeting Subsystem (`budgets`, `budget_allocations`)
- Future occurrences feed into budget capacity analysis and linear spend projections.
- Expected recurring commitments are presented alongside actual category expenditures without double-counting uncompleted transactions.

### 4.2 Analytics Subsystem (`cash_flow_analytics`)
- Aggregates recurring obligations across 7-day, 30-day, and 90-day forward horizons.
- Distinguishes fixed commitments (rent, loan EMIs, insurance) from variable recurring activities.

### 4.3 General Ledger Subsystem (`journal_entries`)
- The General Ledger is strictly decoupled from recurring definitions.
- When an occurrence is matched to a posted transaction, the transaction already contains its verified balanced journal entry. The recurring engine merely registers the link.

---

## 5. Security and Compliance

- **No Credential Storage**: Arthsavora never stores payment credentials, credit card numbers, CVVs, netbanking passwords, or UPI MPINs.
- **No Direct Execution**: Arthsavora does not hold bank licenses to trigger ACH, NACH, or UPI AutoPay debits directly.
- **Audit Traceability**: All changes to recurring definitions and occurrence state transitions log timestamps and user IDs (`created_by_id`, `confirmed_at`).
