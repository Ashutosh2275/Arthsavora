# Arthsavora — Forward-Looking Cash-Flow Commitment Analytics

## 1. Scope & Objective

Commitment Analytics provides forward visibility into anticipated cash inflows and outflows. By analyzing expected occurrences within discrete planning horizons (7 days, 30 days, 90 days), users understand upcoming obligations before bank accounts are debited.

---

## 2. Planning Horizons & Aggregations

The analytics service computes metrics across three standard institutional windows:

| Horizon | Primary Use Case | Aggregations Computed |
|---|---|---|
| **7 Days** | Immediate liquidity & overdraft protection | Immediate due occurrences, pending bills, upcoming payroll deposits. |
| **30 Days** | Monthly budget balancing & working capital | Rent, loan EMIs, utilities, credit card due dates, subscriptions. |
| **90 Days** | Quarterly cash-flow planning & runway assessment | Multi-month obligations, quarterly tax/advance payments, annual renewals. |

For each horizon, the system derives:
- **Total Expected Inflow (`paise`)**: Sum of all active scheduled inflows (salary, rental income, dividends).
- **Total Expected Outflow (`paise`)**: Sum of all active scheduled outflows (rent, bills, EMIs, subscriptions).
- **Net Expected Cash Commitment (`paise`)**:
  $$\text{Net Commitment} = \text{Total Inflow} - \text{Total Outflow}$$
- **Normalized Monthly Recurring Spend**: Normalized monthly run rate across all active recurring definitions.
- **Normalized Annual Recurring Spend**: Normalized annual run rate ($12 \times \text{Monthly Spend}$).

---

## 3. Commitment Classification Taxonomy

Upcoming commitments are categorized into six functional obligation types:

1. **Rent & Housing**: Landlord transfers, apartment maintenance, HOA dues.
2. **Loan & EMI**: Vehicle loans, home mortgages, personal loan installments, education EMIs.
3. **Utilities**: Electricity, municipal water, piped gas, broadband internet, mobile postpaid.
4. **Insurance**: Health insurance, term life policies, auto insurance premiums.
5. **Subscriptions**: Software, digital services, gym memberships, media streaming.
6. **Income**: Scheduled salaries, partner draws, monthly freelance retainers, pension.
7. **Other Commitments**: Discretionary recurring payments, donations, SIP investments.

---

## 4. Integration with Financial Forecasting (Prompt 16 Preparation)

Commitment Analytics acts as the deterministic anchor for future financial forecasting:
- Historical transactions provide statistical baseline spending trends.
- Recurring definitions provide known scheduled future commitments.
- The forecasting engine synthesizes both to project future liquidity curves with bounded uncertainty bands.
