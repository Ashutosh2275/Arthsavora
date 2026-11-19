# Quality Assurance CI/CD Automation and Test Gates

## 1. Overview of Automated Pipeline

The ARTHSAVORA continuous integration and deployment pipeline (`.github/workflows/ci.yml` and `.github/workflows/deploy.yml`) incorporates automated quality gates that execute on every pull request and push to `main`.

```mermaid
flowchart LR
    Push[Git Push / PR] --> LINT[Monorepo Typecheck & Lint]
    LINT --> TEST_FE[Frontend Vitest Suite (158 Tests)]
    LINT --> TEST_BE[Backend Pytest Suite (344 Tests)]
    TEST_FE --> BUILD[Vite Production Bundle Build]
    TEST_BE --> BUILD
    BUILD --> GATE{All Tests & Checks Green?}
    GATE -->|Yes| STAGING[Staging Docker Build & Deploy]
    GATE -->|No| FAIL[Block PR / Halt Pipeline]
```

---

## 2. CI Quality Gate Specifications

| CI Step | Command Executed | Enforcement Criteria | Failure Action |
|---|---|---|---|
| **TypeScript Typecheck** | `pnpm -r run typecheck` | 0 errors across all 5 workspace packages | Immediate pipeline termination |
| **Frontend Test Suite** | `pnpm --filter @arthsavora/web test -- --run` | 158 tests passing (100%) | Immediate pipeline termination |
| **Frontend Production Build** | `pnpm --filter @arthsavora/web build` | Clean bundle generation without syntax or CSS errors | Immediate pipeline termination |
| **Backend Test Suite** | `uv run pytest backend/tests -v` | 344 tests passing (100%) | Immediate pipeline termination |
| **Security Dependency Audit** | `pnpm audit` & `pip-audit` | 0 Critical, 0 High vulnerabilities | Security team alert |
| **Docker Build Preflight** | `docker build -t arthsavora-backend backend/` | Multi-stage build succeeds; non-root user verified | Halt release |

---

## 3. Local Pre-Commit Enforcement

Developers can run the complete preflight check locally with a single script:
```bash
# Full local verification
pnpm -r run typecheck && pnpm --filter @arthsavora/web test -- --run && uv run pytest backend/tests -q
```
All commands execute in under 2 minutes locally.
