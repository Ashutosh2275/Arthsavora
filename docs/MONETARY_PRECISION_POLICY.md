# Monetary Precision and Currency Representation Policy

## 1. Purpose and Scope

This document defines the mandatory engineering policy for representing, calculating, storing, and transmitting monetary values throughout the **ARTHSAVORA** platform.

This policy applies across all backend micro-modules, database schemas, API schemas, shared contracts, and frontend user interfaces.

---

## 2. Core Directives

### Directive 1: Absolute Prohibition of Floating-Point Types
Under no circumstances may IEEE 754 floating-point primitives (`float` in Python, `number` in TypeScript when representing currency without minor units, or `REAL`/`FLOAT`/`DOUBLE PRECISION` in PostgreSQL) be used for storing or calculating monetary amounts.

### Directive 2: Database Storage Standard
1. **Transactional Entities (Operational Layer):**
   - Columns: `accounts.balance`, `transactions.amount`, `business_invoices.total_amount`, `budget_allocations.allocated_amount`.
   - Data Type: PostgreSQL `BIGINT` (`BigInteger` in SQLAlchemy).
   - Unit: Minor units (integer `paise` for INR, cents for USD/EUR).
2. **General Ledger Entries (Accounting Layer):**
   - Columns: `journal_lines.amount`, `tax_classification_records.tax_amount`.
   - Data Type: PostgreSQL `NUMERIC(18, 4)`.
   - Unit: Major units with 4 fractional decimal places.
3. **Rates and Ratios:**
   - Columns: Interest rates, GST percentage, tax slab rates.
   - Data Type: PostgreSQL `NUMERIC(5, 2)` or `NUMERIC(6, 4)`.

### Directive 3: Python Domain Object Standard
- All monetary manipulation in Python business logic must utilize `app.domain.money.Money`.
- `Money` encapsulates a Python `decimal.Decimal` with internal quantization `Decimal("0.0001")`.
- Bankers Rounding (`decimal.ROUND_HALF_EVEN`) is enforced on all operations to eliminate systematic upward or downward rounding bias.
- Float inputs to `Money.from_amount()` must be converted via `str()` before passing to `Decimal`.

### Directive 4: API Contract Standard
- In external JSON API envelopes:
  - Transactional endpoints transmit monetary amounts as integer minor units (`amount_paise: int`).
  - Ledger and reporting endpoints transmit formatted decimal strings (e.g., `"100.5000"`) or explicitly paired structures:
    ```json
    {
      "amount_paise": 10050,
      "amount_display": "100.50",
      "currency": "INR"
    }
    ```
- This prevents JavaScript browser engines from corrupting large integer values or floating-point decimals during JSON parsing.

### Directive 5: Frontend TypeScript Standard
- In `apps/web`:
  - Values from API endpoints are stored in Zustand stores as integer paise (`number` within safe integer range $\pm 9,007,199,254,740,991$).
  - Formatting for UI display is handled exclusively by utility functions in `@arthsavora/utilities`:
    ```typescript
    formatCurrency(amountPaise: number, currency = "INR"): string
    ```
  - Input parsing converts user-entered currency strings (`"100.50"`) directly to integer paise (`10050`) before submission to API endpoints.

---

## 3. Supported Currencies and Minor Units

| ISO Code | Currency Name | Minor Unit Name | Decimal Precision | Factor to Minor Unit |
|---|---|---|---|---|
| **INR** | Indian Rupee | Paisa | 2 | 100 |
| **USD** | US Dollar | Cent | 2 | 100 |
| **EUR** | Euro | Cent | 2 | 100 |
| **GBP** | British Pound | Penny | 2 | 100 |
| **SGD** | Singapore Dollar | Cent | 2 | 100 |
| **AED** | UAE Dirham | Fils | 2 | 100 |
| **JPY** | Japanese Yen | Yen (Zero-decimal) | 0 | 1 |
| **KWD** | Kuwaiti Dinar | Fils | 3 | 1000 |
| **BHD** | Bahraini Dinar | Fils | 3 | 1000 |

---

## 4. Enforcement & Automated Checks

Compliance with this policy is enforced continuously by:
1. **Linter & Ast Scanners:** Prohibiting `float()` type casting in financial calculation modules.
2. **Database Migrations:** Pre-commit hooks blocking PRs that introduce `FLOAT` columns on financial tables.
3. **Unit Tests:** `backend/tests/test_financial_integrity.py` asserting exact minor-unit conversions and rejection of floating-point drift.
