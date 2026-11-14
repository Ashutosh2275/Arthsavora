# Arthsavora — Financial Account Classification and Types Reference

## 1. Overview

Arthsavora enforces a structured taxonomy of financial accounts tailored to the Indian financial ecosystem and workspace tenancy models:
- **Personal Workspaces:** Individual bank accounts, salary credit accounts, credit cards, UPI wallets, and personal loans.
- **Family Workspaces:** Joint bank accounts, shared household wallets, emergency funds, and home loans.
- **Business Workspaces:** Corporate bank accounts, business current accounts, corporate credit cards, petty cash floats, and commercial credit lines.

---

## 2. Supported Account Types Taxonomy

### 2.1 Personal & Household Types

| Type Identifier | Label | Category | Typical Usage in India |
| :--- | :--- | :--- | :--- |
| `savings` | Savings Account | Liquid Asset | Primary savings account with bank (SBI, HDFC, ICICI). |
| `salary` | Salary Account | Liquid Asset | Dedicated payroll credit account with zero-balance facility. |
| `current` | Current Account | Liquid Asset | High-velocity individual transactional account. |
| `credit_card` | Credit Card | Revolving Liability | Credit cards (Visa, Mastercard, RuPay, Amex) with limits and billing cycles. |
| `digital_wallet` / `wallet` | Digital Wallet | Liquid Asset | Prepaid payment instruments (Paytm, PhonePe Wallet, Amazon Pay). |
| `cash` | Cash in Hand | Liquid Asset | Physical cash currency held by individual or household. |
| `fixed_deposit` | Fixed Deposit (FD) | Term Asset | Term deposit held with bank or NBFC earning fixed interest. |
| `recurring_deposit` | Recurring Deposit (RD) | Term Asset | Monthly systematic deposit scheme. |
| `loan` | Loan Account | Term Liability | Personal loans, auto loans, education loans, home loans (EMIs). |
| `investment` | Investment / Demat | Investment Asset | Demat accounts, mutual fund folios (Zerodha, Groww, CAMS/KFintech). |
| `other` | Other Account | Miscellaneous | Any specialized account not fitting standard classifications. |

### 2.2 Small Business Types

| Type Identifier | Label | Category | Typical Usage in India |
| :--- | :--- | :--- | :--- |
| `business_bank` | Business Bank Account | Liquid Asset | Primary operating bank account for company / LLP. |
| `business_current` | Business Current Account | Liquid Asset | Commercial current account with OD (overdraft) facilities. |
| `business_credit_card` | Corporate Credit Card | Revolving Liability | Business expense card issued to directors or employees. |
| `petty_cash` | Petty Cash Float | Liquid Asset | Cash held on premises for daily incidental operational expenses. |
| `loan_account` | Commercial Loan / OD | Term Liability | Term loans, working capital loans, or cash credit (CC) accounts. |
| `business_cash` | Business Cash | Liquid Asset | Cash registers and merchant cash collections. |
| `other_business` | Other Commercial | Miscellaneous | Special commercial accounts (escrow, tax reserve, statutory deposits). |

---

## 3. Workspace Tenancy Validation Rules

When an account is created, the system checks whether the requested `account_type` is valid for the workspace's tenancy model:

```python
ALLOWED_ACCOUNT_TYPES = {
    "personal": {
        "cash", "bank", "savings", "current", "salary",
        "fixed_deposit", "recurring_deposit", "credit_card",
        "loan", "investment", "digital_wallet", "wallet", "other",
    },
    "family": {
        "cash", "bank", "savings", "current", "salary",
        "fixed_deposit", "recurring_deposit", "credit_card",
        "loan", "investment", "digital_wallet", "wallet", "other",
    },
    "business": {
        "business_cash", "business_bank", "business_current",
        "business_credit_card", "petty_cash", "loan_account",
        "other_business", "cash", "bank", "current", "savings",
        "credit_card", "loan", "wallet", "digital_wallet",
        "investment", "other",
    },
}
```

Attempting to register a business-only type in a personal workspace (or vice versa) results in a `422 Unprocessable Entity` with error code `INVALID_ACCOUNT_TYPE`.
