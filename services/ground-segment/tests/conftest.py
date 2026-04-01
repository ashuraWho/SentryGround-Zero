"""
Pytest configuration for SentryGround-Zero tests.
"""

import os
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def api_base() -> str:
    """API base URL for E2E tests."""
    return os.environ.get("API_BASE_URL", "http://localhost:8080/api/v1")


@pytest.fixture(scope="session")
def ws_url() -> str:
    """WebSocket URL for E2E tests."""
    return os.environ.get("WS_URL", "ws://localhost:8765")


@pytest.fixture(scope="session")
def dashboard_url() -> str:
    """Dashboard URL for E2E tests."""
    return os.environ.get("DASHBOARD_URL", "http://localhost:8501")


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "e2e: end-to-end tests requiring external services"
    )
    config.addinivalue_line(
        "markers", "requires_api: tests requiring API server"
    )
    config.addinivalue_line(
        "markers", "requires_dashboard: tests requiring Streamlit dashboard"
    )
    config.addinivalue_line(
        "markers", "requires_websocket: tests requiring WebSocket server"
    )
