# Arthsavora Net Worth & Balance Sheet Position Calculation

## 1. Overview

Net Worth represents the ultimate financial position of a workspace: the difference between everything owned (assets) and everything owed (liabilities).

$$\text{Net Worth} = \text{Total Assets} - \text{Total Liabilities}$$

In Arthsavora, Net Worth is computed in real-time from active financial accounts within the workspace context.

---

## 2. Account Classification Matrix

Financial accounts in `accounts` table are partitioned into assets and liabilities based on their canonical `account_type`:

| Account Type | Classification | Balance Field Used | Sign |
| :--- | :--- | :--- | :--- |
| `savings` | Asset | `current_book_balance_paise` | Positive (+) |
| `current` | Asset | `current_book_balance_paise` | Positive (+) |
| `salary` | Asset | `current_book_balance_paise` | Positive (+) |
| `cash` / `petty_cash` | Asset | `current_book_balance_paise` | Positive (+) |
| `investment` | Asset | `current_book_balance_paise` | Positive (+) |
| `digital_wallet` | Asset | `current_book_balance_paise` | Positive (+) |
| `credit_card` | Liability | `outstanding_liability_paise` (fallback: $\vert \text{book\_balance} \vert$) | Negative (-) |
| `loan` / `loan_account` | Liability | `outstanding_liability_paise` (fallback: $\vert \text{book\_balance} \vert$) | Negative (-) |
| `business_credit_card` | Liability | `outstanding_liability_paise` (fallback: $\vert \text{book\_balance} \vert$) | Negative (-) |

---

## 3. Credit Card Liability Derivation

Credit cards represent revolving credit facilities. An account's debt position is evaluated as:
1. If `outstanding_liability_paise` is recorded, it is used directly.
2. Otherwise, `abs(current_book_balance_paise)` is evaluated (credit card book balances are traditionally negative).
3. `available_credit` is derived as:
   $$\text{Available Credit} = \max(0, \text{credit\_limit\_paise} - \text{outstanding\_liability\_paise})$$

---

## 4. Multi-Currency Accounting Isolation

If a workspace holds accounts in multiple currencies (e.g., an INR savings account and a USD brokerage account), the Net Worth endpoint enforces strict currency isolation:
- By default, queries filter for `currency = 'INR'`.
- The caller can specify `?currency=USD` to evaluate foreign currency assets and liabilities independently.
- Mixed-currency summation is strictly prevented to avoid exchange-rate distortions without explicit FX conversion records.
