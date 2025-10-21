"""
Custom exceptions and error handlers for PaymentMate AI.
Provides consistent error responses across the API.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    message: str
    detail: Optional[Any] = None
    request_id: Optional[str] = None


class PaymentMateException(Exception):
    """Base exception for PaymentMate AI application."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class ModelLoadError(PaymentMateException):
    """Raised when ML model fails to load."""

    def __init__(self, message: str = "Failed to load ML model", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


class ModelPredictionError(PaymentMateException):
    """Raised when model prediction fails."""

    def __init__(self, message: str = "Model prediction failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class FeatureEngineeringError(PaymentMateException):
    """Raised when feature engineering fails."""

    def __init__(self, message: str = "Feature engineering failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class FeatureStoreError(PaymentMateException):
    """Raised when feature store operations fail."""

    def __init__(self, message: str = "Feature store operation failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


async def paymentmate_exception_handler(
    request: Request,
    exc: PaymentMateException
) -> JSONResponse:
    """Handle PaymentMate custom exceptions."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None

    logger.error(
        f"PaymentMate exception: {exc.message}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.message,
            detail=exc.detail,
            request_id=request_id
        ).model_dump()
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None

    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            message=str(exc.detail),
            request_id=request_id
        ).model_dump()
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None

    # Sanitize error details to ensure JSON serializability
    sanitized_errors = []
    for error in exc.errors():
        sanitized_error = {
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", ""))
        }
        # Only include ctx if it exists and is serializable
        if "ctx" in error and error["ctx"]:
            try:
                sanitized_error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
            except (AttributeError, TypeError):
                pass
        sanitized_errors.append(sanitized_error)

    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "errors": sanitized_errors,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            detail=sanitized_errors,
            request_id=request_id
        ).model_dump()
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None

    logger.error(
        f"Unexpected exception: {str(exc)}",
        extra={
            "request_id": request_id,
            "exception_type": exc.__class__.__name__,
            "path": request.url.path
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            request_id=request_id
        ).model_dump()
    )
