# Launch Feature Matrix and Capability Inventory

## 1. Scope and Availability Overview

This matrix catalogs every major user-facing feature across ARTHSAVORA and designates its implementation, testing, production configuration, and launch availability status.

### Status Definitions
- **Fully Available**: Code complete, tested, production-configured, active at launch.
- **Available with Limitations**: Feature operational; certain external provider facets staged or simulated.
- **Sandbox-Only**: End-to-end flow verified against synthetic mock adapters pending formal regulatory onboarding.

---

## 2. Comprehensive Capability Matrix

| Feature Domain | Implemented | Tested | Prod-Configured | External Dependency | Launch Availability |
|---|:---:|:---:|:---:|---|:---:|
| **User Authentication & Profiles** | ✅ | ✅ | ✅ | None (Internal Argon2id) | **Fully Available** |
| **Workspace Isolation & Tenancy** | ✅ | ✅ | ✅ | PostgreSQL RLS | **Fully Available** |
| **Bank & Financial Accounts** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Transaction Recording & Cleared State**| ✅ | ✅ | ✅ | None | **Fully Available** |
| **Double-Entry General Ledger** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **CSV & Bank Statement Import** | ✅ | ✅ | ✅ | Standard CSV/Excel | **Fully Available** |
| **Transaction Auto-Categorization** | ✅ | ✅ | ✅ | Internal Rule/ML Engine | **Fully Available** |
| **Merchant Identity Resolution** | ✅ | ✅ | ✅ | Internal Merchant DB | **Fully Available** |
| **Cash Flow & Net Worth Analytics** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Personal Budgeting & Alerts** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Financial Goal Progress Tracking** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Recurring Commitments & Subscriptions**| ✅ | ✅ | ✅ | None | **Fully Available** |
| **Predictive Cash Flow Forecasting** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Anomaly & Security Risk Detection** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Conversational AI Assistant** | ✅ | ✅ | ✅ | Internal LLM Provider Port | **Available with Limitations** |
| **Receipt Intelligence & OCR Parsing** | ✅ | ✅ | ✅ | Local Vision/OCR Port | **Fully Available** |
| **In-App Notification Center** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Family Finance & Shared Budgets** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Business Client & Invoicing Hub** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **GST Invoicing & Summary Reports** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Income Tax Estimator (Sec 115BAC)** | ✅ | ✅ | ✅ | None | **Fully Available** |
| **Progressive Web App (PWA) Offline** | ✅ | ✅ | ✅ | Service Worker Cache API | **Fully Available** |
| **Account Aggregator Automated Sync** | ✅ | ✅ | ✅ | NBFC-AA Partner Contract | **Sandbox-Only** |
| **External Web Push Notifications** | ✅ | ✅ | ✅ | Production VAPID Keys | **Available with Limitations** |
