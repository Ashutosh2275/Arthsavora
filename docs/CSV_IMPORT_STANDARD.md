# ARTHSAVORA — CSV IMPORT STANDARD & BANK CONVENTIONS

## 1. Scope & Objective

CSV is the universal standard for exporting financial records from internet banking portals and core banking systems across India. The `CsvStatementParser` module normalizes heterogeneous CSV formats into structured `ImportCandidate` records while gracefully handling banking idiosyncrasies, varied delimiters, custom character encodings, and summary lines.

---

## 2. Dialect Sniffing & Character Encoding

### 2.1 Character Encoding Detection
Indian bank statements frequently use non-UTF-8 encodings when exported from legacy web portals. The ingestion pipeline applies fallback decoding in order of precedence:
1. `utf-8` (standard)
2. `utf-8-sig` (UTF-8 with Byte Order Mark emitted by Microsoft Excel)
3. `latin-1` / `ISO-8859-1`
4. `cp1252` (Windows standard)

### 2.2 Delimiter Sniffing
The parser evaluates the first 2,048 bytes of text using `csv.Sniffer().sniff()` with supported delimiter candidates:
- Comma (`,`)
- Semicolon (`;`)
- Tab (`\t`)
- Pipe (`|`)

If sniffing fails, the parser defaults to standard comma `,`.

---

## 3. Indian Bank Header Dictionaries

The parser maintains canonical header synonym dictionaries matching major Indian commercial and public sector banks:

```python
HEADER_SYNONYMS = {
    "date": [
        "date", "txn date", "transaction date", "value date", "post date",
        "booking date", "trans date", "tran date", "date of transaction"
    ],
    "description": [
        "narration", "description", "particulars", "remarks", "transaction details",
        "details", "trans details", "desc", "memo"
    ],
    "amount": [
        "amount", "net amount", "transaction amount", "txn amount", "amount (inr)"
    ],
    "debit": [
        "withdrawal", "withdrawal amt", "withdrawal amt.", "debit", "dr",
        "debit amount", "withdrawal amount", "debit amt", "debit (inr)"
    ],
    "credit": [
        "deposit", "deposit amt", "deposit amt.", "credit", "cr",
        "credit amount", "deposit amount", "credit amt", "credit (inr)"
    ],
    "balance": [
        "closing balance", "balance", "available balance", "bal", "running balance",
        "closing bal", "balance (inr)", "account balance"
    ],
    "ref_no": [
        "chq/ref no", "chq./ref.no.", "ref no", "reference no", "cheque no",
        "chq no", "ref no.", "utr", "transaction id", "txn id", "reference number"
    ],
}
```

### Pre-Configured Bank Profiles

| Bank | Header Pattern | Amount Representation |
| :--- | :--- | :--- |
| **HDFC Bank** | `Date,Narration,Chq./Ref.No.,Withdrawal Amt.,Deposit Amt.,Closing Balance` | Separate debit/credit columns, commas in numbers. |
| **State Bank of India (SBI)** | `Txn Date,Description,Ref No./Cheque No.,Debit,Credit,Balance` | Separate debit/credit, `DD-Mon-YYYY` dates. |
| **ICICI Bank** | `Transaction Date,Transaction Remarks,Cheque Number,Withdrawal Amount (INR),Deposit Amount (INR),Balance (INR)` | Separate columns with currency suffixes. |
| **Axis Bank** | `Tran Date,Particulars,CHQNO,DR,CR,BAL` | Abbreviated uppercase headers. |
| **Kotak Mahindra Bank** | `Date,Description,Reference Number,Amount,Dr/Cr,Balance` | Single amount column with Dr/Cr sign indicator. |

---

## 4. Custom Column Mapping & Override Support

When users import statements with bespoke, regional, or international column headers (e.g., German, French, or custom ERP exports), they can specify a JSON mapping object in the upload request:

```json
{
  "column_mapping": {
    "date": "Datum",
    "description": "Verwendungszweck",
    "amount": "Betrag",
    "ref_no": "Belegnummer"
  }
}
```

The parser applies the custom mapping with higher precedence than auto-detected synonym heuristics.

---

## 5. Non-Transaction Row Filtering

Bank CSVs regularly include metadata rows at the top (e.g., `HDFC BANK STATEMENT`, `Account No: 50100...`) and summary totals at the bottom (e.g., `TOTAL,,,15000.00,45000.00`).

The parser automatically suppresses non-transaction rows:
1. **Header Row Discovery**: Scans lines until finding a row containing at least two recognized header synonyms including `date`.
2. **Summary Row Suppression**: Skips any row containing `"TOTAL"`, `"OPENING BALANCE"`, or `"CLOSING BALANCE"` across any cell.
3. **Empty Cell Filtering**: Ignores empty lines or lines without dates and financial amounts.
