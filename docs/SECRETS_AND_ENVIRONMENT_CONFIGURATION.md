# ARTHSAVORA — Secrets and Environment Configuration

## 1. Secrets Management Philosophy

ARTHSAVORA enforces a **Zero-Secrets-in-Codebase** policy. No plaintext passwords, API keys, private tokens, or database connection strings are permitted in repository commits, git history, client-side bundles, or unmasked log outputs.

## 2. Environment Variables Specification

The platform utilizes Pydantic Settings (`backend/app/core/config.py`) to validate all variables at application bootstrap.

### 2.1 Core Application
| Variable | Type | Default (Dev) | Description | Production Constraint |
| :--- | :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | `str` | `ARTHSAVORA` | Brand application identifier | Immutable |
| `VERSION` | `str` | `1.1.0` | Semantic release version | Synced with Git tag |
| `ENVIRONMENT` | `str` | `development` | Deployment tier: `development`, `staging`, `production` | Strict validation |
| `DEBUG` | `bool` | `False` | Debug diagnostics toggle | **MUST be `False` in Prod** |

### 2.2 Security & Authentication
| Variable | Type | Default (Dev) | Description | Production Constraint |
| :--- | :--- | :--- | :--- | :--- |
| `SECRET_KEY` | `str` | Insecure dev key | HMAC-SHA256 signing key for JWT tokens | **>= 32 chars, entropy check** |
| `ALGORITHM` | `str` | `HS256` | JWT signing algorithm | `HS256` or `RS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `1440` (24h) | Access token lifespan | `60` in high-security Prod |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `30` | Refresh token lifespan | Maximum 30 days |
| `ENABLE_HSTS` | `bool` | `False` | HTTP Strict Transport Security | **Auto-enforced True in Prod** |
| `CORS_ORIGINS` | `List[str]` | `["http://localhost:5173"]`| Permitted HTTP CORS origins | **Wildcard `*` strictly blocked** |

### 2.3 Relational & Cache Datastores
| Variable | Type | Description | Production Source |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `str` | PostgreSQL asyncpg connection URI (`postgresql+asyncpg://...`) | AWS Secrets Manager / Vault |
| `POSTGRES_USER` | `str` | PostgreSQL application user | Injected via secrets engine |
| `POSTGRES_PASSWORD`| `str` | PostgreSQL application password | Injected via secrets engine |
| `REDIS_URL` | `str` | Redis distributed cache URI (`redis://...`) | Injected via secrets engine |

### 2.4 Third-Party & AI Integrations
| Variable | Type | Description | Production Source |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | `str` | Google GenAI API Key for Gemini 2.5 Flash | AWS Secrets Manager / Vault |
| `GEMINI_MODEL` | `str` | Google GenAI model identifier (`gemini-2.5-flash`) | Configuration string |
| `SUPABASE_URL` | `str` | Supabase storage/auth URL | Configuration string |
| `SUPABASE_KEY` | `str` | Supabase Anon Key (Public) | Injected via build config |
| `SUPABASE_SERVICE_ROLE_KEY` | `str` | Supabase Service Role Key (Admin) | Restricted to backend only |

## 3. Storage and Injection Protocol

- **Local Development**: Developer clones repository and copies `.env.example` to `.env.local` (excluded by `.gitignore`).
- **CI Preflight**: Injected as masked GitHub Secrets (`PROD_DATABASE_URL`, `STAGING_DATABASE_URL`).
- **Production Runtime**: Injected directly into container environment variables at task definition time via AWS Systems Manager Parameter Store or AWS Secrets Manager with IAM role least-privilege scoping.

## 4. Cross-Reference Links
- Configuration Validation: [CONFIGURATION_VALIDATION.md](file:///d:/Arthsavora/docs/CONFIGURATION_VALIDATION.md)
- Secret Rotation Procedure: [SECRET_ROTATION_PROCEDURE.md](file:///d:/Arthsavora/docs/SECRET_ROTATION_PROCEDURE.md)
