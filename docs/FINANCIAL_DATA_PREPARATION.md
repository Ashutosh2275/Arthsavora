# ARTHSAVORA — FINANCIAL DATA PREPARATION PIPELINE
**Document Reference:** `docs/FINANCIAL_DATA_PREPARATION.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

A forecast is only as reliable as the financial time-series fed into the model. In financial domains, raw transaction logs are fraught with internal account transfers, credit-card bill settlements, contra-expense refunds, and non-linear calendar clustering that distort statistical inference.

The **Arthsavora Financial Data Preparation Pipeline** (`DataPreparationService`) implements deterministic, auditable data extraction rules to transform raw PostgreSQL transaction and account records into contiguous, normalized time-series suitable for statistical forecasting.

---

## 2. Liquid Account Balance Derivation

Forecasting forward cash-flow requires an accurate starting balance representing immediately accessible liquid capital. 

### Included Liquid Account Types
- `savings` (Personal Savings Accounts)
- `current` (Business Current Accounts)
- `cash` (Physical Cash-in-Hand)
- `salary` (Designated Salary Accounts)
- `digital_wallet` (UPI Wallets, Paytm, PhonePe balances)
- `petty_cash` (Office / Household Petty Cash)

### Excluded Non-Liquid Accounts
- `credit_card` (Revolving debt liability; balance represents outstanding debt, not liquid wealth)
- `loan` (Term loans, home loans, vehicle loans, personal loans)
- `mortgage` (Long-term secured liabilities)
- `investment` (Fixed deposits, mutual funds, equities subject to liquidation penalties or market lock-in)

The starting liquid balance is computed via SQL aggregation:
```sql
SELECT COALESCE(SUM(current_book_balance_paise), 0)
FROM accounts
WHERE workspace_id = :workspace_id
  AND is_deleted = FALSE
  AND status = 'active'
  AND account_type IN ('savings', 'current', 'cash', 'salary', 'digital_wallet', 'petty_cash');
```

---

## 3. Transaction Filtering & Non-Spending Exclusions

To avoid artificial inflation of income or expenses, internal money movements and liability settlements are strictly excluded from statistical series:

### 1. Internal Transfers
- Any transaction where `transfer_id IS NOT NULL` is an internal movement between two accounts within the same workspace.
- `transaction_type IN ('transfer', 'adjustment', 'reversal')` are excluded.

### 2. Credit-Card Bill Payments & Loan Principal Repayments
- Paying a credit-card bill (`credit_card_payment`) or servicing loan principal (`loan_principal_repayment`) transfers money from a savings account to a liability account. Treating this as an expense would double count the purchases previously posted on the credit card.
- Therefore, `transaction_type IN ('credit_card_payment', 'loan_repayment', 'loan_principal_repayment')` are strictly excluded from outflow time-series.

### 3. Investment Contributions & Redemptions
- Money moved into mutual funds or fixed deposits (`investment_contribution`) is capital allocation, not consumptive outflow. They are tracked under scenario cash flows or explicit user goals, not baseline operational spending.

### 4. Status Filtering
- Only transactions with `status = 'posted'` and `is_deleted = FALSE` are extracted.
- Pending authorisations (`pending`), failed payments (`failed`), and cancelled items (`cancelled`) are excluded.

---

## 4. Refund Netting & Contra-Expense Accounting

Merchant refunds and credit-card purchase reversals (`refund`, `credit_card_refund`) represent negative outflows rather than genuine income. If refunds were treated as inflows, gross income and gross expense metrics would both be artificially inflated.

The data preparation pipeline nets refunds against daily outflows on the exact transaction date:
$$\text{Net Daily Outflow}_t = \max(0, \text{Gross Outflows}_t - \text{Total Refunds}_t)$$

```python
refund_stmt = (
    select(
        Transaction.transaction_date,
        func.sum(Transaction.amount_paise).label("total_paise"),
    )
    .where(
        Transaction.workspace_id == workspace_id,
        Transaction.status == "posted",
        Transaction.is_deleted == False,
        Transaction.transaction_date >= start_dt,
        Transaction.transaction_date <= end_dt,
        Transaction.transaction_type.in_(["refund", "credit_card_refund"]),
    )
    .group_by(Transaction.transaction_date)
)
```

---

## 5. Contiguous Time-Series Construction

Time-series algorithms require regular, uninterrupted daily intervals. A naive aggregation of transactions leaves "gaps" on days when no purchases occurred. Treating these missing days as non-existent breaks autoregressive calculations.

The pipeline explicitly constructs a contiguous sequence for each day from $T_{\text{start}}$ to $T_{\text{end}}$, imputing `0 paise` for days with zero transactions:

```python
daily_inflows: List[TimeSeriesPoint] = []
daily_outflows: List[TimeSeriesPoint] = []

curr_dt = start_dt
while curr_dt <= end_dt:
    daily_inflows.append(
        TimeSeriesPoint(date=curr_dt, amount_paise=inflow_map.get(curr_dt, 0))
    )
    daily_outflows.append(
        TimeSeriesPoint(date=curr_dt, amount_paise=outflow_map.get(curr_dt, 0))
    )
    curr_dt += timedelta(days=1)
```

---

## 6. Outlier Handling & Windfall Spikes

Unusual one-time windfalls (e.g., annual bonuses, insurance payouts, asset sales) or massive capital expenditures (e.g., down payments) can distort historical trend slopes.

The pipeline provides winsorization / outlier clipping when enabled:
- Let $\mu$ be the mean daily spend and $\sigma$ be the standard deviation.
- Daily totals exceeding $\mu + 3\sigma$ (or the 98th percentile) are flagged as outliers.
- In baseline trend models, extreme spikes are temporarily clipped to $\mu + 3\sigma$ for parameter estimation, preserving the underlying run-rate without hiding user transactions.

---

## 7. Data Eligibility & Quality Scoring

To enforce institutional transparency, every dataset is evaluated by `assess_data_eligibility`:

| Status | Active Transaction Days | Permitted Models | User Notification |
| :--- | :---: | :--- | :--- |
| **`sufficient`** | $\ge 30$ days | All (Holt-Winters, Trend, SES, MA, Mean) | Full predictive modeling enabled |
| **`limited_baseline_only`**| $7 - 29$ days | Baseline only (Historical Mean, 7-day MA) | "Limited historical data. Forecasts rely on basic averages." |
| **`insufficient_data`** | $< 7$ days | Transparent Historical Mean fallback | "Insufficient historical records. Import statements to unlock ML predictions." |

The engine calculates a **Data Quality Score** ($0.0 \text{ to } 1.0$) based on temporal span, active transaction density, and category coverage, persisted directly on `forecast_runs.data_quality_score`.
