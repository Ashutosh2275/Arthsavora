# Indian Receipt Format Support & Financial Entity Extraction

## 1. Executive Summary

Arthsavora is engineered with an **India-First** financial architecture. In the Indian retail and commercial ecosystem, financial receipts and tax invoices feature specialized statutory numbers, dual-tier taxation structures (Goods and Services Tax - GST), localized numerical grouping (lakhs and crores), and distinctive digital payment rails such as Unified Payments Interface (UPI).

This specification outlines the parsing rules, regular expressions, and architectural adaptations developed to handle Indian receipts, tax invoices, and supporting financial documentation in [document.py](file:///d:/Arthsavora/backend/app/domain/document.py) and [field_extractor.py](file:///d:/Arthsavora/backend/app/services/document/field_extractor.py).

---

## 2. Indian Statutory Identifiers (GSTIN)

### 2.1 15-Character GSTIN Structure
Every business registered under the Indian Goods and Services Tax system receives a 15-character alphanumeric Goods and Services Tax Identification Number (GSTIN).

```
 2 9   A A A C B   7 1 4 4   P   1   Z   9
|---| |---------| |-------| |-| |-| |-| |-|
  |        |          |      |   |   |   |
  |        |          |      |   |   |   +-- Check digit
  |        |          |      |   |   +------ Default 'Z'
  |        |          |      |   +---------- Entity code (1-9, A-Z)
  |        |          |      +-------------- 10th PAN char (check letter)
  |        |          +--------------------- 4 numeric digits of PAN
  |        +-------------------------------- First 5 alphabets of PAN
  +----------------------------------------- 2-digit State code (01-37, 97, 99)
```

### 2.2 Validation Algorithm & Regular Expression
The system evaluates candidate GSTIN tokens using regex patterns that enforce strict state code boundaries and PAN checksum characters:

```python
GSTIN_REGEX = r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b"
```

Common State Code Prefixes:
- `29`: Karnataka
- `27`: Maharashtra
- `07`: Delhi
- `33`: Tamil Nadu
- `36`: Telangana
- `19`: West Bengal
- `24`: Gujarat

When detected, the GSTIN automatically yields a high confidence signal for merchant verification and state of supply origin.

---

## 3. Dual Goods & Services Tax (GST) Architecture

India operates a federal dual-GST framework comprising Intra-State and Inter-State tax levies:

| Tax Component | Scope | Typical Rates | Validation Rule |
|---|---|---|---|
| **CGST** (Central GST) | Intra-State (within same state) | 2.5%, 6%, 9%, 14% | Equal to SGST (`CGST == SGST`) |
| **SGST / UTGST** (State / Union Territory GST) | Intra-State (within same state) | 2.5%, 6%, 9%, 14% | Equal to CGST (`SGST == CGST`) |
| **IGST** (Integrated GST) | Inter-State (between states) | 5%, 12%, 18%, 28% | Mutually exclusive with CGST+SGST |
| **GST Compensation Cess** | Specific luxury / demerit goods | Variable | Added to total tax liability |

### 3.1 Tax Extraction & Parentheses Disambiguation
Thermal receipts and restaurant point-of-sale bills frequently display tax percentages in parentheses alongside the tax amount:
```
CGST (2.5%): 13.75
SGST (2.5%): 13.75
```
Naive regex extractors often extract `2.5` or `2.0` as the tax amount instead of `13.75`. Arthsavora implements an explicit pattern lookahead that detects and skips bracketed percentages or `@ rate%` clauses:

```python
CGST_REGEX = (
    r"(?:CGST|Central\s+GST)\s*"
    r"(?:\s*(?:@|at)?\s*\([0-9\.]+\s*%\)|\s*(?:@|at)\s*[0-9\.]+\s*%)?"
    r"[\s\:\-=]*"
    r"(?:₹|Rs\.?|INR)?\s*([0-9]+(?:[\.,][0-9]{2}))"
)
```

---

## 4. Indian Currency & Numbering System

### 4.1 Rupee Symbols & Denominations
Receipts across India format currency amounts in various notations:
- Unicode Rupee symbol: `₹`
- Ascii variants: `Rs.`, `Rs`, `INR`, `Rupees`, `/-`
- Negative / Refund indicators: `(₹50.00)`, `-Rs 50.00`, `CR`

### 4.2 Lakh and Crore Comma Separators
Unlike international numbering (grouping by thousands: `1,000,000.00`), the Indian numbering system groups the first three digits, followed by pairs of two digits:
- 1 Lakh = `1,00,000.00`
- 10 Lakhs = `10,00,000.00`
- 1 Crore = `1,00,00,000.00`

The field normalizer safely handles both Indian and Western comma layouts, removing thousands/lakh separators before converting the fixed-point decimal into integer **paise**:
```python
def parse_monetary_amount(raw_str: str) -> Optional[int]:
    # Sanitizes '1,49,999.50' -> Decimal('149999.50') -> 14999950 paise
    ...
```

### 4.3 Absolute Integer Paise Rule
Floating-point calculations (`float`) are strictly forbidden across the financial calculation pipelines. All amounts are converted to 64-bit integer minor units (`paise` = `₹1.00 / 100`) and stored alongside high-precision `Decimal(18, 4)` for tax division.

---

## 5. Payment Rails & UTR Extraction

India has the highest volume of real-time digital payments globally. Point-of-sale receipts and delivery slips incorporate payment reference metadata:

### 5.1 UPI Unique Transaction Reference (UTR)
- UPI transactions generate a 12-digit numeric reference number known as the **UTR** (e.g., `Ref: 432156789012` or `UPI Ref No: 432156789012`).
- Receipts often record the Virtual Payment Address (VPA) or handle (e.g., `swiggy@icici`, `merchant@okhdfcbank`).
- The regex detects 12-digit continuous numeric sequences associated with UPI/UTR headers and tags the payment method as `PaymentMethod.UPI`.

### 5.2 Card & POS Slips
- Card transactions display masked PANs conforming to RBI tokenization and storage guidelines: `XXXX XXXX XXXX 4321` or `**** 4321`.
- Slip tags identify card schemes: `VISA`, `Mastercard`, `RuPay`, `Amex`.
- Tagged as `PaymentMethod.CARD`.

### 5.3 Cash & Thermal Invoices
- Invoices marked `CASH`, `PAID BY CASH`, or `ROUND OFF` with `CHANGE DUE` are classified as `PaymentMethod.CASH`.

---

## 6. Indian Date Parsing Conventions

In India, dates follow the British colonial convention of Little-Endian ordering: **Day / Month / Year**.

Supported patterns parsed in [document.py](file:///d:/Arthsavora/backend/app/domain/document.py):
- `DD/MM/YYYY` (e.g. `14/11/2026`)
- `DD-MM-YYYY` (e.g. `14-11-2026`)
- `DD.MM.YYYY` (e.g. `14.11.2026`)
- `DD MMM YYYY` (e.g. `14 Nov 2026`, `14-NOV-2026`)
- `YYYY-MM-DD` (ISO 8601 e-invoices)

Date strings with ambiguous interpretations (e.g. `04/05/2026`) prioritize `Day=04, Month=05` by default in Indian workspace contexts.

---

## 7. Line Items & HSN/SAC Codes

GST tax invoices in India mandate classification codes:
- **HSN (Harmonized System of Nomenclature)**: 4, 6, or 8 digits identifying manufactured products and commodities.
- **SAC (Services Accounting Code)**: 6 digits starting with `99` identifying services (e.g., `996331` for restaurant services).

The field extractor separates table line entries into:
1. `description`: Item or service name.
2. `quantity`: Unit count or weight.
3. `unit_price_paise`: Individual item cost.
4. `total_paise`: Computed line total.
5. `hsn_sac_code`: Extracted 4-8 digit classification code when present.

---

## 8. Related Architectural References

- [Receipt Intelligence Architecture](file:///d:/Arthsavora/docs/RECEIPT_INTELLIGENCE_ARCHITECTURE.md)
- [Receipt Field Extraction](file:///d:/Arthsavora/docs/RECEIPT_FIELD_EXTRACTION.md)
- [OCR Validation & Confidence](file:///d:/Arthsavora/docs/OCR_VALIDATION_AND_CONFIDENCE.md)
- [Transaction Architecture](file:///d:/Arthsavora/docs/TRANSACTION_ARCHITECTURE.md)
