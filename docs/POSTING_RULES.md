# ARTHSAVORA — General Ledger Posting Rules & Transaction Mapping Standard

## 1. Scope & Objective

This document defines the deterministic rules for converting operational financial transactions into double-entry General Ledger journal entries. 

In Arthsavora, user-facing transactions capture business context (e.g. paying for groceries via UPI, receiving salary via NEFT, paying credit card bills). The `LedgerService.post_transaction_to_ledger` engine translates each transaction type into equal debits and credits adhering to standard Indian accounting practice.

---

## 2. Standard Mapping Matrix

| Operational Transaction Type | Direction | Ledger Debit Account | Ledger Credit Account | Accounting Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Income / Salary** | `inflow` | `1020` Bank Accounts | `4010` Salary & Wages (or `4020` Sales) | Asset increases (Debit); Revenue increases (Credit). |
| **Expense / Purchase (Bank/UPI)** | `outflow` | `5000`–`5999` Expense Account | `1020` Bank Accounts (or `1010` / `1030`) | Expense increases (Debit); Asset decreases (Credit). |
| **Expense / Purchase (Credit Card)** | `outflow` | `5000`–`5999` Expense Account | `2010` Credit Card Balances | Expense increases (Debit); Liability increases (Credit). |
| **Credit Card Bill Payment** | `inflow` | `2010` Credit Card Balances | `1020` Bank Accounts | Liability decreases (Debit); Asset decreases (Credit). **Zero double-counting of expenses.** |
| **Account Transfer (Inter-bank / Self)**| `transfer` | `1020` Destination Bank Account | `1020` Source Bank Account | Asset increases at destination (Debit); Asset decreases at source (Credit). |
| **Loan Disbursal (Received)** | `inflow` | `1020` Bank Accounts | `2230` Personal Loans (Liability) | Asset increases (Debit); Loan liability increases (Credit). |
| **Loan EMI Repayment** | `outflow` | `2230` Loan Principal / `5080` Interest | `1020` Bank Accounts | Liability & expense decrease/increase (Debit); Bank decreases (Credit). |
| **Refund Received** | `inflow` | `1020` Bank Accounts | `5000`–`5999` Original Expense Account | Asset increases (Debit); Expense decreases/offset (Credit). |
| **Opening Balance** | `inflow` | `1000`–`1999` Asset Account | `3999` Opening Balance Equity | Asset established (Debit); Equity established (Credit). |

---

## 3. Detailed Case Studies & Accounting Mechanics

### 3.1 Credit Card Spending vs. Bill Payment (Preventing Double Counting)
A classic flaw in naive personal finance software is counting both the credit card swipe as an expense AND the monthly credit card bill payment as an expense. Arthsavora resolves this with true double-entry bookkeeping:

1. **Step 1: User purchases laptop for ₹85,000 using Credit Card:**
   - **Debit:** `5040 Office Equipment / General Expense` (₹85,000)
   - **Credit:** `2010 Credit Card Balances (Liability)` (₹85,000)
   - *Result:* Expenses increase by ₹85,000; Liabilities increase by ₹85,000. Bank balance untouched.

2. **Step 2: User pays ₹85,000 Credit Card Bill from HDFC Bank:**
   - **Debit:** `2010 Credit Card Balances (Liability)` (₹85,000)
   - **Credit:** `1020 Bank Accounts (Asset)` (₹85,000)
   - *Result:* Liability is wiped clean to ₹0; Bank asset decreases by ₹85,000. **Expense is ₹0**, completely preventing double counting.

### 3.2 Inter-Account Transfers
Moving ₹20,000 from Savings Account to Digital Wallet (e.g. Paytm / PhonePe):
- **Debit:** `1030 UPI & Digital Wallets` (₹20,000)
- **Credit:** `1020 Bank Accounts` (₹20,000)
- *Result:* Net assets remain unchanged; only asset composition shifts.

### 3.3 Opening Balance Recognition
When connecting an existing bank account with an existing balance of ₹2,50,000:
- **Debit:** `1020 Bank Accounts` (₹2,50,000)
- **Credit:** `3999 Opening Balance Equity` (₹2,50,000)
- *Result:* Accurate initial equity recognition without fabricating fictitious revenue.

---

## 4. Operational Invariants

1. **Exact Precision Matching:** Both debit and credit lines are created with identical `amount` and `amount_paise`.
2. **Deterministic Category Resolution:** If an operational transaction specifies a known category (e.g., "Housing & Rent"), the mapping selects code `5010`. If unspecified, it safely defaults to `5999 General & Miscellaneous Expenses`.
3. **Traceability:** The posted `JournalEntry` stores `source_type = "transaction"` and `source_id = transaction.id`, establishing bidirectional provenance between the transaction register and the general ledger.
