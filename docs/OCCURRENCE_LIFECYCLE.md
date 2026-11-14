# Arthsavora — Recurring Occurrence Lifecycle Specification

## 1. Scope & Objective

Every scheduled financial commitment in Arthsavora transitions through a well-defined, auditable lifecycle. This document outlines the state machine, valid state transitions, automatic evaluations, and user interventions governing `RecurringOccurrence` records.

---

## 2. Occurrence State Machine

```
                            ┌───────────────┐
                            │   Scheduled   │
                            └───────┬───────┘
                                    │ expected_date <= today + 7
                                    ▼
                            ┌───────────────┐
                            │   Upcoming    │
                            └───────┬───────┘
                                    │ expected_date == today
                                    ▼
                            ┌───────────────┐
                     ┌─────►│      Due      ├──────┐
                     │      └───────┬───────┘      │
                     │              │              │
      expected_date  │              │              │
        <= today - 2 │              │              │
                     │              ▼              │
                     │      ┌───────────────┐      │
                     └──────┤    Overdue    │      │
                            └───────┬───────┘      │
                                    │              │
                     ┌──────────────┴──────────────┤
                     │                             │
    User Skips /     │                             │ Matched with posted
    Paused           ▼                             ▼ Transaction / User confirms
             ┌───────────────┐             ┌───────────────┐
             │    Skipped    │             │    Matched    │
             └───────────────┘             └───────┬───────┘
                                                   │ User confirmed / Reconciled
                                                   ▼
             ┌───────────────┐             ┌───────────────┐
             │   Cancelled   │             │   Confirmed   │
             └───────────────┘             └───────────────┘
```

---

## 3. Occurrence Status Definitions

| Status | Code | Criteria / Invariant |
|---|---|---|
| `scheduled` | Pending future | `expected_date > today + 7`. In active horizon, awaiting notification window. |
| `upcoming` | Near-term alert | `today < expected_date <= today + 7`. Candidate for reminder delivery. |
| `due` | Action day | `expected_date == today`. Payment or deposit expected today. |
| `overdue` | Unmatched past | `expected_date < today - 2` and no matched transaction has been recorded. |
| `matched` | Auto/manual link | Reconciled against a verified posted `transaction_id`. |
| `confirmed` | User acknowledged | Manually confirmed by user (e.g., cash payment outside connected bank feeds). |
| `skipped` | Non-occurrence | Explicitly bypassed by user (e.g., billing holiday, temporary pause). |
| `cancelled` | Revoked | Recurring definition was cancelled or occurrence revoked prior to due date. |

---

## 4. State Evaluation Logic

The pure domain function `evaluate_occurrence_state` determines the current status based on calendar coordinates and matching state:

```python
def evaluate_occurrence_state(
    expected_date: date,
    current_date: date,
    matched_transaction_id: Optional[UUID] = None,
    is_confirmed: bool = False,
    is_skipped: bool = False,
    is_cancelled: bool = False,
) -> str:
    if is_cancelled:
        return "cancelled"
    if is_skipped:
        return "skipped"
    if is_confirmed:
        return "confirmed"
    if matched_transaction_id is not None:
        return "matched"

    days_diff = (expected_date - current_date).days

    if days_diff > 7:
        return "scheduled"
    elif 0 < days_diff <= 7:
        return "upcoming"
    elif days_diff == 0:
        return "due"
    elif days_diff < 0:
        if days_diff < -2:
            return "overdue"
        return "due"
```

---

## 5. Transition Rules & Invariants

1. **Terminal vs Mutable States**:
   - `confirmed` and `matched` can be reverted to `due` or `overdue` if the user explicitly unmatches the transaction.
   - `skipped` occurrences do not match transactions unless explicitly reopened.
   - `cancelled` occurrences are archived.

2. **Decoupling from Accounting Ledgers**:
   - Marking an occurrence as `confirmed` or `matched` **does not create an accounting journal entry**.
   - If an occurrence is confirmed manually without an underlying bank transaction, it represents an informational note for cash-flow tracking, not an unverified ledger balance injection.

3. **Audit Trail**:
   - `confirmed_at` records the exact UTC timestamp of confirmation.
   - `notes` records user context or discrepancy explanations.
