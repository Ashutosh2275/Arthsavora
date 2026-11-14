# Arthsavora Financial Metric Dictionary

## 1. Scope & Standards

This document establishes the canonical definitions, mathematical formulas, minor-unit (paise) conventions, and edge-case behavior for all analytical metrics computed by Arthsavora.

All monetary amounts are represented as exact integers in minor units (`paise`) in persistent storage and computation, formatted to major decimal units (`INR`) with two decimal digits in UI and API presentations.

---

## 2. Core Operational Metrics

### 2.1 Total Operating Income
- **Definition:** Authoritative cash and revenue received from employment, investments, dividends, or customer receipts during the evaluation period.
- **SQL Invariant:**
  $$\text{Income} = \sum \text{amount\_paise} \quad \text{where } \text{status} = \text{'posted'} \land \text{direction} = \text{'inflow'} \land \text{transfer\_id IS NULL} \land \text{type} \in \{\text{'income'}, \text{'deposit'}, \text{'dividend'}, \text{'interest\_income'}\}$$
- **Exclusions:** Excludes loan disbursals, internal transfers, and merchant refunds.

### 2.2 Gross Expenses
- **Definition:** Aggregate posted monetary outflows from expense classifications before factoring in return refunds or cashbacks.
- **SQL Invariant:**
  $$\text{Gross Expenses} = \sum \text{amount\_paise} \quad \text{where } \text{status} = \text{'posted'} \land \text{direction} = \text{'outflow'} \land \text{transfer\_id IS NULL} \land \text{type} \notin \{\text{'transfer'}, \text{'credit\_card\_payment'}, \text{'loan\_principal\_repayment'}, \text{'investment\_contribution'}\}$$

### 2.3 Refunds & Cashbacks (Contra-Expenses)
- **Definition:** Reversals, returns, or merchant promotional rebates that credit an account following a previous expense.
- **SQL Invariant:**
  $$\text{Refunds} = \sum \text{amount\_paise} \quad \text{where } \text{status} = \text{'posted'} \land \text{type} \in \{\text{'refund'}, \text{'credit\_card\_refund'}\}$$

### 2.4 Net Operating Expenses
- **Definition:** The actual economic cost of living or operations during the period, defined as gross expenses less contra-expense refunds:
  $$\text{Net Operating Expenses} = \max(0, \text{Gross Expenses} - \text{Refunds})$$

### 2.5 Net Cash Flow
- **Definition:** The net operational liquidity generated or consumed over the period:
  $$\text{Net Cash Flow} = \text{Total Income} - \text{Net Operating Expenses}$$
- **Interpretation:** Positive net cash flow indicates capital accumulation; negative indicates burn.

### 2.6 Savings Rate Percentage
- **Definition:** The percentage of operating income retained rather than expended:
  $$\text{Savings Rate} = \begin{cases} \left( \frac{\text{Total Income} - \text{Net Operating Expenses}}{\text{Total Income}} \right) \times 100 & \text{if } \text{Total Income} > 0 \\ 0.0 & \text{if } \text{Total Income} \le 0 \end{cases}$$
- **Bounds:** Lower bound capped at $-1000.0\%$ to avoid visual distortion in periods with extreme negative cash flow.

### 2.7 Average Daily Spend (Burn Rate)
- **Definition:** The pace of daily operational expenditure:
  $$\text{Average Daily Spend} = \left\lfloor \frac{\text{Net Operating Expenses}}{\max(1, \text{Days in Period})} \right\rfloor$$

---

## 3. Balance Sheet & Net Worth Metrics

### 3.1 Total Assets
- **Definition:** The aggregate fair value or book balance of all active asset accounts owned by the workspace:
  $$\text{Total Assets} = \sum \text{current\_book\_balance\_paise} \quad \text{where } \text{account\_type} \in \{\text{'savings'}, \text{'current'}, \text{'cash'}, \text{'salary'}, \text{'investment'}, \text{'digital\_wallet'}, \text{'petty\_cash'}\} \land \text{status} = \text{'active'}$$

### 3.2 Total Liabilities
- **Definition:** The aggregate outstanding obligations owed across credit cards and loans:
  $$\text{Total Liabilities} = \sum \text{outstanding\_liability\_paise} \quad \text{where } \text{account\_type} \in \{\text{'credit\_card'}, \text{'loan'}, \text{'business\_credit\_card'}, \text{'loan\_account'}\} \land \text{status} = \text{'active'}$$

### 3.3 Net Worth
- **Definition:** The overall equity position of the workspace:
  $$\text{Net Worth} = \text{Total Assets} - \text{Total Liabilities}$$

---

## 4. Comparative Delta Metrics & Sentiment Analysis

### 4.1 Percentage Delta
- **Formula:**
  $$\text{Percentage Delta} = \begin{cases} \left( \frac{\text{Current} - \text{Previous}}{|\text{Previous}|} \right) \times 100 & \text{if } \text{Previous} \ne 0 \\ \text{null} & \text{if } \text{Previous} = 0 \land \text{Current} \ne 0 \\ 0.0 & \text{if } \text{Previous} = 0 \land \text{Current} = 0 \end{cases}$$

### 4.2 Financial Sentiment Direction
- **Income, Savings, Net Cash Flow, Assets, Net Worth:**
  - $\Delta > 0$: `favorable` (green indicator).
  - $\Delta < 0$: `unfavorable` (rose indicator).
  - $\Delta = 0$: `neutral`.
- **Expenses, Liabilities:**
  - $\Delta < 0$: `favorable` (spending or debt reduced).
  - $\Delta > 0$: `unfavorable` (spending or debt expanded).
  - $\Delta = 0$: `neutral`.
