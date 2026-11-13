"""
Arthsavora Health & Readiness Probe Verification Tests
Validates liveness and database dependency readiness checks for Kubernetes/container orchestrators.
"""

from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient
from app.infrastructure.database.session import get_db_session
from app.main import app


@pytest.mark.asyncio
async def test_liveness_probe_returns_200(client: AsyncClient):
    """Verifies liveness probe is responsive, fast, and does not require database connection."""
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["service"] == "ARTHSAVORA"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_returns_200_when_db_healthy(client: AsyncClient):
    """Verifies readiness probe returns 200 OK when PostgreSQL is reachable."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_readiness_probe_returns_503_when_db_unreachable(client: AsyncClient):
    """
    Verifies readiness probe returns HTTP 503 Service Unavailable with standard error
    when the database connection drops or times out.
    """
    # Mock database session that raises an operational exception
    mock_session = AsyncMock()
    mock_session.execute.side_effect = ConnectionRefusedError("PostgreSQL connection refused")

    async def mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = mock_get_db
    try:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "DATABASE_UNAVAILABLE"
    finally:
        app.dependency_overrides.clear()
