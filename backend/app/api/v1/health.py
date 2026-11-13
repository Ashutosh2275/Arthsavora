"""
Arthsavora V1 Health & Readiness Endpoints
Provides bounded liveness and database readiness probes for orchestrators and load balancers.
"""

from datetime import datetime, timezone
import asyncio
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import DatabaseUnavailableException
from app.infrastructure.database.session import get_db_session

router = APIRouter(tags=["Health & Probes"])


@router.get("/live", summary="Process Liveness Probe")
async def liveness():
    """
    Returns 200 OK if the Python FastAPI application process is alive.
    Fast and non-blocking; does not query downstream databases.
    """
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready", summary="Service Readiness Probe")
async def readiness(session: AsyncSession = Depends(get_db_session)):
    """
    Verifies that critical dependencies (PostgreSQL database) are reachable.
    Returns 200 OK when ready to accept traffic; returns 503 Service Unavailable if degraded.
    """
    try:
        # Bounded database health query with 2.0s timeout
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=2.0)
        return {
            "status": "ready",
            "service": settings.PROJECT_NAME,
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise DatabaseUnavailableException(
            message=f"Readiness probe failed: Database is unreachable."
        )
