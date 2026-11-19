# ARTHSAVORA — Deployment Pipeline and Execution Protocol

## 1. Pipeline Stages

The deployment pipeline automates the progression of verified code from version control to production hosting.

```
+------------+     +------------+     +------------+     +------------+     +------------+
|  STAGE 1   |     |  STAGE 2   |     |  STAGE 3   |     |  STAGE 4   |     |  STAGE 5   |
| Preflight  | --> | Pre-Deploy | --> | Zero-Lock  | --> | Rolling    | --> | Edge Purge |
| Metadata & |     | Database   |     | Migration  |     | Container  |     | & Post-Dep |
| Validation |     | Snapshot   |     | Runner     |     | Deployment |     | Probing    |
+------------+     +------------+     +------------+     +------------+     +------------+
```

## 2. Detailed Execution Steps

### Stage 1: Preflight Metadata & Configuration Validation
- Extracts commit SHA (8 characters) or semantic version tag (e.g., `v1.2.0`).
- Validates production configuration rules using `backend/app/core/config.py`.
- Rejects deployment if `SECRET_KEY` is insecure, `DEBUG=True`, or CORS is misconfigured.

### Stage 2: Automated Pre-Deployment Database Snapshot
- Triggers AWS RDS snapshot or Neon/Supabase Point-in-Time Recovery (PITR) checkpoint:
  ```bash
  aws rds create-db-snapshot \
    --db-instance-identifier arthsavora-prod-db \
    --db-snapshot-identifier pre-deploy-v1-2-0
  ```
- Ensures Point-in-Time Recovery capability before applying schema changes.

### Stage 3: Zero-Downtime Database Migration Runner
- Executes `backend/scripts/run_migrations.py`.
- Acquires exclusive session-level advisory lock `pg_advisory_lock(987654321)` to prevent concurrent migration runs in multi-instance clusters.
- Runs Alembic migrations to `head` in an isolated background thread.
- Automatically re-synchronizes Row-Level Security (`ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`) across all 46 workspace-scoped tables via `generate_rls_sql()`.
- Releases the advisory lock cleanly upon completion.

### Stage 4: Rolling Backend & Frontend Deployment
- **Backend**:
  - Updates ECS Task Definition with new container image tag.
  - Deploys with `minimumHealthyPercent = 100` and `maximumPercent = 200`.
  - Ensures new containers pass container-level healthcheck (`/api/v1/health/live`) before traffic routing shifts.
  - Old containers are drained and gracefully stopped after 30 seconds.
- **Frontend**:
  - Pushes newly compiled Vite assets (`dist/assets/*`) with 1-year immutable cache headers to edge CDN.
  - Deploys new `index.html` and `sw.js` with `Cache-Control: no-cache, no-store, must-revalidate`.

### Stage 5: Edge Invalidation & Post-Deployment Synthetic Probes
- Invalidates edge CDN cache for root HTML document and service worker:
  ```bash
  curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
       -H "Authorization: Bearer $CF_API_TOKEN" \
       -d '{"files":["https://app.arthsavora.com/index.html", "https://app.arthsavora.com/sw.js"]}'
  ```
- Executes synthetic HTTP probes against production:
  - `GET https://api.arthsavora.com/api/v1/health/live` -> Expects HTTP 200 within 500ms.
  - `GET https://api.arthsavora.com/api/v1/health/ready` -> Expects HTTP 200 with `"database": "connected"`.
- If post-deployment checks fail within 120 seconds, automated rollback is triggered.

## 3. Cross-Reference Links
- CI/CD Architecture: [CI_CD_ARCHITECTURE.md](file:///d:/Arthsavora/docs/CI_CD_ARCHITECTURE.md)
- Deployment Rollback: [DEPLOYMENT_ROLLBACK.md](file:///d:/Arthsavora/docs/DEPLOYMENT_ROLLBACK.md)
- Database Migration Operations: [DATABASE_MIGRATION_OPERATIONS.md](file:///d:/Arthsavora/docs/DATABASE_MIGRATION_OPERATIONS.md)
