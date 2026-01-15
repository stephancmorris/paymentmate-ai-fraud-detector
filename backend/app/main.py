"""Main FastAPI application for PaymentMate AI Fraud Detection System."""

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
from app.api.v1 import health, transaction, data
from app.services.model_service import initialize_model_service
from app.services.feature_store import initialize_feature_store

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            "environment": settings.environment,
            "debug": settings.debug
        }
    )

    try:
        logger.info("Initializing feature store...")
        initialize_feature_store()
        logger.info("✓ Feature store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize feature store: {e}", exc_info=True)
        logger.warning("Application will start but velocity features may not work")

    try:
        logger.info("Loading ML model...")
        initialize_model_service(model_path=settings.model_path)
        logger.info("✓ ML model loaded successfully")
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        logger.warning("Application will start but fraud scoring may not work correctly")
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}", exc_info=True)
        logger.warning("Application will start but fraud scoring may not work correctly")

    yield

    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time fraud detection system using ML and explainable AI",
    debug=settings.debug,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.add_exception_handler(PaymentMateException, paymentmate_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(
    health.router,
    prefix=settings.api_v1_prefix,
    tags=["monitoring"]
)

app.include_router(
    transaction.router,
    prefix=settings.api_v1_prefix,
    tags=["transactions"]
)

app.include_router(
    data.router,
    prefix=settings.api_v1_prefix,
    tags=["data"]
)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with basic service information."""
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
