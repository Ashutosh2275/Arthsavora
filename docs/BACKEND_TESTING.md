# Arthsavora — Backend Testing Strategy and Test Suite Catalog

## 1. Testing Philosophy and Architecture

Arthsavora enforces rigorous test-driven development (TDD) across all backend layers. Financial systems cannot rely on mocks alone; tests must verify exact decimal precision, database transactions, Row-Level Security, and cryptographic token verification against a real PostgreSQL engine.

### Technology Stack
- **Test Runner:** `pytest 9.0+`
- **Async Engine:** `pytest-asyncio` with `mode=AUTO`
- **HTTP Client:** `httpx.AsyncClient` with `ASGITransport(app=app)`
- **Database Engine:** Real PostgreSQL 15+ on `localhost:5433` (`arthsavora_test`)
- **Connection Isolation:** `NullPool` to prevent asyncpg socket handles from crossing event loops

---

## 2. Test Environment and Fixtures (`backend/tests/conftest.py`)

### 2.1 Database Isolation Pattern
```python
test_engine = create_async_engine(
    "postgresql+asyncpg://postgres:postgres@localhost:5433/arthsavora_test",
    echo=False,
    poolclass=NullPool,
)
```
- **Session-Scoped Table Provisioning (`init_test_database`):** Ensures all 15 relational tables exist prior to test suite execution.
- **Dependency Override:** `client` automatically overrides `get_db_session` on the FastAPI application, ensuring API requests execute within the isolated `arthsavora_test` database.
- **Rollback Discipline:** The `db_session` fixture automatically rolls back uncommitted transactions after every test.

---

## 3. Test Suite Catalog and Verification Coverage

As of Prompt 05, the backend test suite comprises **49 automated tests across 10 test modules** (100% pass rate in ~8.3 seconds):

| Test Module | Test Count | Key Areas Covered |
| :--- | :---: | :--- |
| **`test_auth_api.py`** | 11 | Complete registration flow, personal workspace auto-provisioning, password verification, duplicate email rejection (409), `/me` profile retrieval, unauthenticated 401, invalid token 401, expired token 401 (`TOKEN_EXPIRED`), suspended account 401 (`ACCOUNT_DISABLED`), token refresh flow, and clean logout. |
| **`test_authorization.py`** | 7 | User workspace listing, Family/Business workspace provisioning, owner access, **cross-tenant IDOR 404 rejection**, owner member invitations, **viewer role privilege escalation rejection (403)**, and suspended membership rejection (403). |
| **`test_api_standards.py`** | 7 | Correlation ID (`X-Request-ID`) automated generation and header propagation, caller ID preservation, security headers (`nosniff`, `DENY`), `Cache-Control: no-store` on API routes, standardized 422 error JSON envelope, CORS preflight options headers, and pagination bounds. |
| **`test_database.py`** | 8 | Real PostgreSQL integration: user/workspace cascade creation, exact `NUMERIC(18, 4)` decimal precision, partial unique index idempotency, double-entry balanced journal posting, unbalanced journal rejection, posted entry immutability and reversal entries, audit log survival on member revocation, and transaction-scoped RLS context. |
| **`test_health_readiness.py`**| 3 | Liveness probe returns 200 without DB dependency, readiness probe returns 200 with active PostgreSQL, and readiness probe returns 503 `DATABASE_UNAVAILABLE` when database drops. |
| **`test_idempotency.py`** | 3 | In-flight lock acquisition, concurrent duplicate request rejection with 409 Conflict (`CONCURRENT_REQUEST`), and payload tampering rejection (`IDEMPOTENCY_FINGERPRINT_MISMATCH`). |
| **`test_config.py`** | 2 | Default configuration values and CORS wildcard prohibition validation. |
| **`test_security.py`** | 2 | Bcrypt salted password hashing and timezone-aware JWT creation. |
| **`test_health.py`** | 3 | Top-level root discovery and legacy health routes. |
| **`test_exceptions.py`** | 3 | Custom domain exception hierarchy, status codes, and error detail serialization. |

---

## 4. Test Execution Instructions

### Run All Backend Tests
```bash
python -m pytest backend/tests -v
```

### Run Focused Module Tests
```bash
# Authentication tests
python -m pytest backend/tests/test_auth_api.py -v

# Authorization & Multi-Tenancy tests
python -m pytest backend/tests/test_authorization.py -v

# Database and ledger tests
python -m pytest backend/tests/test_database.py -v
```

### Run with Coverage
```bash
python -m pytest backend/tests --cov=app --cov-report=term-missing
```
