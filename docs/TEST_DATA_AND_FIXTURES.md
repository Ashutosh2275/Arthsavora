# Test Data and Fixtures Specification

## 1. Overview

Testing institutional commercial FinTech software requires realistic, standardized, and deterministic test data. The ARTHSAVORA fixture library provides factory functions and mock generators for Indian banking, tax, and commercial entities without utilizing any real personally identifiable information (PII) or live account credentials.

---

## 2. Standard Indian Financial Data Fixtures

### 2.1 GSTIN (Goods and Services Tax Identification Number)
Format: `22AAAAA0000A1Z5` (2 digits state code + 10 chars PAN + 1 entity code + 'Z' + 1 checksum char).
- Maharashtra Intra-State: `27AABCA1234F1Z8`
- Karnataka Inter-State: `29AABCA1234F1Z2`
- Delhi Intra-State: `07AABCA1234F1Z9`

### 2.2 Permanent Account Number (PAN)
Format: `AAAAA9999A` (5 uppercase letters, 4 digits, 1 uppercase letter).
- Individual PAN: `ABCDE1234F`
- Company / LLP PAN: `AABCA1234F`

### 2.3 Indian Financial System Code (IFSC) & Banking
Format: 4 alphabetic chars (Bank code) + `0` + 6 alphanumeric chars (Branch code).
- HDFC Bank Mumbai: `HDFC0001234`
- ICICI Bank Bangalore: `ICIC0000002`
- State Bank of India New Delhi: `SBIN0000691`

---

## 3. Monetary Fixtures and Minor Unit Quantization

To ensure exact minor unit arithmetic throughout test suites, the following standard monetary quantities are predefined:

| Identifier | Rupee Display Value | Minor Units (Paise) | Test Scenario Context |
|---|---|---|---|
| `OPENING_BALANCE_SAVINGS` | ₹1,00,000.00 | `10000000` | Initial capital deposit in savings account |
| `SALARY_CREDIT` | ₹75,000.00 | `7500000` | Monthly corporate salary inflow |
| `GROCERY_EXPENSE` | ₹4,500.00 | `450000` | Everyday domestic grocery debit |
| `COMMERCIAL_INVOICE_BASE` | ₹50,000.00 | `5000000` | B2B consulting services subtotal |
| `GST_18_PERCENT` | ₹9,000.00 | `900000` | 18% GST (CGST ₹4,500 + SGST ₹4,500) |
| `COMMERCIAL_INVOICE_TOTAL` | ₹59,000.00 | `5900000` | Total payable on commercial tax invoice |
| `SECTION_87A_LIMIT` | ₹7,00,000.00 | `70000000` | Maximum income for 100% tax rebate under Section 87A |

---

## 4. Teardown and Data Sanitization Protocols

1. **Synthetic Isolation**: No test interacts with production databases, external SMS gateways, or live banking APIs.
2. **Deterministic UUIDs & Prefixes**: Test workspaces, users, and accounts use clear synthetic prefixes (`test_user_*`, `test_ws_*`) to prevent ambiguity in execution logs.
3. **Savepoint Reversal**: Database fixtures use SQLAlchemy savepoints, rolling back mutations cleanly when test execution terminates.
