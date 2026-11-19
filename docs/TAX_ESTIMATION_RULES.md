# ARTHSAVORA — TAX ESTIMATION RULES & SLABS

## 1. Overview & Statutory Foundation

ARTHSAVORA implements exact mathematical tax models comparing:
1. **New Tax Regime (Section 115BAC) — Default**
2. **Old Tax Regime (Optional)**

All computations include Standard Deduction, Section 87A Tax Rebate, and 4% Health and Education Cess.

---

## 2. New Tax Regime (Section 115BAC) Slabs

Under the New Tax Regime:
- **Standard Deduction:** ₹75,000 for salaried employees and pensioners.
- **Section 87A Rebate:** If Taxable Income $\le \text{₹7,00,000}$, tax rebate equals 100% of calculated tax (effective tax = ₹0).

| Taxable Income Slab (₹) | Slab Tax Rate (%) |
| :--- | :---: |
| ₹0 to ₹3,00,000 | Nil (0%) |
| ₹3,00,001 to ₹7,00,000 | 5% |
| ₹7,00,001 to ₹10,00,000 | 10% |
| ₹10,00,001 to ₹12,00,000 | 15% |
| ₹12,00,001 to ₹15,00,000 | 20% |
| Above ₹15,00,000 | 30% |

### New Regime Algorithm
```python
def calculate_new_regime_tax(taxable_income: Decimal) -> Decimal:
    if taxable_income <= Decimal("300000"):
        return Decimal("0.00")
    
    tax = Decimal("0.00")
    # 3L - 7L @ 5% (Max 20,000)
    if taxable_income > Decimal("300000"):
        taxable_in_slab = min(taxable_income - Decimal("300000"), Decimal("400000"))
        tax += taxable_in_slab * Decimal("0.05")
    # 7L - 10L @ 10% (Max 30,000)
    if taxable_income > Decimal("700000"):
        taxable_in_slab = min(taxable_income - Decimal("700000"), Decimal("300000"))
        tax += taxable_in_slab * Decimal("0.10")
    # 10L - 12L @ 15% (Max 30,000)
    if taxable_income > Decimal("1000000"):
        taxable_in_slab = min(taxable_income - Decimal("1000000"), Decimal("200000"))
        tax += taxable_in_slab * Decimal("0.15")
    # 12L - 15L @ 20% (Max 60,000)
    if taxable_income > Decimal("1200000"):
        taxable_in_slab = min(taxable_income - Decimal("1200000"), Decimal("300000"))
        tax += taxable_in_slab * Decimal("0.20")
    # Above 15L @ 30%
    if taxable_income > Decimal("1500000"):
        taxable_in_slab = taxable_income - Decimal("1500000")
        tax += taxable_in_slab * Decimal("0.30")

    # Section 87A full rebate if taxable income <= 7,00,000
    if taxable_income <= Decimal("700000"):
        tax = Decimal("0.00")

    return tax
```

---

## 3. Old Tax Regime Slabs

Under the Old Tax Regime:
- **Standard Deduction:** ₹50,000.
- **Chapter VI-A Deductions Allowed:** Section 80C (up to ₹1.5L), Section 80D (up to ₹25k/₹50k), Section 24(b) Home loan interest (up to ₹2L).
- **Section 87A Rebate:** If Taxable Income $\le \text{₹5,00,000}$, rebate up to ₹12,500 applies.

| Taxable Income Slab (₹) | Slab Tax Rate (%) |
| :--- | :---: |
| ₹0 to ₹2,50,000 | Nil (0%) |
| ₹2,50,001 to ₹5,00,000 | 5% |
| ₹5,00,001 to ₹10,00,000 | 20% |
| Above ₹10,00,000 | 30% |

---

## 4. Health and Education Cess
$$\text{Total Tax Liability} = \text{Tax after 87A Rebate} + 4\% \text{ Health & Education Cess}$$
$$\text{Effective Tax Rate (\%)} = \left(\frac{\text{Total Tax Liability}}{\text{Gross Income}}\right) \times 100$$
