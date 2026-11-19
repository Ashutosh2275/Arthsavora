# ARTHSAVORA — INDIA TAX INTELLIGENCE

## 1. Statutory Context & Principles

Indian direct tax regulations operate under the **Income-tax Act, 1961**, and indirect taxes under the **Central Goods and Services Tax (CGST) Act, 2017**.

ARTHSAVORA implements mathematical models and rules reflecting the latest statutory updates:
- **Finance Act 2023 / 2024 Amendments**
- **Default Regime:** Section 115BAC (New Tax Regime) is the statutory default regime for Individuals and HUFs.
- **Old Tax Regime:** Available as an annual opt-in exercise for individuals with or without business income.
- **Higher Standard Deduction:** ₹75,000 under the New Tax Regime (vs ₹50,000 under the Old Regime).
- **Section 87A Tax Rebate:** Full tax rebate for taxable income up to ₹7,00,000 under the New Regime (effective zero tax).

---

## 2. Tax Assessment Timeline

| Milestone | Financial Year (FY) | Assessment Year (AY) |
| :--- | :--- | :--- |
| **Earning Period** | April 1, $Y$ – March 31, $Y+1$ | — |
| **Tax Assessment Period** | — | April 1, $Y+1$ – March 31, $Y+2$ |
| **Example** | `FY 2026-27` | `AY 2027-28` |

---

## 3. Direct vs Indirect Tax Separation

ARTHSAVORA strictly separates direct income tax calculations from indirect Goods and Services Tax (GST) data:
1. **Direct Tax Module:** Evaluates taxable net income, salary deductions, professional expense deductibility, Chapter VI-A deductions, and computes estimated liability under Section 115BAC.
2. **Indirect Tax (GST) Module:** Analyzes outward commercial supplies (invoices issued), identifies place of supply, and computes intra-state vs inter-state tax liabilities (CGST, SGST, IGST).
