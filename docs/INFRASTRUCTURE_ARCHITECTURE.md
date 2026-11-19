# ARTHSAVORA — Production Infrastructure Architecture

## 1. Overview and Architectural Tenets

ARTHSAVORA is engineered as a **high-integrity modular monolith** optimized for institutional-grade reliability, compliance with Indian financial data regulations (RBI, SEBI, DPDP Act 2023), and low operational complexity. The platform avoids premature distributed systems complexity (such as unneeded microservices, Kubernetes clusters, or multi-broker event buses) in favor of a lean, vertically scalable container topology with strict logical boundaries.

```
+-----------------------------------------------------------------------------------+
|                                  INTERNET CLIENTS                                 |
|                       (Desktop Browsers, PWA Mobile, TWA)                        |
+----------------------------------------+------------------------------------------+
                                         | HTTPS (TLS 1.3)
                                         v
+-----------------------------------------------------------------------------------+
|                        EDGE & CONTENT DELIVERY NETWORK                            |
|             (Cloudflare / Edge Proxy: DDoS Protection, WAF, DNS, SSL)              |
+-------------------+---------------------------------------+-----------------------+
                    |                                       |
    Static Assets   | Cached (HTML, JS, CSS, PWA Assets)    | API Requests
    & PWA Shell     v                                       v
+----------------------------------------+ +----------------------------------------+
|      FRONTEND WEB CONTAINER / EDGE     | |       BACKEND APPLICATION RUNNER       |
|  - Nginx 1.27 Alpine Static Server     | |  - FastAPI / Uvicorn Python 3.11       |
|  - Immutable Asset Caching (1yr max)   | |  - Async Modular Monolith Engine       |
|  - No-Cache sw.js & manifest           | |  - Non-Root Container (UID 10001)      |
|  - Security Response Headers & CSP     | |  - Rate Limiter (Redis-backed)         |
+----------------------------------------+ |  - Structured JSON Logging & PII Mask  |
                                           +-------------------+--------------------+
                                                               |
                                   +---------------------------+--------------------+
                                   |                                                |
                                   v                                                v
               +----------------------------------------+ +-------------------------+
               |     PRIMARY DATA STORE (PERSISTENCE)   | | IN-MEMORY CACHE & QUEUE |
               |  - Managed PostgreSQL 18 (AWS RDS/Neon)| | - Managed Redis 7       |
               |  - Double-Entry Ledger Single Source   | | - Distributed Rate Limit|
               |  - Row-Level Security (RLS) on 46 tbls | | - Token JTI Revocation  |
               |  - Automated Hourly PITR & Daily Snap  | | - Ephemeral Session Ctx |
               +----------------------------------------+ +-------------------------+
```

## 2. Core Infrastructure Components

### 2.1 Edge Delivery & Network Security
- **Edge CDN & WAF**: Cloudflare Enterprise / Business tier terminating TLS 1.3, providing DDoS mitigation (L3/L4/L7), managed OWASP Core Rulesets, and edge rate limiting.
- **Frontend Hosting**: Pre-rendered Vite SPA / PWA served via Nginx Alpine container or edge object hosting (Cloudflare Pages / AWS S3 + CloudFront).
- **Reverse Proxy**: Nginx 1.27 with hardened security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, strict `Content-Security-Policy`).

### 2.2 Application Services (FastAPI Modular Monolith)
- **Runtime**: Python 3.11-slim containerized multi-stage image running `uvicorn` with `uvloop`.
- **Process Model**: Non-root execution (`arthsavora:arthsavora` UID/GID 10001), read-only root filesystem where feasible, explicit temporary directory mounting.
- **Service Boundaries**: Single deployable unit with internally decoupled domain modules (Auth, Accounts, Ledger, Family Finance, Business Finance, Analytics, Reporting, Documents, AI Assistant, Notifications).

### 2.3 Primary Relational Persistence (PostgreSQL 18)
- **Role**: Single authoritative financial source of truth.
- **Multi-Tenancy Isolation**: Row-Level Security (`ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`) applied across all 46 workspace-scoped tables using `app.current_workspace_id`.
- **Integrity Constraints**: Database-level foreign keys, unique idempotency indexes, double-entry balanced transaction check invariants, and advisory locking for migrations.

### 2.4 Distributed Cache & Session State (Redis 7)
- **Role**: High-throughput distributed rate limiting, token revocation registry (JTI blacklist), and fast cache.
- **Durability**: Append-Only File (AOF) enabled with `everysec` fsync policy.

## 3. Resilience and Failure Domains

| Component | Failure Mode | Mitigation Strategy | Recovery Objective |
| :--- | :--- | :--- | :--- |
| **API Container** | Process crash, OOM | Container orchestrator auto-restart; healthcheck failure initiates replacement | Downtime < 5 seconds |
| **PostgreSQL Primary** | Node hardware failure | Managed Multi-AZ automatic failover with standby replica | RTO < 2 minutes |
| **Redis Cache** | Node restart | Backend falls back to in-memory rate limiting; tokens validated via signature | Graceful degradation |
| **Edge CDN** | Transit route partition | Multi-Anycast routing failover by CDN provider | RTO < 30 seconds |

## 4. Architectural Documents Cross-Reference
- Environment Separation: [ENVIRONMENT_STRATEGY.md](file:///d:/Arthsavora/docs/ENVIRONMENT_STRATEGY.md)
- Deployment Topology: [DEPLOYMENT_TOPOLOGY.md](file:///d:/Arthsavora/docs/DEPLOYMENT_TOPOLOGY.md)
- Cost Model: [INFRASTRUCTURE_COST_MODEL.md](file:///d:/Arthsavora/docs/INFRASTRUCTURE_COST_MODEL.md)
