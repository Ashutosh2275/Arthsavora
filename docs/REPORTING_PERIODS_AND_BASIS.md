# ARTHSAVORA — REPORTING PERIODS AND ACCOUNTING BASIS

## 1. Indian Financial Year (FY) Standards

In the Indian jurisdiction, the statutory financial year runs from **April 1 to March 31** of the following Gregorian calendar year.

### 1.1 Canonical FY Representation
- The canonical string format is `FY YYYY-YY` (e.g. `FY 2026-27`).
- Supported input variants parsed by the engine:
  - `"FY 2026-27"`
  - `"2026-27"`
  - `"2026-2027"`
  - `"FY 2026-2027"`

### 1.2 Fiscal Year Bounds Calculation
Given reference date $D = (Y, M, D_{\text{day}})$:
$$\text{If } M \ge 4: \quad \text{FY Start} = \text{April 1, } Y; \quad \text{FY End} = \text{March 31, } Y + 1$$
$$\text{If } M < 4: \quad \text{FY Start} = \text{April 1, } Y - 1; \quad \text{FY End} = \text{March 31, } Y$$

### 1.3 Quarterly Breakdown (Indian Quarters)
| Quarter | Calendar Months | Start Date | End Date | Canonical Label |
| :---: | :--- | :---: | :---: | :--- |
| **Q1** | April – June | April 1, $Y$ | June 30, $Y$ | `FY YYYY-YY Q1 (Apr-Jun)` |
| **Q2** | July – September | July 1, $Y$ | September 30, $Y$ | `FY YYYY-YY Q2 (Jul-Sep)` |
| **Q3** | October – December | October 1, $Y$ | December 31, $Y$ | `FY YYYY-YY Q3 (Oct-Dec)` |
| **Q4** | January – March | January 1, $Y+1$ | March 31, $Y+1$ | `FY YYYY-YY Q4 (Jan-Mar)` |

---

## 2. Supported Reporting Period Types

The `PeriodType` enumeration supports:
1. `financial_year`: Entire statutory 12-month period.
2. `quarterly`: One of the 4 statutory quarters.
3. `monthly`: Single calendar month.
4. `weekly`: 7-day operational cycle.
5. `daily`: Single day ledger snapshot.
6. `custom`: User-specified arbitrary $[T_{\text{start}}, T_{\text{end}}]$ date range.

---

## 3. Accounting Basis Comparison

| Characteristic | Cash Basis | Accrual Basis |
| :--- | :--- | :--- |
| **Recognition Event** | Settlement of bank/cash transfer | Generation of invoice or journal entry |
| **Accounts Receivable** | Ignored until collected | Recorded at issuance |
| **Accounts Payable** | Ignored until disbursed | Recorded upon bill receipt |
| **Suitability** | Individuals, Freelancers, Section 44ADA | Corporate entities, GST-registered firms |
| **Data Source** | `transactions` table (`status='completed'`) | `journal_lines` & `journal_entries` |
