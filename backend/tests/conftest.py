"""
Pytest Test Fixtures and Test Environment Setup
Provides PostgreSQL test engine, async sessions, dependency overrides,
and authenticated API test clients against the isolated test database.
"""

import os
import sys
import uuid
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
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.infrastructure.database.models import User, UserProfile, Workspace, WorkspaceMember
from app.core.security import create_access_token, get_password_hash

# Test database connection URL on port 5433
TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/arthsavora_test"

# Use NullPool to prevent asyncpg connections from outliving their respective test event loops
test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


@pytest.fixture(scope="session", autouse=True)
async def init_test_database():
    """Ensures all relational tables exist in arthsavora_test before running any tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


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
    """Provides an async HTTP client for testing FastAPI route endpoints with DB override."""
    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def registered_user(db_session: AsyncSession) -> dict:
    """Provisions a persistent test user with personal workspace and valid access token."""
    user_id = uuid.uuid4()
    email = f"test_fintech_{user_id.hex[:8]}@example.com"
    user = User(
        id=user_id,
        email=email,
        full_name="Test Investor",
        hashed_password=get_password_hash("StrongSecretPass123!"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        default_currency="INR",
        timezone="Asia/Kolkata",
        locale="en-IN",
        theme="dark",
    )
    db_session.add(profile)

    workspace = Workspace(
        name="Test Investor Finances",
        slug=f"test-personal-{user.id.hex[:8]}",
        type="personal",
        owner_id=user.id,
        default_currency="INR",
        timezone="Asia/Kolkata",
        status="active",
        settings={"is_default": True},
    )
    db_session.add(workspace)
    await db_session.flush()

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    db_session.add(membership)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), email=user.email)
    return {
        "user": user,
        "workspace": workspace,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
