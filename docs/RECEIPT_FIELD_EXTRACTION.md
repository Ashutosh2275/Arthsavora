# Receipt Field Extraction & Entity Normalization

## 1. Extraction Pipeline Overview

The `ReceiptFieldExtractor` transforms raw OCR text strings into strongly typed, normalized domain structures (`StructuredReceiptDataVO`). It handles noisy OCR outputs, character substitutions (e.g. `O` vs `0`, `l` vs `1`), and multiple formatting variations.

```
Raw Text Stream
      │
      ├──> [GSTIN Extractor] ─────────> 15-char regex + structure validation
      ├──> [Merchant Extractor] ──────> Non-generic header detection
      ├──> [Date Extractor] ──────────> Indian DD/MM/YYYY & ISO formats
      ├──> [Invoice No Extractor] ────> Bill/Tax Invoice alphanumeric patterns
      ├──> [Amount Extractor] ────────> Total, Subtotal, Discount, Tax breakdowns
      ├──> [Payment Details] ─────────> UPI UTR, Card ending digits, Cash
      └──> [Line Items Extractor] ────> Tabular description, quantity, price, amount
```

---

## 2. Field Extraction Specifications

### 2.1 Merchant Recognition
- **Strategy**: Discards generic receipt headings (`TAX INVOICE`, `CASH MEMO`, `RETAIL INVOICE`, `BILL OF SUPPLY`) and inspects the first prominent lines of the document.
- **Pattern Matchers**: Evaluates explicit prefixes (`Merchant:`, `Seller:`, `Vendor:`, `Store:`) or detects high-density alphabetic lines in the top 6 lines.

### 2.2 Date Extraction & Parsing
- Supports Indian domestic conventions:
  - `DD/MM/YYYY`, `DD-MM-YYYY`, `DD.MM.YYYY`
  - `DD Mon YYYY` (e.g., `12 Oct 2026`)
  - `YYYY-MM-DD` (ISO 8601)
  - `DD/MM/YY`, `DD-MM-YY`
- Output normalized to standard `date` object and ISO string representation.

### 2.3 Monetary Amounts & Indian Number System
- **Symbols**: Strips `₹`, `Rs.`, `Rs`, `INR`, `/-`.
- **Comma Structure**: Recognizes Indian lakh/crore commas (e.g. `1,50,000.50`) and standard thousands formatting (`150,000.50`).
- **Precision**: Parses into `Decimal(18, 4)` and integer `paise`. Floating-point arithmetic is strictly banned to prevent rounding distortion.

### 2.4 Tax Components
- Extracted individually:
  - **CGST**: Central Goods and Services Tax
  - **SGST**: State Goods and Services Tax
  - **IGST**: Integrated Goods and Services Tax
- Regex ignores tax rate percentages in parentheses (e.g. `CGST (2.5%): 13.75` extracts `13.75`, not `2.5`).

### 2.5 Line Items
- Parses itemized purchase rows matching:
  `[Description] [Quantity] [Unit Price] [Line Total]`
- Captures description text, quantity, unit price in paise, and line total in paise.
