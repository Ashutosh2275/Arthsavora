# Arthsavora — Transaction Type Reference & Taxonomy

## 1. Overview & Taxonomy Structure

Arthsavora establishes a comprehensive, domain-driven taxonomy of transaction types to support personal money management, family shared finances, and small-business operations. Every transaction belongs to an authoritative `TransactionType` enum and resolves deterministically to a canonical `TransactionDirection` (`inflow`, `outflow`, or `neutral`).

This taxonomy eliminates ambiguous financial movements, standardizes balance recalculation, and provides consistent classification for future double-entry general ledger mappings.

---

## 2. Comprehensive Transaction Type Catalog

### 2.1 General & Core Types

| Transaction Type | Canonical Direction | Category / Group | Description & Ledger Effect |
| :--- | :--- | :--- | :--- |
| `income` | `inflow` | General | Salary, consulting earnings, freelance payments, or general monetary inflows. Increases asset balance. |
| `expense` | `outflow` | General | General expenditures for goods, services, or personal living expenses. Decreases asset balance. |
| `transfer_in` | `inflow` | Transfers | Inbound leg of an internal account transfer. Increases receiving account balance. |
| `transfer_out` | `outflow` | Transfers | Outbound leg of an internal account transfer. Decreases source account balance. |
| `refund` | `inflow` | Adjustments | Reimbursement or reversal of a previous expense. Increases asset balance and links to original transaction via `related_transaction_id`. |
| `adjustment` | `neutral` | Adjustments | Ledger reconciliation adjustment, balance correction, or memo entry. |
| `opening_balance`| `inflow` | System | Initial balance recorded when creating or bootstrapping a new financial account. |
| `fee` | `outflow` | Administrative | Service charges, transaction fees, processing fees, or platform fees. |
| `tax` | `outflow` | Statutory | GST, TDS, advance income tax, professional tax, or local cess deductions. |

---

### 2.2 Banking & Cash Management

| Transaction Type | Canonical Direction | Category / Group | Description & Ledger Effect |
| :--- | :--- | :--- | :--- |
| `deposit` | `inflow` | Banking | Cash or cheque deposit credited into a savings or current bank account. |
| `withdrawal` | `outflow` | Banking | Cash withdrawal from an ATM or bank branch counter. |
| `interest_credit`| `inflow` | Banking | Quarterly or annual savings account interest credited by the banking institution. |
| `dividend` | `inflow` | Banking / Invest | Dividend distribution received from equities, mutual funds, or business holdings. |
| `bank_charge` | `outflow` | Banking | Annual maintenance charges (AMC), SMS alert fees, or non-maintenance penalty charges. |
| `emi` | `outflow` | Banking / Loans | Equated Monthly Installment payment towards personal loans, mortgages, or vehicle loans. |
| `cashback` | `inflow` | Banking / Promo | Reward points redeemed as cash credit, promotional cashback, or UPI incentives. |

---

### 2.3 Credit Card & Revolving Credit

| Transaction Type | Canonical Direction | Category / Group | Description & Ledger Effect |
| :--- | :--- | :--- | :--- |
| `payment` | `inflow` | Credit Card | Bill payment made towards a credit card liability. Decreases outstanding liability and restores available credit limit. |
| `purchase` | `outflow` | Credit Card | Point-of-sale or online merchant purchase utilizing credit line. Increases outstanding liability. |
| `late_fee` | `outflow` | Credit Card | Penalty charged for failure to make minimum amount due by payment due date. |
| `annual_fee` | `outflow` | Credit Card | Annual renewal fee or card membership charge billed to the credit card statement. |
| `credit_adjustment`| `inflow` | Credit Card | Merchant dispute credit, chargeback settlement, or goodwill fee waiver. |

---

### 2.4 Loans, Mortgages & Borrowing

| Transaction Type | Canonical Direction | Category / Group | Description & Ledger Effect |
| :--- | :--- | :--- | :--- |
| `loan_disbursement`| `inflow` | Borrowing | Sanctioned loan capital disbursed into the borrower's savings/current account. |
| `principal_repayment`| `outflow` | Borrowing | Direct capital repayment reducing the principal outstanding loan liability. |
| `interest_payment` | `outflow` | Borrowing | Financing cost and interest charges paid to the lending institution. |
| `processing_fee` | `outflow` | Borrowing | Upfront origination, documentation, or legal appraisal charges deducted during loan sanction. |

---

### 2.5 Investments & Wealth Management

| Transaction Type | Canonical Direction | Category / Group | Description & Ledger Effect |
| :--- | :--- | :--- | :--- |
| `buy` | `outflow` | Investments | Capital deployment to acquire equities, mutual fund units, gold bonds, or fixed deposits. |
| `sell` | `inflow` | Investments | Liquidation or redemption of investment assets back into liquid funds. |
| `capital_gain` | `inflow` | Investments | Realized profit or capital appreciation resulting from an asset sale or liquidation. |
| `dividend_reinvestment`| `neutral` | Investments | Automatic reinvestment of dividend proceeds to purchase additional units without cash movement. |

---

### 2.6 Business Operations & Commercial Finance

| Transaction Type | Canonical Direction | Category / Group | Description & Ledger Effect |
| :--- | :--- | :--- | :--- |
| `payroll` | `outflow` | Business Ops | Employee salary distribution, contractual stipends, or partner remuneration. |
| `vendor_payout` | `outflow` | Business Ops | Invoiced payments made to suppliers, SaaS vendors, or contractors. |
| `subscription` | `outflow` | Business Ops | Recurring SaaS software subscriptions, utility fees, or platform licensing costs. |
| `insurance_premium`| `outflow` | Risk Management | Term life, health insurance, business liability, or asset protection premiums. |
| `bill_payment` | `outflow` | Utilities | Utility expenses including electricity, water, internet broadband, and office lease rent. |

---

## 3. Direction Resolution Algorithm

The mapping from `TransactionType` to `TransactionDirection` is strictly deterministic. The engine executes the following resolution logic in `backend/app/domain/transaction_types.py`:

```python
INFLOW_TYPES = {
    TransactionType.INCOME,
    TransactionType.TRANSFER_IN,
    TransactionType.REFUND,
    TransactionType.OPENING_BALANCE,
    TransactionType.DEPOSIT,
    TransactionType.INTEREST_CREDIT,
    TransactionType.DIVIDEND,
    TransactionType.CASHBACK,
    TransactionType.PAYMENT,            # Inflow to credit liability (debt reduction)
    TransactionType.CREDIT_ADJUSTMENT,
    TransactionType.LOAN_DISBURSEMENT,
    TransactionType.SELL,
    TransactionType.CAPITAL_GAIN,
}

NEUTRAL_TYPES = {
    TransactionType.ADJUSTMENT,
    TransactionType.DIVIDEND_REINVESTMENT,
}

def resolve_direction(transaction_type: TransactionType) -> TransactionDirection:
    if transaction_type in INFLOW_TYPES:
        return TransactionDirection.INFLOW
    elif transaction_type in NEUTRAL_TYPES:
        return TransactionDirection.NEUTRAL
    else:
        return TransactionDirection.OUTFLOW
```

When custom manual entries are received without an explicit direction, the service invokes `resolve_direction()` to ensure consistent balance mutation rules.
