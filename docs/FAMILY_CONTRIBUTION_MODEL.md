# ARTHSAVORA — FAMILY CONTRIBUTION MODEL & SETTLEMENT NETTING

## 1. Executive Summary

Household financial cooperation typically combines two operational models:
1. **Ad-hoc Expense Splitting:** Members pay for specific goods/services out-of-pocket and seek reimbursement.
2. **Shared Household Funds (Pool Contributions):** Members deposit money on a monthly or periodic cadence into a common household fund to cover recurring utilities, groceries, and domestic staff.

The **ARTHSAVORA Family Contribution Model** unifies these two approaches into a unified, mathematically closed **Net Settlement System**.

---

## 2. Contribution Types & Lifecycles

```
+-----------------------------------------------------------------------------------------+
|                               CONTRIBUTION TYPES                                        |
|                                                                                         |
|   1. MONTHLY_FIXED               2. PERCENTAGE_INCOME         3. ONE_TIME               |
|      * Set amount per month         * Proportional to salary     * Special events,      |
|      * Predictable cadence          * Equity-oriented            * renovations, repairs |
|                                                                                         |
|   4. VOLUNTARY                   5. CUSTOM                                              |
|      * Discretionary top-ups        * Milestone or target-based                         |
|      * No penalty for skipping      * Ad-hoc household needs                            |
+-----------------------------------------------------------------------------------------+
```

### 2.1 Status Lifecycle
Each scheduled or recorded contribution transitions through defined states:
- `PENDING`: Expected contribution recorded for the active period.
- `PAID`: Member has transferred funds into the family pool or designated shared account.
- `OVERDUE`: Expected period deadline elapsed without confirmed payment.
- `WAIVED`: Household admin or consensus agreed to waive the contribution for this period.

---

## 3. The Net Settlement Formulation

For any given household member $i$ within period $T$:
Let:
- $E_{\text{paid}, i}$ = Total expenses paid upfront by member $i$ for household activities.
- $C_{\text{paid}, i}$ = Total pool contributions paid by member $i$.
- $S_{\text{allocated}, i}$ = Total expense shares allocated to member $i$ across all shared expenses.

### 3.1 Net Position Equation
$$\text{Net Position}_i = (E_{\text{paid}, i} + C_{\text{paid}, i}) - S_{\text{allocated}, i}$$

### 3.2 Position Semantics
- **Creditor ($\text{Net Position}_i > 0$):** The member has contributed more in expenses paid or pool deposits than their consumption share. The household or peers owe them this amount.
- **Debtor ($\text{Net Position}_i < 0$):** The member has consumed more in allocated expenses than they have paid. The member owes this amount.
- **Balanced ($\text{Net Position}_i = 0$):** The member's payments and obligations are in exact equilibrium.

### 3.3 Conservation Theorem
In any closed household system where all expense remainder paise have been conserved:
$$\sum_{i=1}^N \text{Net Position}_i \equiv \sum_{i=1}^N C_{\text{paid}, i}$$
If all expenses are funded solely through ad-hoc member payments (no pool contributions, $\sum C = 0$), then:
$$\sum_{i=1}^N \text{Net Position}_i \equiv 0$$
Debts and credits sum to exactly zero.

---

## 4. Peer Settlement Netting Algorithm

When household members wish to settle outstanding debts directly, calculating bilateral transfers for every single shared bill creates unnecessary transaction fatigue ($O(N^2)$ transfers). ARTHSAVORA executes a **Greedy Minimal Netting Algorithm** that reduces the total number of peer transfers to at most $N - 1$:

```
ALGORITHM: ComputeSettlementRecommendations
INPUT: List of MemberSettlementVO with net_position_paise
OUTPUT: List of SettlementRecommendationVO (from_user, to_user, amount_paise)

1. Separate members into two priority lists:
   - Debtors:  { (user_id, debt = -net_position) | net_position < 0 } sorted descending by debt
   - Creditors:{ (user_id, credit = net_position) | net_position > 0 } sorted descending by credit

2. While Debtors and Creditors are non-empty:
   a. d = Debtors.pop_first()
   b. c = Creditors.pop_first()
   c. transfer_amount = MIN(d.debt, c.credit)
   d. EMIT recommendation: (from_user = d.user_id, to_user = c.user_id, amount = transfer_amount)
   e. d.debt -= transfer_amount
   f. c.credit -= transfer_amount
   g. IF d.debt > 0: Debtors.push_first(d)
   h. IF c.credit > 0: Creditors.push_first(c)

3. RETURN recommendations
```

### 4.1 Worked Example
Three roommates (Alice, Bob, Charlie):
- Alice paid ₹9,000 for rent & groceries. Allocated share: ₹3,000. $\text{Net} = +6,000$.
- Bob paid ₹0. Allocated share: ₹4,000. $\text{Net} = -4,000$.
- Charlie paid ₹0. Allocated share: ₹2,000. $\text{Net} = -2,000$.

**Settlement Netting Output:**
1. Bob pays Alice: ₹4,000. (Bob balanced, Alice remaining credit: ₹2,000).
2. Charlie pays Alice: ₹2,000. (Charlie balanced, Alice balanced).
Total peer transfers required: **2** (instead of separate transfers for rent, groceries, wifi, electricity).

---

## 5. Settlement Execution Safeguards

1. **Informational Guidance Only:** ARTHSAVORA never initiates automated bank withdrawals or direct debits.
2. **Explicit Member Confirmation:** A settlement recommendation can be marked as `SETTLED` in the UI by either the payer, the recipient, or a family admin upon confirming that UPI/bank transfer took place.
3. **Transaction Linking:** Users may optionally associate an existing bank transaction (e.g., a UPI transfer to the roommate) to serve as verified evidence of the settlement.
