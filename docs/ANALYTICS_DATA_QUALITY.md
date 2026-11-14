# Arthsavora Financial Analytics Data Quality & Integrity

## 1. Principle of Financial Transparency

In commercial and institutional finance, an analytics summary is only as credible as its underlying data hygiene. A common failing of consumer personal finance apps is presenting a clean chart while silently hiding missing data, uncategorized transactions, or unverified holds.

Arthsavora provides transparent **Data Quality Indicators** alongside every financial overview response.

---

## 2. Tracked Data Quality Dimensions

```json
"data_quality": {
  "uncategorized_count": 1,
  "uncategorized_amount_paise": 300000,
  "uncategorized_amount": "3000.00",
  "excluded_transfers_count": 2,
  "excluded_transfers_amount_paise": 3000000,
  "excluded_transfers_amount": "30000.00",
  "excluded_pending_count": 1,
  "excluded_pending_amount_paise": 250000,
  "excluded_pending_amount": "2500.00"
}
```

### 2.1 Uncategorized Outflow Indicator
- **Why It Matters:** High uncategorized spending undermines budgeting, category budgets, and tax estimations.
- **System Behavior:** Quantifies the exact count and sum of transactions lacking a category assignment.
- **UI Presentation:** Displays an amber warning pill badge on the dashboard (`"3 Uncategorized (₹4,500)"`) with a direct drill-down link to the transaction categorization interface.

### 2.2 Excluded Transfers (Non-Revenue Volume)
- **Why It Matters:** Internal transfers (moving funds between savings and investment accounts, or settling credit card bills) generate high raw transaction volume without representing true economic income or living expenses.
- **System Behavior:** Surfaces the total volume of excluded transfers to assure users that their capital movements were recognized and intentionally omitted from operational turnover.

### 2.3 Excluded Pending Transactions (Holds & In-Flight Payments)
- **Why It Matters:** A credit card authorization hold (e.g. hotel deposit or petrol pump pre-auth) may adjust or be reversed before final settlement. Counting pending holds in verified accounting totals leads to volatile balances.
- **System Behavior:** Pending transactions are strictly excluded from posted totals and reported in data quality (`"2 Pending Excluded (₹1,200)"`). Once settled by the provider or bank feed, they automatically transition to `posted` and flow into authoritative totals.

---

## 3. CSV Formula Injection Defense

Exporting financial data to spreadsheets is a standard operational requirement. However, opening CSV files in Microsoft Excel or LibreOffice exposes users to **CSV Formula Injection (Command Injection via DDE/Macros)** if a malicious actor names a merchant or description starting with arithmetic or command characters (`=`, `+`, `-`, `@`, `\t`, `\r`).

### Defense Implementation
Arthsavora applies defensive neutralization via `sanitize_csv_cell`:
```python
def sanitize_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    str_val = str(value)
    if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{str_val}"
    return str_val
```
Prepending an apostrophe `'` forces spreadsheet engines to interpret the payload strictly as literal text, completely disarming macro and formula execution.
