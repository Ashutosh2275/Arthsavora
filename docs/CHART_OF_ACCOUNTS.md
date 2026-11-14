# ARTHSAVORA — Chart of Accounts (COA) Standard

## 1. Overview

The Chart of Accounts (COA) is the taxonomic foundation of Arthsavora's General Ledger. It classifies every rupee inflow, outflow, asset, and liability into standardized categories compliant with Indian accounting standards and standard personal/small-business practice.

Every workspace is seeded with a baseline 28-account Chart of Accounts upon initialization. Workspaces can add custom accounts under existing parents while system accounts (`is_system=True`) are protected from deletion or classification modification.

---

## 2. Classification Structure & Numbering Plan

Arthsavora adopts a standard 4-digit hierarchical numbering structure:

| Code Range | Classification | Normal Balance | Purpose / Description |
| :--- | :--- | :--- | :--- |
| **1000–1999** | **Assets** | **Debit** | What the workspace owns (cash, bank accounts, investments, receivables) |
| **2000–2999** | **Liabilities** | **Credit** | What the workspace owes (credit card balances, loans, payables) |
| **3000–3999** | **Equity** | **Credit** | Net worth / Owner's stake (capital, opening balance equity, retained earnings) |
| **4000–4999** | **Revenue** | **Credit** | Rupee inflows (salary, business revenue, interest, dividends) |
| **5000–5999** | **Expenses** | **Debit** | Rupee outflows (housing, utilities, food, interest paid, taxes) |

---

## 3. Standard Seeded Accounts (28 Baseline Accounts)

### 3.1 Assets (1000–1999)
- **1000 — Current Assets** (Parent Header)
  - `1010` — **Cash on Hand** (`cash`, Normal: Debit, System: Yes)
  - `1020` — **Bank Accounts** (`bank`, Normal: Debit, System: Yes)
  - `1030` — **UPI & Digital Wallets** (`wallet`, Normal: Debit, System: Yes)
  - `1040` — **Accounts Receivable** (`receivable`, Normal: Debit, System: Yes)
- **1200 — Non-Current Assets** (Parent Header)
  - `1210` — **Mutual Funds & Stocks** (`investment`, Normal: Debit, System: Yes)
  - `1220` — **Fixed Deposits** (`investment`, Normal: Debit, System: Yes)
  - `1230` — **Property & Real Estate** (`fixed_asset`, Normal: Debit, System: Yes)

### 3.2 Liabilities (2000–2999)
- **2000 — Current Liabilities** (Parent Header)
  - `2010` — **Credit Card Balances** (`credit_card`, Normal: Credit, System: Yes)
  - `2020` — **Accounts Payable** (`payable`, Normal: Credit, System: Yes)
  - `2030` — **Short-term Borrowings** (`liability`, Normal: Credit, System: Yes)
- **2200 — Long-Term Liabilities** (Parent Header)
  - `2210` — **Home Loans** (`loan`, Normal: Credit, System: Yes)
  - `2220` — **Vehicle Loans** (`loan`, Normal: Credit, System: Yes)
  - `2230` — **Personal Loans** (`loan`, Normal: Credit, System: Yes)

### 3.3 Equity (3000–3999)
- `3010` — **Owner's Equity / Initial Capital** (`equity`, Normal: Credit, System: Yes)
- `3020` — **Retained Earnings** (`equity`, Normal: Credit, System: Yes)
- `3999` — **Opening Balance Equity** (`equity`, Normal: Credit, System: Yes)

### 3.4 Revenue (4000–4999)
- `4010` — **Salary & Wages** (`operating_revenue`, Normal: Credit, System: Yes)
- `4020` — **Business Sales & Invoicing** (`operating_revenue`, Normal: Credit, System: Yes)
- `4030` — **Interest Income** (`interest_revenue`, Normal: Credit, System: Yes)
- `4040` — **Investment Dividends & Gains** (`investment_revenue`, Normal: Credit, System: Yes)
- `4090` — **Other Inflows & Reimbursements** (`other_revenue`, Normal: Credit, System: Yes)

### 3.5 Expenses (5000–5999)
- `5010` — **Housing & Rent** (`operating_expense`, Normal: Debit, System: Yes)
- `5020` — **Utilities & Telecom** (`operating_expense`, Normal: Debit, System: Yes)
- `5030` — **Groceries & Food** (`operating_expense`, Normal: Debit, System: Yes)
- `5040` — **Transportation & Fuel** (`operating_expense`, Normal: Debit, System: Yes)
- `5050` — **Healthcare & Medical** (`operating_expense`, Normal: Debit, System: Yes)
- `5060` — **Education & Learning** (`operating_expense`, Normal: Debit, System: Yes)
- `5070` — **Entertainment & Dining** (`operating_expense`, Normal: Debit, System: Yes)
- `5080` — **Bank Charges & Interest Paid** (`financial_expense`, Normal: Debit, System: Yes)
- `5090` — **Taxes Paid (Direct & Indirect)** (`tax_expense`, Normal: Debit, System: Yes)
- `5999` — **General & Miscellaneous Expenses** (`other_expense`, Normal: Debit, System: Yes)

---

## 4. Operational Financial Account Mapping

When financial accounts are created in Arthsavora (Prompt 08), they map automatically to corresponding Ledger Accounts in the General Ledger:

| Financial Account Type | Default Ledger Account Code | Ledger Account Name |
| :--- | :--- | :--- |
| `savings` | `1020` | Bank Accounts |
| `current` | `1020` | Bank Accounts |
| `credit_card` | `2010` | Credit Card Balances |
| `loan` | `2230` | Personal Loans |
| `investment` | `1210` | Mutual Funds & Stocks |
| `wallet` | `1030` | UPI & Digital Wallets |
| `cash` | `1010` | Cash on Hand |

---

## 5. System Protection Rules

1. **System Flag (`is_system = True`):** Prevents deletion or code renumbering of core accounts required by system automation rules.
2. **Account Renaming:** Allowed for personalization (e.g., updating `1020` display name to "HDFC & ICICI Banks").
3. **Custom Accounts:** Users can create subsidiary accounts (e.g., `5031 — Organic Groceries`, `1021 — SBI Salary Account`) under any existing header or parent account.
