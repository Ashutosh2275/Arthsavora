"""
Arthsavora Standardized Exception Handlers
Formats all uncaught, domain, HTTP, and validation exceptions into a consistent API response schema.
Guarantees zero internal tracebacks or SQL details leak to public consumers.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from app.core.exceptions import ArthsavoraException
from app.core.logging import logger


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ArthsavoraException)
    async def arthsavora_exception_handler(request: Request, exc: ArthsavoraException) -> JSONResponse:
        request_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "correlation_id", None)
        # Map common HTTP status codes to clean codes
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = str(exc.detail) if isinstance(exc.detail, str) else "An error occurred."
        details = exc.detail if isinstance(exc.detail, list) else []

        return JSONResponse(
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                    "details": details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "correlation_id", None)
        details = []
        for err in exc.errors():
            details.append({
                "loc": [str(x) for x in err.get("loc", [])],
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            })

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload.",
                    "request_id": request_id,
                    "details": details,
                }
            },
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        request_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": "60"},
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down and try again.",
                    "request_id": request_id,
                    "details": [{"detail": str(exc.detail if hasattr(exc, "detail") else exc)}],
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "correlation_id", None)
        logger.error(
            f"Unhandled internal server exception [RequestId: {request_id}]: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "request_id": request_id,
                    "details": [],
                }
            },
        )
