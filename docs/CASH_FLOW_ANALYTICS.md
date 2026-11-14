# Arthsavora Cash Flow Analytics

## 1. Overview

Cash flow analytics track the trajectory, periodicity, and cumulative velocity of funds moving into and out of an Arthsavora workspace. Unlike simple accounting balance sheets, cash flow reveals liquidity trends over time and serves as the deterministic foundation for future forecasting and runway estimations.

---

## 2. Temporal Partitioning & Grouping Intervals

Arthsavora supports five temporal grouping intervals via PostgreSQL server-side `func.date_trunc`:

| Interval Enum | SQL Truncate | Period Label Format | Example |
| :--- | :--- | :--- | :--- |
| `day` | `'day'` | `%d %b %Y` | `14 Feb 2026` |
| `week` | `'week'` | `W%V %Y` (ISO Week) | `W07 2026` |
| `month` | `'month'` | `%b %Y` | `Feb 2026` |
| `quarter` | `'quarter'` | `Q%q %Y` | `Q1 2026` |
| `financial_year` | `'year'` | `FY YYYY-YY` | `FY 2025-26` |

---

## 3. India Financial Year (FY) Date Alignment

In India, the financial year runs from **1 April to 31 March**:
- If reference date month $\ge 4$: Starts `YYYY-04-01`, ends `(YYYY + 1)-03-31`.
- If reference date month $< 4$: Starts `(YYYY - 1)-04-01`, ends `YYYY-03-31`.

### Example Test Vectors:
- `2026-02-14` $\rightarrow$ `FY 2025-26` (`2025-04-01` to `2026-03-31`)
- `2026-04-01` $\rightarrow$ `FY 2026-27` (`2026-04-01` to `2027-03-31`)

The frontend date toolbar includes a dedicated **"Current FY (India)"** one-click preset button.

---

## 4. Cumulative Cash Flow Mechanics

In addition to per-period net flow, the engine computes running **Cumulative Cash Flow**:
$$\text{Cumulative Cash Flow}_k = \sum_{i=1}^k \text{Net Cash Flow}_i$$

This provides an immediate visual indication of whether the workspace is on a sustainable capital accumulation slope or experiencing protracted operational drain.

---

## 5. Excluded Movements in Cash Flow Calculations

The following transactions are strictly excluded from cash flow totals:
1. `transfer_id IS NOT NULL` (both legs of internal account transfers).
2. `transaction_type = 'transfer'`.
3. `transaction_type = 'credit_card_payment'` (settlement of debt).
4. `transaction_type = 'loan_disbursal'` / `loan_principal_repayment`.
5. `transaction_type = 'investment_contribution'` / `investment_withdrawal`.
6. Any transaction with `status != 'posted'`.
