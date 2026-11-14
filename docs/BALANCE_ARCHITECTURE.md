# Arthsavora — Multi-Balance Architecture & Financial Precision Reference

## 1. Executive Summary

A critical failure mode in fintech applications is conflating distinct balance concepts into a single ambiguous `balance` column. In commercial financial management, treating a credit card statement balance, available credit, outstanding debt, and posted transaction sum as the same number corrupts calculations and leads to double-counting.

Arthsavora implements an **unambiguous multi-balance architecture** with strict monetary quantization:
1. **Integer Minor Unit Storage (Paise):** Zero floating-point representation in the database. All amounts are stored as 64-bit `BigInteger` paise (e.g. ₹1,500.50 is stored as `150050`).
2. **Explicit Balance Taxonomy:** Clear separation between Book Balance, Available Balance, Provider-Reported Balance, Outstanding Liability, and Pending Amounts.
3. **Immutable Point-in-Time Snapshots:** Full audit trail preserving statement reconciliations and feed updates.

---

## 2. Multi-Balance Taxonomy

```
+-------------------------------------------------------------------------------------------------+
|                                     FINANCIAL ACCOUNT                                           |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|  [Asset Accounts: Savings, Bank, Cash, Wallets]                                                 |
|  * current_book_balance_paise   --> Derived from posted transactions & journals                 |
|  * available_balance_paise      --> Usable funds (book balance minus holds/minimum reserve)     |
|  * provider_reported_balance    --> Feed balance from Account Aggregator / Bank API             |
|  * opening_balance_paise        --> Baseline opening amount upon registration                   |
|                                                                                                 |
|  [Liability Accounts: Credit Cards, Loans]                                                      |
|  * outstanding_liability_paise  --> Total debt owed to institution                              |
|  * credit_limit_paise           --> Sanctioned credit card limit                                |
|  * available_credit_paise       --> max(0, credit_limit - outstanding_liability)                |
|  * statement_balance_paise      --> Amount due on last generated billing statement              |
|  * minimum_due_paise            --> Minimum mandatory payment to avoid delinquency              |
|  * original_principal_paise     --> Sanctioned disbursed loan principal                         |
|  * outstanding_principal_paise  --> Remaining principal balance                                 |
|  * repayment_amount_paise       --> Monthly Equated Monthly Installment (EMI)                   |
|                                                                                                 |
|  [Unsettled Activity]                                                                           |
|  * pending_amount_paise         --> In-flight/draft transactions not yet posted                 |
+-------------------------------------------------------------------------------------------------+
```

### Balance Concepts Defined

| Balance Field | Minor Unit Column | Definition |
| :--- | :--- | :--- |
| **Book Balance** | `current_book_balance_paise` | Authoritative calculation derived from opening balance + posted income - posted expenses + inward transfers - outward transfers. |
| **Available Balance** | `available_balance_paise` | Readily spendable funds. For bank accounts, defaults to book balance unless holds or minimum balance limits apply. |
| **Provider-Reported Balance** | `provider_reported_balance_paise` | Real-time or batch balance reported by an external provider (Account Aggregator, Open Banking, Plaid, Setu). Stamped with `provider_reported_at`. |
| **Outstanding Liability** | `outstanding_liability_paise` | Money owed by the workspace to a financial institution (credit card debt, loan principal). |
| **Pending Amount** | `pending_amount_paise` | Aggregate sum of transactions currently in `draft` or `pending` status. |
| **Opening Balance** | `opening_balance_paise` | Initial balance baseline at the time the account was registered. Stored as an opening snapshot. |

---

## 3. Credit Card & Loan Calculations

### 3.1 Credit Card Math

- **Available Credit:**
  $$\text{available\_credit\_paise} = \max(0, \text{credit\_limit\_paise} - \text{outstanding\_liability\_paise})$$
- **Transaction Impact:**
  - A purchase transaction on a credit card *increases* `outstanding_liability_paise` and *decreases* `available_credit_paise`.
  - A credit card payment transaction is recorded as an *internal transfer* from an asset account (e.g. Bank Account) to the credit card liability account. It decreases bank assets and decreases card liabilities. It is **never** double-counted as an expense.

### 3.2 Loan & EMI Math

- **Original Principal (`original_principal`):** Sanctioned disbursed loan amount.
- **Outstanding Principal (`outstanding_principal`):** Remaining amortized balance owed, mapped to `outstanding_liability_paise`.
- **Repayment Amount (`repayment_amount`):** Monthly Equated Monthly Installment (EMI).
- **Interest Rate (`interest_rate`):** Annual percentage rate stored with 2 decimal precision (e.g. `8.50%`).

---

## 4. Immutable Point-in-Time Balance Snapshots

Historical balance states are captured in the `account_balance_snapshots` table:

```sql
CREATE TABLE account_balance_snapshots (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    balance_type VARCHAR(50) NOT NULL, -- book, available, provider_reported, liability, opening
    balance_amount NUMERIC(18, 4) NOT NULL,
    balance_paise BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL,
    effective_at TIMESTAMPTZ NOT NULL,
    source VARCHAR(50) NOT NULL, -- manual, account_aggregator, bank_feed, statement_import
    source_reference VARCHAR(255),
    reconciliation_status VARCHAR(30) NOT NULL DEFAULT 'unreconciled',
    created_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_snapshots_account_effective ON account_balance_snapshots(account_id, effective_at DESC);
CREATE INDEX ix_snapshots_account_type ON account_balance_snapshots(account_id, balance_type, effective_at DESC);
```

### Snapshot Workflow

1. **Account Creation:**
   - When an account is created with an opening balance, an initial snapshot with `balance_type = "opening"` is automatically inserted.
2. **Provider Sync / Statement Reconciliation:**
   - External provider syncs create snapshots with `balance_type = "provider_reported"`, updating the fast-read pointer on the `Account` entity (`provider_reported_balance_paise` and `provider_reported_at`).
   - Manual statement uploads insert snapshots with `source = "statement_import"`.
3. **Reconciliation Verification:**
   - Discrepancies between `book_balance` and `provider_reported_balance` can be audited by comparing the transaction log with historical snapshots.
