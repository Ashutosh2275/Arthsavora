# ARTHSAVORA — DOMAIN MODEL CONVENTIONS

## 1. Absolute Prohibition of Floating-Point Arithmetic

In Arthsavora, financial calculations must never utilize native IEEE 754 floating-point types (`float` in Python, standard `number` in JavaScript/TypeScript for mathematical operations).

### Justification:
Floating-point binary representations cannot accurately represent base-10 fractions. For example:
```python
0.1 + 0.2 != 0.3  # Evaluates to 0.30000000000000004
```
In commercial financial software handling millions of rupees across hundreds of accounts and tax calculations, floating-point drift creates cumulative accounting discrepancies, breaking the double-entry equation ($\sum \text{Debits} = \sum \text{Credits}$).

---

## 2. The `Money` Value Object Standard

All financial calculations, validation, and storage representations must use the `Money` value object (`backend/app/domain/money.py`).

### 2.1 Technical Characteristics
- **Immutability:** Implemented as a `@dataclass(frozen=True)`. Instances cannot be mutated post-creation.
- **Precision:**
  - **Internal Storage & Ledger:** Quantized to 4 decimal places (`Decimal("0.0001")`) to accommodate multi-step fractional tax, interest, or FX conversions without precision loss.
  - **Display & Minor Units:** Quantized to standard currency precision (2 decimal places for `INR`, `USD`, `EUR`, etc.; 0 for `JPY`; 3 for `KWD`, `BHD`).
- **Rounding Strategy:** Strict **Bankers Rounding** (`ROUND_HALF_EVEN`), rounding to the nearest even number on half-ties to eliminate upward statistical bias.

### 2.2 Currency Precisions & Minor Units (Paise)
| Currency | ISO Code | Minor Unit | Decimals | Factor | Minor Unit Name |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Indian Rupee | `INR` | 100 | 2 | 100 | Paise |
| US Dollar | `USD` | 100 | 2 | 100 | Cents |
| Euro | `EUR` | 100 | 2 | 100 | Cents |
| British Pound | `GBP` | 100 | 2 | 100 | Pence |
| Japanese Yen | `JPY` | 1 | 0 | 1 | Yen |
| UAE Dirham | `AED` | 100 | 2 | 100 | Fils |
| Kuwaiti Dinar | `KWD` | 1000 | 3 | 1000 | Fils |

### 2.3 Strict Currency Mismatch Enforcement
Operations across different currencies without an explicit FX exchange rate raise `CurrencyMismatchError`:
```python
inr = Money("500.00", "INR")
usd = Money("10.00", "USD")
total = inr + usd  # Raises CurrencyMismatchError!
```

---

## 3. Serialization and API Transport

1. **Database:** Persisted as PostgreSQL `NUMERIC(18, 4)` for exact relational arithmetic and index efficiency.
2. **REST APIs (JSON):**
   - Transmitted as high-precision decimal strings (e.g. `"1500.50"`) or standard Decimal representation in Pydantic v2.
   - Prohibits string truncation or float conversion in transit.
3. **Frontend Contracts:** Stored as `string` or `number` (with minor-unit integer alternatives where exactness is required).

---

## 4. Entity vs. Value Object Guidelines

- **Entity:** Has unique UUID identity that persists over time regardless of attribute changes (e.g., `Account`, `Transaction`, `User`).
- **Value Object:** Has no unique identity; defined purely by its structural attributes (e.g., `Money`, `Address`, `TaxRate`). Two `Money` objects with identical amount and currency are completely interchangeable.
- **Aggregate Root:** The primary entity controlling access and maintaining invariants across an internal cluster of entities (e.g., `Workspace` controls `Account` and `Transaction` boundaries).
