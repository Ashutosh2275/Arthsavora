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
| **DEF-11** | P1 | Document OCR | `ModuleNotFoundError: No module named 'pypdf'` in `pdf_text_extractor.py` | Missing dependency declaration in `requirements.txt` | Installed `pypdf==7.1.1`, added `pypdf>=5.0.0` to requirements, added `pdfplumber` fallback | **RESOLVED** |
| **DEF-12** | P0 | Multi-Tenancy / RLS | Table `accounts` had `relrowsecurity=False` in PostgreSQL catalog | RLS was forced but not explicitly enabled on table | Ran `ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;` and provisioned `arthsavora_app` non-superuser role | **RESOLVED** |
| **DEF-13** | P2 | QA Documentation | Discrepancy in reported backend test suite counts (344 passed / 1 skipped vs 344 passed / 0 skipped) | Category P operational dependency block mistakenly transcribed into unit test summary | Validated exact empirical collection (344 items, 344 passed, 0 skipped) and reconciled audit reports | **RESOLVED** |
| **DEF-14** | P3 | Frontend Code Quality | ESLint build failure due to `public/sw.js` global and redundant try/catch in `useCategoryStore.ts` | Missing ignore rule and unnecessary catch-throw wrapper | Configured ESLint ignore for `public/` and simplified store method | **RESOLVED** |
| **DEF-15** | P2 | Release Certification | Discrepancy between reported route counts (17 pages vs 19 table rows vs 33 router declarations) and unclarified single-thread microbenchmark context | Early specification aggregation grouped sub-routes and conflated single-client microbenchmarks with cloud concurrent load | Enumerate all 33 routes (1 public, 20 pages, 10 aliases, 2 redirects); verify all 32 path targets in Playwright (0 crashes); publish route reconciliation and benchmark context reports | **RESOLVED** |

---

## 3. Residual Defect Summary

- **Open P0 Defects**: **0**
- **Open P1 Defects**: **0**
- **Open P2 Defects**: **0**
- **Open P3 Observations**: 1 (Non-blocking bundle chunk optimization)
- **Defect Resolution Rate**: **93.3% Resolved (14/15) / 6.7% Documented Non-Blocking (1/15)**
