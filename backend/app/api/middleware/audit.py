"""
Arthsavora Request Audit Middleware
Logs incoming HTTP requests, paths, client status, and latency.
"""

import time
from fastapi import FastAPI, Request, Response
from app.core.logging import logger


def setup_audit_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def audit_request_middleware(request: Request, call_next) -> Response:
        start_time = time.time()
        path = request.url.path
        method = request.method

        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"HTTP {method} {path} -> Status: {response.status_code} | Duration: {duration:.4f}s"
        )
        return response
