# Master Defect Register and Remediation History

## 1. Defect Governance Framework

This register tracks the complete defect triage and resolution history across all prompt cycles in ARTHSAVORA.

### Severity Classification
- **P0 (Critical)**: Financial calculation discrepancy, unauthorized financial access, cross-tenant leak, severe crash.
- **P1 (Major)**: Major broken workflow, severe authorization failure, deployment failure.
- **P2 (Moderate)**: Degraded non-critical functionality, significant UX issue.
- **P3 (Minor)**: Visual polish, cosmetic warning, future optimization item.

---

## 2. Complete Defect Register

| Defect ID | Severity | Module | Description | Root Cause | Implemented Resolution | Status |
|---|:---:|---|---|---|---|:---:|
| **DEF-01** | P0 | Accounting Core | Risk of IEEE 754 floating-point drift in balance calculations | Binary float representation ($0.10 + 0.20 \neq 0.30$) | Created `Money` value object backed by 64-bit integer paise and `Decimal` | **RESOLVED** |
| **DEF-02** | P0 | Multi-Tenancy | Cross-workspace entity query returning HTTP 403 leaks entity existence | Default authorization handler returned 403 | Enforced Anti-IDOR: cross-workspace entity queries return HTTP 404 (Not Found) | **RESOLVED** |
| **DEF-03** | P0 | Ledger Integrity | Unbalanced journal submissions could enter ledger if not rejected at service layer | Missing pre-commit balance validation | Implemented balance check raising `UnbalancedJournalError` before commit | **RESOLVED** |
| **DEF-04** | P0 | Family Privacy | Family members could view primary user's personal bank accounts | Missing workspace boundary check on personal accounts | Isolated personal workspaces; cross-workspace access returns HTTP 404 | **RESOLVED** |
| **DEF-05** | P1 | Document Upload | Malicious shell script named `receipt.jpg` could bypass extension check | File extension-only validation | Implemented binary magic bytes validation using `python-magic` (`%PDF`, JPEG, PNG) | **RESOLVED** |
| **DEF-06** | P1 | Database Ops | Multiple container instances deploying simultaneously could collide on Alembic migrations | Uncoordinated Alembic runners | Added PostgreSQL session-level advisory lock `pg_advisory_lock(987654321)` in `run_migrations.py` | **RESOLVED** |
| **DEF-07** | P1 | AI Assistant | Adversarial prompt injection instructing assistant to reveal internal prompts or schemas | Unsanitized prompt forwarding | Added `PromptSanitizer` with regex pattern blocking and regulatory disclaimers | **RESOLVED** |
| **DEF-08** | P2 | Frontend Test | Net trial balance aggregation expectation in test asserted sum of gross debits | Netting logic aggregates balances per account before summing | Corrected test assertion to mirror net trial balance accounting principles | **RESOLVED** |
| **DEF-09** | P3 | Repo Hygiene | Obsolete empty 0-byte placeholder files `recommendations.py` and `report_gen.py` | Early scaffolding files superseded by domain services | Removed obsolete files in Prompt 30 | **RESOLVED** |
| **DEF-10** | P3 | Frontend Build | Vite minification warning: `Some chunks are larger than 500 kB` | High number of bundled icons and libraries | Non-blocking (app cached by service worker); code splitting planned for future sprint | **DEFERRED (ACCEPTABLE)** |

---

## 3. Residual Defect Summary

- **Open P0 Defects**: **0**
- **Open P1 Defects**: **0**
- **Open P2 Defects**: **0**
- **Open P3 Observations**: 1 (Non-blocking bundle chunk optimization)
- **Defect Resolution Rate**: **90.0% Resolved / 10.0% Documented Non-Blocking**
