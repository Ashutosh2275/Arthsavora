# OCR Validation, Mathematical Reconciliation and Confidence Scoring

## 1. Overview

Document extraction is inherently probabilistic. Distortions, low camera resolution, uneven lighting, thermal paper fading, and folded bills can introduce character misrecognitions (e.g., confusing `8` with `B`, or `0` with `O`).

To ensure that unverified suggestions never compromise ledger integrity, Arthsavora implements a multi-tiered **Mathematical Reconciliation Engine** and a **Weighted Confidence Scoring Model** within [document.py](file:///d:/Arthsavora/backend/app/domain/document.py) and [field_extractor.py](file:///d:/Arthsavora/backend/app/services/document/field_extractor.py).

---

## 2. Mathematical Reconciliation Invariant

### 2.1 The Master Balance Formula
Every financial invoice or point-of-sale receipt must satisfy the primary arithmetic balance equation:

$$\text{Subtotal} + \text{Total Taxes} - \text{Discounts} = \text{Total Amount}$$

In integer `paise`, this invariant is expressed as:
```python
calculated_total = subtotal_paise + tax_paise - discount_paise
discrepancy = abs(calculated_total - extracted_total_paise)
```

### 2.2 Line-Item Summation
When line items are parsed from tabular bills, the engine calculates the sum of all item totals:

$$\sum_{i=1}^{N} \text{line\_item\_total}_i = \text{Subtotal}$$

### 2.3 Rounding Tolerance & Indian Round-Off Conventions
Indian retail establishments and grocery stores frequently apply a statutory "Round-Off" line item to eliminate loose paise on cash or POS payments (e.g., rounding ₹549.60 to ₹550.00).
- **Tolerance Threshold**: Differences $\le 100\text{ paise}$ ($\le ₹1.00$) are treated as benign rounding variations.
- **Classification**:
  - If `discrepancy == 0`: Status is `ValidationStatus.VALID`.
  - If `0 < discrepancy <= 100`: Status is `ValidationStatus.WARNING` with message `Minor rounding difference of X paise (acceptable)`.
  - If `discrepancy > 100`: Status is `ValidationStatus.INVALID_MATH` with message `Mathematical discrepancy: subtotal + tax - discount does not equal total (diff: X paise)`.

---

## 3. Validation Status Taxonomy

The domain model categorizes document mathematical status into four explicit states:

```
+---------------------------------------------------------------------------------+
|                                 ValidationStatus                                |
+---------------------------------------------------------------------------------+
| VALID        | Total matches components exactly (discrepancy == 0 paise)        |
| WARNING      | Minor round-off discrepancy (<= 100 paise / ₹1.00)               |
| INVALID_MATH | Substantial discrepancy (> 100 paise) requiring manual review   |
| INCOMPLETE   | Essential fields missing (e.g. Total amount not found)           |
+---------------------------------------------------------------------------------+
```

Documents marked `INVALID_MATH` or `INCOMPLETE` display prominent warning banners in the user review drawer, preventing accidental confirmation without field inspection.

---

## 4. Weighted Confidence Scoring Model

### 4.1 Weight Distribution Matrix
Overall confidence is not a simple arithmetic average. Certain fields carry immense financial significance (such as the total amount payable), while secondary metadata (such as invoice reference number) is less critical for ledger integrity.

| Field | Weight ($\omega$) | Rationalization |
|---|---|---|
| **Total Amount** | **0.35** | Most critical numerical figure for ledger mutation |
| **Transaction Date** | **0.20** | Necessary for accounting period attribution and statement matching |
| **Merchant Name** | **0.20** | Essential for counterparty identity and category assignment |
| **Taxes (CGST/SGST/IGST)** | **0.10** | Crucial for commercial GST input tax credit (ITC) reconciliation |
| **GSTIN** | **0.10** | High-fidelity proof of corporate legitimacy and tax identity |
| **Line Items** | **0.05** | Granular itemization supporting auditability |
| **Total** | **1.00** | Full confidence vector sum |

### 4.2 Mathematical Calculation
The base confidence score $C_{\text{base}}$ is computed as:

$$C_{\text{base}} = \sum_{k \in \text{Fields}} \omega_k \cdot c_k$$

where $c_k \in [0.0, 1.0]$ represents the extraction confidence for field $k$.

### 4.3 Deterministic Adjustments (Bonuses & Penalties)
1. **Mathematical Verification Bonus (+0.10)**:
   If `subtotal + tax - discount == total` reconciles with zero discrepancy, the document gains a +0.10 confidence boost (capped at 1.00).
2. **Mathematical Failure Penalty (-0.25)**:
   If the extracted subtotal, taxes, and total contradict each other with a discrepancy $> ₹1.00$, the document suffers an immediate 0.25 penalty, as one or more numeric fields are demonstrably corrupted by OCR misreading.
3. **GSTIN Checksum Validation Bonus (+0.05)**:
   A valid 15-character GSTIN passing the state code and structure check boosts counterparty confidence.

---

## 5. UI Presentation & Confidence Indicators

The Web interface renders clear visual indicators to communicate extraction fidelity:

| Score Range | Status Badge | Color Scheme | Recommended User Action |
|---|---|---|---|
| **90% – 100%** | `High Confidence` | Green (`#16a34a`) | Quick sanity check and instant confirmation |
| **70% – 89%** | `Medium Confidence` | Amber (`#d97706`) | Verify total and merchant before confirming |
| **0% – 69%** | `Needs Review` | Rose (`#e11d48`) | Full field review required; re-enter blurred numbers |

---

## 6. Related Documentation

- [Receipt Intelligence Architecture](file:///d:/Arthsavora/docs/RECEIPT_INTELLIGENCE_ARCHITECTURE.md)
- [Receipt Field Extraction](file:///d:/Arthsavora/docs/RECEIPT_FIELD_EXTRACTION.md)
- [Document Review Workflow](file:///d:/Arthsavora/docs/DOCUMENT_REVIEW_WORKFLOW.md)
- [Transaction Architecture](file:///d:/Arthsavora/docs/TRANSACTION_ARCHITECTURE.md)
