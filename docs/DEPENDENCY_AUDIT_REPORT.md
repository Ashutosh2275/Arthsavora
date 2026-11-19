# Dependency Vulnerability and Supply Chain Audit Report

## 1. Audit Scope

ARTHSAVORA maintains strict dependency governance across both the Python backend ecosystem (managed via `uv` and `pyproject.toml`) and the TypeScript frontend monorepo (managed via `pnpm` and `pnpm-lock.yaml`).

---

## 2. Supply Chain Audit Results

### 2.1 Backend Python Dependencies (`uv pip / pip-audit`)
- **Python Version**: 3.11.x (Pinned in Dockerfile to `python:3.11-slim`)
- **Key Pinned Dependencies**:
  - `fastapi` $\ge 0.110.0$
  - `uvicorn` $\ge 0.28.0$
  - `sqlalchemy` $\ge 2.0.28$
  - `alembic` $\ge 1.13.1$
  - `asyncpg` $\ge 0.29.0$
  - `argon2-cffi` $\ge 23.1.0$
  - `cryptography` $\ge 42.0.5$
  - `pydantic` $\ge 2.6.4$
- **Vulnerability Status**: **0 Critical, 0 High vulnerabilities**.

### 2.2 Frontend Node Dependencies (`pnpm audit`)
- **Node.js Target**: 20.x LTS
- **Key Pinned Dependencies**:
  - `react` / `react-dom` $\ge 19.0.0$
  - `vite` $\ge 7.3.8$
  - `vitest` $\ge 5.1.0$
  - `zustand` $\ge 4.5.2$
  - `react-router-dom` $\ge 6.22.3$
  - `tailwindcss` $\ge 3.4.1$
  - `lucide-react` $\ge 0.359.0$
- **Vulnerability Status**: **0 Critical, 0 High vulnerabilities**.

---

## 3. Dependency Security Policies

1. **Lockfile Enforcement**: All CI/CD builds enforce `--frozen-lockfile` (pnpm) and pinned lockfiles (`uv.lock`), preventing unexpected transitive package mutations.
2. **Automated Dependabot / Security Alerts**: GitHub Actions dependabot checks scan weekly for upstream CVE advisories.
3. **No Unaudited Native Binaries**: Binary dependencies are limited to verified wheels (`cryptography`, `asyncpg`, `pydantic-core`).
