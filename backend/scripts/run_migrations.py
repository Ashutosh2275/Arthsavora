#!/usr/bin/env python3
"""
ARTHSAVORA Production Database Migration Runner
Acquires a PostgreSQL advisory lock prior to running Alembic migrations,
preventing race conditions during rolling container deployments.
Post-migration, executes Row-Level Security (RLS) policy synchronization.
"""

import asyncio
import logging
import os
from pathlib import Path
import sys

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.infrastructure.database.rls import generate_rls_sql

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_runner")

# Global Advisory Lock Identifier for Arthsavora Migrations
MIGRATION_ADVISORY_LOCK_ID = 987654321


async def acquire_advisory_lock(engine) -> bool:
    """Acquires a cluster-wide advisory lock to prevent concurrent migration runs."""
    async with engine.connect() as conn:
        logger.info(f"Acquiring PostgreSQL advisory lock ({MIGRATION_ADVISORY_LOCK_ID})...")
        await conn.execute(text(f"SELECT pg_advisory_lock({MIGRATION_ADVISORY_LOCK_ID})"))
        await conn.commit()
    logger.info("Advisory lock acquired successfully.")
    return True


async def release_advisory_lock(engine) -> None:
    """Releases the cluster-wide advisory lock."""
    try:
        async with engine.connect() as conn:
            logger.info(f"Releasing PostgreSQL advisory lock ({MIGRATION_ADVISORY_LOCK_ID})...")
            await conn.execute(text(f"SELECT pg_advisory_unlock({MIGRATION_ADVISORY_LOCK_ID})"))
            await conn.commit()
        logger.info("Advisory lock released successfully.")
    except Exception as exc:
        logger.warning(f"Error releasing advisory lock: {exc}")


async def sync_rls_policies(engine) -> None:
    """Synchronizes Row-Level Security policies across all workspace-scoped tables."""
    rls_sql = generate_rls_sql()
    logger.info("Applying PostgreSQL Row-Level Security (RLS) policies...")
    async with engine.connect() as conn:
        for stmt in rls_sql.split(";"):
            cleaned = stmt.strip()
            if cleaned and not cleaned.startswith("--"):
                await conn.execute(text(cleaned))
        await conn.commit()
    logger.info("All Row-Level Security policies synchronized successfully.")


def run_alembic_upgrade() -> None:
    """Executes Alembic upgrade to head revision."""
    ini_path = backend_root / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_root / "migrations"))
    logger.info("Executing Alembic upgrade head...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic schema migrations completed successfully.")


async def main():
    logger.info(f"Connecting to database: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    lock_acquired = False
    try:
        await acquire_advisory_lock(engine)
        lock_acquired = True

        # Run Alembic upgrade in separate thread so its internal asyncio.run works without loop conflict
        await asyncio.to_thread(run_alembic_upgrade)

        # Synchronize RLS policies
        await sync_rls_policies(engine)

        logger.info("Production database deployment operations completed without error.")
    except Exception as exc:
        logger.error(f"FATAL: Database migration failed: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        if lock_acquired:
            await release_advisory_lock(engine)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
