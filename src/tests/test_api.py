"""
Tests for the API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from src.main import app
from src.agents.claim_detector import ClaimDetector, Claim
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.verdict_writer import VerdictWriter
from src.models.factcheck import Evidence, Verdict


# Create a test client
client = TestClient(app)


@pytest.fixture
def mock_claim():
    """Return a mock claim for testing."""
    return Claim(
        text="The Earth is flat",
        context="In a discussion about conspiracy theories",
        checkworthy=True
    )


@pytest.fixture
def mock_evidence():
    """Return mock evidence for testing."""
    return [
        Evidence(
            text="Scientific evidence confirms Earth is spherical.",
            source="https://example.com/earth-shape",
            source_name="Science Organization",
            relevance=0.98,
            stance="contradicting",
            credibility=0.95
        )
    ]


@pytest.fixture
def mock_verdict():
    """Return a mock verdict for testing."""
    return Verdict(
        claim="The Earth is flat",
        verdict="false",
        confidence=0.98,
        explanation="Scientific evidence confirms Earth is spherical.",
        sources=["https://example.com/earth-shape"]
    )


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_factcheck_endpoint_success(mock_claim, mock_evidence, mock_verdict):
    """Test the factcheck endpoint with successful response."""
    # Set up mocks for the agents
    with patch("src.api.factcheck.ClaimDetector") as MockClaimDetector, \
         patch("src.api.factcheck.EvidenceHunter") as MockEvidenceHunter, \
         patch("src.api.factcheck.VerdictWriter") as MockVerdictWriter:
        
        # Configure mock claim detector
        mock_claim_detector = MagicMock()
        mock_claim_detector.detect_claims = AsyncMock(return_value=[mock_claim])
        MockClaimDetector.return_value = mock_claim_detector
        
        # Configure mock evidence hunter
        mock_evidence_hunter = MagicMock()
        mock_evidence_hunter.gather_evidence = AsyncMock(return_value=mock_evidence)
        MockEvidenceHunter.return_value = mock_evidence_hunter
        
        # Configure mock verdict writer
        mock_verdict_writer = MagicMock()
        mock_verdict_writer.generate_verdict = AsyncMock(return_value=mock_verdict)
        MockVerdictWriter.return_value = mock_verdict_writer
        
        # Make request to factcheck endpoint
        response = client.post(
            "/api/v1/factcheck",
            json={"text": "The Earth is flat", "options": {}}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        assert len(data["claims"]) == 1
        assert data["claims"][0]["verdict"] == "false"
        assert data["claims"][0]["confidence"] == 0.98
        
        # Verify agents were called
        mock_claim_detector.detect_claims.assert_called_once()
        mock_evidence_hunter.gather_evidence.assert_called_once()
        mock_verdict_writer.generate_verdict.assert_called_once()


def test_factcheck_endpoint_no_claims():
    """Test the factcheck endpoint when no claims are detected."""
    # Set up mocks for the agents
    with patch("src.api.factcheck.ClaimDetector") as MockClaimDetector:
        # Configure mock claim detector to return no claims
        mock_claim_detector = MagicMock()
        mock_claim_detector.detect_claims = AsyncMock(return_value=[])
        MockClaimDetector.return_value = mock_claim_detector
        
        # Make request to factcheck endpoint
        response = client.post(
            "/api/v1/factcheck",
            json={"text": "This is not a claim.", "options": {}}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        assert len(data["claims"]) == 0
        assert "metadata" in data
        assert "message" in data["metadata"]
        assert "No check-worthy claims detected" in data["metadata"]["message"]


def test_factcheck_endpoint_error():
    """Test the factcheck endpoint when an error occurs."""
    # Set up mocks for the agents
    with patch("src.api.factcheck.ClaimDetector") as MockClaimDetector:
        # Configure mock claim detector to raise an exception
        mock_claim_detector = MagicMock()
        mock_claim_detector.detect_claims = AsyncMock(side_effect=Exception("Test exception"))
        MockClaimDetector.return_value = mock_claim_detector
        
        # Make request to factcheck endpoint
        response = client.post(
            "/api/v1/factcheck",
            json={"text": "The Earth is flat", "options": {}}
        )
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "An error occurred" in data["detail"] 