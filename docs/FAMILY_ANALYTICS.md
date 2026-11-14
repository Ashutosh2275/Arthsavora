# ARTHSAVORA — FAMILY FINANCE ANALYTICS & INSIGHTS

## 1. Executive Summary

The **ARTHSAVORA Family Analytics Engine** provides high-level transparency into collective domestic consumption, member contribution patterns, category-wise cost distribution, and historical household cash flow. 

It answers core domestic questions:
- What is our total household run rate this month?
- Where is the majority of household money going (groceries vs. utilities vs. housing)?
- Who has paid the most upfront for family needs?
- Are member contributions keeping pace with household expenditure commitments?
- What is our projected net settlement across all members?

---

## 2. The Zero-Leakage Privacy Invariant in Analytics

```
+-----------------------------------------------------------------------------------------+
|                               ANALYTICS PRIVACY FIREWALL                                |
|                                                                                         |
|   +--------------------------+                         +----------------------------+   |
|   |  Member Personal Space   |                         |  Family Household Space    |   |
|   |  - Personal Discretionary|                         |  - Shared Grocery Bills    |   |
|   |  - Medical / Health      | -- [ PRIVACY FIREWALL ] -->  - Society Maintenance   |   |
|   |  - Private Gifts / Subsc |   (Blocked from Query)  |  - Domestic Utilities      |   |
|   +--------------------------+                         +----------------------------+   |
|                                                                       |                 |
|                                                                       v                 |
|                                                        +----------------------------+   |
|                                                        | Household Spend Aggregates |   |
|                                                        | Total: ₹62,500             |   |
|                                                        +----------------------------+   |
+-----------------------------------------------------------------------------------------+
```

### Absolute Data Isolation
When querying `GET /family/overview` or running analytics aggregations:
- The SQL queries are scoped strictly by `workspace_id == family_ws.id` or through active records in `family_account_shares`.
- Unshared personal transactions and personal account balances are mathematically excluded from `SUM`, `AVG`, and grouping aggregates.
- There is **zero technical possibility** for an individual member's personal spending (e.g. personal shopping, pharmacy, discretionary tech) to appear in the family spend breakdown unless explicitly recorded as a shared household expense.

---

## 3. Core Analytical Dimensions

### 3.1 Household Category Breakdown
Aggregates household expenditures across standardized domestic categories:
$$\text{Spend}(C) = \sum_{t \in \text{FamilyTransactions}(C)} \text{amount\_paise}(t)$$
Visualized as an interactive donut/pie chart displaying top expense categories (Groceries, Housing/Rent, Utilities, Food & Dining, Children/Education, Healthcare).

### 3.2 Member Payment vs. Consumption Analysis
Compares the capital provided by each member against their allocated consumption share:
- **Upfront Payer Proportion:**
  $$\% \text{ Paid Upfront}_i = \frac{E_{\text{paid}, i} + C_{\text{paid}, i}}{\sum (E_{\text{paid}} + C_{\text{paid}})} \times 100$$
- **Consumption Proportion:**
  $$\% \text{ Consumed}_i = \frac{S_{\text{allocated}, i}}{\sum S_{\text{allocated}}} \times 100$$

### 3.3 Historical Monthly Spend Trends
Tracks the household burn rate over trailing 6-month and 12-month periods, comparing actual monthly expenditures against the aggregated family budget ceiling.

---

## 4. Key Performance Indicators (KPIs)

The Family Overview dashboard displays four institutional-grade KPIs:

1. **Total Shared Expenses (Current Period):** Total monetary volume of all active allocated household expenses in the active month.
2. **Total Pool Contributions:** Cumulative funds deposited into the household operational pool for the active month.
3. **Active Members & Shared Accounts:** Count of active collaborating household members and bridged/native accounts.
4. **Outstanding Settlement Debt:** The total absolute netting balance awaiting peer settlement.
