"""Pytest configuration for VeriFact tests."""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test that makes real API calls")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "unit: mark test as a unit test")


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Set up logging for tests."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@pytest.fixture
def mock_openai_key(monkeypatch):
    """Mock the OPENAI_API_KEY environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-api-key-for-testing")


@pytest.fixture
def mock_search_key(monkeypatch):
    """Mock the SEARCH_API_KEY environment variable."""
    monkeypatch.setenv("SEARCH_API_KEY", "mock-search-api-key-for-testing")
