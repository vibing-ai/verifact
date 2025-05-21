"""Tests for the VerdictWriter agent.

Combines both unit tests and standalone testing script functionality.
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter.hunter import Evidence as StandaloneEvidence
from src.verifact_agents.verdict_writer import VerdictWriter
from src.verifact_agents.verdict_writer.writer import VerdictWriter as StandaloneVerdictWriter
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
            credibility=0.95,
        ),
        Evidence(
            text="Ships disappearing hull-first over the horizon, observation of other planets, the shape of Earth's shadow on the moon during lunar eclipses, and photos from space all confirm Earth is not flat.",
            source="https://example.com/evidence-round-earth",
            source_name="Science Organization",
            relevance=0.97,
            stance="contradicting",
            credibility=0.93,
        ),
    ]


@pytest.fixture
def mock_verdict():
    """Return a mock verdict for testing."""
    return Verdict(
        claim="The Earth is flat",
        verdict="false",
        confidence=0.98,
        explanation="Multiple lines of scientific evidence confirm that the Earth is approximately spherical, not flat. This includes observations from space, the behavior of ships disappearing over the horizon, and the curved shadow Earth casts on the moon during lunar eclipses.",
        sources=["https://example.com/earth-shape", "https://example.com/evidence-round-earth"],
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
            checkworthy=True,
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
            sources=[],
        )
        mock_result = AsyncMock()
        mock_result.output = mock_unverifiable
        mock_run.return_value = mock_result

        # Create a test claim
        claim = Claim(
            text="The Earth is flat",
            context="In a discussion about conspiracy theories",
            checkworthy=True,
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
            checkworthy=True,
        )

        # Call generate_verdict and expect an exception
        with pytest.raises(Exception) as exc_info:
            await verdict_writer.generate_verdict(claim, mock_evidence)

        # Verify the exception
        assert "Test exception" in str(exc_info.value)
        assert mock_run.called


# Standalone test function merged from root test_verdict_writer.py
@pytest.mark.skip("Manual standalone test script - run directly if needed")
async def test_verdict_writer_standalone():
    """Test the VerdictWriter component (standalone version)."""
    print("\n=== Testing VerdictWriter ===\n")

    writer = StandaloneVerdictWriter()

    # Test cases with different claim/evidence combinations
    test_cases = [
        {
            "name": "True claim with strong supporting evidence",
            "claim": Claim(
                text="The Earth is approximately 4.54 billion years old",
                context="Discussion about planetary science",
                checkworthy=True,
            ),
            "evidence": [
                StandaloneEvidence(
                    content="Scientists have determined that the Earth is 4.54 billion years old with an error range of less than 1 percent.",
                    source="https://example.edu/earth-age",
                    relevance=0.95,
                    stance="supporting",
                ),
                StandaloneEvidence(
                    content="Radiometric dating of meteorites has shown that they, and therefore the Solar System, formed between 4.53 and 4.58 billion years ago.",
                    source="https://example.gov/geological-survey",
                    relevance=0.92,
                    stance="supporting",
                ),
            ],
        },
        {
            "name": "False claim with contradicting evidence",
            "claim": Claim(
                text="The Earth is flat",
                context="Discussion about conspiracy theories",
                checkworthy=True,
            ),
            "evidence": [
                StandaloneEvidence(
                    content="Multiple lines of evidence confirm Earth is approximately spherical, including direct observation from space, the curved shadow during lunar eclipses, and the way ships disappear hull-first over the horizon.",
                    source="https://example.edu/earth-shape",
                    relevance=0.98,
                    stance="contradicting",
                ),
                StandaloneEvidence(
                    content="All space agencies worldwide have captured images showing Earth's spherical shape, and no credible scientific evidence supports a flat Earth.",
                    source="https://example.gov/space-imagery",
                    relevance=0.97,
                    stance="contradicting",
                ),
            ],
        },
        {
            "name": "Partially true claim with mixed evidence",
            "claim": Claim(
                text="COVID-19 vaccines are 100% effective at preventing infection",
                context="Discussion about vaccine efficacy",
                checkworthy=True,
            ),
            "evidence": [
                StandaloneEvidence(
                    content="COVID-19 vaccines have demonstrated high efficacy rates, typically between 70-95% in preventing symptomatic disease in clinical trials.",
                    source="https://example.gov/vaccine-efficacy",
                    relevance=0.96,
                    stance="partially_supporting",
                ),
                StandaloneEvidence(
                    content="Breakthrough infections can still occur in fully vaccinated individuals, though they are generally less severe than infections in unvaccinated people.",
                    source="https://example.org/breakthrough-infections",
                    relevance=0.95,
                    stance="partially_contradicting",
                ),
            ],
        },
    ]

    # Test each case
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        print(f'Claim: "{case["claim"].text}"')
        print(f"Evidence: {len(case['evidence'])} pieces")

        try:
            # Time the verdict generation process
            start = time.time()

            # Generate verdict
            verdict = await writer.generate_verdict(case["claim"], case["evidence"])

            duration = time.time() - start
            print(f"Verdict generation took {duration:.2f} seconds")

            # Display results
            print(f"Verdict: {verdict.verdict}")
            print(f"Confidence: {verdict.confidence}")
            print(
                f"Explanation: {verdict.explanation[:300]}..."
                if len(verdict.explanation) > 300
                else f"Explanation: {verdict.explanation}"
            )
            print("Sources:")
            for source in verdict.sources:
                print(f"  - {source}")

        except Exception as e:
            print(f"Error during verdict generation: {e}")

    print("\n=== VerdictWriter Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_verdict_writer_standalone())
