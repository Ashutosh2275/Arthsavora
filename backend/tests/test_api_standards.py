"""
Arthsavora API Design Standards & Protocol Verification
Validates correlation IDs, response envelopes, error schemas,
security headers, cache policies, and pagination constraints.
"""

import uuid
import pytest
from httpx import AsyncClient
from app.schemas.common import PaginationParams, PaginatedResponse


@pytest.mark.asyncio
async def test_correlation_id_generated_and_propagated(client: AsyncClient):
    """Verifies that every response returns an X-Request-ID header."""
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    # Verify it is a valid UUID
    uuid.UUID(response.headers["X-Request-ID"])


@pytest.mark.asyncio
async def test_correlation_id_preserved_when_provided(client: AsyncClient):
    """Verifies that a caller-supplied X-Request-ID is preserved across processing."""
    custom_id = str(uuid.uuid4())
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


@pytest.mark.asyncio
async def test_security_headers_present_on_responses(client: AsyncClient):
    """Verifies critical security response headers to guard against common web vulnerabilities."""
    response = await client.get("/api/v1/health/live")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "0"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_cache_control_no_store_on_api_endpoints(client: AsyncClient):
    """Verifies that API responses instruct clients and proxies never to store sensitive financial data."""
    response = await client.get("/api/v1/health/live")
    cache_control = response.headers.get("Cache-Control", "")
    assert "no-store" in cache_control
    assert "no-cache" in cache_control


@pytest.mark.asyncio
async def test_standard_error_envelope_structure_on_validation_failure(client: AsyncClient):
    """Verifies that 422 Request Validation errors strictly adhere to the Arthsavora error schema."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "123"},  # Password too short, invalid email
    )
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert "request_id" in data["error"]
    assert isinstance(data["error"]["details"], list)
    assert len(data["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_cors_preflight_options_response(client: AsyncClient):
    """Verifies CORS preflight response headers for approved origins."""
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_pagination_params_bounds():
    """Verifies pagination parameter default and limit constraints."""
    params = PaginationParams(page=2, page_size=50)
    assert params.offset == 50
    assert params.page == 2
    assert params.page_size == 50

    # Max page size capped at 100 via validation
    with pytest.raises(Exception):
        PaginationParams(page=1, page_size=500)
