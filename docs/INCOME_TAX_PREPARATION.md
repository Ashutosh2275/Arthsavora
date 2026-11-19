# ARTHSAVORA — INCOME TAX PREPARATION

## 1. Overview & Preparatory Workpapers

The Income Tax Preparation module automates the compilation of tax workpapers for personal and business taxpayers preparing for annual Income Tax Return (ITR-1, ITR-2, ITR-3, ITR-4) filings.

---

## 2. Income Computation & Inflow Aggregation

### 2.1 Gross Total Income (GTI) Derivation
$$\text{GTI} = \text{Income from Salaries} + \text{Income from Business/Profession} + \text{Capital Gains} + \text{Income from Other Sources}$$
- In ARTHSAVORA, verified inflows tagged as income are aggregated across the statutory financial year $[T_{\text{start}}, T_{\text{end}}]$.
- Non-taxable transfers between self-owned accounts are systematically excluded.

### 2.2 Deductions & Chapter VI-A Verification
- **Section 80C Cap:** Maximum deduction allowed is ₹1,50,000 across all qualifying investments (ELSS, PPF, EPF, Life Insurance, Principal Home Loan).
- **Section 80D Cap:** Up to ₹25,000 for self/family (₹50,000 for senior citizens) and an additional ₹25,000/₹50,000 for parents' health insurance.
- **Section 24(b):** Home loan interest deduction up to ₹2,00,000 for self-occupied property (Old Regime only).

---

## 3. Presumptive Taxation (Section 44ADA / 44AD)

For small businesses and freelancers using ARTHSAVORA's business workspaces:
- The system computes presumptive income ($50\%$ for 44ADA; $6\%$ digital / $8\%$ cash for 44AD).
- Displays side-by-side comparison with actual net surplus from the Income & Expense Statement to help taxpayers determine if audit under Section 44AB is warranted.
