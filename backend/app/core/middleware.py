"""Middleware for request processing and logging."""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request/response details with timing."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        request_id = getattr(request.state, "request_id", None)

        start_time = time.time()

        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None
            }
        )

        response = await call_next(request)

        process_time = time.time() - start_time
        response_time_ms = round(process_time * 1000, 2)

        response.headers["X-Process-Time"] = str(response_time_ms)

        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms
            }
        )

        return response
