# ARTHSAVORA — Release Management and Versioning Policy

## 1. Semantic Versioning Specification

ARTHSAVORA adheres to **Semantic Versioning 2.0.0 (SemVer)**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Incompatible API changes, major architectural changes, breaking schema modifications requiring database migration windows.
- **MINOR**: Backward-compatible new features (e.g. Account Aggregator provider addition, new financial report type).
- **PATCH**: Backward-compatible bug fixes, security patches, performance optimizations.

## 2. Release Cadence & Lifecycle

```
Feature Branch (feat/*) 
       |
       v (PR & CI pass)
Develop Branch (`develop`) 
       |
       v (Merge & Staging verification)
Main Branch (`main`)
       |
       v (Tag: v1.2.0 & Production Approval Gate)
Production Deployment (`app.arthsavora.com`)
```

- **Standard Releases**: Bi-weekly scheduled release windows (Tuesdays at 11:00 AM IST to maximize engineering coverage during Indian banking operating hours).
- **Security Hotfixes**: Out-of-band immediate release triggered by vulnerability severity `HIGH` or `CRITICAL`.
- **Change Freeze Windows**:
  - Month-end financial reporting days (last day of calendar month).
  - Indian Financial Year-End (March 28 – April 3).
  - Indian Banking settlement holidays (major national holidays).

## 3. Release Checklist & Evidence Pack

Before promoting any tag to production, the Release Manager must ensure:
1. `ci.yml` is passing on `main` for the targeted commit.
2. All 334 backend tests and 158 frontend tests are green.
3. TypeScript validation passes with 0 errors across all monorepo packages.
4. Database migrations are verified to be backward-compatible (Expand/Contract pattern).
5. Staging smoke testing confirms:
   - User authentication and token refresh.
   - Bank transaction ingestion and double-entry ledger balance.
   - PWA service worker caching and offline fallback.
   - Gemini AI assistant query responsiveness.
6. Production Security Release Gate is signed off ([PRODUCTION_SECURITY_RELEASE_GATE.md](file:///d:/Arthsavora/docs/PRODUCTION_SECURITY_RELEASE_GATE.md)).

## 4. Cross-Reference Links
- CI/CD Architecture: [CI_CD_ARCHITECTURE.md](file:///d:/Arthsavora/docs/CI_CD_ARCHITECTURE.md)
- Deployment Pipeline: [DEPLOYMENT_PIPELINE.md](file:///d:/Arthsavora/docs/DEPLOYMENT_PIPELINE.md)
- Deployment Rollback: [DEPLOYMENT_ROLLBACK.md](file:///d:/Arthsavora/docs/DEPLOYMENT_ROLLBACK.md)
