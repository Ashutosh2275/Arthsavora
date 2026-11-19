# ARTHSAVORA — FINANCIAL STATEMENT CALCULATIONS

## 1. Mathematical Specifications

ARTHSAVORA computes four principal financial statements:
1. **Income and Expense Statement (Profit & Loss)**
2. **Statement of Cash Flows**
3. **Balance Sheet**
4. **Trial Balance**

All monetary arithmetic is performed in integer **paise** ($1\text{ INR} = 100\text{ paise}$) to eliminate IEEE 754 floating-point rounding errors.

---

## 2. Income and Expense Statement (P&L)

### 2.1 Cash vs Accrual Derivation
- **Cash Basis:** Derives revenues and expenses exclusively from settled transactions where `status = 'completed'` and `booking_date` falls within the period $[T_{\text{start}}, T_{\text{end}}]$.
- **Accrual Basis:** Derives balances from journal lines linked to ledger accounts of type `revenue` and `expense` posted in closed or active accounting periods.

### 2.2 Mathematical Formulas
$$\text{Total Revenue} = \sum \text{Operating Inflows} + \sum \text{Other Income}$$
$$\text{Total Expenses} = \sum \text{Operating Expenses} + \sum \text{Financial/Tax Expenses}$$
$$\text{Net Surplus / (Deficit)} = \text{Total Revenue} - \text{Total Expenses}$$

### 2.3 Percentage of Total
For each line item $i$:
$$\text{Percentage}_i = \left(\frac{\text{Line Balance}_i}{\text{Category Total}}\right) \times 100$$
Percentages are rounded to two decimal places.

---

## 3. Statement of Cash Flows

The Cash Flow Statement categorizes cash movements into three standardized activity streams:

### 3.1 Operating Activities
$$\text{Net Operating Cash Flow} = \text{Operating Receipts} - \text{Operating Disbursements}$$
Includes client invoice collections, payroll, software subscriptions, office expenses, and vendor payments.

### 3.2 Investing Activities
$$\text{Net Investing Cash Flow} = \text{Asset Disposals / Investment Returns} - \text{Capital Expenditures / Fixed Assets}$$
Includes hardware purchases, equipment, and portfolio transfers.

### 3.3 Financing Activities
$$\text{Net Financing Cash Flow} = \text{Equity Contributions / Debt Inflows} - \text{Loan Repayments / Dividends / Drawings}$$

### 3.4 Liquidity Reconciliation
$$\Delta \text{Cash} = \text{Net Operating} + \text{Net Investing} + \text{Net Financing}$$
$$\text{Closing Cash Balance} = \text{Opening Cash Balance} + \Delta \text{Cash}$$

---

## 4. Balance Sheet

The Balance Sheet represents a point-in-time financial posture as of a specific date $T_{\text{as\_of}}$.

### 4.1 Fundamental Accounting Equation
$$\text{Total Assets} = \text{Total Liabilities} + \text{Total Equity}$$

### 4.2 Automated Balance Verification
```python
def validate_balance_sheet_equation(
    total_assets_paise: int,
    total_liabilities_paise: int,
    total_equity_paise: int,
) -> Tuple[bool, int]:
    discrepancy = total_assets_paise - (total_liabilities_paise + total_equity_paise)
    is_balanced = (discrepancy == 0)
    return is_balanced, discrepancy
```
If $\text{Discrepancy} \neq 0$, the system flags a `VAL_BS_EQUALS` warning finding and surfaces the exact paise mismatch on the UI.

---

## 5. Trial Balance

The Trial Balance aggregates all general ledger accounts as of date $T_{\text{as\_of}}$.

### 5.1 Verification Invariant
$$\sum \text{Debits} = \sum \text{Credits}$$

If $\sum \text{Debits} \neq \sum \text{Credits}$, double-entry integrity is compromised, prompting a critical `VAL_TB_EQUALS` finding.
