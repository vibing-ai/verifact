"""
Tests for the EvidenceHunter agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.claim_detector import Claim
from src.models.factcheck import Evidence


@pytest.fixture
def mock_evidence():
    """Return mock evidence for testing."""
    return [
        Evidence(
            text="The Earth is approximately 4.54 billion years old, with an error range of about 50 million years.",
            source="https://example.com/earth-age",
            source_name="Scientific Journal",
            relevance=0.95,
            stance="supporting",
            credibility=0.9
        ),
        Evidence(
            text="Radiometric age dating of meteorites has shown that they, and therefore the Solar System, formed between 4.53 and 4.58 billion years ago.",
            source="https://example.com/meteorite-age",
            source_name="Science Organization",
            relevance=0.85,
            stance="supporting",
            credibility=0.92
        )
    ]


@pytest.fixture
def evidence_hunter():
    """Return an instance of EvidenceHunter for testing."""
    return EvidenceHunter(model_name="test-model")


@pytest.mark.asyncio
async def test_gather_evidence_success(evidence_hunter, mock_evidence):
    """Test successful evidence gathering."""
    # Mock the Agent.run method to return mock evidence
    with patch("agents.Runner.run") as mock_run:
        mock_result = AsyncMock()
        mock_result.output = mock_evidence
        mock_run.return_value = mock_result
        
        # Create a test claim
        claim = Claim(
            text="The Earth is 4.5 billion years old.", 
            context="In a discussion about planetary formation.",
            checkworthy=True
        )
        
        # Call gather_evidence
        result = await evidence_hunter.gather_evidence(claim)
        
        # Verify the result
        assert len(result) == 2
        assert result[0].source == "https://example.com/earth-age"
        assert result[1].stance == "supporting"
        assert mock_run.called


@pytest.mark.asyncio
async def test_gather_evidence_empty_result(evidence_hunter):
    """Test evidence gathering with no results."""
    # Mock the Agent.run method to return empty results
    with patch("agents.Runner.run") as mock_run:
        mock_result = AsyncMock()
        mock_result.output = []
        mock_run.return_value = mock_result
        
        # Create a test claim
        claim = Claim(
            text="The Earth is flat.", 
            context="In a discussion about conspiracy theories.",
            checkworthy=True
        )
        
        # Call gather_evidence
        result = await evidence_hunter.gather_evidence(claim)
        
        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0
        assert mock_run.called


@pytest.mark.asyncio
async def test_gather_evidence_exception(evidence_hunter):
    """Test evidence gathering when an exception occurs."""
    # Mock the Agent.run method to raise an exception
    with patch("agents.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test exception")
        
        # Create a test claim
        claim = Claim(
            text="The Earth is flat.", 
            context="In a discussion about conspiracy theories.",
            checkworthy=True
        )
        
        # Call gather_evidence and expect an exception
        with pytest.raises(Exception) as exc_info:
            await evidence_hunter.gather_evidence(claim)
        
        # Verify the exception
        assert "Test exception" in str(exc_info.value)
        assert mock_run.called 