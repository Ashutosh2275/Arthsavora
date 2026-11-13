"""
Pytest Test Fixtures and Test Environment Setup
"""

import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

# Ensure backend root is on sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session")
def test_settings():
    return settings


@pytest.fixture
async def client():
    """Provides an async HTTP client for testing FastAPI route endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
