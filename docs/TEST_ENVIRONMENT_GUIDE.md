# Test Environment and Execution Guide

## 1. Environment Setup

ARTHSAVORA provides a completely isolated, reproducible testing environment across both backend (Python 3.11+, `uv`, `pytest`) and frontend (Node.js 20+, `pnpm`, `vitest`).

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 20.x or higher
- **Package Managers**: `uv` (Python), `pnpm` (Node)
- **Database**: PostgreSQL 15+ (or isolated SQLite in-memory for fast unit testing)
- **Cache**: Redis 7+ (optional for local mock tests, mandatory for production integration)

---

## 2. Test Execution Commands

### 2.1 Backend Tests (Pytest)
```bash
# Run entire backend test suite (344 tests)
uv run pytest backend/tests -v

# Run fast quick mode
uv run pytest backend/tests -q

# Run specific E2E integration test suite
uv run pytest backend/tests/test_system_integration_e2e_qa.py -v

# Run operational readiness test suite
uv run pytest backend/tests/test_production_operational_readiness.py -v

# Run with test coverage report
uv run pytest backend/tests --cov=app --cov-report=term-missing
```

### 2.2 Frontend Tests (Vitest)
```bash
# Run web application unit & component tests (158 tests)
pnpm --filter @arthsavora/web test -- --run

# Run full monorepo typecheck across all 5 workspace packages
pnpm -r run typecheck

# Run production frontend bundle build
pnpm --filter @arthsavora/web build
```

---

## 3. Environment Variable Configuration for CI/Test

The test runner utilizes dedicated test settings (`backend/app/core/config.py`):
```ini
ENVIRONMENT=testing
DEBUG=false
TESTING=true
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/arthsavora_test
REDIS_URL=redis://localhost:6379/1
JWT_SECRET_KEY=testing_secret_key_minimum_32_characters_long_for_security_compliance
ENCRYPTION_MASTER_KEY=dGVzdF9tYXN0ZXJfa2V5XzMyX2J5dGVzX2xvbmdfMTIzNDU2Nw==
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

## 4. Test Concurrency and Isolation Guarantees

- **Process Isolation**: Each test module operates independently. Shared database states are strictly prohibited.
- **Port Isolation**: Backend test servers bind to dynamic high ports (`localhost:0`) or run via in-process `FastAPI TestClient`.
- **Zero Network Egress**: Integration tests do not invoke external HTTP endpoints; all third-party adapters are mock-stubbed by default in test mode.
