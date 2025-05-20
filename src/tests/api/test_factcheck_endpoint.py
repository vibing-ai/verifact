"""Tests for the factcheck API endpoints.

Uses FastAPI TestClient to test the API endpoints with mocked dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.agents.verdict_writer.writer import Verdict
from src.main import app
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
        sources=["https://example.com/earth-shape"],
    )

    # Configure the mock to return the verdict
    mock.process_text.return_value = [mock_verdict]
    return mock


@pytest.fixture
def mock_auth():
    """Mock for authentication dependencies."""
    mock = MagicMock()
    mock.validate_token.return_value = {"user_id": "test_user"}
    return mock


def test_factcheck_endpoint_success(test_client, mock_pipeline):
    """Test successful request to factcheck endpoint."""
    # Patch the pipeline dependency
    with patch("src.api.dependencies.get_pipeline", return_value=mock_pipeline):
        # Create test request
        request_data = {
            "text": "The Earth is round.",
            "options": {"min_check_worthiness": 0.5, "max_claims": 3},
        }

        # Make request to the endpoint
        response = test_client.post("/api/v1/factcheck", json=request_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "verdicts" in data
        assert len(data["verdicts"]) == 1
        assert data["verdicts"][0]["claim"] == "The Earth is round"
        assert data["verdicts"][0]["verdict"] == "true"
        assert data["verdicts"][0]["confidence"] == 0.95

        # Verify pipeline was called with correct arguments
        mock_pipeline.process_text.assert_called_once_with(
            "The Earth is round.", min_check_worthiness=0.5, max_claims=3
        )


def test_factcheck_endpoint_input_validation(test_client):
    """Test input validation for factcheck endpoint."""
    # Empty text
    request_data = {"text": "", "options": {}}

    response = test_client.post("/api/v1/factcheck", json=request_data)
    assert response.status_code == 422  # Validation error

    # Text too long
    request_data = {"text": "A" * 10001, "options": {}}  # Assuming 10000 is the limit

    response = test_client.post("/api/v1/factcheck", json=request_data)
    assert response.status_code == 422  # Validation error

    # Invalid options
    request_data = {
        "text": "The Earth is round.",
        "options": {"min_check_worthiness": 1.5},  # Should be 0-1
    }

    response = test_client.post("/api/v1/factcheck", json=request_data)
    assert response.status_code == 422  # Validation error


def test_factcheck_endpoint_error_handling(test_client, mock_pipeline):
    """Test error handling in factcheck endpoint."""
    # Configure the mock to raise an exception
    mock_pipeline.process_text.side_effect = Exception("Test error")

    # Patch the pipeline dependency
    with patch("src.api.dependencies.get_pipeline", return_value=mock_pipeline):
        # Create test request
        request_data = {"text": "The Earth is round.", "options": {}}

        # Make request to the endpoint
        response = test_client.post("/api/v1/factcheck", json=request_data)

        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "detail" in data


def test_factcheck_batch_endpoint(test_client, mock_pipeline):
    """Test the batch factcheck endpoint."""
    # Configure the mock to return multiple results
    mock_pipeline.process_text.side_effect = [
        [
            Verdict(
                claim="The Earth is round",
                verdict="true",
                confidence=0.95,
                explanation="Multiple scientific observations confirm Earth's spherical shape.",
                sources=["https://example.com/earth-shape"],
            )
        ],
        [
            Verdict(
                claim="The sky is blue",
                verdict="partially_true",
                confidence=0.85,
                explanation="The sky appears blue due to Rayleigh scattering, but can be other colors at sunrise/sunset.",
                sources=["https://example.com/sky-color"],
            )
        ],
    ]

    # Patch the pipeline dependency
    with patch("src.api.dependencies.get_pipeline", return_value=mock_pipeline):
        # Create test request
        request_data = {
            "texts": ["The Earth is round.", "The sky is blue."],
            "options": {"min_check_worthiness": 0.5},
        }

        # Make request to the endpoint
        response = test_client.post("/api/v1/factcheck/batch", json=request_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["verdicts"][0]["claim"] == "The Earth is round"
        assert data["results"][1]["verdicts"][0]["claim"] == "The sky is blue"


def test_factcheck_with_auth(test_client, mock_pipeline, mock_auth):
    """Test factcheck endpoint with authentication."""
    # Patch dependencies
    with patch("src.api.dependencies.get_pipeline", return_value=mock_pipeline):
        with patch("src.api.dependencies.get_auth_service", return_value=mock_auth):
            # Create test request
            request_data = {"text": "The Earth is round.", "options": {}}

            # Make request with auth header
            response = test_client.post(
                "/api/v1/factcheck",
                json=request_data,
                headers={"Authorization": "Bearer test_token"},
            )

            # Verify response
            assert response.status_code == 200

            # Verify auth was checked
            mock_auth.validate_token.assert_called_once_with("test_token")


def test_rate_limiting(test_client, mock_pipeline):
    """Test rate limiting on the factcheck endpoint."""
    # This test is more of a placeholder as proper rate limiting would need
    # to be tested with integration tests that maintain state between requests

    # Patch the pipeline dependency
    with patch("src.api.dependencies.get_pipeline", return_value=mock_pipeline):
        # Create test request
        request_data = {"text": "The Earth is round.", "options": {}}

        # Make multiple requests to test rate limiting
        for _ in range(5):  # Assuming rate limit is higher than 5
            response = test_client.post("/api/v1/factcheck", json=request_data)
            assert response.status_code == 200  # Should all succeed

        # Note: If rate limiting is implemented, this test would need to be adjusted
        # to account for the specific rate limits and reset periods
