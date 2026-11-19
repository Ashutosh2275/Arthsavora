# Indian Small Business Finance Statutory Requirements

## 1. Regulatory Context

Arthsavora's business finance module is tailored for the Indian regulatory and tax landscape while retaining international compatibility.

Target users include:
- Indian freelancers and tech consultants.
- Chartered accountants, architects, and legal practitioners.
- Digital marketing, design, and development agencies.
- Sole proprietors and LLPs.

---

## 2. Indian Statutory Identifiers

### Goods & Services Tax Identification Number (GSTIN):
- 15-character alphanumeric format:
  `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`
- Formatted as:
  - 2 digits: State code (e.g. `27` for Maharashtra, `29` for Karnataka, `07` for Delhi).
  - 10 characters: Entity PAN.
  - 1 character: Entity number of the same PAN within the state.
  - 1 character: Default 'Z'.
  - 1 character: Checksum.

### Permanent Account Number (PAN):
- 10-character alphanumeric format:
  `^[A-Z]{5}[0-9]{4}[A-Z]{1}$`
- Formatted as:
  - 5 uppercase letters.
  - 4 numeric digits.
  - 1 uppercase letter.

---

## 3. GST Invoicing Rules

1. **Tax Invoice Requirements**:
   - Must show Supplier GSTIN, Name, Address.
   - Must show Recipient GSTIN, Name, Address (B2B).
   - Unique sequential invoice number per financial year.
   - Date of issue.
   - Description of goods/services and HSN/SAC code.
   - Taxable value, tax rate, and tax split (CGST + SGST or IGST).
2. **Reverse Charge Mechanism (RCM)**:
   - Supported through metadata flags for specified professional categories.
3. **Paise Precision**:
   - Central GST law mandates exact round-off to integer paise or nearest rupee on invoice grand totals.
