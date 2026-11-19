# Business Financial Analytics, Reporting & CSV Security

## 1. Analytics & Operational KPIs

The business service computes operational metrics in real-time across invoices, receivables, payables, and client concentration:

- **Total Invoiced Revenue**: Gross billing across all issued commercial invoices.
- **Total Realized Cash**: Cash collected and deposited in operating accounts.
- **Outstanding Accounts Receivable (AR)**: Pending client balances.
- **Total Vendor Bills**: Accrual expenses logged from suppliers and contractors.
- **Outstanding Accounts Payable (AP)**: Unsettled vendor liabilities.
- **Net Operating Result**: Invoiced revenue minus vendor bills.
- **Top Clients by Billed Revenue**: Identifies client revenue concentration to mitigate dependency risk.
- **Top Vendors by Bill Volume**: Highlights primary suppliers and operational cost drivers.

---

## 2. CSV Export Security & Formula Injection Sanitization

Exporting commercial invoice registers to CSV presents a critical security vulnerability: **CSV / Formula Injection (CWE-1236)**.

If a client name, notes field, or description starts with an execution character (`=`, `+`, `-`, `@`, `\t`, `\r`), spreadsheet engines (Excel, Google Sheets, LibreOffice) can execute arbitrary macro commands or exfiltrate data.

### Mitigation Implementation (`app/domain/business.py`):
```python
def sanitize_csv_cell(value: Any) -> str:
    val_str = str(value)
    if any(val_str.startswith(trigger) for trigger in ("=", "+", "-", "@", "\t", "\r")):
        return f"'{val_str}"
    return val_str
```
Every text field exported through `export_invoices_csv()` passes through `sanitize_csv_cell()`, neutralizing formula injection while preserving readability.
