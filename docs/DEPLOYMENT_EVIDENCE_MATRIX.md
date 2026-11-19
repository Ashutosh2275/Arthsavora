# Deployment Evidence Matrix

## 1. Overview

This matrix inventories every deployable component within the ARTHSAVORA ecosystem, detailing containerization standards, configuration contracts, runtime limits, and deployment verification status.

---

## 2. Component Deployment Inventory

| Component | Packaging Artifact | Runtime / Base Image | Port | Healthcheck | Scaling Model | Verification Status |
|---|---|---|---|---|---|:---:|
| **API Backend** | `backend/Dockerfile` | `python:3.11-slim` (non-root UID 10001) | 8000 | `GET /api/v1/health/live` | Horizontal (Stateless) | **VERIFIED (Docker/CI)** |
| **Web Frontend** | `apps/web/Dockerfile` | `nginx:1.27-alpine` (hardened SPA config) | 80 / 443 | `GET /health` | Horizontal (Static Edge / CDN) | **VERIFIED (Docker/CI)** |
| **Database** | Docker Hub Official | `postgres:18-alpine` | 5432 / 5433 | `pg_isready -U arthsavora` | Single Master + Multi-AZ Standby | **VERIFIED (Local/CI)** |
| **Cache & Broker** | Docker Hub Official | `redis:7-alpine` | 6379 | `redis-cli ping` | In-memory cluster | **VERIFIED (Local/CI)** |
| **Migration Runner**| `backend/scripts/run_migrations.py` | Python 3.11 CLI | N/A | Exits 0 on success; advisory lock | Ephemeral Pre-Deploy Task | **VERIFIED (Local/CI)** |
| **Document Storage**| Local volume / AWS S3 | POSIX filesystem / S3 API | N/A | Read/Write probe on init | Object Store | **VERIFIED (POSIX) / CONFIGURED (S3)** |

---

## 3. Configuration Contract & Environment Variables

| Variable Name | Purpose | Target Environment | Secret Management |
|---|---|---|---|
| `ENVIRONMENT` | Runtime mode (`development`, `staging`, `production`) | All | Container ENV |
| `DATABASE_URL` | Async PostgreSQL connection string | Backend, Migrations | Cloud Secret Vault / Env |
| `REDIS_URL` | Redis cache and token blacklist URI | Backend | Cloud Secret Vault / Env |
| `SECRET_KEY` | HMAC secret for JWT token issuance | Backend | Cloud Secret Vault / Env |
| `ALGORITHM` | JWT signing algorithm (`HS256`) | Backend | Container ENV |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (15 minutes) | Backend | Container ENV |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Sliding session lifetime (7 days) | Backend | Container ENV |
| `VITE_API_URL` | Backend API base URL for web client | Frontend (Build-time) | Vite `.env` / Build ARG |
| `VAPID_PUBLIC_KEY` | Public key for browser Web Push | Frontend (Build-time) | Vite `.env` / Build ARG |
| `VAPID_PRIVATE_KEY`| Private key for Web Push delivery | Backend | Cloud Secret Vault / Env |
| `AA_CLIENT_ID` | RBI Account Aggregator Client ID | Backend | Cloud Secret Vault (Post-Onboarding) |
| `AA_CLIENT_SECRET` | RBI Account Aggregator Client Secret | Backend | Cloud Secret Vault (Post-Onboarding) |

---

## 4. Rollback and Disaster Recovery Procedures

1. **Database Rollback:**
   - Down migrations available via Alembic: `alembic downgrade -1`.
   - Pre-deployment point-in-time database snapshot required before running production migrations.
2. **Container Rollback:**
   - Container images tagged with immutable Git SHA (e.g., `arthsavora-backend:d75c730`).
   - Rollback executes by repointing orchestrator task definition to the previous stable Git SHA tag.
3. **Frontend Rollback:**
   - Previous compiled distribution folder restored or CDN cache invalidated to point to prior release artifact.
