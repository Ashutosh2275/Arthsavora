# ARTHSAVORA — Privacy Engineering & Data Governance Framework

## 1. Governance Objectives

ARTHSAVORA's privacy framework establishes systematic data governance over personal, household, and commercial financial records. The platform complies with modern privacy principles:
- **Data Minimization:** Only collecting data strictly necessary for financial management and reporting.
- **Purpose Limitation:** Financial records are processed exclusively for user-authorized accounting and budgeting purposes.
- **Storage Limitation:** Time-bound retention and user-driven deletion capabilities.
- **Confidentiality & Integrity:** Encryption in transit, encryption at rest, and granular access controls.
- **Transparency:** Clear audit logging and explicit consent management for third-party financial data acquisition.

---

## 2. Information Classification Taxonomy

| Data Tier | Examples | Storage Standard | Access Controls | Retention Standard |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Authentication Secrets** | Hashed passwords, JWT signing keys, OAuth client secrets, API tokens | Salted bcrypt, environment variables, secrets manager | Strictly machine-readable; zero logging; zero UI exposure | Lifetime of credential; immediate revocation on rotation |
| **Tier 2: Highly Sensitive Financial Data** | Bank account numbers, IFSC codes, PAN, GSTIN, Account Aggregator consent tokens, raw bank statements | Column-level encryption, TLS in transit, database RLS | Scoped to active workspace owner/admin; masked in UI (e.g. `••••1234`) | Duration of account or until explicit user deletion request |
| **Tier 3: Confidential Ledger & Transactions** | General ledger lines, journal entries, invoice amounts, client/vendor names, receipt photos | PostgreSQL RLS, private object storage, TLS 1.3 | Workspace role-gated (RBAC) | 8 years for business records (Indian Companies Act / GST compliance) |
| **Tier 4: Internal Analytics & Telemetry** | Categorization rules, anomaly scores, audit trails, correlation IDs, performance latency | Structured JSON logs, append-only audit tables | Internal operators, workspace audit viewers | 180 days for application logs; permanent for financial audit logs |
| **Tier 5: Public Information** | System health status, documentation, API error code descriptions | Public HTTP endpoints | Unrestricted read | Indefinite |

---

## 3. Privacy by Design in Multi-Member Workspaces

### 3.1. Personal Workspace Isolation
Personal workspaces are strictly isolated. External members cannot be invited or attached. Personal financial information remains completely private to the owner.

### 3.2. Family Workspace Privacy Boundary
Household financial collaboration often fails when platforms force members to disclose every private expense. ARTHSAVORA solves this with fine-grained account sharing:
- **Shared Accounts:** Explicitly designated as visible to household members (e.g., Joint Rent Account, Household Grocery Account).
- **Private Accounts:** Remain visible only to the owning member. Transactions on private accounts are hidden from other family members unless explicitly allocated to a shared household budget.

### 3.3. Small Business Operational Segregation
- Invoices and payables are visible to authorized staff.
- General ledger accounts and tax reports are restricted to Accountants and Owners.
- Business partner / client contact details are protected against unauthorized export.

---

## 4. User Privacy Rights (DPDP Alignment)

1. **Right to Access & Portability:** Users can generate and export complete JSON/CSV archives of their accounts, transactions, invoices, and audit history.
2. **Right to Correction:** Users can edit transaction descriptions, categories, invoice line items, and merchant aliases at any time.
3. **Right to Erasure ("Right to be Forgotten"):**
   - Personal accounts and workspaces can be marked for deletion (`DELETE /api/v1/workspaces/{id}`).
   - Deletion removes user profile data, unlinks uploaded receipt files from disk, and cascades through non-audited records.
   - Financial audit logs and posted ledger entries retain cryptographic hashes for statutory compliance (under Indian Companies Act requirements for commercial businesses).
4. **Consent Revocation:** Users can revoke Account Aggregator consent or disconnect external bank synchronizations at any time (`POST /api/v1/connections/{id}/revoke`), immediately terminating future synchronization jobs.
