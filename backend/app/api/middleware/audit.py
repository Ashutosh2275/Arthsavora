"""
Arthsavora Request Audit and Correlation ID Middleware
Injects correlation IDs, tracks request duration, and logs structured telemetry.
Prepares the backend for OpenTelemetry and Sentry distributed tracing.
"""

import time
import uuid
from fastapi import FastAPI, Request, Response
from app.core.logging import logger


def setup_audit_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def audit_request_middleware(request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # Extract or generate correlation ID
        correlation_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or str(uuid.uuid4())
        )
        request.state.correlation_id = correlation_id

        path = request.url.path
        method = request.method

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Inject correlation ID into response headers
        response.headers["X-Request-ID"] = correlation_id

        # Structured audit log
        logger.info(
            f"HTTP {method} {path} - Status: {response.status_code} - "
            f"Latency: {duration_ms:.2f}ms - RequestId: {correlation_id}"
        )
        return response
