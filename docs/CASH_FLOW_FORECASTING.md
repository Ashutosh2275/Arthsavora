# ARTHSAVORA — CASH-FLOW FORECASTING AND LIQUIDITY TRAJECTORY
**Document Reference:** `docs/CASH_FLOW_FORECASTING.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

Cash flow is the lifeblood of personal financial stability and business solvency. A user may have healthy net savings on paper while still encountering severe cash-flow crunches mid-month if major outflows (such as rent or loan EMIs) precede delayed salary or invoice inflows.

The **Arthsavora Cash-Flow Forecasting Engine** projects daily balance trajectories and net liquidity positions across horizons of 7, 30, 60, and 90 days. It seamlessly integrates confirmed recurring obligations (Prompt 15) with statistical discretionary spending, alerts users to liquidity troughs, and directly projects budget exhaustion and goal pacing (Prompt 14).

---

## 2. The Core Cash-Flow Balance Equation

For any forward date $t$ within the projection horizon:
$$\text{Projected Balance}_t = \text{Starting Balance}_t + \text{Inflow}_t - \text{Outflow}_t$$

### Resolving Inflow and Outflow Components
In conventional personal finance tools, integrating scheduled bills with historical averages leads to fatal double-counting: an average daily spend of ₹1,000 already reflects past rent payments, so adding a ₹30,000 rent commitment creates a phantom ₹60,000 monthly rent burden.

Arthsavora resolves this with **Discretionary-Commitment Decoupling**:
$$\text{Inflow}_t = \text{Recurring Inflow}_t + \max(0, \text{Statistical Inflow}_t - \text{Recurring Inflow}_t)$$
$$\text{Outflow}_t = \text{Recurring Outflow}_t + \max(0, \text{Statistical Outflow}_t - \text{Recurring Outflow}_t)$$

- Scheduled recurring commitments are treated as **deterministic anchor events** on their scheduled calendar dates.
- Discretionary activity is treated as a **probabilistic spread** filling the non-committed gap.
- If known commitments on day $t$ exceed the daily statistical average (e.g., rent day), the commitment takes precedence and no artificial discretionary double-count is added.

---

## 3. Daily Balance Progression & Liquidity Risk Detection

The daily projection generates a full chronological ledger entry for each date in the timeline:
- `starting_balance_paise`: Balance at beginning of day $t$.
- `inflow_paise` & `inflow_recurring_paise`: Total and scheduled recurring inflows.
- `outflow_paise` & `outflow_recurring_paise`: Total and scheduled recurring outflows.
- `net_cash_flow_paise`: $\text{Inflows} - \text{Outflows}$.
- `projected_balance_paise`: Expected balance at close of day $t$.
- `lower_balance_paise` & `upper_balance_paise`: Statistical confidence bounds.

### Liquidity Troughs & Overdraft Warnings
When `projected_balance_paise` drops below zero (or below a user-configured safety reserve such as ₹10,000), the system flags a **Liquidity Trough Risk**:
- **Date of Lowest Liquidity:** The specific date on which the cash balance hits its minimum point during the forecast horizon.
- **Deficit Magnitude:** The exact shortfall amount in paise.
- **Recommended Action:** Rescheduling discretionary purchases or delaying non-urgent expenses until after the next scheduled inflow.

---

## 4. Budget Exhaustion Engine (Integration with Prompt 14)

The engine monitors active budgets created under Prompt 14 (`BudgetExhaustionService`) to answer the critical question: *"At current spending rates, when will this budget run out?"*

### Calculation Mechanics
For a budget period from $D_{\text{start}}$ to $D_{\text{end}}$, evaluated on $D_{\text{as\_of}}$:
1. **Days Elapsed:** $N_{\text{elapsed}} = \max(1, (D_{\text{as\_of}} - D_{\text{start}}).days)$
2. **Current Actual Net Spend:** $S_{\text{actual}}$ (gross posted expenses minus refunds).
3. **Daily Burn Rate:**
   $$\text{Burn Rate} = \frac{S_{\text{actual}}}{N_{\text{elapsed}}}$$
4. **Remaining Budget:**
   $$\text{Remaining} = \max(0, \text{Allocated Amount} - S_{\text{actual}})$$
5. **Days to Exhaustion:**
   $$\text{Days to Exhaustion} = \begin{cases} 
   \lfloor \frac{\text{Remaining}}{\text{Burn Rate}} \rfloor & \text{if } \text{Burn Rate} > 0 \\
   \infty & \text{if } \text{Burn Rate} = 0 
   \end{cases}$$
6. **Projected Exhaustion Date:** $D_{\text{as\_of}} + \text{Days to Exhaustion}$

### Exhaustion Status Classification
- **`exhausted`**: Utilization $\ge 100\%$ (budget already exceeded).
- **`critical`**: Projected exhaustion date is before the period end date, and utilization $\ge 80\%$.
- **`warning`**: Projected exhaustion date is before the period end date, but utilization $< 80\%$.
- **`on_track`**: Projected exhaustion date is on or after the period end date (sustainable burn rate).

---

## 5. Savings Goal Trajectory Engine (Integration with Prompt 14)

For each active savings goal (`FinancialGoal`), the engine projects completion milestones based on historical contribution velocity:

1. **Contribution Pace Derivation:**
   - Evaluates all past ledger entries on the goal with `activity_type = 'contribution'`.
   - Derives the average monthly contribution rate:
     $$\text{Monthly Savings Pace} = \frac{\sum \text{Contributions}}{\text{Days Active} / 30.4375}$$
2. **Remaining Target Amount:**
   $$\text{Remaining Target} = \max(0, \text{Target Amount} - \text{Current Balance})$$
3. **Months to Target:**
   $$\text{Months to Target} = \frac{\text{Remaining Target}}{\text{Monthly Savings Pace}}$$
4. **Projected Completion Date:** $D_{\text{as\_of}} + \text{Months to Target} \times 30.4375 \text{ days}$.
5. **Pacing Status:**
   - **`ahead`**: Projected completion is at least 15 days ahead of user's target deadline.
   - **`on_track`**: Projected completion is within $\pm 15$ days of target deadline.
   - **`behind`**: Projected completion is $> 15$ days after target deadline.
   - **`at_risk`**: Savings pace is zero or negative (withdrawals exceeding contributions).
   - **`achieved`**: Current accumulated balance $\ge$ Target amount.
