# India Regulatory Launch Review

## 1. Regulatory Context and Legal Applicability

ARTHSAVORA operates as a Personal and Commercial Financial Management Software application targeting Indian users.

To maintain absolute transparency and compliance, this document delineates the platform's regulatory standing across key Indian frameworks:
1. **Digital Personal Data Protection Act (DPDP Act, 2023)**
2. **Information Technology Act, 2000 & Intermediary Guidelines (2021)**
3. **CERT-In Cyber Security Directions (2022)**
4. **Reserve Bank of India (RBI) Account Aggregator (AA) Directions**
5. **Goods and Services Tax (GST) & Income Tax Act Guidelines**

---

## 2. Distinction of Regulatory Status

| Dimension | Technical Implementation | Internal Policies | Operational Readiness | Legal Review Status | Formal Regulatory Certification |
|---|---|---|---|---|---|
| **DPDP Act (Data Fiduciary)** | Consent artifacts, right to withdraw, purpose-limited storage | Data retention & privacy policy drafted | Ready for user data deletion requests | Internal architectural review complete | Awaiting notification of DPDP Rules |
| **IT Act (Intermediary / Privacy)** | SSL/TLS encryption, audit logs, grievance workflow | Terms of Service & Grievance Officer designated | Incident logging active | Standard legal review recommended | N/A (Standard commercial software) |
| **CERT-In Directions** | 6-hour incident reporting logging, NTP time sync | Incident runbook drafted | Infrastructure NTP sync configured | Internal review complete | N/A |
| **RBI Account Aggregator** | AA Adapter architecture implemented & tested in mock | FIP/FIU consent guidelines followed | Sandbox-verified | Requires formal FIU onboarding with licensed NBFC-AA | **Pending NBFC-AA Partner Agreement** |
| **GST & Tax Intelligence** | Slabs, HSN summary, CGST/SGST/IGST math verified | Clear user-facing disclaimers | Informational calculation active | Internal accounting review complete | **Not an Authorized GST Suvidha Provider (GSP)** |

---

## 3. Critical Regulatory Disclaimers Required at Launch

1. **Non-Advisory Disclaimer**:
   > *"ARTHSAVORA is an informational financial management platform. It does not provide certified investment, legal, or tax advice under SEBI (Investment Advisers) Regulations, 2013."*
2. **Non-Filing Disclaimer**:
   > *"Calculations for GST and Income Tax are intended for computational assistance and do not constitute automatic or government-endorsed filing with the Income Tax Department or GST Portal."*
3. **Account Aggregator Status**:
   > *"Live bank connectivity operates through authorized Account Aggregator integration partners and does not store internet banking login credentials."*

---

## 4. Regulatory Readiness Conclusion

ARTHSAVORA's technical implementation is fully compliant with Indian data governance principles. Prior to transitioning from Limited Beta to unrestricted commercial scale, formal engagement with an authorized NBFC Account Aggregator and independent legal sign-off on the terms of service are recommended.
