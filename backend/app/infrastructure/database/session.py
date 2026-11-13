"""
Arthsavora Database Session Infrastructure
Provides PostgreSQL SQLAlchemy 2.0 async session management with connection pooling,
along with legacy compatibility utilities during architectural transition.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings
from app.core.logging import logger

# 1. PostgreSQL Asynchronous Engine (SQLAlchemy 2.0)
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily initializes the PostgreSQL async engine with connection pooling."""
    global engine, async_session_factory
    if engine is None:
        db_url = settings.DATABASE_URL or settings.assemble_db_connection(None, None)
        logger.info(f"Initializing PostgreSQL Async Engine: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
        engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        async_session_factory = async_sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a managed PostgreSQL async session."""
    if async_session_factory is None:
        get_engine()
    assert async_session_factory is not None
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
