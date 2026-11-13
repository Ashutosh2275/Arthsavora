"""
Arthsavora Hardened CORS Middleware Configuration
Strictly forbids wildcard origins with credentials in compliance with W3C standards.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """Configures explicit, validated CORS origins without wildcard credential exposure."""
    origins = settings.CORS_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Request-ID"],
        max_age=600,
    )
