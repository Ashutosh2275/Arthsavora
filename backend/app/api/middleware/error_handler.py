"""
Arthsavora Standardized Exception Handlers
Formats all uncaught, domain, and validation exceptions into standardized API responses.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from app.core.exceptions import ArthsavoraException
from app.core.logging import logger


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ArthsavoraException)
    async def arthsavora_exception_handler(_: Request, exc: ArthsavoraException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for err in exc.errors():
            details.append({
                "loc": err.get("loc", []),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            })

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "details": details,
                }
            },
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down.",
                    "details": [{"detail": str(exc)}],
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled server exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "details": [],
                }
            },
        )
