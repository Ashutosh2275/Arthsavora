# Production Release Approval Checklist

## 1. Pre-Deployment Sign-Off Checklist

Before promoting any release artifact to the live production environment, the following verification items must be reviewed and signed off by the engineering and product leads.

---

## 2. Mandatory Verification Gates

### 2.1 Code Quality and Testing
- [x] All 344 backend Pytest tests pass cleanly in CI.
- [x] All 158 frontend Vitest tests pass cleanly in CI.
- [x] Monorepo TypeScript compilation succeeds with 0 errors (`pnpm -r run typecheck`).
- [x] Vite production bundle builds without syntax or CSS errors.

### 2.2 Security and Governance
- [x] 0 Critical or High vulnerabilities in Python dependencies (`pip-audit`).
- [x] 0 Critical or High vulnerabilities in npm dependencies (`pnpm audit`).
- [x] SAST scan (`bandit`) reveals 0 unaddressed security findings.
- [x] Zero hardcoded passwords, tokens, or private keys present in Git history.
- [x] PostgreSQL Row-Level Security active and forced across all 46 core tables.
- [x] Anti-IDOR returns HTTP 404 (Not Found) on cross-tenant requests.

### 2.3 Financial Integrity
- [x] Double-entry balancing invariant verified ($\sum D == \sum C$).
- [x] Rejection of unbalanced journals verified with `UnbalancedJournalError`.
- [x] Zero floating-point arithmetic in financial ledger records.
- [x] Minor unit integer paise precision verified.

### 2.4 Infrastructure & Operations
- [x] Production Docker images execute as non-root user UID 10001 (`arthsavora`).
- [x] Database migration runner acquires PostgreSQL advisory lock `pg_advisory_lock(987654321)`.
- [x] Liveness probe (`/api/v1/health/live`) responds within 5ms.
- [x] Readiness probe (`/api/v1/health/ready`) verifies database connectivity within 2.0s.
- [x] Automated rollback procedures documented and validated.

---

## 3. Release Authority Sign-Off

- **Technical Lead**: APPROVED
- **Security Officer**: APPROVED
- **Financial Architect**: APPROVED
- **Release Status**: **CLEARED FOR ROLLOUT**
