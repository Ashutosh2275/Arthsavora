# ARTHSAVORA — IMPORT VALIDATION & NORMALIZATION RULES

## 1. Scope & Principles

The `StatementNormalizer` and `StatementValidator` components transform raw, unvalidated text strings extracted by parsers into mathematically exact, semantically validated financial candidate objects.

Financial data rules enforced:
1. Every candidate must possess an explicit ISO 8601 date (`YYYY-MM-DD`).
2. Every candidate must possess a non-zero, positive monetary amount (`amount > 0` and `amount_paise > 0`).
3. Direction must be unambiguously resolved to `inflow` or `outflow`.
4. Summary rows, subtotals, and non-financial remarks must be rejected.

---

## 2. Normalization Engine (`StatementNormalizer`)

### 2.1 Date Parsing
Dates across Indian bank statements appear in numerous formats. `StatementNormalizer.parse_date` tests against standard patterns in order:
- `%d/%m/%Y` (e.g. `14/11/2026`)
- `%d-%m-%Y` (e.g. `14-11-2026`)
- `%Y-%m-%d` (e.g. `2026-11-14`)
- `%d-%b-%Y` (e.g. `14-Nov-2026`)
- `%d-%B-%Y` (e.g. `14-November-2026`)
- `%d/%m/%y` (e.g. `14/11/26`)
- `%d %b %Y` (e.g. `14 Nov 2026`)

Unparseable dates return `None`, causing the candidate to be flagged `INVALID`.

### 2.2 Currency Cleaning & Integer Minor Units (Paise)
Currency parsing follows deterministic rules:
1. Strip currency markers: `INR`, `Rs.`, `Rs`, `₹`, `$`.
2. Strip parentheses and trailing signs indicating outflows:
   - `(1,250.00)` -> `1250.00`, `is_negative = True`
   - `1,250.00-` -> `1250.00`, `is_negative = True`
   - `1,250.00 Dr` -> `1250.00`, `is_negative = True`
   - `1,250.00 Cr` -> `1250.00`, `is_negative = False`
3. Remove Indian thousand/lakh commas: `1,25,000.50` -> `125000.50`.
4. Quantize to 4 decimal places (`Decimal("125000.5000")`) and multiply by 100 to yield exact integer paise (`12500050`).

### 2.3 Direction & Type Inference Heuristics

| Parser Columns Found | Computed Direction | Transaction Type |
| :--- | :--- | :--- |
| `Debit Amt > 0` | `outflow` | `expense` |
| `Credit Amt > 0` | `inflow` | `income` |
| `Amount` with `(val)` or `-val` | `outflow` | `expense` |
| `Amount` with positive `val` | `inflow` | `income` |
| Description contains `SALARY` or `PAYROLL` | `inflow` | `income` |
| Description contains `DIVIDEND` | `inflow` | `dividend` |
| Description contains `INTEREST` | `inflow` | `interest` |
| Description contains `ATM` or `CASH WDL` | `outflow` | `withdrawal` |
| Description contains `REFUND` or `CASHBACK` | `inflow` | `refund` |
| Description contains `TRANSFER` or `NEFT` or `RTGS` | `inflow`/`outflow` | `transfer` |

---

## 3. Validation Engine (`StatementValidator`)

Every normalized candidate is evaluated against `validate_candidate()`:

```python
class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    AMBIGUOUS = "ambiguous"
```

### 3.1 Validation Rules & Error Messages

| Condition | Verdict | Error Code / Message |
| :--- | :--- | :--- |
| Missing or unparseable date | `INVALID` | `Missing or invalid transaction date` |
| Future date > 1 day ahead | `INVALID` | `Transaction date cannot be in the future` |
| Amount is `None` or $\le 0$ | `INVALID` | `Amount must be a positive non-zero number` |
| Invalid direction string | `INVALID` | `Invalid transaction direction: must be 'inflow' or 'outflow'` |
| Conflicting debit and credit | `AMBIGUOUS` | `Both debit and credit values present on same row` |
| Empty description | Warning | `Description is empty (auto-populated to 'Imported Transaction')` |

### 3.2 UI Treatment of Validation Status
- **`VALID`**: Highlighted with green badge. Pre-selected for batch confirmation (`selected_for_import = True`).
- **`AMBIGUOUS`**: Highlighted with amber badge. Allowed for import if user explicitly reviews and edits direction.
- **`INVALID`**: Highlighted with red badge. De-selected by default (`selected_for_import = False`). The confirm action blocks posting invalid candidates until corrected via the Edit Modal.
