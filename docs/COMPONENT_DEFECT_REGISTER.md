# Component Defect Register & Remediation Log [Post-Audit QA]

## 1. Defect Governance Framework

This register tracks all observations, issues, and minor defects evaluated during the post-audit comprehensive testing phase.

### Severity Classification
- **P0 (Critical / Blocker):** Financial discrepancy, ledger corruption, unauthorized cross-tenant leak, application crash.
- **P1 (Major):** Broken core workflow, severe authorization failure, build/deployment failure.
- **P2 (Moderate):** Degraded secondary functionality, missing fallback, minor test discrepancy.
- **P3 (Minor / Polish):** Console warning, cosmetic styling issue, bundle size optimization.

---

## 2. Tracked Defect & Remediation Log

| Defect ID | Severity | Component | Summary & Observation | Root Cause | Implemented Resolution | Status |
|---|:---:|---|---|---|---|:---:|
| **DEF-QA-01** | P1 | Document Extraction | `PdfTextExtractor` failed on import of `pypdf` when only `pdfplumber` was present in venv | Explicit un-fallback import `from pypdf import PdfReader` | Installed `pypdf==7.1.1`, added to `requirements.txt`, and implemented dynamic fallback to `pdfplumber` in `pdf_text_extractor.py` | **RESOLVED** |
| **DEF-QA-02** | P2 | Benchmark Harness | Empirical benchmark script threw `TypeError` on `Account` balance attribute | Column named `current_book_balance_paise` and `opening_balance_paise` rather than generic `balance` | Corrected benchmark initialization to use authoritative minor unit column names | **RESOLVED** |
| **DEF-QA-03** | P2 | Benchmark Harness | Empirical benchmark failed on `workspaces` table not-null constraints (`slug`, `owner_id`) | Script instantiated transient `Workspace` without linking a real `User` | Added `User` creation fixture and unique slug generator | **RESOLVED** |
| **DEF-QA-04** | P2 | Benchmark Harness | Empirical benchmark threw `KeyError: 'entry_type'` on journal line creation | Journal line schema requires `entry_type` (`debit`/`credit`) rather than `direction` | Updated benchmark line dictionaries to pass `entry_type` key | **RESOLVED** |
| **DEF-QA-05** | P3 | Frontend Build | Vite minification warning: `Some chunks are larger than 500 kB` | Vendor libraries bundled into single asset chunk | Non-blocking. Service worker precaches bundle; route-level dynamic imports scheduled for post-launch v1.1 | **OPEN (NON-BLOCKING)** |
| **DEF-QA-06** | P3 | Test Environment | React Router future flag deprecation warnings in test console | React Router v6 warning about opt-in v7 flags | Non-breaking. Flags scheduled for adoption during router version upgrade | **OPEN (NON-BLOCKING)** |
| **DEF-QA-07** | P3 | Accessibility | Real-browser Axe-core audit flagged minor contrast on `.text-slate-500` and heading order | Muted text color token on dark background; h2 to h4 jump in marketing banner | Non-blocking cosmetic items scheduled for UI theme refinement sprint | **OPEN (NON-BLOCKING)** |

---

## 3. Defect Metrics Summary

- **Total Tracked Defects/Observations:** 7
- **Resolved Defects (P1/P2):** **4** (100% of functional & harness defects resolved and re-verified)
- **Open Critical / P0 Blockers:** **0**
- **Open Major / P1 Blockers:** **0**
- **Open Moderate / P2 Issues:** **0**
- **Open Minor / P3 Observations:** **3** (All documented, non-blocking cosmetic/optimization items)

---

## 4. Release Blocker Assessment

**RELEASE BLOCKER COUNT: 0**
No functional, mathematical, security, or deployment blockers remain. The codebase satisfies all release stability criteria.
