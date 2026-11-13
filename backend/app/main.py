"""
ARTHSAVORA — Production-Grade FinTech Application Engine
Modular Monolith Entrypoint with centralized routing, hardened CORS, and error handling.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.api.router import api_router
from app.api.middleware.cors import setup_cors
from app.api.middleware.audit import setup_audit_middleware
from app.api.middleware.error_handler import setup_exception_handlers
from app.db.mongodb import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and clean resource shutdown."""
    logger.info(f"Initializing {settings.PROJECT_NAME} Engine (v{settings.VERSION})...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")

    # Initialize persistence connections gracefully
    try:
        await connect_to_mongo()
    except Exception as e:
        logger.warning(
            f"Transitional MongoDB connection could not be established: {e}. "
            "Continuing in standalone/offline mode."
        )

    yield

    logger.info("Initiating engine graceful shutdown...")
    try:
        await close_mongo_connection()
    except Exception as e:
        logger.warning(f"Error during database shutdown: {e}")
    logger.info(f"{settings.PROJECT_NAME} Engine Shutdown Cleanly.")


# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Commercial-grade AI-powered financial management ecosystem for India.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. Attach Rate Limiter
app.state.limiter = limiter

# 2. Setup Hardened CORS
setup_cors(app)

# 3. Setup Request Auditing Middleware
setup_audit_middleware(app)

# 4. Setup Standardized Exception Handlers
setup_exception_handlers(app)

# 5. Register Master API Router
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["System"])
async def root():
    """Root health and version discovery endpoint."""
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["System"])
async def health():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
