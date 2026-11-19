# End-to-End Test Standard

## 1. Purpose and Scope

The ARTHSAVORA End-to-End (E2E) Test Standard defines the design patterns, coding practices, and assertion protocols for authoring realistic multi-step user journey tests. E2E tests validate complete business journeys through public API endpoints, simulating authentic user sessions, multi-entity relationships, and commercial operations.

---

## 2. Standard Authoring Rules

### Rule 1: Multi-Step Business Workflows
E2E tests must never test isolated functions in isolation; they must exercise cohesive user lifecycles:
- **Registration & Setup**: User registration -> Workspace provisioning -> Chart of accounts generation.
- **Financial Activity**: Account creation -> Inflow/Outflow posting -> Ledger verification -> Trial balance reconciliation.
- **Reporting & Closure**: Statement generation -> Tax estimation -> Compliance audit logging.

### Rule 2: Explicit Monetary Assertions in Paise
Assertions on monetary fields must assert exact minor unit integers (`paise`) or exact `Decimal` strings:
```python
# CORRECT
assert response.json()["current_balance_paise"] == 7050000
assert trial_balance["total_debits"] == Decimal("75000.0000")

# FORBIDDEN (Floating-point comparison)
assert response.json()["balance"] == 70500.00  # FORBIDDEN
```

### Rule 3: Anti-IDOR Security Validation in Every Journey
Every multi-user journey must include negative authorization assertions:
```python
# Attempt cross-workspace retrieval
res = client.get(f"/api/v1/workspaces/{other_ws_id}/accounts/{account_id}", headers=user_headers)
assert res.status_code == 404, "Cross-workspace access must return 404 Not Found, never 403"
```

### Rule 4: Indian FinTech Compliance Rules
E2E tests must explicitly validate Indian fiscal conventions:
- Financial year boundaries: April 1 to March 31.
- Indian numbering format: ₹1,00,000 (Lakhs and Crores).
- GST dual-component taxation: CGST (Central) + SGST (State) for intra-state, IGST for inter-state.
- Income tax regimes: Section 115BAC new tax regime slabs and Section 87A rebate limits.

---

## 3. Directory Layout and Conventions

All system integration and E2E tests reside under `backend/tests/`:
- `test_system_integration_e2e_qa.py`: Master E2E journey suite (Personal, Family, Business, Indian Tax, Anti-IDOR, Leap Year Recurrence, Magic Bytes).
- `test_production_operational_readiness.py`: Infrastructure, Dockerfile, Nginx, advisory migration lock tests.
- `test_security_hardening.py`: Authentication, session revocation, token rotators, RLS audits.
