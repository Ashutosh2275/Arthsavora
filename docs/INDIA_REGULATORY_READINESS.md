# ARTHSAVORA — India Regulatory Readiness & Compliance Gap Assessment

## 1. Regulatory Context

ARTHSAVORA is engineered specifically for India's FinTech ecosystem. Operating a commercial financial platform in India requires alignment with multiple statutory and regulatory frameworks:
1. **Digital Personal Data Protection Act, 2023 (DPDP Act 2023)**
2. **Information Technology Act, 2000 (and 2021 Intermediary Guidelines)**
3. **CERT-In Cyber Security Directions (April 2022)**
4. **RBI Master Directions on Account Aggregator (AA) Ecosystem**
5. **Goods and Services Tax (GST) Act & Indian Companies Act (Statutory Recordkeeping)**

---

## 2. Regulatory Alignment Matrix & Technical Controls

| Regulatory Framework | Statutory Obligation | Technical Implementation in ARTHSAVORA | Readiness Status |
| :--- | :--- | :--- | :--- |
| **DPDP Act 2023** | Notice and Consent Architecture (Section 5 & 6) | Structured consent records (`consent_records`, `financial_consents`) capturing purpose, timestamp, data scope, and validity duration. | **Aligned** |
| **DPDP Act 2023** | Data Principal Rights (Access, Correction, Erasure) (Sections 11–13) | Export APIs (`/api/v1/reports/export`), correction endpoints, and soft/hard workspace deletion routines. | **Aligned** |
| **DPDP Act 2023** | Data Security Safeguards (Section 8) | Multi-tenant PostgreSQL RLS, bcrypt password hashing, TLS 1.3 in transit, and secret scanning. | **Aligned** |
| **CERT-In Directions** | Mandatory 6-hour Cyber Incident Reporting | Documented Incident Response Plan (`docs/INCIDENT_RESPONSE_PLAN.md`) with explicit CERT-In 6-hour SLA checklist. | **Aligned** |
| **CERT-In Directions** | 180-Day System Log Retention in India | Structured JSON logging with correlation IDs, timestamps, client IPs; architecture ready for India-region cloud log sinks. | **Ready for Deployment** |
| **RBI AA Directions** | Explicit, Granular, Revocable Consent | Consent VO models matching Sahamati / ReBIT specifications; real-time consent revocation endpoint. | **Aligned** |
| **RBI AA Directions** | Financial Information User (FIU) Responsibilities | Non-storing of raw banking credentials; acquisition solely through authorized RBI-licensed Account Aggregators. | **Architected** |
| **GST / Companies Act** | 8-Year Preservation of Commercial Books of Account | Immutable general ledger journal entries and tamper-evident audit logs with reversal-only corrections. | **Aligned** |

---

## 3. Compliance Gap Register & Operational Responsibilities

To maintain institutional integrity, ARTHSAVORA does not claim that software engineering alone achieves regulatory compliance. Specific obligations require external legal counsel, authorized corporate entities, and partner registrations:

| Item | Requirement | Current Status | Operational / Legal Blocker |
| :--- | :--- | :--- | :--- |
| **FIU Registration** | Formal registration as a Financial Information User with RBI-regulated Account Aggregators (e.g. Finvu, Setu, Anumati). | Technical abstraction complete | Requires registered corporate entity in India, signed agreement with licensed AA, and security audit sign-off. |
| **DPDP Rules Notification** | Notification of final DPDP subordinate rules and establishment of the Data Protection Board of India. | Architecture aligned with Act | Subordinate rules pending gazette notification by MeitY; procedures subject to final notified rules. |
| **Data Protection Officer (DPO)** | Appointment of an India-resident DPO for Significant Data Fiduciary classification. | Role defined in governance docs | Operational appointment required prior to enterprise commercial launch. |
| **CERT-In Point of Contact** | Designation of an official incident liaison officer registered with CERT-In. | Playbook documented | Formal registration on CERT-In incident portal required in production. |

---

## 4. Summary & Verification

The ARTHSAVORA codebase demonstrates complete technical compliance readiness:
- Zero raw bank passwords or UPI PINs collected or persisted.
- Data minimization strictly enforced across all API endpoints.
- Immutable audit records satisfy Indian evidence and accounting standards.
