# Privacy Release Review and Data Governance

## 1. Overview and Core Privacy Guarantees

In financial management software, privacy is paramount. ARTHSAVORA provides strong technical boundaries ensuring personal financial data is never exposed across family members, business colleagues, or unauthorized third parties.

---

## 2. Key Privacy Invariants Verified

### 2.1 Family Workspace Separation
- **Verified Invariant**: A user's personal accounts are NEVER visible to family members in a shared family workspace.
- **Evidence**: `test_e2e_family_finance_lifecycle_and_privacy_boundary` proved that a spouse attempting to query the primary user's personal high-value savings account receives **HTTP 404 (Not Found)**.

### 2.2 PII Redaction in Logs and Audit Records
- **Verified Invariant**: Aadhaar, PAN, bank account numbers, passwords, and Bearer tokens are scrubbed from structured application logs.
- **Evidence**: `backend/app/core/logging.py` executes automated regex and dictionary key scrubbing prior to emitting JSON log lines.

### 2.3 Consent Management for Account Aggregator
- **Verified Invariant**: External bank connections require explicit user consent with specified purpose codes and validity periods.
- **Evidence**: Consent revocation transitions status to `REVOKED` immediately and halts background sync jobs.

---

## 3. Privacy Boundary Matrix

| Data Classification | Storage Security | Visibility Scope | Redaction / Masking |
|---|---|---|---|
| **Account Numbers** | Encrypted / Plain with RLS | Workspace Members only | Masked to last 4 digits in UI (`••••1234`) |
| **PAN / Tax Identifiers** | AES-256-GCM Encrypted | Workspace Owner only | Masked (`••••567A`) |
| **Transaction Narratives** | Plain with RLS | Workspace Members only | Unaltered in UI; scrubbed in telemetry |
| **Receipt Images** | Local / S3 Private Bucket | Workspace Members only | Pre-signed URLs with 15-minute expiry |
| **User Passwords** | Argon2id Hash | Never readable | Irreversible cryptographic hash |

---

## 4. Privacy Recommendation

The platform satisfies all technical privacy boundaries. **Approved for release.**
