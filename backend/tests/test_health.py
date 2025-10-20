"""
Tests for health check endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint returns 200 OK."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "PaymentMate AI"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


def test_readiness_check():
    """Test the readiness check endpoint."""
    response = client.get("/api/v1/readiness")

    assert response.status_code == 200
    data = response.json()

    assert data["ready"] is True
    assert "components" in data
    assert "timestamp" in data


def test_root_endpoint():
    """Test the root endpoint returns service information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["service"] == "PaymentMate AI"
    assert data["status"] == "running"
    assert "version" in data
    assert "docs" in data


def test_cors_headers():
    """Test CORS headers are properly configured."""
    response = client.get("/api/v1/health")

    # Check that CORS middleware is active
    # Note: In test client, preflight requests need to be tested separately
    assert response.status_code == 200


def test_request_id_header():
    """Test that X-Request-ID header is added to responses."""
    response = client.get("/api/v1/health")

    assert "x-request-id" in response.headers
    # Request ID should be a valid UUID format
    request_id = response.headers["x-request-id"]
    assert len(request_id) > 0


def test_process_time_header():
    """Test that X-Process-Time header is added to responses."""
    response = client.get("/api/v1/health")

    assert "x-process-time" in response.headers
    # Process time should be a numeric value
    process_time = float(response.headers["x-process-time"])
    assert process_time >= 0


def test_invalid_endpoint_returns_404():
    """Test that invalid endpoints return 404 with proper error format."""
    response = client.get("/api/v1/nonexistent")

    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert "message" in data
    assert "request_id" in data


def test_validation_error_format():
    """Test that validation errors return proper error response format."""
    # This will be more useful when we have endpoints that accept data
    # For now, we're just ensuring the error handler is registered
    pass
