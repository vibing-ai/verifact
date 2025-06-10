import pytest
import os
import warnings
from typing import Generator, Dict, Any
from src.verifact_agents.verdict_writer import VerdictWriter

# Suppress the starlette multipart deprecation warning
warnings.filterwarnings("ignore", category=PendingDeprecationWarning, module="starlette.formparsers")

@pytest.fixture(scope="session")
def test_evidence() -> Dict[str, Any]:
    """Provide sample evidence for testing."""
    return {
        "content": "This is a sample evidence content for testing purposes.",
        "source": "Test Source",
        "relevance": 0.9,
        "stance": "supporting"
    }

@pytest.fixture(scope="session")
def test_claim() -> str:
    """Provide a sample claim for testing."""
    return "This is a test claim that needs verification."

@pytest.fixture(scope="session")
def verdict_writer() -> Generator[VerdictWriter, None, None]:
    """Create a VerdictWriter instance for testing."""
    writer = VerdictWriter()
    yield writer

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
    yield
    # Cleanup after tests if needed 