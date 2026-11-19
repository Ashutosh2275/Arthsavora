# Privacy Boundary and Multi-Family Isolation Tests

## 1. Overview and Core Privacy Invariant

In multi-member family workspaces, users frequently share common household expenses (utilities, rent, school fees) while maintaining distinct personal financial lives (salary savings, personal investments, credit cards).

**The Core Privacy Invariant**: An individual's personal workspace accounts must NEVER be visible or accessible to family members unless explicitly designated as a shared family account.

---

## 2. Test Verification (`test_e2e_family_finance_lifecycle_and_privacy_boundary`)

In `test_system_integration_e2e_qa.py`:
1. **User Setup**:
   - `primary_user`: Head of household.
   - `spouse_user`: Family member.
2. **Workspace Setup**:
   - Primary user creates a `FAMILY` workspace `family_ws`.
   - Primary user invites `spouse_user` as a member.
3. **Private Account Creation**:
   - Primary user also possesses their own `PERSONAL` workspace `primary_personal_ws`.
   - Primary user creates a personal high-net-worth savings account in `primary_personal_ws`.
4. **Cross-Tenant & Privacy Probing**:
   - `spouse_user` queries accounts under `family_ws`: Only shared family accounts are returned.
   - `spouse_user` attempts to query `primary_user`'s personal account directly using their spouse session:
     - Request: `GET /api/v1/workspaces/{primary_personal_ws.id}/accounts/{private_account.id}`
     - **Result**: **HTTP 404 Not Found**.
     - Spouse is completely prevented from discovering or accessing the private account.

---

## 3. Masked PII and Redaction Guarantees

In shared family and business views:
- Bank Account Numbers are masked to last 4 digits: `••••••••1234`.
- Aadhaar / PAN numbers are masked: `••••••••567A`.
- Phone numbers in notification displays are masked: `+91 ••••• ••890`.
- All financial exports and AI prompts redact PII tokens prior to transmission.
