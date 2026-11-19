# Accounts Receivable & Accounts Payable Aging Schedules

## 1. Aging Buckets Standard

Both Accounts Receivable (AR) and Accounts Payable (AP) are classified into standard commercial aging intervals based on days past due (`as_of_date - due_date`):

| Aging Bucket | Days Overdue Range | Meaning |
| :--- | :--- | :--- |
| **Current** | `<= 0 days` | Within credit terms; not yet due |
| **1–30 Days** | `1 to 30 days` | Recently overdue; primary follow-up |
| **31–60 Days** | `31 to 60 days` | Moderately overdue; formal reminder |
| **61–90 Days** | `61 to 90 days` | Severely overdue; credit freeze review |
| **91+ Days** | `>= 91 days` | Critical default risk; doubtful debt |

---

## 2. Mathematical Categorization (`app/domain/business.py`)

Aging computation is executed deterministically without rounding errors:

```python
def compute_ar_aging(invoices: List[Dict[str, Any]], as_of_date: Optional[date] = None) -> ReceivablesAgingVO:
    as_of = as_of_date or date.today()
    current, d1_30, d31_60, d61_90, d91_plus, total = 0, 0, 0, 0, 0, 0

    for inv in invoices:
        if inv.get("status") in ("paid", "cancelled", "draft"):
            continue
        balance = max(0, int(inv.get("total_amount_paise", 0)) - int(inv.get("paid_amount_paise", 0)))
        if balance == 0:
            continue
        days = (as_of - inv["due_date"]).days
        if days <= 0:
            current += balance
        elif 1 <= days <= 30:
            d1_30 += balance
        elif 31 <= days <= 60:
            d31_60 += balance
        elif 61 <= days <= 90:
            d61_90 += balance
        else:
            d91_plus += balance
        total += balance

    return ReceivablesAgingVO(current, d1_30, d31_60, d61_90, d91_plus, total)
```

---

## 3. Accounts Payable (AP) Workflow

Vendor bills (`BusinessPayable`) record accrual expenses and outstanding liabilities owed to vendors:

1. **Bill Logging**:
   ```
   Debit:  5000 Operating Expenses (Expense recognized)
   Credit: 2020 Accounts Payable    (Liability recognized)
   ```
2. **Bill Payment**:
   ```
   Debit:  2020 Accounts Payable    (Liability cleared)
   Credit: 1020 Bank Accounts       (Cash asset decreased)
   ```
