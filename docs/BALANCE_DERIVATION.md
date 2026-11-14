# ARTHSAVORA — Account Balance Derivation & Trial Balance Calculation Standard

## 1. Overview & Mathematical Definition

In double-entry accounting, account balances and financial reports are not static counter variables stored in the database; they are dynamically derived aggregations over the set of all posted journal lines.

This document describes the exact formulas, normal balance conventions, and Trial Balance validation algorithms used by the Arthsavora General Ledger.

---

## 2. Normal Balances and Account Classification

Every ledger account has an inherent **Normal Balance** direction determined by its fundamental classification:

| Account Type | Normal Balance | Balance Formula |
| :--- | :--- | :--- |
| **Asset** | **Debit** | $\text{Balance} = \sum \text{Debits} - \sum \text{Credits}$ |
| **Liability** | **Credit** | $\text{Balance} = \sum \text{Credits} - \sum \text{Debits}$ |
| **Equity** | **Credit** | $\text{Balance} = \sum \text{Credits} - \sum \text{Debits}$ |
| **Revenue** | **Credit** | $\text{Balance} = \sum \text{Credits} - \sum \text{Debits}$ |
| **Expense** | **Debit** | $\text{Balance} = \sum \text{Debits} - \sum \text{Credits}$ |

---

## 3. Account Balance Derivation Algorithm

To compute the derived balance of an account $A$ up to an optional date $T$:

```sql
SELECT 
    COALESCE(SUM(CASE WHEN jl.entry_type = 'debit' THEN jl.amount ELSE 0 END), 0) AS total_debits,
    COALESCE(SUM(CASE WHEN jl.entry_type = 'credit' THEN jl.amount ELSE 0 END), 0) AS total_credits,
    COALESCE(SUM(CASE WHEN jl.entry_type = 'debit' THEN jl.amount_paise ELSE 0 END), 0) AS total_debits_paise,
    COALESCE(SUM(CASE WHEN jl.entry_type = 'credit' THEN jl.amount_paise ELSE 0 END), 0) AS total_credits_paise
FROM journal_lines jl
JOIN journal_entries je ON jl.journal_entry_id = je.id
WHERE jl.ledger_account_id = :account_id
  AND je.workspace_id = :workspace_id
  AND je.status = 'posted'
  AND (:as_of_date IS NULL OR je.entry_date <= :as_of_date);
```

### 3.1 Normal Balance Sign Evaluation
Once `total_debits` and `total_credits` are aggregated:
- If `normal_balance == "debit"`:
  - $\text{net\_balance} = \text{total\_debits} - \text{total\_credits}$
  - $\text{net\_balance\_paise} = \text{total\_debits\_paise} - \text{total\_credits\_paise}$
- If `normal_balance == "credit"`:
  - $\text{net\_balance} = \text{total\_credits} - \text{total\_debits}$
  - $\text{net\_balance\_paise} = \text{total\_credits\_paise} - \text{total\_debits\_paise}$

---

## 4. Trial Balance Derivation

The Trial Balance is a diagnostic report listing every active ledger account and its net balance placed into either the Debit column or the Credit column:

1. For each active account $A$:
   - Compute $\text{net\_diff} = \text{total\_debits}(A) - \text{total\_credits}(A)$.
   - If $\text{net\_diff} > 0$:
     - $\text{debit\_balance} = \text{net\_diff}$
     - $\text{credit\_balance} = 0$
   - Else if $\text{net\_diff} < 0$:
     - $\text{debit\_balance} = 0$
     - $\text{credit\_balance} = |\text{net\_diff}|$
   - Else:
     - Account is zero; omit from active display if desired.
2. Sum all columns:
   - $\text{Total Debits} = \sum \text{debit\_balance}_i$
   - $\text{Total Credits} = \sum \text{credit\_balance}_j$
3. Invariant Verification:
   $$\text{Difference} = |\text{Total Debits} - \text{Total Credits}|$$
   $$\text{is\_balanced} = (\text{Difference} == 0)$$
