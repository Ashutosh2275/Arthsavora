# Business Budgeting & Operational Cost Control

## 1. Business Budget Scope

Business budgeting builds directly upon Arthsavora's category and budget infrastructure (Prompts 07 & 09), scoped to the active commercial workspace.

### Core Objectives:
- Budgeting for operational cost categories (e.g. Cloud Hosting, Marketing, Office Rent, Professional Fees).
- Preventing cash burn and runaway SaaS subscriptions.
- Aligning operational expenditure with quarterly billing cycles.

---

## 2. Accrual vs. Cash Budgeting

1. **Accrual Budgeting**:
   - Compares budgeted operational expenses against logged vendor bills (`BusinessPayable`) within the accounting period.
2. **Cash-Flow Budgeting**:
   - Compares budgeted outflows against actual bank account disbursements (`BusinessPayablePayment`).

---

## 3. Thresholds & Alerts Integration

When business expenditure crosses configured budget thresholds (80%, 90%, 100%):
- Automated in-app notifications are dispatched via `NotificationService` (Prompt 20).
- Budget status is exposed to the AI Financial Assistant (Prompt 18) for conversational queries.
