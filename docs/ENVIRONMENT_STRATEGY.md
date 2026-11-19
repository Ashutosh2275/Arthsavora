# ARTHSAVORA — Environment Strategy & Isolation Boundaries

## 1. Principles of Environment Separation

ARTHSAVORA maintains strict cryptographic, network, and operational isolation across three standard environments: **Development**, **Staging**, and **Production**.

No state, credentials, user data, or encryption keys are ever shared across environment boundaries.

```
+------------------------+      +------------------------+      +------------------------+
|      DEVELOPMENT       |      |        STAGING         |      |       PRODUCTION       |
|  - Local / Branch CI   |      |  - Production Mirror   |      |  - High Availability   |
|  - Synthetic Test Data | ---> |  - Anonymized Data     | ---> |  - Live Financial Data |
|  - Mock AA & Providers |      |  - Sandbox Integrations|      |  - Zero Human Access   |
|  - Fast Iteration      |      |  - Full E2E & Pre-rel  |      |  - RLS Enforced Always |
+------------------------+      +------------------------+      +------------------------+
```

## 2. Environment Matrix

| Dimension | Development (`dev`) | Staging (`staging`) | Production (`production`) |
| :--- | :--- | :--- | :--- |
| **Domain** | `localhost:5173` / `127.0.0.1` | `staging.arthsavora.com` | `app.arthsavora.com` |
| **Backend API** | `localhost:8000` | `api-staging.arthsavora.com` | `api.arthsavora.com` |
| **Database** | Local PostgreSQL 18 (`port 5433`) | Managed RDS/Neon PostgreSQL 18 | Managed RDS Multi-AZ PostgreSQL 18 |
| **Redis** | Local Redis 7 (`port 6379`) | Managed ElastiCache/Upstash | Managed Redis Multi-AZ Cluster |
| **Data Policy** | Ephemeral synthetic fixtures | Anonymized synthetic fixtures | Production encrypted customer data |
| **Secrets Engine**| `.env.local` (git-ignored) | GitHub Secrets / AWS Secrets | AWS Secrets Manager / Vault |
| **SSL / TLS** | Self-signed / Plain HTTP local | TLS 1.3 Managed (Let's Encrypt)| TLS 1.3 Custom Cert with HSTS |
| **Rate Limiting** | Disabled or high threshold | Realistic production thresholds| Strict enforcement (5/min auth) |
| **Logging** | Human-readable text format | Structured JSON format | Structured JSON + PII Redaction |
| **DEBUG Mode** | `True` (optional) | `False` (mandatory) | `False` (strictly validated) |

## 3. Strict Promotion Protocol

1. **Commit to `develop` / Feature Branch**:
   - Triggers `ci.yml`: Typecheck, lint, unit tests, integration tests against containerized PostgreSQL, container build preflight.
2. **Merge to `main`**:
   - Deploys automatically to **Staging**.
   - Runs automated Alembic migration runner with PostgreSQL advisory lock `pg_advisory_lock(987654321)`.
   - Executes smoke test suite verifying `/api/v1/health/live` and `/api/v1/health/ready`.
3. **Release Tag Creation (`v*.*.*`)**:
   - Triggers `deploy.yml` with manual production approval gate.
   - Executes automated pre-migration database snapshot.
   - Applies zero-downtime database migrations with advisory lock and RLS verification.
   - Performs rolling blue-green deployment of backend container.
   - Deploys web frontend with edge cache purge of `index.html` and `sw.js`.
   - Performs automated synthetic health checks with rollback on failure.

## 4. Cross-Reference Links
- Infrastructure Architecture: [INFRASTRUCTURE_ARCHITECTURE.md](file:///d:/Arthsavora/docs/INFRASTRUCTURE_ARCHITECTURE.md)
- Secrets Configuration: [SECRETS_AND_ENVIRONMENT_CONFIGURATION.md](file:///d:/Arthsavora/docs/SECRETS_AND_ENVIRONMENT_CONFIGURATION.md)
- CI/CD Architecture: [CI_CD_ARCHITECTURE.md](file:///d:/Arthsavora/docs/CI_CD_ARCHITECTURE.md)
