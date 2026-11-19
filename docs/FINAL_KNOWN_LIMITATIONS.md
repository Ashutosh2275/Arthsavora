# Final Known Limitations and External Boundaries

## 1. Scope and Transparency

This document provides transparent, authoritative disclosure regarding the functional and operational boundaries of ARTHSAVORA at release time.

---

## 2. Categorization of Operational Limitations

### 2.1 External Institutional Dependencies
1. **Account Aggregator Automated Sync**:
   - *Status*: **SANDBOX-VERIFIED**.
   - *Boundary*: The adapter, consent lifecycle, and ingestion engines are implemented and verified against synthetic bank data. Live bank account synchronization requires a commercial Data Access Agreement with a licensed NBFC Account Aggregator (e.g. Setu, Finvu).
   - *Workaround*: Manual bank account creation and the CSV/Excel statement import pipeline support all major Indian banks.
2. **Payment Execution**:
   - *Status*: **NOT APPLICABLE BY DESIGN**.
   - *Boundary*: ARTHSAVORA does not hold customer funds or execute NEFT/RTGS/UPI debits directly. Invoice payment links provide external handoff to banking or UPI apps.

### 2.2 Statutory and Regulatory Scope
1. **Non-Advisory Standing**:
   - *Status*: **COMPLIANT VIA MANDATORY DISCLAIMER**.
   - *Boundary*: The platform provides informational summaries and does not constitute certified financial or investment advisory under SEBI regulations.
2. **Non-Filing Standing**:
   - *Status*: **COMPLIANT VIA MANDATORY DISCLAIMER**.
   - *Boundary*: GST summaries and Section 115BAC tax calculations provide computational assistance. The platform does not submit filings directly to government portals.

### 2.3 Technical and Network Boundaries
1. **Offline Ledger Mutations**:
   - *Status*: **READ-SAFE OFFLINE ENFORCED**.
   - *Boundary*: Financial transactions cannot be posted to the double-entry general ledger while offline. Cached balances and statements remain readable; receipt photo drafts are queued for upload on reconnection.
2. **Web Push Notification Credentials**:
   - *Status*: **IN-APP ACTIVE / BROWSER PUSH STAGED**.
   - *Boundary*: Local development environments without VAPID credentials rely on the in-app Notification Center.

---

## 3. Summary of Release Impact

None of the above boundaries impede the platform's core personal, family, or small business financial management capabilities. The application is fully prepared for its intended Limited Beta and phased public rollout.
