"""
Shared fixtures for API tests.

This module provides fixtures for testing API endpoints,
including mocks for authentication and database dependencies.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.factcheck import Verdict
from src.pipeline.factcheck_pipeline import FactcheckPipeline


@pytest.fixture
def test_client():
    """Create a FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture
def mock_pipeline():
    """Create a mock FactcheckPipeline for testing."""
    mock = AsyncMock(spec=FactcheckPipeline)
    
    # Create mock verdict
    mock_verdict = Verdict(
        claim="The Earth is round",
        verdict="true",
        confidence=0.95,
        explanation="Multiple scientific observations confirm Earth's spherical shape.",
        sources=["https://example.com/earth-shape"]
    )
    
    # Configure the mock to return the verdict
    mock.process_text.return_value = [mock_verdict]
    return mock


@pytest.fixture
def mock_auth_service():
    """Mock for authentication dependencies."""
    mock = MagicMock()
    mock.validate_token.return_value = {"user_id": "test_user"}
    mock.verify_api_key.return_value = True
    return mock


@pytest.fixture
def mock_db():
    """Mock for database dependencies."""
    mock = MagicMock()
    
    # Configure mock methods
    mock.get_user.return_value = {"id": "test_user", "name": "Test User", "role": "user"}
    mock.save_factcheck.return_value = "factcheck_id_123"
    mock.get_factcheck.return_value = {
        "id": "factcheck_id_123",
        "text": "The Earth is round.",
        "verdicts": [
            {
                "claim": "The Earth is round",
                "verdict": "true",
                "confidence": 0.95,
                "explanation": "Multiple scientific observations confirm Earth's spherical shape.",
                "sources": ["https://example.com/earth-shape"]
            }
        ],
        "created_at": "2023-06-01T12:00:00Z",
        "user_id": "test_user"
    }
    
    return mock


@pytest.fixture
def mock_cache():
    """Mock for cache dependencies."""
    mock = MagicMock()
    
    # Configure mock methods
    mock.get.return_value = None  # Default to cache miss
    mock.set.return_value = True
    
    return mock


@pytest.fixture
def mock_rate_limiter():
    """Mock for rate limiting dependencies."""
    mock = MagicMock()
    
    # Configure mock methods
    mock.check_limit.return_value = (True, 10)  # (allowed, remaining)
    
    return mock


@pytest.fixture
def override_dependencies(mock_pipeline, mock_auth_service, mock_db, mock_cache, mock_rate_limiter):
    """Override app dependencies for testing."""
    from src.api import dependencies

    # Store original dependencies
    original_get_pipeline = dependencies.get_pipeline
    original_get_auth_service = dependencies.get_auth_service
    original_get_db = dependencies.get_db
    original_get_cache = dependencies.get_cache
    original_get_rate_limiter = dependencies.get_rate_limiter
    
    # Override dependencies
    dependencies.get_pipeline = lambda: mock_pipeline
    dependencies.get_auth_service = lambda: mock_auth_service
    dependencies.get_db = lambda: mock_db
    dependencies.get_cache = lambda: mock_cache
    dependencies.get_rate_limiter = lambda: mock_rate_limiter
    
    yield
    
    # Restore original dependencies
    dependencies.get_pipeline = original_get_pipeline
    dependencies.get_auth_service = original_get_auth_service
    dependencies.get_db = original_get_db
    dependencies.get_cache = original_get_cache
    dependencies.get_rate_limiter = original_get_rate_limiter


@pytest.fixture
def authenticated_client(test_client):
    """Create a test client with authentication headers."""
    test_client.headers = {
        "Authorization": "Bearer test_token",
        "X-API-Key": "test_api_key"
    }
    return test_client


@pytest.fixture
def sample_factcheck_request():
    """Return a sample factcheck request for testing the API."""
    return {
        "text": "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface.",
        "options": {
            "min_check_worthiness": 0.7
        }
    }


@pytest.fixture
def sample_factcheck_batch_request():
    """Return a sample batch factcheck request for testing the API."""
    return {
        "texts": [
            "The Earth is approximately 4.54 billion years old.",
            "Water covers about 71% of the Earth's surface."
        ],
        "options": {
            "min_check_worthiness": 0.7
        }
    }


@pytest.fixture
def mock_factcheck_response():
    """Return a mock factcheck response."""
    return {
        "claims": [
            {
                "text": "The Earth is approximately 4.54 billion years old.",
                "verdict": "TRUE",
                "confidence": 0.95,
                "explanation": "Scientific evidence supports this claim.",
                "sources": [
                    "https://example.com/earth-age",
                    "https://example.org/earth-formation"
                ]
            },
            {
                "text": "Water covers about 71% of the Earth's surface.",
                "verdict": "TRUE",
                "confidence": 0.98,
                "explanation": "This is a well-established fact.",
                "sources": [
                    "https://example.com/earth-water",
                    "https://example.org/oceans"
                ]
            }
        ],
        "metadata": {
            "processing_time": 2.35,
            "model": "test-model"
        }
    }

# Add API-specific fixtures here 