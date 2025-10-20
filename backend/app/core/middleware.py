"""
Middleware for request processing, logging, and monitoring.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to each request.
    The request ID is used for tracing and logging.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process the request and add a unique request ID.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response with X-Request-ID header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request and response information.
    Includes timing information for performance monitoring.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Log request details and measure response time.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response with timing information in headers
        """
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)

        # Record start time
        start_time = time.time()

        # Log incoming request
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

        # Process request
        response = await call_next(request)

        # Calculate response time
        process_time = time.time() - start_time
        response_time_ms = round(process_time * 1000, 2)

        # Add timing header
        response.headers["X-Process-Time"] = str(response_time_ms)

        # Log response
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
