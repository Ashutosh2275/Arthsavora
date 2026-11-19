# Financial Calculation and Compliance Validation

## 1. Overview

This document presents the mathematical proofs, statutory logic rules, and validation test results for all India-specific financial calculations in ARTHSAVORA.

---

## 2. Indian Financial Year (FY) Boundaries and Quarters

Indian tax and fiscal reporting operates on an April 1 to March 31 cycle.

### Test Evidence (`test_indian_financial_year_bounds_and_quarters`)
- **April 15, 2026**:
  - Financial Year: `FY 2026-27`
  - Quarter: `Q1` (April 1 to June 30)
  - Period Bounds: `2026-04-01` to `2027-03-31`
- **January 10, 2027**:
  - Financial Year: `FY 2026-27`
  - Quarter: `Q4` (January 1 to March 31)
  - Period Bounds: `2026-04-01` to `2027-03-31`
- **Result**: **100% PASS**.

---

## 3. Indian Income Tax Estimation (Section 115BAC New Tax Regime)

The Finance Act New Tax Regime provides revised progressive tax slabs and a full tax rebate under Section 87A for taxable income up to ₹7,00,000.

### Tax Slab Structure
1. ₹0 to ₹3,00,000: Nil (0%)
2. ₹3,00,001 to ₹6,00,000: 5%
3. ₹6,00,001 to ₹9,00,000: 10%
4. ₹9,00,001 to ₹12,00,000: 15%
5. ₹12,00,001 to ₹15,00,000: 20%
6. Above ₹15,00,000: 30%
7. Section 87A Rebate: 100% tax rebate if total taxable income $\le$ ₹7,00,000.
8. Health & Education Cess: 4% applied to net tax after rebate.

### Test Evidence (`test_indian_income_tax_estimation_new_regime`)
- **Case 1: Income ₹7,00,000 (Section 87A Limit)**
  - Gross Tax before rebate: ₹25,000 (5% of 3L + 10% of 1L).
  - Section 87A Rebate: ₹25,000 (100% rebate).
  - Net Estimated Tax: **₹0.00** (`0` paise).
  - Test Result: **Verified PASS**.
- **Case 2: Income ₹10,00,000 (Above Section 87A Limit)**
  - Slab 1 (0 to 3L): ₹0
  - Slab 2 (3L to 6L @ 5%): ₹15,000
  - Slab 3 (6L to 9L @ 10%): ₹30,000
  - Slab 4 (9L to 10L @ 15%): ₹15,000
  - Base Tax: ₹60,000
  - Health & Education Cess (4% of ₹60,000): ₹2,400
  - Total Estimated Tax: **₹62,400.00** (`6240000` paise).
  - Test Result: **Verified PASS**.

---

## 4. Goods and Services Tax (GST) Calculations

For B2B commercial invoicing (`test_e2e_business_finance_invoicing_and_receivables`):
- Subtotal: ₹50,000.00 (`5000000` paise)
- GST Rate: 18%
  - Intra-State: 9% CGST (₹4,500.00) + 9% SGST (₹4,500.00)
  - Inter-State: 18% IGST (₹9,000.00)
- Total Invoice Payable: ₹59,000.00 (`5900000` paise)
- Test Result: **Verified PASS**.

---

## 5. Leap Year & End-of-Month Scheduling Rules

In `test_recurrence_leap_year_and_end_of_month_pinning`:
- Leap Day Pinning: February 29 scheduled recurrence advances to February 28 in non-leap years (e.g. 2027), never overflowing into March 1.
- Month-End Pinning: January 31 recurrence pinned to February 28 (or 29) and March 31.
- Test Result: **Verified PASS**.
