# Arthsavora — Budget Calculation Rules & Pacing Formulation

## 1. Objective & Mathematical Foundation

This document specifies the exact deterministic formulas, aggregation logic, threshold state transitions, and linear projection models used across Arthsavora's budgeting engine.

All financial amounts are stored, computed, and compared using **integer minor units (`paise`)** to eliminate IEEE-754 binary floating-point representation drift. Major currency units (e.g. `INR`) are formatted using fixed-point `NUMERIC(18, 4)` and rounded to 2 decimal places strictly at presentation boundaries.

---

## 2. Actual Spending Aggregation Rules

Actual spending is derived from authoritative PostgreSQL `transactions` records meeting strict accounting criteria:

$$\text{Eligible Spend} = \sum (\text{Posted Outflow Expenses}) - \sum (\text{Posted Inflow Refunds})$$

### 2.1 Transaction Inclusion Invariants

| Condition | Status | Rationale |
|---|---|---|
| `status = 'posted'` | **INCLUDED** | Confirmed financial settlement. |
| `status = 'pending'` | **EXCLUDED** | Unsettled pre-authorizations are not confirmed outflows. |
| `transaction_type IN ('expense', 'fee', 'interest_charge')` | **INCLUDED** | True consumption of financial resources. |
| `transaction_type = 'refund'` | **NETTED** | Offsets prior expenditure in the matching category. |
| `transfer_id IS NOT NULL` | **EXCLUDED** | Internal account-to-account movements do not consume budget. |
| `transaction_type = 'transfer'` | **EXCLUDED** | Liquidity rebalancing is neutral to budget capacity. |
| `transaction_type = 'credit_card_payment'` | **EXCLUDED** | Paying credit card bill settles a liability, preventing double-counting with original card purchases. |
| `transaction_type = 'loan_principal_repayment'` | **EXCLUDED** | Debt principal balance reduction is balance sheet accounting, not operating expenditure. |

---

## 3. Budget Utilization & Remaining Capacity

Given:
- $A$: Total allocated budget cap in paise ($A \ge 0$).
- $S$: Actual eligible spend in paise ($S \ge 0$).
- $T$: Warning threshold percentage (default $80\%$).

### 3.1 Remaining Spending Capacity ($R$)
$$R = A - S$$
- If $R \ge 0$, $R$ represents remaining spending headroom.
- If $R < 0$, the budget is in an **overspent** condition by $|R|$ paise.

### 3.2 Utilization Percentage ($U$)
$$U = \begin{cases} \text{round}\left(\frac{S}{A} \times 100, 2\right) & \text{if } A > 0 \\ 100.00 & \text{if } A = 0 \text{ and } S > 0 \\ 0.00 & \text{if } A = 0 \text{ and } S = 0 \end{cases}$$

### 3.3 Warning State Transitions

The system maps utilization to five discrete, color-coded health states:

| Utilization Range | Warning State | UI Badge | Severity |
|---|---|---|---|
| $U < 75\%$ | `normal` | Green (`income`) | Healthy spending trajectory. |
| $75\% \le U < T$ (e.g. $80\%$) | `caution` | Yellow (`warning`) | Approaching warning ceiling. |
| $T \le U < 90\%$ | `warning` | Amber (`warning`) | Configured alert tier crossed. |
| $90\% \le U < 100\%$ | `critical` | Orange (`expense`) | Imminent budget exhaustion. |
| $U \ge 100\%$ | `exceeded` | Red (`expense`) | Budget cap fully consumed / breached. |

---

## 4. Deterministic Period-End Linear Run-Rate Projection

To give users early visibility into period-end outcomes without black-box ML, Arthsavora implements a **transparent linear burn rate projection** with disclosed assumptions.

### 4.1 Temporal Progress Metrics
Let $D_{\text{total}}$ be total calendar days in the budget period, and $D_{\text{elapsed}}$ be elapsed days as of the evaluation date:
$$D_{\text{total}} = (\text{end\_date} - \text{start\_date}) + 1$$
$$D_{\text{elapsed}} = \max(1, \min(D_{\text{total}}, (\text{as\_of\_date} - \text{start\_date}) + 1))$$
$$D_{\text{remaining}} = \max(0, D_{\text{total}} - D_{\text{elapsed}})$$

### 4.2 Daily Run Rate ($B_{\text{daily}}$)
$$B_{\text{daily}} = \left\lfloor \frac{S}{D_{\text{elapsed}}} \right\rfloor \quad (\text{paise per day})$$

### 4.3 Projected Period-End Spending ($S_{\text{projected}}$)
$$S_{\text{projected}} = B_{\text{daily}} \times D_{\text{total}}$$

### 4.4 Projected Variance ($\Delta_{\text{projected}}$)
$$\Delta_{\text{projected}} = S_{\text{projected}} - A$$
- If $\Delta_{\text{projected}} > 0$: Projected to **exceed** budget by $\Delta_{\text{projected}}$ paise.
- If $\Delta_{\text{projected}} \le 0$: Projected to **remain within** budget with $|\Delta_{\text{projected}}|$ paise surplus.

### 4.5 Mandatory Model Disclosure
Every projection carries an explicit methodology disclaimer:
> *"Deterministic baseline projection assuming uniform daily run rate ($B_{\text{daily}}$) continues through period end. Excludes non-recurring lump-sum payments or future seasonal anomalies."*

---

## 5. Unallocated Spending Capacity Buffer

When category allocations are configured:
$$C_{\text{allocated}} = \sum_{i=1}^{k} A_i$$
$$C_{\text{unallocated}} = \max(0, A - C_{\text{allocated}})$$

- $C_{\text{unallocated}}$ represents the discretionary or contingency buffer not reserved for explicit categories.
- If $C_{\text{allocated}} > A$, the system flags an over-allocation warning in budget revisions.

---

## 6. File References

- Pure Domain Calculations: [budget.py](file:///d:/Arthsavora/backend/app/domain/budget.py)
- Aggregation SQL: [budget_repository.py](file:///d:/Arthsavora/backend/app/repositories/budget_repository.py)
- Test Verification: [test_personal_budgeting_and_goals.py](file:///d:/Arthsavora/backend/tests/test_personal_budgeting_and_goals.py)
