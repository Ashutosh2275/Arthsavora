# Beta Release Execution Plan

## 1. Beta Objectives and Guardrails

The ARTHSAVORA Limited Beta program validates real-world usability with selected Indian freelancers, consultants, and families while keeping operational and financial risks strictly contained.

### Beta Parameters
- **Cohort Size**: 50 active beta testers (by invitation only).
- **Duration**: 4 calendar weeks.
- **Support Channels**: Dedicated in-app feedback modal and monitored support email (`support@arthsavora.in`).
- **Data Safeguards**: Nightly automated PostgreSQL backups with 30-day retention and point-in-time recovery (PITR).

---

## 2. Beta Feature Entitlements

| Capability | Beta Availability | Status Indicator | User Notice |
|---|:---:|:---:|---|
| Personal Dashboard | Available | Full | General availability |
| Transaction Entry & CSV Import | Available | Full | Standard statement import |
| Double-Entry General Ledger | Available | Full | Continuous audit trail |
| Small Business GST Invoicing | Available | Full | Issue tax invoices with 18% GST |
| Family Shared Budgeting | Available | Full | Private accounts remain confidential |
| Tax Estimator (Sec 115BAC) | Available | Full | Informational summary disclaimer |
| Receipt OCR Scanning | Available | Full | 10MB limit per receipt |
| Account Aggregator Sync | Sandbox Only | Badge: "Sandbox Mode" | Real bank sync disabled in beta |

---

## 3. Feedback Loop and Defect Escalation

Beta testers can submit observations directly via the frontend user feedback component:
- Feedback items route directly to the engineering issue tracker.
- Any reported ledger discrepancy or calculation error is flagged as a **P0 Emergency** and halts further user onboarding.
