# Quality Assurance Defect Register (Non-Blocking Triage)

## 1. Overview

This register tracks minor observations, non-blocking cosmetic items, and scheduled post-launch optimizations identified during Prompt 29 integration and end-to-end testing. None of these items impact financial accuracy, tenant isolation, or deployment stability.

---

## 2. Tracked Non-Blocking Items

| Defect ID | Severity | Component | Description | Workaround / Mitigation | Target Milestone |
|---|---|---|---|---|---|
| **DEF-01** | Low | Frontend Web | Vite bundle build produces warning: `Some chunks are larger than 500 kB after minification`. | App loads swiftly; code-splitting with dynamic `React.lazy` imports can further optimize initial chunk size. | Prompt 30 Packaging |
| **DEF-02** | Low | Vitest Console | React Router v6 warns about future v7 flags (`v7_startTransition`, `v7_relativeSplatPath`). | Non-breaking deprecation warning; early opt-in flag can be added to router config. | Post-Release Minor |
| **DEF-03** | Low | Legacy File | Empty 0-byte files `backend/app/services/recommendations.py` and `backend/app/services/report_gen.py`. | Definitively deleted in Prompt 30 (commit `836ce0d`). Verified absent from repository. | Resolved (Prompt 30) |
| **DEF-04** | Low | Accessibility | Small screens with dynamic island may require 4px additional top margin on custom headers. | Covered by safe area inset classes; can be fine-tuned on physical device lab testing. | Post-Release Minor |

---

## 3. Defect Summary

- **Critical**: 0
- **High**: 0
- **Medium**: 0
- **Low**: 3 open (all non-blocking, documented with clear remediation paths); 1 resolved (DEF-03 removed in Prompt 30)
