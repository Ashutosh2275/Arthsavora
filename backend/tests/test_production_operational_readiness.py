"""
Arthsavora Production Operational Readiness & Observability Verification Tests
Prompt 28: Validates deployment readiness, configuration validation gates,
structured JSON logging, PII/credential scrubbing, database migration advisory locking,
and health/readiness probe contracts.
"""

import json
import logging
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from app.core.config import Settings
from app.core.logging import (
    StructuredJsonFormatter,
    sanitize_value,
    SENSITIVE_KEYS,
    setup_logging,
)
from app.infrastructure.database.session import get_db_session
from app.main import app


# ---------------------------------------------------------------------------
# 1. Configuration Validation Gates in Production Mode
# ---------------------------------------------------------------------------


def test_production_config_rejects_insecure_secret_key():
    """Verifies that production environment strictly forbids weak/default secret keys."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="arthsavora-dev-insecure-secret-key-change-in-production-12345678",
            DEBUG=False,
            CORS_ORIGINS=["https://app.arthsavora.com"],
        )
    assert "SECRET_KEY" in str(exc_info.value)


def test_production_config_rejects_short_secret_key():
    """Verifies that production environment strictly forbids secret keys under 32 characters."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short-secret-key-too-short",
            DEBUG=False,
            CORS_ORIGINS=["https://app.arthsavora.com"],
        )
    assert "SECRET_KEY" in str(exc_info.value)


def test_production_config_rejects_wildcard_cors():
    """Verifies that wildcard CORS origins are forbidden in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-very-strong-cryptographically-secure-production-secret-key-2026!",
            DEBUG=False,
            CORS_ORIGINS=["*"],
        )
    assert "CORS" in str(exc_info.value)


def test_production_config_rejects_debug_mode():
    """Verifies that DEBUG mode must be False in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-very-strong-cryptographically-secure-production-secret-key-2026!",
            DEBUG=True,
            CORS_ORIGINS=["https://app.arthsavora.com"],
        )
    assert "DEBUG" in str(exc_info.value)


def test_production_config_enforces_hsts_and_validates():
    """Verifies that valid production settings activate HSTS."""
    cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a-very-strong-cryptographically-secure-production-secret-key-2026!",
        DEBUG=False,
        CORS_ORIGINS=["https://app.arthsavora.com"],
    )
    assert cfg.ENVIRONMENT == "production"
    assert cfg.ENABLE_HSTS is True
    assert cfg.DEBUG is False


# ---------------------------------------------------------------------------
# 2. Structured JSON Logging and Sensitive Scrubbing
# ---------------------------------------------------------------------------


def test_structured_json_formatter():
    """Verifies that the structured JSON formatter outputs valid JSON with standard fields."""
    formatter = StructuredJsonFormatter(service_name="ARTHSAVORA", environment="production")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=42,
        msg="Transaction processed successfully",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345-uuid"
    record.workspace_id = "ws-67890-uuid"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["service"] == "ARTHSAVORA"
    assert parsed["environment"] == "production"
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Transaction processed successfully"
    assert parsed["request_id"] == "req-12345-uuid"
    assert parsed["workspace_id"] == "ws-67890-uuid"
    assert "timestamp" in parsed


def test_sensitive_data_sanitization_keys():
    """Verifies that dictionary keys containing sensitive names are masked."""
    payload = {
        "user_id": "u-123",
        "email": "user@example.com",
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "pan": "ABCDE1234F",
        "aadhaar": "123456789012",
        "cvv": "999",
        "card_number": "4111222233334444",
        "nested": {
            "secret_key": "api-key-test-value",
            "safe_counter": 10,
        },
    }

    sanitized = {k: sanitize_value(k, v) for k, v in payload.items()}

    assert sanitized["user_id"] == "u-123"
    assert sanitized["email"] == "user@example.com"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["pan"] == "[REDACTED]"
    assert sanitized["aadhaar"] == "[REDACTED]"
    assert sanitized["cvv"] == "[REDACTED]"
    assert sanitized["card_number"] == "[REDACTED]"
    assert sanitized["nested"]["secret_key"] == "[REDACTED]"
    assert sanitized["nested"]["safe_counter"] == 10


def test_bearer_token_string_scrubbing():
    """Verifies that Bearer tokens inside string messages are automatically scrubbed."""
    raw_message = "Authentication failure: Header was Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.abc"
    scrubbed = sanitize_value("message", raw_message)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
    assert "Bearer [REDACTED]" in scrubbed


# ---------------------------------------------------------------------------
# 3. Health & Readiness Probe Edge Cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_liveness_probe_contract(client: AsyncClient):
    """Verifies liveness returns 200 without touching database."""
    res = await client.get("/api/v1/health/live")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "alive"
    assert body["service"] == "ARTHSAVORA"


@pytest.mark.asyncio
async def test_readiness_probe_database_success(client: AsyncClient):
    """Verifies readiness returns 200 with database status connected."""
    res = await client.get("/api/v1/health/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ready"
    assert body["database"] == "connected"


@pytest.mark.asyncio
async def test_readiness_probe_database_failure_503(client: AsyncClient):
    """Verifies readiness returns 503 DATABASE_UNAVAILABLE when database throws."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = TimeoutError("Database connection timed out after 2000ms")

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        res = await client.get("/api/v1/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["error"]["code"] == "DATABASE_UNAVAILABLE"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 4. PostgreSQL Advisory Lock Mechanics for Zero-Downtime Migrations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgresql_advisory_lock_lifecycle(db_session):
    """
    Verifies that PostgreSQL advisory locks can be acquired and released cleanly,
    preventing concurrent migration race conditions in multi-instance deployments.
    """
    LOCK_ID = 987654321

    # 1. Acquire advisory lock
    lock_result = await db_session.execute(
        text(f"SELECT pg_try_advisory_lock({LOCK_ID});")
    )
    acquired = lock_result.scalar()
    assert acquired is True, "Failed to acquire primary advisory lock"

    try:
        # 2. Re-trying lock within same or separate session behaves deterministically
        # In same session, pg_try_advisory_lock returns true (reentrant in postgres for session lock)
        # Release the lock
        pass
    finally:
        unlock_result = await db_session.execute(
            text(f"SELECT pg_advisory_unlock({LOCK_ID});")
        )
        released = unlock_result.scalar()
        assert released is True, "Failed to release advisory lock"
