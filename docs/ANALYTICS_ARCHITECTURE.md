# Arthsavora Financial Analytics & Dashboard Intelligence Architecture

## 1. Executive Summary

The **Financial Analytics Engine** in Arthsavora bridges authoritative PostgreSQL accounting and transactional records with interactive user experiences, providing institutional-grade transparency across personal, family, and business workspaces.

All metrics are derived directly from verified financial source records (`transactions` where `status = 'posted'` and `accounts` / `journal_entries` in the double-entry general ledger). Unconfirmed AI predictions are strictly barred from contaminating financial calculations.

```
                          ┌───────────────────────────┐
                          │   Client Application      │
                          │  (Web / PWA / Mobile)     │
                          └─────────────┬─────────────┘
                                        │ REST / JSON (or CSV Stream)
                                        ▼
                          ┌───────────────────────────┐
                          │    Analytics Router       │
                          │  (RBAC & Tenant Security) │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   Analytics Application   │
                          │          Service          │
                          │  - Date Range Validation  │
                          │  - Multi-Currency Gate    │
                          │  - CSV Injection Defense  │
                          │  - Quality Metric Agg     │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   Analytics Repository    │
                          │  Server-Side PostgreSQL   │
                          │  SQL SUM, CASE, GROUP BY  │
                          └─────────────┬─────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
            ┌──────────────────────┐        ┌──────────────────────┐
            │     transactions     │        │       accounts       │
            │  (status = 'posted') │        │   (active balances)  │
            └──────────────────────┘        └──────────────────────┘
```

---

## 2. Core Architectural Principles

### 2.1 Authoritative Source of Truth
Financial analytics must never run on cached, speculative, or unconfirmed machine learning inferences. 
- Income and expenses are aggregated exclusively from `transactions` where `status = 'posted'` and `is_deleted = false`.
- Pending transactions are segregated and tracked solely as data-quality indicators.
- Failed, cancelled, and reversed transactions are omitted from cash flow totals.

### 2.2 Transfer & Liability Segregation (Double-Counting Prevention)
A foundational failure mode in naive financial software is treating internal account transfers and credit card payments as income or expense:
1. **Paired Transfers:** Moving ₹50,000 from a savings account to a fixed deposit does not represent ₹50,000 of expenditure nor ₹50,000 of income. Any transaction with `transaction_type = 'transfer'` or `transfer_id IS NOT NULL` is omitted from operating cash flows.
2. **Credit Card Bill Settlements:** When a user pays a credit card bill from their bank account, the expense was already incurred upon purchasing goods (`credit_card_purchase`). The repayment settles the card liability. Counting both the card purchase and the repayment would double-count living costs. Thus, `credit_card_payment` is treated as a balance sheet settlement.
3. **Loan Capital Disbursals and Repayments:** Disbursing a loan increases cash and debt (not income). Principal repayment reduces debt and cash (not operating expense). Only interest (`loan_interest_payment`) and fees (`loan_fee`) constitute expenses.

### 2.3 Refund & Contra-Expense Treatment
Refunds and merchant cashbacks (`refund`, `credit_card_refund`) represent reversals or reductions of past expenditure. Arthsavora computes:
$$\text{Net Operating Expenses} = \max(0, \text{Gross Expenses} - \text{Refunds})$$
This guarantees that operational turnover is not artificially inflated by purchase-refund cycles.

### 2.4 Server-Side PostgreSQL Aggregation
To achieve sub-50ms response times and prevent OOM crashes on high-volume accounts, computations are pushed down to PostgreSQL via SQL `SUM(CASE WHEN ... THEN amount_paise ELSE 0 END)`, `func.date_trunc(...)`, and `COALESCE(...)`. Full transaction histories are never deserialized into application runtime memory.

### 2.5 Multi-Currency Isolation
Arthsavora enforces strict currency isolation. Analytics queries require a target currency (defaulting to `INR`). Transactions in disparate currencies are filtered to their respective currency silos unless explicit conversion ledger adjustments are recorded. Zero mixed-currency additions occur.

---

## 3. High-Level System Components

| Component | File Path | Primary Responsibility |
| :--- | :--- | :--- |
| **Domain Foundation** | `backend/app/domain/analytics.py` | Period grouping enums, India FY bounds, savings rate math, percentage deltas, sentiment indicators, and CSV sanitization. |
| **Analytics Repository** | `backend/app/repositories/analytics_repository.py` | Server-side PostgreSQL aggregation queries for overview, cash flow trends, category breakdown, top merchants, and net worth. |
| **Application Service** | `backend/app/services/analytics/analytics_service.py` | Validates date spans (bounded $\le 10$ years), enforces currency formats, orchestrates queries, and builds sanitized CSV streams. |
| **API Endpoints** | `backend/app/api/v1/analytics_routes.py` | Authenticated, tenant-isolated REST endpoints guarded by `Permission.VIEW_ANALYTICS` and `Permission.EXPORT_ANALYTICS`. |
| **Zustand Store** | `apps/web/src/store/useAnalyticsStore.ts` | Frontend reactive state managing period presets (This Month, India FY, etc.), account filters, and data fetching. |
| **Interactive UI** | `apps/web/src/pages/Dashboard.tsx` | Recharts-powered responsive dashboard with Area Cash Flow trends, Donut Category breakdowns, KPI delta cards, and CSV export. |
