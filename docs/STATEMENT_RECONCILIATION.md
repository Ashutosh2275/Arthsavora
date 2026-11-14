# ARTHSAVORA — STATEMENT BALANCE RECONCILIATION

## 1. Mathematical Foundation

Bank statements represent an unbroken temporal sequence of account state. A mathematically correct statement must satisfy the balance continuity equation:

$$\text{Calculated Closing Balance} = \text{Opening Balance} + \sum \text{Inflows} - \sum \text{Outflows}$$

Where:
- $\text{Opening Balance}$: The ledger balance at the start of the statement period.
- $\sum \text{Inflows}$: The sum of all credit transactions, interest, and deposits extracted from the statement.
- $\sum \text{Outflows}$: The sum of all debit transactions, fees, and withdrawals extracted from the statement.
- $\text{Reported Closing Balance}$: The statement closing balance extracted from the statement footer or header.

The **Reconciliation Discrepancy** is defined as:

$$\Delta = \text{Reported Closing Balance} - \text{Calculated Closing Balance}$$

---

## 2. Discrepancy Classifications

| Discrepancy | Classification | Significance & Recommended User Action |
| :--- | :--- | :--- |
| $\Delta = 0$ | **Perfect Reconciliation** | Every movement in the statement is accounted for. Safe for one-click batch confirmation. |
| $\Delta > 0$ | **Missing Inflow / Hidden Credit** | The bank reports more money than the sum of extracted rows. Suggests a missing deposit row, multi-page skip, or unparsed credit item. |
| $\Delta < 0$ | **Missing Outflow / Unrecorded Debit** | The bank reports less money than calculated. Suggests unparsed bank charges, tax deducted at source (TDS), or skipped debit lines. |

---

## 3. Storage & Batch Reconciliation Fields

Every `import_batches` row stores the complete reconciliation state:
- `opening_balance`: Extracted opening balance (`Numeric(18, 4)`).
- `closing_balance`: Extracted statement closing balance (`Numeric(18, 4)`).
- `calculated_closing_balance`: Summed balance derived from candidates (`Numeric(18, 4)`).
- `reconciliation_discrepancy`: $\Delta$ (`Numeric(18, 4)`).

---

## 4. API & Frontend Integration

### 4.1 Endpoint
The reconciliation breakdown is retrieved via:
```http
GET /api/v1/workspaces/{workspace_id}/imports/jobs/{job_id}/batches/{batch_id}/reconciliation
```

Response JSON:
```json
{
  "opening_balance": 100000.0,
  "opening_balance_paise": 10000000,
  "closing_balance": 130000.0,
  "closing_balance_paise": 13000000,
  "total_inflows": 75000.0,
  "total_inflows_paise": 7500000,
  "total_outflows": 45000.0,
  "total_outflows_paise": 4500000,
  "calculated_closing_balance": 130000.0,
  "calculated_closing_balance_paise": 13000000,
  "discrepancy": 0.0,
  "discrepancy_paise": 0,
  "is_reconciled": true
}
```

### 4.2 UI Presentation
The Web interface (`apps/web/src/pages/Import.tsx`) renders a dedicated **Statement Balance Reconciliation Card**:
- When `is_reconciled == true`: Green border with a checkmark badge (`Reconciled (₹0.00 difference)`).
- When `is_reconciled == false`: Amber warning box displaying the exact discrepancy in Indian Rupees (`₹`), alerting the user before they confirm the batch.
