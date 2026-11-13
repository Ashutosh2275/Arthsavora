"""
Pytest Test Fixtures and Test Environment Setup
Provides PostgreSQL test engine and async sessions against isolated test database.
"""

import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend root is on sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.config import settings

# Test database connection URL
TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/arthsavora_test"

# Use NullPool to prevent asyncpg connections from outliving their respective test event loops
test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


@pytest.fixture(scope="session")
def test_settings():
    return settings


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provides an isolated async session for database tests."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client():
    """Provides an async HTTP client for testing FastAPI route endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
