"""End-to-end tests for the VeriFact pipeline.

These tests use the actual agents and make real API calls.
They are marked with the 'e2e' marker and can be skipped in CI.
To run these tests, use: pytest -m e2e
"""

import os
import pytest
from dotenv import load_dotenv

from src.verifact_manager import VerifactManager, ManagerConfig
from src.verifact_agents.verdict_writer import Verdict

# Load environment variables
load_dotenv()

# Skip all tests in this module if the OPENAI_API_KEY is not set
pytestmark = [
    pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY") is None,
        reason="OPENAI_API_KEY environment variable not set"
    ),
    pytest.mark.e2e  # Mark all tests as end-to-end tests
]


@pytest.fixture
def manager():
    """Create a VerifactManager instance for testing."""
    config = ManagerConfig(
        min_checkworthiness=0.5,
        max_claims=2,  # Limit to 2 claims to reduce API costs
        evidence_per_claim=2,  # Limit to 2 evidence pieces per claim
        timeout_seconds=60.0,
        enable_fallbacks=True,
        retry_attempts=1,
        raise_exceptions=True,
        include_debug_info=False,
    )
    return VerifactManager(config)


@pytest.mark.asyncio
async def test_simple_factual_statement(manager):
    """Test the pipeline with a simple factual statement."""
    # A simple, verifiable factual statement
    text = "The Earth is the third planet from the Sun in our solar system."

    # Run the pipeline
    results = await manager.run(text)

    # Verify results
    assert len(results) > 0
    assert all(isinstance(verdict, Verdict) for verdict in results)

    # The statement should be true
    assert any(verdict.verdict == "true" for verdict in results)

    # Check that explanations and sources are provided
    for verdict in results:
        assert len(verdict.explanation) > 0
        assert len(verdict.sources) > 0


@pytest.mark.asyncio
async def test_false_statement(manager):
    """Test the pipeline with a false statement."""
    # A false statement
    text = "The Earth is flat and sits at the center of our solar system."

    # Run the pipeline
    results = await manager.run(text)

    # Verify results
    assert len(results) > 0
    assert all(isinstance(verdict, Verdict) for verdict in results)

    # The statement should be false
    assert any(verdict.verdict == "false" for verdict in results)

    # Check that explanations and sources are provided
    for verdict in results:
        assert len(verdict.explanation) > 0
        assert len(verdict.sources) > 0


@pytest.mark.asyncio
async def test_multiple_claims(manager):
    """Test the pipeline with text containing multiple claims."""
    # Text with multiple claims
    text = """
    The United States has the largest military budget in the world.
    Vaccines have been proven to cause autism in children.
    """

    # Run the pipeline
    results = await manager.run(text)

    # Verify results
    assert len(results) > 0
    assert all(isinstance(verdict, Verdict) for verdict in results)

    # Check that we have at least one true and one false verdict
    verdicts = [verdict.verdict for verdict in results]
    assert any(v == "true" for v in verdicts) or any(v == "partially true" for v in verdicts)
    assert any(v == "false" for v in verdicts)

    # Check that explanations and sources are provided
    for verdict in results:
        assert len(verdict.explanation) > 0
        assert len(verdict.sources) > 0


@pytest.mark.asyncio
async def test_no_claims(manager):
    """Test the pipeline with text containing no clear factual claims."""
    # Text with no clear factual claims
    text = "I wonder what the weather will be like tomorrow. Maybe I should bring an umbrella just in case."

    # Run the pipeline
    results = await manager.run(text)

    # Verify results - should be empty or have unverifiable claims
    if results:
        assert all(isinstance(verdict, Verdict) for verdict in results)
        assert all(verdict.verdict == "unverifiable" for verdict in results)
    else:
        assert results == []


@pytest.mark.asyncio
async def test_partially_true_claim(manager):
    """Test the pipeline with a partially true claim."""
    # A partially true statement
    text = "Coffee is the most consumed beverage in the world."

    # Run the pipeline
    results = await manager.run(text)

    # Verify results
    assert len(results) > 0
    assert all(isinstance(verdict, Verdict) for verdict in results)

    # The statement should be partially true or false (water is actually most consumed)
    verdicts = [verdict.verdict for verdict in results]
    assert any(v in ["partially true", "false"] for v in verdicts)

    # Check that explanations and sources are provided
    for verdict in results:
        assert len(verdict.explanation) > 0
        assert len(verdict.sources) > 0


@pytest.mark.asyncio
async def test_unverifiable_claim(manager):
    """Test the pipeline with an unverifiable claim."""
    # An unverifiable statement
    text = "There is intelligent alien life in our galaxy."

    # Run the pipeline
    results = await manager.run(text)

    # Verify results
    assert len(results) > 0
    assert all(isinstance(verdict, Verdict) for verdict in results)

    # The statement should be unverifiable or have low confidence
    for verdict in results:
        assert verdict.verdict == "unverifiable" or verdict.confidence < 0.7
        assert len(verdict.explanation) > 0
        assert len(verdict.sources) > 0


@pytest.mark.asyncio
async def test_subjective_claim(manager):
    """Test the pipeline with a subjective claim that should be unverifiable."""
    # A subjective statement
    text = "Chocolate ice cream tastes better than vanilla ice cream."

    # Run the pipeline
    results = await manager.run(text)

    # Verify results - should be empty or have unverifiable claims
    if results:
        assert all(isinstance(verdict, Verdict) for verdict in results)
        assert all(verdict.verdict == "unverifiable" for verdict in results)

        # Check that explanations mention subjectivity
        for verdict in results:
            assert any(term in verdict.explanation.lower() for term in ["subjective", "opinion", "preference", "taste"])
    else:
        # If no claims were detected, that's also acceptable
        assert results == []
