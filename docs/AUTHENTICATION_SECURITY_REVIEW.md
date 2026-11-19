# ARTHSAVORA — Authentication Security & Session Review

## 1. Scope & Architecture

This security review audits the identity, credential management, token issuance, session verification, and session revocation mechanisms across the ARTHSAVORA platform.

ARTHSAVORA implements a production-grade authentication engine designed to support both local database-backed credential authentication and external enterprise identity providers (such as Supabase Auth).

---

## 2. Token Lifecycle & Specifications

| Claim / Property | Access Token | Refresh Token | Security Purpose |
| :--- | :--- | :--- | :--- |
| **Token Type (`type`)** | `"access"` | `"refresh"` | Strictly typed; access endpoints reject refresh tokens, refresh endpoint rejects access tokens. |
| **Subject (`sub`)** | User UUID string | User UUID string | Unique user identifier; verified against database active state. |
| **Issuer (`iss`)** | `settings.JWT_ISSUER` (`"ARTHSAVORA"`) | `settings.JWT_ISSUER` (`"ARTHSAVORA"`) | Rejects tokens minted by external or unauthorized issuers. |
| **Expiration (`exp`)** | `ACCESS_TOKEN_EXPIRE_MINUTES` (24h default) | `REFRESH_TOKEN_EXPIRE_DAYS` (30 days) | Limits window of opportunity in case of token leakage. |
| **Issued At (`iat`)** | Timezone-aware UTC timestamp | Timezone-aware UTC timestamp | Rejects pre-dated or future-dated tokens. |
| **Not Before (`nbf`)** | Timezone-aware UTC timestamp | Timezone-aware UTC timestamp | Prevents premature token validation. |
| **JWT ID (`jti`)** | Cryptographic UUIDv4 string | Cryptographic UUIDv4 string | Unique identifier for server-side revocation tracking. |
| **Algorithm** | HMAC-SHA256 (`HS256`) | HMAC-SHA256 (`HS256`) | Cryptographically signed using 256-bit secret key. |

---

## 3. Verified Security Controls

### 3.1. Immediate Server-Side Session Revocation on Logout
- **Mechanism:** When a user calls `/api/v1/auth/logout`, the backend parses the Bearer token from the `Authorization` header, decodes the claims, extracts the `jti` (JWT ID), and registers it in the thread-safe `_REVOKED_JTIS` registry.
- **Verification:** In `decode_token`, incoming tokens have their `jti` verified against the revocation registry:
  ```python
  jti = payload.get("jti")
  if jti and is_token_revoked(jti):
      raise InvalidTokenException("Token has been revoked.")
  ```
- **Test Evidence:** Verified in `test_logout_revokes_token_jti_and_blocks_subsequent_use`. An access token used after logout is rejected with `401 Unauthorized` and code `INVALID_TOKEN`.

### 3.2. Password Storage & Salt Hashing
- **Hashing Algorithm:** `bcrypt` with work factor 12 (`rounds=12`), providing strong resistance against GPU-accelerated dictionary attacks and rainbow tables.
- **Verification:** Plaintext passwords are never persisted or logged. Verification uses constant-time byte comparisons (`bcrypt.checkpw`) to prevent timing side-channel attacks.

### 3.3. Timing-Resistant User Enumeration Defense
- **Defense Mechanism:** When authenticating via `/api/v1/auth/login`, non-existent email addresses and incorrect passwords return identical responses:
  - HTTP Status: `401 Unauthorized`
  - Error Code: `"INVALID_CREDENTIALS"`
  - Error Message: `"Invalid email or password."`
- **Test Evidence:** Verified in `test_user_enumeration_prevention_on_login`. Attackers cannot determine whether a given email address is registered on the platform.

### 3.4. Brute-Force & Credential Stuffing Throttling
- **Rate Limit:** Authentication endpoints (`/api/v1/auth/login` and `/api/v1/auth/register`) are throttled to 5 requests per minute per client remote IP (`RATE_LIMIT_AUTH = "5/minute"`).
- **Protection:** Protects against distributed botnet attacks attempting automated dictionary guessing against user accounts.

### 3.5. Suspended & Inactive Account Enforcement
- **Enforcement:** During token decoding and database user resolution (`get_current_user`), the user's `is_active` and `is_deleted` flags are revalidated. If an administrator disables an account, active tokens are rejected immediately with `ACCOUNT_DISABLED` or `ACCOUNT_DELETED`.

---

## 4. Multi-Factor Authentication (MFA) Readiness

The identity architecture includes data fields and workflow hooks for TOTP (Time-Based One-Time Password) multi-factor authentication:
1. `User` schema supports `mfa_enabled` and `mfa_secret` fields.
2. Login workflow is architected to return an intermediate `MFA_CHALLENGE` status token requiring a TOTP second-factor verification code prior to minting final access tokens.
3. Recommended for deployment in institutional enterprise phases.

---

## 5. Audit Summary

| Checkpoint | Status | Assessment |
| :--- | :--- | :--- |
| Token Expiration & Typing | **Passed** | Strict `type` validation; access tokens cannot be used to refresh, refresh tokens cannot access APIs. |
| Token Revocation | **Passed** | Logout immediately blacklists token JTI. |
| Password Storage Security | **Passed** | Salted bcrypt with 12 rounds. Zero plaintext storage. |
| User Enumeration Resistance | **Passed** | Consistent timing-resistant error messages on login. |
| Rate Limiting on Auth Endpoints | **Passed** | 5 req/min per IP enforced on `/login` and `/register`. |
| Inactive / Deleted User Rejection | **Passed** | Disabled accounts blocked on every authenticated request. |
