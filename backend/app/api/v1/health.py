"""
Health check endpoints for service monitoring.
Provides system status and readiness information.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str
    environment: str
    timestamp: datetime


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["monitoring"],
    summary="Health check endpoint",
    description="Returns the health status of the service"
)
async def health_check() -> HealthResponse:
    """
    Check if the service is healthy and running.

    Returns:
        HealthResponse: Service health information including status, version, and timestamp.
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow()
    )


@router.get(
    "/readiness",
    status_code=status.HTTP_200_OK,
    tags=["monitoring"],
    summary="Readiness check endpoint",
    description="Returns whether the service is ready to accept requests"
)
async def readiness_check() -> Dict[str, Any]:
    """
    Check if the service is ready to accept requests.
    In production, this would check database connections, model loading, etc.

    Returns:
        dict: Readiness status and component health information.
    """
    # TODO: Add actual readiness checks for:
    # - Model loaded
    # - Feature store connection
    # - Any other critical dependencies

    return {
        "ready": True,
        "service": settings.app_name,
        "timestamp": datetime.utcnow(),
        "components": {
            "api": "ready",
            "model": "not_loaded",  # Will be updated when model is integrated
            "feature_store": "not_configured"  # Will be updated when feature store is integrated
        }
    }
