"""
Main FastAPI application for PaymentMate AI Fraud Detection System.
Configures middleware, routes, and error handlers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, RequestLoggingMiddleware
from app.core.exceptions import (
    PaymentMateException,
    paymentmate_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.api.v1 import health

# Setup logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            "environment": settings.environment,
            "debug": settings.debug
        }
    )

    # TODO: Initialize services on startup:
    # - Load ML model
    # - Connect to feature store (Redis if configured)
    # - Initialize any caches

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")

    # TODO: Cleanup on shutdown:
    # - Close feature store connections
    # - Release resources


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time fraud detection system using ML and explainable AI",
    debug=settings.debug,
    lifespan=lifespan
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)


# Register exception handlers
app.add_exception_handler(PaymentMateException, paymentmate_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# Include routers
app.include_router(
    health.router,
    prefix=settings.api_v1_prefix,
    tags=["monitoring"]
)

# TODO: Add additional routers as they are developed:
# app.include_router(transaction.router, prefix=settings.api_v1_prefix)
# app.include_router(data.router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with basic service information.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
