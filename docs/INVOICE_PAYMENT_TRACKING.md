# Invoice Payment Tracking & Accounts Receivable Lifecycle

## 1. Accounts Receivable Tracking

Accounts Receivable (AR) represents money legally owed to the business by clients for goods delivered or services rendered on credit terms.

### Accrual Recognition:
Upon invoice issuance:
```
Debit:  1040 Accounts Receivable   (Asset increases)
Credit: 4020 Sales & Revenue       (Revenue recognized)
```

---

## 2. Payment Recording (`BusinessInvoicePayment`)

When a client settles an invoice partially or fully, a payment record is created.

### Over-Allocation Guard:
```python
remaining_balance = invoice.total_amount_paise - invoice.paid_amount_paise
if amount_paise <= 0:
    raise ValidationException("Payment amount must be strictly greater than zero.")
if amount_paise > remaining_balance:
    raise ValidationException(
        f"Payment amount (₹{amount_paise / 100:,.2f}) exceeds remaining balance of ₹{remaining_balance / 100:,.2f}."
    )
```

### Cash Realization Ledger Posting:
Upon recording the payment:
```
Debit:  1020 Operating Bank Accounts (Cash asset increases)
Credit: 1040 Accounts Receivable     (AR asset decreases)
```

### Supported Payment Channels:
- `bank_transfer`: NEFT, RTGS, IMPS.
- `upi`: Unified Payments Interface / QR code.
- `cheque`: Paper bank cheques with clearance reference.
- `card`: Credit or debit card merchant processors.
- `cash`: Physical cash receipts.

### Status Transitions:
- If `new_paid == total_amount_paise`: Status becomes `paid`.
- If `new_paid < total_amount_paise`: Status becomes `partially_paid`.
