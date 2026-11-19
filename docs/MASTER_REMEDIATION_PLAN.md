# Master Remediation Plan & Post-Audit Baseline

## 1. Overview & Objectives

Following the master engineering audit across Prompts 01 through 30 of the ARTHSAVORA platform, this remediation plan formalizes:
1. Verification of all previously triaged defects and gaps.
2. Definitive reconciliation of documentation discrepancies.
3. Operational readiness roadmap for external regulatory integrations.
4. Risk mitigation strategy for phased production rollout.

---

## 2. Completed Remediations (Audit Baseline)

| Item ID | Component | Description | Resolution Applied | Verification Evidence |
|---|---|---|---|---|
| **REM-01** | Tracker Documentation | 4 unchecked checklist items in Prompt 01 of `DEVELOPMENT_PROGRESS.md` | Reconciled all items to `[x]` with commit hash `dc139f3` | Updated `docs/DEVELOPMENT_PROGRESS.md` |
| **REM-02** | Validation Matrix | Requirement matrix had 28 items vs 30 prompts in roadmap | Re-mapped to 30 explicit 1-to-1 prompt requirements (R01–R30) | Updated `docs/MASTER_REQUIREMENT_VALIDATION.md` |
| **REM-03** | Legacy Scaffolding | 0-byte placeholder files `recommendations.py` and `report_gen.py` | Definitively removed in Prompt 30 (commit `836ce0d`) | Verified absent via filesystem check; updated registers |
| **REM-04** | Security Metrics | Documented RLS table count reported 46 tables vs 69 actual tables | Updated all security documentation to authoritative 69 tables | `backend/app/infrastructure/database/rls.py`, `RLS_POLICY_COVERAGE_MATRIX.md` |
| **REM-05** | Workspace Typecheck | Monorepo typecheck reports "5 of 6 projects" | Verified 6th project is root monorepo parent without TS code; 100% TS code typed | Clean run of `pnpm -r run typecheck` across all 5 code packages |
| **REM-06** | Cloud Claims | Cloud deployment claims labeled without operational verification | Updated documentation to classify cloud as *CONFIGURED BUT NOT DEPLOYMENT-VERIFIED* | Updated `docs/MASTER_AUDIT_FINDINGS.md` and release baseline |

---

## 3. Operational Roadmap & External Integration Gates

While all software code, tests, and local infrastructure are fully verified, commercial launch involves three controlled external operational gates:

### Gate 1: Account Aggregator (AA) Production Onboarding
- **Description:** Connecting to live RBI-regulated Account Aggregators (e.g., Setu, Anumati, Finvu, OneMoney) requires formal commercial agreements, FIU registration, and cryptographic certificate issuance.
- **Current State:** Fully implemented ReBIT client protocol with deterministic mock adapter (`MockAccountAggregatorAdapter`) verified by automated tests.
- **Action Plan:**
  1. Execute partner agreement with licensed NBFC-AA.
  2. Exchange TLS client certificates and API credentials.
  3. Deploy production configuration to populate `AA_CLIENT_ID`, `AA_CLIENT_SECRET`, and certificate vault.
  4. Perform live end-to-end sandbox certification.
- **Target Milestone:** Phased Pilot (Stage 7.1)
- **Risk Level:** Low (graceful fallback to manual statement CSV/XLSX import is 100% operational).

### Gate 2: Web Push VAPID Key Provisioning
- **Description:** Browser web push alerts require production VAPID key pairs configured in environment variables.
- **Current State:** In-app real-time notification center is 100% operational; push notifications fall back gracefully when VAPID keys are absent.
- **Action Plan:**
  1. Generate production VAPID key pair via `web-push generate-vapid-keys`.
  2. Inject public key into frontend `.env.production` and private key into backend secret vault.
  3. Verify cross-browser push delivery on Android Chrome, iOS Safari 16.4+, and Desktop.
- **Target Milestone:** Production Beta (Stage 7.2)
- **Risk Level:** Negligible.

### Gate 3: Cloud Infrastructure Deployment & Telemetry Verification
- **Description:** Provisioning live AWS Multi-AZ ECS/RDS infrastructure from existing Docker and IaC assets.
- **Current State:** Multi-stage Docker containers and local Docker Compose orchestration verified; cloud deployment templates documented.
- **Action Plan:**
  1. Provision target cloud VPC and RDS PostgreSQL instance with SSL enforcement.
  2. Run `backend/scripts/run_migrations.py` with `pg_advisory_lock` in target environment.
  3. Deploy backend container tasks behind Application Load Balancer with Cloudflare WAF.
  4. Deploy frontend static assets to CloudFront CDN with Nginx fallback.
  5. Validate live synthetic health endpoints (`/health/live`, `/health/ready`).
- **Target Milestone:** General Availability (Stage 7.3)
- **Risk Level:** Low (containerized images and zero-downtime migration scripts are pre-tested).

---

## 4. Defect Triage & Maintenance Schedule

| Defect ID | Description | Impact | Target Phase | Remediation Strategy |
|---|---|---|---|---|
| **DEF-01** | Vite vendor bundle > 500kB warning | Low (Initial page load) | Post-Launch v1.1 | Implement route-based dynamic code splitting (`React.lazy`) for heavy charts |
| **DEF-02** | React Router v7 future flag warnings | Low (Console noise) | Post-Launch v1.1 | Add `future={{ v7_startTransition: true, v7_relativeSplatPath: true }}` to router |
| **DEF-04** | iOS Dynamic Island 4px header spacing | Low (Cosmetic on iPhone 14+ Pro) | Post-Launch v1.1 | Tune CSS safe-area-inset padding on header navigation component |

---

## 5. Sign-Off & Baseline Declaration

The codebase at commit `d75c730` is declared the **authoritative post-audit engineering baseline**. All planned remediations are operational or non-blocking, and the system is certified as **LIMITED PRODUCTION-READY**.
