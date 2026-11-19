# Root Cause Analysis (RCA) — Prompt 29 Integration Testing

## 1. Executive Summary

During the integration and E2E test authoring phase of Prompt 29, several schema and interface misalignments were detected and systematically diagnosed using root cause analysis before final test execution.

All issues were immediately resolved at their source, resulting in a 100% test pass rate across 344 backend tests and 158 frontend tests.

---

## 2. Diagnosed Defects and Remediation

### 2.1 Trial Balance Net Aggregation Discrepancy
- **Symptom**: Integration test asserted total trial balance debits equaled the sum of all individual inflows and outflows (₹79,500), but `LedgerService.get_trial_balance()` returned ₹75,000.
- **Root Cause**: Accounting trial balance logic net-aggregates debits and credits per individual account before summing across accounts. For a bank account with ₹75,000 debit inflow and ₹4,500 credit outflow, the net account balance is ₹70,500 debit. Adding the ₹4,500 grocery expense debit yields total debits of ₹75,000, exactly balancing the ₹75,000 salary credit.
- **Remediation**: Corrected test expectation to accurately mirror net-aggregated double-entry trial balance principles.

### 2.2 Domain Money Value Object Property Access
- **Symptom**: Calling `money.paise()` raised `TypeError: 'int' object is not callable`.
- **Root Cause**: In `backend/app/domain/money.py`, `paise` and `display_amount` are decorated with `@property`, making them read-only attributes rather than callable methods.
- **Remediation**: Updated test invocation from `money.paise()` to `money.paise`.

### 2.3 Tax Estimation Return Type Interface
- **Symptom**: Calling `estimate.total_tax_paise` raised `AttributeError`.
- **Root Cause**: The property name on `IncomeTaxEstimateVO` in `backend/app/domain/financial_report.py` is `total_estimated_tax_paise`.
- **Remediation**: Aligned test assertions with domain VO contract (`assert est.total_estimated_tax_paise == 0`).

### 2.4 Document Service Module Path
- **Symptom**: `from app.services.document_service import DocumentService` raised `ModuleNotFoundError`.
- **Root Cause**: The document domain was refactored into a submodule under `app.services.document.document_service`.
- **Remediation**: Corrected import path to `from app.services.document.document_service import DocumentService`.

---

## 3. Preventive Measures Instituted

1. **Strict Type Annotations**: Integration tests import DTO and VO types directly, enabling immediate IDE / linter autocompletion and typechecking.
2. **Deterministic Regression Tests**: All RCA fixes are permanently codified in `backend/tests/test_system_integration_e2e_qa.py`.
