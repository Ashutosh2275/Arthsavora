"""
ARTHSAVORA — Production-Grade FinTech Application Engine
Modular Monolith Entrypoint with centralized routing, hardened CORS, security headers,
enterprise exception handling, and robust async lifecycle management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.api.router import api_router
from app.api.v1.router import v1_router
from app.api.middleware.cors import setup_cors
from app.api.middleware.security_headers import setup_security_headers
from app.api.middleware.audit import setup_audit_middleware
from app.api.middleware.error_handler import setup_exception_handlers
from app.infrastructure.database.session import get_engine
from app.db.mongodb import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup lifecycle and clean resource teardown."""
    logger.info(f"Initializing {settings.PROJECT_NAME} Engine (v{settings.VERSION})...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")

    # 1. Verify PostgreSQL Primary Relational Connection
    try:
        pg_engine = get_engine()
        async with pg_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL primary relational engine connected successfully.")
    except Exception as e:
        logger.warning(
            f"PostgreSQL connection verification failed during startup: {e}. "
            "Engine will retry dynamically on request."
        )

    # 2. Initialize Transitional Persistence Connections
    try:
        await connect_to_mongo()
    except Exception as e:
        logger.warning(
            f"Transitional MongoDB connection could not be established: {e}. "
            "Continuing in standalone/relational mode."
        )

    yield

    # 3. Clean Resource Teardown on Shutdown
    logger.info("Initiating engine graceful shutdown...")
    try:
        pg_engine = get_engine()
        await pg_engine.dispose()
        logger.info("PostgreSQL connection pool disposed.")
    except Exception as e:
        logger.warning(f"Error during PostgreSQL pool disposal: {e}")

    try:
        await close_mongo_connection()
    except Exception as e:
        logger.warning(f"Error during MongoDB shutdown: {e}")

    logger.info(f"{settings.PROJECT_NAME} Engine Shutdown Cleanly.")


def create_app() -> FastAPI:
    """Application factory provisioning the configured FastAPI application instance."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Commercial-grade AI-powered financial management ecosystem for India.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. Attach Rate Limiter State
    application.state.limiter = limiter

    # 2. Attach Hardened CORS Middleware
    setup_cors(application)

    # 3. Attach Security Response Headers Middleware
    setup_security_headers(application)

    # 4. Attach Request Auditing & Correlation ID Middleware
    setup_audit_middleware(application)

    # 5. Attach Standardized Exception Handlers
    setup_exception_handlers(application)

    # 6. Mount Canonical V1 Production API Router
    application.include_router(v1_router, prefix="/api/v1")

    # 7. Mount Legacy / Transitional Router for Backwards Compatibility
    application.include_router(api_router, prefix="/api")

    # 8. Root Discovery Endpoints
    @application.get("/", tags=["System"])
    async def root():
        """Root health and version discovery endpoint."""
        return {
            "status": "online",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "v1_api": "/api/v1",
        }

    @application.get("/health", tags=["System"])
    async def health():
        """Top-level health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        }

    return application


# Top-level application instance for Uvicorn and ASGI servers
app = create_app()
