"""
Tests for the VerdictWriter agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.verdict_writer import VerdictWriter
from src.agents.claim_detector import Claim
from src.models.factcheck import Evidence, Verdict


@pytest.fixture
def mock_evidence():
    """Return mock evidence for testing."""
    return [
        Evidence(
            text="Despite widespread conspiracy theories, all available scientific evidence confirms Earth is approximately spherical.",
            source="https://example.com/earth-shape",
            source_name="National Geographic",
            relevance=0.98,
            stance="contradicting",
            credibility=0.95
        ),
        Evidence(
            text="Ships disappearing hull-first over the horizon, observation of other planets, the shape of Earth's shadow on the moon during lunar eclipses, and photos from space all confirm Earth is not flat.",
            source="https://example.com/evidence-round-earth",
            source_name="Science Organization",
            relevance=0.97,
            stance="contradicting",
            credibility=0.93
        )
    ]


@pytest.fixture
def mock_verdict():
    """Return a mock verdict for testing."""
    return Verdict(
        claim="The Earth is flat",
        verdict="false",
        confidence=0.98,
        explanation="Multiple lines of scientific evidence confirm that the Earth is approximately spherical, not flat. This includes observations from space, the behavior of ships disappearing over the horizon, and the curved shadow Earth casts on the moon during lunar eclipses.",
        sources=["https://example.com/earth-shape", "https://example.com/evidence-round-earth"]
    )


@pytest.fixture
def verdict_writer():
    """Return an instance of VerdictWriter for testing."""
    return VerdictWriter(model_name="test-model")


@pytest.mark.asyncio
async def test_generate_verdict_success(verdict_writer, mock_evidence, mock_verdict):
    """Test successful verdict generation."""
    # Mock the Agent.run method to return mock verdict
    with patch("agents.Runner.run") as mock_run:
        mock_result = AsyncMock()
        mock_result.output = mock_verdict
        mock_run.return_value = mock_result
        
        # Create a test claim
        claim = Claim(
            text="The Earth is flat", 
            context="In a discussion about conspiracy theories",
            checkworthy=True
        )
        
        # Call generate_verdict
        result = await verdict_writer.generate_verdict(claim, mock_evidence)
        
        # Verify the result
        assert result.claim == "The Earth is flat"
        assert result.verdict == "false"
        assert result.confidence > 0.9
        assert len(result.sources) == 2
        assert mock_run.called


@pytest.mark.asyncio
async def test_generate_verdict_no_evidence(verdict_writer, mock_verdict):
    """Test verdict generation with no evidence."""
    # Mock the Agent.run method
    with patch("agents.Runner.run") as mock_run:
        # Set up mock to return an "unverifiable" verdict when no evidence is provided
        mock_unverifiable = Verdict(
            claim="The Earth is flat",
            verdict="unverifiable",
            confidence=0.5,
            explanation="There is insufficient evidence to verify this claim.",
            sources=[]
        )
        mock_result = AsyncMock()
        mock_result.output = mock_unverifiable
        mock_run.return_value = mock_result
        
        # Create a test claim
        claim = Claim(
            text="The Earth is flat", 
            context="In a discussion about conspiracy theories",
            checkworthy=True
        )
        
        # Call generate_verdict with empty evidence
        result = await verdict_writer.generate_verdict(claim, [])
        
        # Verify the result
        assert result.verdict == "unverifiable"
        assert result.confidence == 0.5
        assert len(result.sources) == 0
        assert mock_run.called


@pytest.mark.asyncio
async def test_generate_verdict_exception(verdict_writer, mock_evidence):
    """Test verdict generation when an exception occurs."""
    # Mock the Agent.run method to raise an exception
    with patch("agents.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test exception")
        
        # Create a test claim
        claim = Claim(
            text="The Earth is flat", 
            context="In a discussion about conspiracy theories",
            checkworthy=True
        )
        
        # Call generate_verdict and expect an exception
        with pytest.raises(Exception) as exc_info:
            await verdict_writer.generate_verdict(claim, mock_evidence)
        
        # Verify the exception
        assert "Test exception" in str(exc_info.value)
        assert mock_run.called 