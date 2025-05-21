"""Tests for the EvidenceHunter agent.

Combines both unit tests and standalone testing script functionality.
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from src.verifact_agents.claim_detector.detector import Claim
from src.verifact_agents.evidence_hunter.hunter import Evidence, EvidenceHunter


@pytest.fixture
def mock_evidence():
    """Create mock evidence for testing."""
    return [
        Evidence(
            content="The Earth is approximately 4.54 billion years old based on radiometric dating of meteorites.",
            source="https://example.com/earth-age",
            relevance=0.95,
            stance="supporting",
        ),
        Evidence(
            content="Studies of rocks from the Moon, as well as meteorites, support an age of around 4.5 billion years for Earth.",
            source="https://example.org/planetary-science",
            relevance=0.9,
            stance="supporting",
        ),
    ]


@pytest.fixture
def evidence_hunter():
    """Create an EvidenceHunter instance for testing."""
    with patch("src.utils.search_tools.get_search_tool") as mock_get_search_tool:
        mock_get_search_tool.return_value = "mock_search_tool"
        with patch("src.agents.evidence_hunter.hunter.Agent"):
            return EvidenceHunter(model_name="test/model")


@pytest.mark.asyncio
async def test_gather_evidence_success(evidence_hunter, mock_evidence):
    """Test successful evidence gathering."""
    # Mock the Agent.run method to return mock evidence
    with patch("openai.agents.Runner.run") as mock_run:
        mock_result = AsyncMock()
        mock_result.output = mock_evidence
        mock_run.return_value = mock_result

        # Create a test claim
        claim = Claim(
            text="The Earth is 4.5 billion years old.",
            context="In a discussion about planetary formation.",
            checkworthy=True,
        )

        # Call gather_evidence
        result = await evidence_hunter.gather_evidence(claim)

        # Verify the result
        assert len(result) == 2
        assert result[0].source == "https://example.com/earth-age"
        assert result[1].stance == "supporting"
        assert mock_run.called

        # Check the query format (should contain the enhanced instructions)
        call_args = mock_run.call_args[0]
        assert len(call_args) == 2  # (agent, query)
        assert "Claim to investigate:" in call_args[1]
        assert "Context of the claim:" in call_args[1]
        assert "1. Find evidence from credible sources" in call_args[1]


@pytest.mark.asyncio
async def test_gather_evidence_empty_result(evidence_hunter):
    """Test evidence gathering with no results."""
    # Mock the Agent.run method to return empty results
    with patch("openai.agents.Runner.run") as mock_run:
        mock_result = AsyncMock()
        mock_result.output = []
        mock_run.return_value = mock_result

        # Create a test claim
        claim = Claim(
            text="The Earth is flat.",
            context="In a discussion about conspiracy theories.",
            checkworthy=True,
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
    with patch("openai.agents.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test exception")

        # Create a test claim
        claim = Claim(
            text="The Earth is flat.",
            context="In a discussion about conspiracy theories.",
            checkworthy=True,
        )

        # Call gather_evidence and expect an exception
        with pytest.raises(Exception) as exc_info:
            await evidence_hunter.gather_evidence(claim)

        # Verify the exception
        assert "Test exception" in str(exc_info.value)
        assert mock_run.called


@pytest.mark.asyncio
async def test_evidence_hunter_initialization():
    """Test EvidenceHunter initialization with different parameters."""
    # Test with default model name
    with patch("src.utils.search_tools.get_search_tool") as mock_get_search_tool:
        mock_get_search_tool.return_value = "mock_search_tool"
        with patch("src.agents.evidence_hunter.hunter.Agent") as mock_agent:
            hunter = EvidenceHunter()

            # Verify the agent was created with the right parameters
            args, kwargs = mock_agent.call_args
            assert kwargs["name"] == "EvidenceHunter"
            assert kwargs["tools"] == ["mock_search_tool"]
            assert "evidence gathering agent" in kwargs["instructions"]

    # Test with custom model name
    with patch("src.utils.search_tools.get_search_tool") as mock_get_search_tool:
        mock_get_search_tool.return_value = "mock_search_tool"
        with patch("src.agents.evidence_hunter.hunter.Agent") as mock_agent:
            hunter = EvidenceHunter(model_name="custom/model")

            # Verify model name was set correctly
            assert hunter.model_manager.model_name == "custom/model"


# Standalone test function merged from root test_evidence_hunter.py
@pytest.mark.skip("Manual standalone test script - run directly if needed")
async def test_evidence_hunter_standalone():
    """Test the EvidenceHunter component (standalone version)."""
    print("\n=== Testing EvidenceHunter ===\n")

    hunter = EvidenceHunter()

    # Test claims of different types
    test_claims = [
        {
            "name": "Scientific fact",
            "claim": Claim(
                text="The Earth is approximately 4.54 billion years old",
                context="Discussion about the age of celestial bodies",
                checkworthy=True,
            ),
        },
        {
            "name": "Historical fact",
            "claim": Claim(
                text="World War II ended in 1945",
                context="Discussion about major historical events",
                checkworthy=True,
            ),
        },
        {
            "name": "Controversial claim",
            "claim": Claim(
                text="Climate change is primarily caused by human activities",
                context="Discussion about environmental issues",
                checkworthy=True,
            ),
        },
    ]

    # Test each claim
    for test in test_claims:
        print(f"\nTesting: {test['name']}")
        print(f'Claim: "{test["claim"].text}"')
        print(f"Context: {test['claim'].context}")

        try:
            # Time the evidence gathering process
            start = time.time()

            # Gather evidence
            evidence = await hunter.gather_evidence(test["claim"])

            duration = time.time() - start
            print(f"Evidence gathering took {duration:.2f} seconds")

            # Display results
            if evidence:
                print(f"Found {len(evidence)} pieces of evidence:")
                for i, e in enumerate(evidence):
                    print(f"\n  Evidence {i + 1}:")
                    print(
                        f"    Content: {e.content[:200]}..."
                        if len(e.content) > 200
                        else f"    Content: {e.content}"
                    )
                    print(f"    Source: {e.source}")
                    print(f"    Relevance: {e.relevance}, Stance: {e.stance}")
                    if hasattr(e, "credibility") and e.credibility:
                        print(f"    Credibility: {e.credibility}")
            else:
                print("No evidence found.")

        except Exception as e:
            print(f"Error during evidence gathering: {e}")

    print("\n=== EvidenceHunter Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_evidence_hunter_standalone())
