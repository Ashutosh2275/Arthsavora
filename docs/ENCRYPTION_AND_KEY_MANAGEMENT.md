# ARTHSAVORA — Encryption & Key Management Architecture

## 1. Overview

ARTHSAVORA secures sensitive financial data across all lifecycle phases: data in transit across public networks, data in processing within application memory, and data at rest in relational and object storage.

---

## 2. Encryption in Transit

| Communication Channel | Protocol / Standard | Cipher Suites | Enforcement Point |
| :--- | :--- | :--- | :--- |
| **Client to API Gateway** | HTTPS (TLS 1.3 / 1.2) | TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256, ECDHE-RSA-AES256-GCM-SHA384 | Reverse Proxy (Nginx / Caddy / Cloudflare) |
| **HSTS Enforcement** | HTTP Strict Transport Security | `max-age=31536000; includeSubDomains; preload` | Global FastAPI Middleware |
| **Backend to PostgreSQL** | TLS / SSL (Encrypted) | TLS 1.3 encrypted connection pool (`sslmode=require`) | asyncpg connection driver |
| **Backend to Redis** | TLS / SSL (Rediss) | Encrypted transport for job payloads | Celery / Redis client |
| **Backend to Third-Party APIs** | HTTPS (TLS 1.3) | Provider-enforced modern cipher suites | HTTPX / httpx.AsyncClient |

---

## 3. Encryption at Rest

### 3.1. Database Storage
- **PostgreSQL Database Storage:** Full volume encryption using AES-256 (AWS EBS encryption / dm-crypt LUKS on Linux hosts).
- **Sensitive Column Encryption:** Bank account numbers, IFSC codes, Account Aggregator consent tokens, and PAN identifiers are encrypted at the application layer prior to persistence using AES-256-GCM or HMAC tokenization.

### 3.2. Document & Object Storage
- **Storage Encryption:** Files stored in local filesystem volumes inherit disk-level BitLocker (Windows) or dm-crypt/ext4 (Linux) encryption.
- **Cloud Object Storage (Supabase Storage / AWS S3):** Configured with Server-Side Encryption (SSE-S3 / SSE-KMS) utilizing customer-managed or service-managed AES-256 keys.

---

## 4. Key Management & Secrets Separation

### 4.1. Key Separation Principle
- **Separation of Keys and Data:** Encryption keys are never stored alongside encrypted data in database columns or filesystem tables.
- **Environment Injection:** Keys are injected into the runtime environment via container secrets, environment variables, or dedicated secrets managers (AWS Secrets Manager, HashiCorp Vault, or Google Cloud Secret Manager).

### 4.2. Key Inventory & Rotation Schedule

| Key Name | Purpose | Recommended Rotation | Rotation Procedure |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | Signs internal JWT access and refresh tokens | 90 Days | Supports key versioning. Old tokens expire within 24 hours; refresh tokens re-mint on login. |
| `SUPABASE_JWT_SECRET` | Validates external Supabase Auth tokens | On compromise / 180 Days | Synchronized with Supabase project management dashboard. |
| `POSTGRES_PASSWORD` | Primary database user credentials | 90 Days | Zero-downtime rotation via connection pool rolling updates. |
| `GEMINI_API_KEY` | Google GenAI API access | 180 Days | Dual-key rotation in Google Cloud Console. |
| `WEBHOOK_SIGNING_KEY` | HMAC verification of provider callbacks | 180 Days | Provider portal key generation and dual-secret verification grace period. |

---

## 5. Cryptographic Fail-Safe Standards

1. **Zero Hardcoded Secrets in Production:** `validate_production_security` in `backend/app/core/config.py` enforces that in `ENVIRONMENT=production`, if `SECRET_KEY` is under 32 characters or contains `"insecure"`, the application aborts immediately with a critical `ValueError`.
2. **Key Erasure:** Deprecated keys are removed from secrets managers and invalidated across all active containers.
