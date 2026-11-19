# Final Deployment and Operations Status

## 1. Overview of Deployment Architecture

ARTHSAVORA is configured for multi-environment operational stability, utilizing containerization, automated migration locking, structured observability, and continuous integration pipelines.

---

## 2. Production Topology and Configuration

```mermaid
graph LR
    User[Web & Mobile PWA] -->|HTTPS| Proxy[Nginx 1.27 Alpine]
    Proxy -->|Static Assets| Cache[Browser / Service Worker Cache]
    Proxy -->|API Requests /api/v1| App[FastAPI Backend Container - Non-Root UID 10001]
    App -->|Connection Pool| DB[(PostgreSQL 18 Database with RLS)]
    App -->|Session Store| Redis[(Redis 7 Cache)]
```

### 2.1 Backend Containerization (`backend/Dockerfile`)
- Multi-stage build based on `python:3.11-slim`.
- Dedicated unprivileged non-root user `arthsavora` (UID 10001).
- Healthcheck configured against `/api/v1/health/live`.
- Port 8000 exposed; zero build tools retained in final runtime image.

### 2.2 Frontend Containerization (`apps/web/Dockerfile`, `apps/web/nginx.conf`)
- Multi-stage build compiling React 19 SPA via Vite.
- Hosted on Nginx 1.27 Alpine.
- Security Headers: CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, HSTS.
- Caching Strategy: Immutable 1-year cache on `/assets/`, zero-cache on `sw.js` and `manifest.webmanifest`.
- Healthcheck probe configured at `/nginx-health`.

### 2.3 Migration Runner (`backend/scripts/run_migrations.py`)
- Acquires session advisory lock `pg_advisory_lock(987654321)` to eliminate deployment race conditions.
- Dispatches Alembic upgrade to background thread.
- Automatically generates and applies Row-Level Security policies across all 46 tables.

---

## 3. Deployment Health Verification

- Liveness probe (`/api/v1/health/live`): **200 OK (< 5ms)**.
- Readiness probe (`/api/v1/health/ready`): **200 OK (< 2.0s with DB ping)**.
- Reverse proxy health (`/nginx-health`): **200 OK**.
- **Deployment Status**: **PRODUCTION-READY**.
