# ARTHSAVORA — FINANCIAL REPORT VALIDATION & INTEGRITY CHECKS

## 1. Overview & Validation Framework

Before financial statements are published or exported, ARTHSAVORA executes deterministic validation rules to ensure mathematical equilibrium, double-entry integrity, and document completeness.

Validation findings are classified by severity:
- `critical`: Integrity failure that prevents statutory reliance.
- `warning`: Potential discrepancy or unconfirmed item requiring human inspection.
- `info`: Advisory recommendation or optimization hint.

---

## 2. Standard Validation Rules

| Rule Code | Severity | Description | Evaluation Logic | Recommended Action |
| :--- | :---: | :--- | :--- | :--- |
| `VAL_TB_EQUALS` | `critical` | Trial Balance Equality | $\sum \text{Debits} \ne \sum \text{Credits}$ | Investigate unbalanced journal entries or manual ledger adjustments. |
| `VAL_BS_EQUALS` | `warning` | Balance Sheet Equilibrium | $\text{Assets} \ne \text{Liabilities} + \text{Equity}$ | Reconcile retained earnings, net period surplus, or unlinked equity entries. |
| `VAL_DOC_EVIDENCE` | `warning` | Missing Document Evidence | Expense transaction $> \text{₹20,000}$ without attached receipt or invoice. | Upload supporting invoice or receipt via OCR/Receipt Intelligence module. |
| `VAL_TAX_UNREVIEWED` | `info` | Unreviewed Tax Items | Transactions with `status = 'suggested'` pending confirmation. | Review and confirm pending tax classifications in Tax Intelligence tab. |

---

## 3. Finding Resolution Lifecycle

1. Findings are recorded in `report_validation_findings`.
2. Unresolved findings are highlighted across financial statement headers and the Validation Center tab.
3. Users or accountants can resolve a finding with an audit note explaining the business rationale, permanently logged with timestamp and `resolved_by_id`.
