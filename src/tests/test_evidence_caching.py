"""Tests for the EvidenceHunter's Redis caching functionality."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.verifact_agents.claim_detector.detector import Claim
from src.verifact_agents.evidence_hunter.hunter import Evidence, EvidenceHunter
from src.utils.cache.cache import evidence_cache

# Set up test environment
os.environ["REDIS_ENABLED"] = "true"
os.environ["EVIDENCE_CACHE_TTL"] = "3600"


@pytest.fixture
def mock_runner():
    """Mock the OpenAI agent Runner to avoid actual API calls."""
    with patch("openai.agents.Runner.run") as mock_run:
        # Create mock evidence
        mock_evidence = [
            Evidence(
                content="Test evidence content 1",
                source="https://example.com/1",
                relevance=0.9,
                stance="supporting",
            ),
            Evidence(
                content="Test evidence content 2",
                source="https://example.com/2",
                relevance=0.8,
                stance="contradicting",
            ),
        ]

        # Setup the mock response
        mock_response = MagicMock()
        mock_response.output = mock_evidence
        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 200}

        mock_run.return_value = mock_response
        yield mock_run


@pytest.fixture
def test_claim():
    """Create a test claim for consistent testing."""
    return Claim(
        text="The Earth is flat.",
        context="Testing cache functionality",
        source="test",
        confidence=1.0,
    )


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the cache before and after each test."""
    evidence_cache.clear_namespace()
    yield
    evidence_cache.clear_namespace()


@pytest.mark.asyncio
async def test_cache_miss_and_store(mock_runner, test_claim):
    """Test that cache miss triggers API call and stores result."""
    hunter = EvidenceHunter()

    # First call should miss cache and call API
    result = await hunter.gather_evidence(test_claim)

    # Verify API was called
    mock_runner.assert_called_once()
    assert len(result) == 2

    # Reset mock for next assertion
    mock_runner.reset_mock()

    # Generate cache key to verify it exists in cache
    cache_key = hunter._generate_cache_key(test_claim)
    assert evidence_cache.exists(cache_key)


@pytest.mark.asyncio
async def test_cache_hit(mock_runner, test_claim):
    """Test that cache hit prevents API call."""
    hunter = EvidenceHunter()

    # First call to populate cache
    await hunter.gather_evidence(test_claim)

    # Reset mock to verify second call doesn't use it
    mock_runner.reset_mock()

    # Second call should hit cache
    result = await hunter.gather_evidence(test_claim)

    # Verify API was not called
    mock_runner.assert_not_called()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_similar_claims_use_same_cache(mock_runner):
    """Test that similar claims with different wording use the same cache entry."""
    hunter = EvidenceHunter()

    # Original claim
    original_claim = Claim(
        text="The Earth is flat.",
        context="Testing cache functionality",
        source="test",
        confidence=1.0,
    )

    # Similar claim (different capitalization, punctuation)
    similar_claim = Claim(
        text="THE EARTH IS FLAT!",
        context="Testing cache functionality",
        source="test",
        confidence=1.0,
    )

    # First call to populate cache
    await hunter.gather_evidence(original_claim)

    # Reset mock to verify second call doesn't use it
    mock_runner.reset_mock()

    # Call with similar claim should hit cache
    result = await hunter.gather_evidence(similar_claim)

    # Verify API was not called
    mock_runner.assert_not_called()
    assert len(result) == 2

    # Verify both claims generate the same cache key
    original_key = hunter._generate_cache_key(original_claim)
    similar_key = hunter._generate_cache_key(similar_claim)
    assert original_key == similar_key


@pytest.mark.asyncio
async def test_different_claims_use_different_cache(mock_runner):
    """Test that different claims use different cache entries."""
    hunter = EvidenceHunter()

    # First claim
    claim1 = Claim(
        text="The Earth is flat.",
        context="Testing cache functionality",
        source="test",
        confidence=1.0,
    )

    # Different claim
    claim2 = Claim(
        text="The Moon is made of cheese.",
        context="Testing cache functionality",
        source="test",
        confidence=1.0,
    )

    # First call to populate cache for claim1
    await hunter.gather_evidence(claim1)

    # Reset mock to verify second call does use it
    mock_runner.reset_mock()

    # Call with different claim should miss cache
    await hunter.gather_evidence(claim2)

    # Verify API was called for the second claim
    mock_runner.assert_called_once()

    # Verify the claims generate different cache keys
    key1 = hunter._generate_cache_key(claim1)
    key2 = hunter._generate_cache_key(claim2)
    assert key1 != key2
