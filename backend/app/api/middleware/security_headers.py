"""
Arthsavora Security Headers Middleware
Applies enterprise-grade HTTP response headers to harden the API against clickjacking,
MIME-sniffing, cross-site leaks, and unauthorized caching of sensitive financial data.
"""

from fastapi import FastAPI, Request, Response
from app.core.config import settings


def setup_security_headers(app: FastAPI) -> None:
    """Configures global security headers on all HTTP responses."""

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # 1. Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Prevent UI Redressing / Clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Modern XSS filter standard (0 disables legacy buggy browser filters)
        response.headers["X-XSS-Protection"] = "0"

        # 4. Strict referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Disable caching on financial API endpoints to prevent local disk exposure
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        # 6. HTTP Strict Transport Security (HSTS) in staging/production
        if settings.ENABLE_HSTS:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
