# Known Product Limitations and Operational Boundaries

## 1. Scope of Limitations

This document provides transparent disclosure regarding capabilities that are intentionally limited, pending external regulatory agreements, or constrained by current architectural boundaries.

---

## 2. Identified Functional Limitations

| Area | Limitation Description | Underlying Cause | User Experience & Workaround |
|---|---|---|---|
| **Account Aggregator Sync** | Live bank automated synchronization is simulated using synthetic sandbox adapters. | Live connection requires RBI-licensed NBFC-AA contract and production digital certificates. | Users can manually create accounts and import bank statements via the CSV/Excel import pipeline. |
| **Direct Payment Execution** | ARTHSAVORA does not directly initiate or execute NEFT/RTGS/UPI transfers. | Direct bank payment debit requires Payment Aggregator (PA) or banking API license. | Users manage internal records; payment handoff links provided for external banking apps. |
| **Government Tax Filing** | The platform does not automatically submit ITR-1/2 or GSTR-1/3B to government portals. | Government filing requires authorized GSP (GST Suvidha Provider) or ERI (e-Return Intermediary) license. | The system generates fully structured computation statements for filing via tax portals or Chartered Accountants. |
| **Offline Ledger Writes** | Financial transactions cannot be posted to the double-entry general ledger while offline. | Offline concurrent posting introduces irreconcilable double-entry race conditions and negative balances. | Read-only access to cached statements is permitted offline; receipt drafts are staged for upload on reconnection. |
| **Live Web Push** | External browser push notifications are inactive when running without production VAPID keys. | Requires configured Web Push server credentials. | In-app notification center remains fully functional for real-time alerts. |

---

## 3. Product Roadmap Timeline for Limitations

1. **Phase 1 (Beta)**: Manual account management, CSV imports, invoicing, ledger, and tax computation.
2. **Phase 2 (Post-Beta)**: Formal NBFC-AA onboarding for automated bank data synchronization.
3. **Phase 3 (Enterprise)**: GSP API integration for direct one-click GST return validation.
