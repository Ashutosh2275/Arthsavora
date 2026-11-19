# ARTHSAVORA — CI/CD Pipeline Architecture

## 1. Principles of Automated Delivery

The ARTHSAVORA Continuous Integration & Continuous Delivery (CI/CD) system enforces automated quality gates, security audits, database migration safety, and zero-downtime releases.

```
+---------------------------------------------------------------------------------------------------+
|                                  CONTINUOUS INTEGRATION (ci.yml)                                  |
+---------------------+---------------------+---------------------+---------------------------------+
|   SECURITY AUDIT    |   BACKEND CHECKS    |   FRONTEND CHECKS   |      CONTAINER BUILD PREFLIGHT   |
| - pnpm audit (prod) | - Python 3.11 env   | - pnpm 12 workspace | - Multi-stage Backend Dockerfile |
| - Bandit SAST scan  | - Postgres 18 srv   | - Monorepo typecheck| - Multi-stage Web Nginx build    |
| - Credential check  | - Redis 7 srv       | - ESLint rules      | - Image layer caching            |
|                     | - Alembic run check | - Vitest test suite | - Architecture linux/amd64       |
|                     | - Pytest + coverage | - Vite prod build   |                                  |
+---------------------+---------------------+---------------------+---------------------------------+
                                                     |
                                   All Gates Green & Tag Created
                                                     v
+---------------------------------------------------------------------------------------------------+
|                                 CONTINUOUS DEPLOYMENT (deploy.yml)                                |
+---------------------+---------------------+---------------------+---------------------------------+
| PRE-FLIGHT & TAGS   | DATABASE MIGRATION  | BLUE-GREEN DEPLOY   | EDGE INVALIDATION & VERIFY      |
| - Commit SHA / Tag  | - RDS auto snapshot | - Rolling container | - Purge index.html / sw.js      |
| - Target Env eval   | - pg_advisory_lock  |   task replacement  | - Probe /health/live            |
| - Config validation | - Alembic upgrade   | - Zero connection   | - Probe /health/ready           |
|                     | - RLS re-sync check |   drop (min 100%)   | - Auto-rollback on fail         |
+---------------------+---------------------+---------------------+---------------------------------+
```

## 2. GitHub Actions Workflow Structure

The repository maintains two primary workflows:

1. [ci.yml](file:///d:/Arthsavora/.github/workflows/ci.yml):
   - **Trigger**: Every push and pull request to `main` and `develop`.
   - **Concurrency**: Cancels in-progress duplicate runs per branch.
   - **Parallel Jobs**:
     - `security-audit`: Dependency vulnerability scanning and static security analysis.
     - `backend-checks`: Automated Alembic schema migration and 334+ unit/integration tests running against live PostgreSQL 18 and Redis 7 service containers.
     - `frontend-checks`: TypeScript validation across all monorepo packages, ESLint, 158 Vitest unit/component tests, and production Vite compilation.
     - `container-build-checks`: Verifies container builds for both backend and web images.

2. [deploy.yml](file:///d:/Arthsavora/.github/workflows/deploy.yml):
   - **Trigger**: Git tags matching `v*.*.*` or manual `workflow_dispatch`.
   - **Concurrency**: Queue sequential deployments without cancellation to prevent race conditions.
   - **Environments**: Explicit GitHub environments (`staging` and `production`) with required manual reviewer approvals for production.

## 3. Quality & Security Gates

A deployment will be blocked automatically if:
1. Any backend or frontend test fails.
2. Any TypeScript type error exists across the monorepo.
3. Vulnerabilities of `high` or `critical` severity are detected in dependencies.
4. Database migrations fail to apply or create lock contention.
5. Production configuration fails strict validation (e.g. weak secret key, wildcard CORS, DEBUG=True).

## 4. Cross-Reference Links
- Deployment Pipeline: [DEPLOYMENT_PIPELINE.md](file:///d:/Arthsavora/docs/DEPLOYMENT_PIPELINE.md)
- Release Management: [RELEASE_MANAGEMENT.md](file:///d:/Arthsavora/docs/RELEASE_MANAGEMENT.md)
- Deployment Rollback: [DEPLOYMENT_ROLLBACK.md](file:///d:/Arthsavora/docs/DEPLOYMENT_ROLLBACK.md)
