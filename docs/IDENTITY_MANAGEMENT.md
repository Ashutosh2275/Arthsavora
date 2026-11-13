# ARTHSAVORA — IDENTITY AND USER PROFILE MANAGEMENT ARCHITECTURE

## 1. Executive Summary

This document specifies the identity, user profile, and authentication mapping architecture of the **Arthsavora** fintech platform. Designed for commercial financial operations in India, Arthsavora separates user authentication identity from tenant tenancy scopes: a single user identity can participate in multiple isolated financial workspaces (Personal, Family, and Business) without permission bleeding or financial data co-mingling.

---

## 2. Core Identity Principles

1. **Decoupled Identity and Tenancy:** A `User` record represents a persistent natural or corporate person. Workspaces represent distinct legal, family, or operational financial entities.
2. **Stable Internal Identity (UUIDv4):** All relational integrity, foreign keys, audit logs, and accounting journals reference internal 128-bit cryptographic UUIDs (`User.id`), never external provider tokens or subject IDs.
3. **Delegated Authentication Agnosticism:** Authentication can be provided via local password hashes (Argon2id) or external OIDC / OAuth providers (Google, Apple, Phone OTP) without altering application-level relational structures.
4. **Idempotent Identity Mapping:** External identities map via `(auth_provider, auth_provider_id)` with strict unique partial indexing on non-null values, preventing account clobbering or duplicate registrations.
5. **Auditable Account Lifecycle:** Account state changes (registration, verification, suspension, self-deactivation) generate immutable audit records.

---

## 3. Data Model Architecture

### 3.1 `users` Table Schema

| Column | Data Type | Constraints / Modifiers | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, default `gen_random_uuid()` | Authoritative internal user identifier |
| `email` | `VARCHAR(255)` | `UNIQUE`, `NOT NULL`, indexed | Normalized lowercase email address |
| `hashed_password` | `VARCHAR(255)` | `NOT NULL` | Argon2id cryptographic hash (or dummy for OAuth) |
| `full_name` | `VARCHAR(128)` | `NOT NULL` | Legal full name for KYC/invoicing |
| `phone_number` | `VARCHAR(20)` | `NULLABLE` | E.164 formatted telephone number |
| `auth_provider` | `VARCHAR(30)` | `NOT NULL`, default `'local'` | Authentication source (`local`, `google`, `apple`) |
| `auth_provider_id` | `VARCHAR(255)` | `NULLABLE` | External subject/provider ID |
| `is_active` | `BOOLEAN` | `NOT NULL`, default `TRUE` | Global activity flag; `FALSE` blocks token issuance |
| `is_verified` | `BOOLEAN` | `NOT NULL`, default `FALSE` | Email / phone OTP verification status |
| `is_superuser` | `BOOLEAN` | `NOT NULL`, default `FALSE` | System administration override |
| `is_deleted` | `BOOLEAN` | `NOT NULL`, default `FALSE` | Soft-deletion flag |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `CURRENT_TIMESTAMP` | Account creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL`, default `CURRENT_TIMESTAMP` | Last profile update timestamp |

### 3.2 `user_profiles` Table Schema

The `user_profiles` entity isolates personal preferences, localization, and customization settings from core authentication credentials:

| Column | Data Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `gen_random_uuid()` | Profile record primary key |
| `user_id` | `UUID` | Foreign Key to `users.id` | 1-to-1 unique mapping to user (`ON DELETE CASCADE`) |
| `display_name` | `VARCHAR(255)` | `NULL` | Preferred user nickname or informal title |
| `avatar_url` | `VARCHAR(1024)` | `NULL` | Secure HTTPS link to profile photo/avatar |
| `preferred_language` | `VARCHAR(10)` | `'en-IN'` | Language preference code (e.g., `en-IN`, `hi-IN`) |
| `locale` | `VARCHAR(20)` | `'en-IN'` | Locale string for number and date formatting |
| `default_currency` | `VARCHAR(3)` | `'INR'` | ISO 4217 currency preference |
| `timezone` | `VARCHAR(50)` | `'Asia/Kolkata'` | IANA standard timezone string |
| `country` | `VARCHAR(2)` | `'IN'` | ISO 3166-1 alpha-2 country code |
| `theme` | `VARCHAR(20)` | `'dark'` | UI theme (`dark`, `light`, `system`) |
| `notification_preferences` | `JSONB` | `{}` | Granular email/SMS/push alert channels |
| `is_profile_complete` | `BOOLEAN` | `FALSE` | Evaluated flag (display name, currency, timezone) |

### 3.3 Unique Partial Index for External Authentication

To ensure strict uniqueness across external authentication providers while allowing multiple local users to have `auth_provider_id IS NULL`, PostgreSQL creates a partial unique index:

```sql
CREATE UNIQUE INDEX uq_user_auth_provider_id
ON users (auth_provider, auth_provider_id)
WHERE auth_provider_id IS NOT NULL;
```

---

## 4. User Profile Lifecycle & Self-Service Operations

### 4.1 Profile Retrieval (`GET /api/v1/users/me`)
- Requires valid Bearer JWT.
- Returns composite response of user contact details, authentication metadata, and personal preferences.
- If profile record is uninitialized, the service automatically seeds default preferences (`INR`, `Asia/Kolkata`, `en-IN`).

### 4.2 Profile Updates (`PATCH /api/v1/users/me`)
- Allows selective updating of `full_name`, `display_name`, `avatar_url`, `preferred_language`, `locale`, `default_currency`, `timezone`, `country`, `theme`, and `notification_preferences`.
- Automatically recalibrates `is_profile_complete`.
- Emits structured audit log record: `action="user:update_profile"`.
- Prevents tampering with security-critical properties (`email`, `auth_provider`, `is_active`, `is_verified`).

### 4.3 Account Self-Deactivation (`POST /api/v1/users/me/deactivate`)
- Requires explicit confirmation payload: `{"confirm": true}`.
- Sets `is_active = FALSE` in PostgreSQL.
- Invalidates active JWT access (via `get_current_user` active check).
- Revokes user's active login capability while strictly preserving historical accounting and financial audit records.
- Emits structured audit log record: `action="user:deactivate"`.

---

## 5. Security & Privacy Guardrails

1. **Email Normalization:** All emails are stripped, lowercased, and validated against RFC 5322 before hashing or matching.
2. **Password Cryptography:** Implemented via Argon2id with memory cost 65536 KiB, time cost 3 iterations, and parallelism 4 threads.
3. **Token Invalidation on Inactivity:** Inactive or deleted accounts immediately fail the authentication dependency (`AccountDisabledException` / `AccountDeletedException`), rejecting subsequent API requests with HTTP 401.
4. **Anti-Enumeration Responses:** Non-existent profiles or unauthorized attempts to access foreign user data yield uniform HTTP 404 or generic authorization responses.
