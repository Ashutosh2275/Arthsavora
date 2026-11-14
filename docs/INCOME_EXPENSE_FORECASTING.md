# ARTHSAVORA — INCOME AND EXPENSE FORECASTING ENGINE
**Document Reference:** `docs/INCOME_EXPENSE_FORECASTING.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

Forecasting financial health requires decomposing inflows and outflows into distinct behavioral components:
1. **Fixed Commitments:** Deterministic, contractually bound or scheduled payments (e.g., apartment rent, loan EMIs, school fees, Netflix subscriptions, regular monthly salary).
2. **Variable Discretionary Activity:** Elastic day-to-day spending (e.g., groceries, dining out, shopping, fuel, weekend entertainment).
3. **Seasonal & Day-of-Week Cycles:** Recurring cyclical surges (e.g., higher dining/entertainment on Saturdays/Sundays; festival surges during Diwali/Dussehra; month-end bill spikes).

The **Arthsavora Income & Expense Forecasting Engine** models these components separately and recombines them into coherent, calibrated forward projections.

---

## 2. Income Forecasting Methodology

Personal and commercial income exhibits two primary modalities:

### 1. Salaried & Regular Cadence
- Inflows recur on fixed days of the month (e.g., 1st or 28th) or fixed weekdays (bi-weekly).
- Modeled directly via **Prompt 15 Recurring Definitions**:
  $$\text{Scheduled Inflow}_t = \sum \text{Expected Occurrence Amounts on date } t$$
- If recurring definitions have not been explicitly configured by the user, the historical pattern detector identifies recurring deposits exceeding ₹5,000 with low cadence variance and proposes them as income schedules.

### 2. Variable & Freelance / Business Inflows
- Freelance invoices, consulting fees, retail daily sales, or dividend payouts.
- Modeled through historical mean or moving-average rate smoothing across the horizon:
  $$\hat{y}_{\text{inflow}, t} = \frac{1}{N} \sum_{k=1}^N y_{\text{inflow}, k}$$
- This avoids projecting sudden artificial spikes on arbitrary future days while accurately representing expected income velocity over the 30-to-90-day horizon.

---

## 3. Expense Forecasting & Category Decomposition

Expenses are forecasted at both the **aggregate portfolio level** and the **individual category level**.

### Category Spending Extraction
The pipeline aggregates 90 days of daily spending per category:
```python
stmt = (
    select(
        Transaction.category_id,
        Transaction.transaction_date,
        func.sum(Transaction.amount_paise).label("total_paise"),
    )
    .where(
        Transaction.workspace_id == workspace_id,
        Transaction.status == "posted",
        Transaction.direction == "outflow",
        Transaction.is_deleted == False,
        Transaction.transaction_date >= start_dt,
        Transaction.transaction_date <= end_dt,
        Transaction.transaction_type.notin_(["transfer", "credit_card_payment", "loan_repayment"]),
    )
    .group_by(Transaction.category_id, Transaction.transaction_date)
)
```

### Trend Direction Classification
For each active category, the engine projects forward spending over the horizon $H$ (typically 30 days) using an adaptive 14-day moving average and compares it against the historical monthly baseline:
$$\text{Historical Monthly Average} = \frac{\text{Total 90-Day Spend}}{3.0}$$

A trend classification is assigned:
- **`increasing`**: $\text{Projected Spend} > \text{Monthly Average} \times 1.10$ (spending accelerating by $>10\%$)
- **`decreasing`**: $\text{Projected Spend} < \text{Monthly Average} \times 0.90$ (spending curtailing by $>10\%$)
- **`stable`**: Within $\pm 10\%$ of historical monthly average

This allows users to immediately spot ballooning expense categories (e.g., Dining Out, Online Shopping) before month-end.

---

## 4. Seasonal & Cyclical Patterns

### Weekly Seasonality (Holt-Winters Additive Seasonality)
Consumer spending in India demonstrates strong day-of-week seasonality:
- Monday–Thursday: Baseline routine necessities (groceries, transport, daily food).
- Friday–Sunday: Elevated dining, entertainment, shopping, and family outings.

To capture this without overfitting, the engine includes a **7-period Additive Holt-Winters Model**:
- Season length $L = 7$ days.
- Initial seasonal indices $s_i$ are derived from normalized day-of-week spending ratios:
  $$s_i = \bar{y}_{\text{day } i} - \bar{y}_{\text{overall}}$$
- Level equation:
  $$L_t = \alpha (y_t - s_{t-L}) + (1 - \alpha)(L_{t-1} + b_{t-1})$$
- Trend equation:
  $$b_t = \beta (L_t - L_{t-1}) + (1 - \beta) b_{t-1}$$
- Seasonality equation:
  $$s_t = \gamma (y_t - L_t) + (1 - \gamma) s_{t-L}$$
- Point forecast for lead $k$:
  $$\hat{y}_{t+k} = \max(0, L_t + k \cdot b_t + s_{t+k-L})$$

### Month-End Utility & Rent Clustering
Utility bills, rent, and credit-card payments predominantly concentrate between the 25th of the month and the 5th of the following month. Because these are tracked as **scheduled recurring commitments**, they are placed on their exact calendar due dates rather than being smeared arbitrarily across all 30 days.

---

## 5. Merchant-Level Pattern Integration

Recurring expenses tied to specific merchants (e.g., BESCOM Electricity, Airtel Broadband, Tata Play, LIC Premium, Amazon Prime) are automatically correlated with category forecasts:
- When a recurring merchant commitment is confirmed, its exact expected amount is anchored to the due date.
- The discretionary residual for that category is estimated by subtracting the merchant's historical contribution:
  $$\text{Discretionary Category Spend} = \max(0, \text{Baseline Category Forecast} - \text{Known Merchant Commitments})$$

This guarantees that an upcoming ₹4,500 electricity bill is neither forgotten nor counted twice.
