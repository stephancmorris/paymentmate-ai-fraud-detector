"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from app.services.feature_store import initialize_feature_store, get_feature_store


@pytest.fixture(scope="session", autouse=True)
def initialize_services():
    """Initialize all required services before running tests."""
    # Initialize feature store (required for velocity service)
    initialize_feature_store()
    yield


@pytest.fixture(autouse=True)
def clear_feature_store():
    """Clear feature store between tests to avoid test interference."""
    store = get_feature_store()
    store.clear()
    yield
    store.clear()
