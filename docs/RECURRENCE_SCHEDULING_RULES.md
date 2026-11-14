# Arthsavora — Recurrence Scheduling Rules & Date Math Specification

## 1. Scope & Objective

This document defines the mathematical and calendar algorithms used to compute scheduled recurrence dates across Arthsavora. Because financial recurrences (such as salary disbursement, rent payments, SIP investments, and utility billing) operate on Gregorian calendar months of varying lengths, accurate scheduling requires rigorous rules that avoid cumulative calendar drift.

---

## 2. Supported Frequencies & Cadences

| Frequency Identifier | Interval Multiplier | Base Unit | Step Calculation |
|---|---|---|---|
| `daily` | `interval >= 1` | Days | `current_date + timedelta(days=interval)` |
| `weekly` | `interval >= 1` | Weeks | `current_date + timedelta(weeks=interval)` |
| `biweekly` | `1` | 2 Weeks | `current_date + timedelta(weeks=2 * interval)` |
| `monthly` | `interval >= 1` | Months | Month arithmetic with pinned day-of-month and end-of-month clamping. |
| `quarterly` | `interval >= 1` | 3 Months | Monthly addition stepping `3 * interval` months forward. |
| `semi_annual` | `interval >= 1` | 6 Months | Monthly addition stepping `6 * interval` months forward. |
| `annual` | `interval >= 1` | Years | Year addition preserving target month and pinned day. |
| `custom` | `interval >= 1` | Days | `current_date + timedelta(days=interval)` |

---

## 3. Month Addition & The Pinning Invariant

### 3.1 The Permanent Drift Problem
A naïve date increment algorithm that computes `next_month = current_date + 1 month` suffers from irreversible drift:
- Starting Date: January 31
- Cycle 1 (February): February has 28 days (or 29 in leap years). The date clamps to February 28.
- Naïve Cycle 2 (March): Adding one month to February 28 results in March 28.
- Result: **The user loses their original intention of paying on the 31st for the rest of the year.**

### 3.2 The Deterministic Pinning Solution
Arthsavora explicitly decouples the **pinned day-of-month** (`target_day`) from the **current clamped date**:
1. When a definition is created, the system stores `day_of_month = start_date.day` (e.g. 31).
2. For each step forward, the algorithm calculates:
   $$\text{target\_year} = \text{start\_year} + \frac{\text{start\_month} - 1 + \text{months\_ahead}}{12}$$
   $$\text{target\_month} = ((\text{start\_month} - 1 + \text{months\_ahead}) \pmod{12}) + 1$$
3. The maximum days in `(target_year, target_month)` is computed:
   $$\text{max\_days} = \text{calendar.monthrange}(\text{target\_year}, \text{target\_month})[1]$$
4. The resolved day is clamped:
   $$\text{day} = \min(\text{target\_day}, \text{max\_days})$$
5. When `target_day = 31`:
   - January 31 $\to$ February 28 (or 29)
   - February 28 $\to$ March 31
   - March 31 $\to$ April 30
   - April 30 $\to$ May 31
   - May 31 $\to$ June 30
   - June 30 $\to$ July 31

The schedule **never drifts permanently**.

---

## 4. Leap Year Handling

A leap year occurs in the Gregorian calendar when:
$$\text{is\_leap} = (\text{year} \pmod 4 = 0 \land \text{year} \pmod{100} \ne 0) \lor (\text{year} \pmod{400} = 0)$$

For schedules pinned to February 29:
- In leap years (e.g., 2024, 2028), occurrences generate on February 29.
- In non-leap years (e.g., 2025, 2026, 2027), occurrences clamp to February 28.
- In 2028 (the next leap year), the schedule automatically returns to February 29 without manual intervention.

---

## 5. End of Month Policy

Definitions support explicit policies via `end_of_month_policy`:
- `last_day`: Always pins to the final day of the target month (28, 29, 30, or 31).
- `closest_business_day`: If the resolved date falls on a weekend, adjust backward to Friday (or forward to Monday, depending on institutional rules).
- `strict_day`: Adheres to the exact numeric day; if the month has fewer days, clamps to the month's final day.

---

## 6. Forward Occurrence Generation Windows

1. **Horizon**: By default, occurrences are generated 90 days into the future from `current_date` or `next_expected_date`.
2. **Termination**: Generation ceases if `expected_date > definition.end_date`.
3. **Idempotency**: The relational database enforces `UNIQUE (recurring_definition_id, expected_date)`. Attempting to generate existing occurrences is treated as a safe no-op.
