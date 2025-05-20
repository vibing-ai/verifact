"""Unit tests for the ClaimDetector agent."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.claim_detector.detector import (
    Claim,
    ClaimDetector,
    ClaimDomain,
    Entity,
    EntityType,
)

# Sample test data
TEST_CLAIMS = [
    "The United States has 50 states.",
    "Global temperatures have risen by 1.1°C since pre-industrial times.",
    "COVID-19 vaccines are 95% effective at preventing serious illness.",
    "More than 8 billion people live on Earth.",
    "The average human body temperature is 98.6°F.",
]

TEST_NON_CLAIMS = [
    "I think pizza is delicious.",
    "What is the capital of France?",
    "Please consider my application.",
    "I hope you're having a great day!",
    "Let's go to the movies tonight.",
]


class MockRunner:
    """Mock implementation of the Runner class for testing."""

    @staticmethod
    async def run(agent, text):
        """Mock the OpenAI Runner.run method."""
        mock_result = MagicMock()

        # Create mock claims based on the input text
        if any(claim in text for claim in TEST_CLAIMS):
            mock_claims = []
            for test_claim in TEST_CLAIMS:
                if test_claim in text:
                    mock_claims.append(
                        Claim(
                            text=test_claim,
                            original_text=test_claim,
                            check_worthiness=0.85,
                            confidence=0.9,
                            domain=ClaimDomain.SCIENCE,
                            entities=(
                                [Entity(text="Temperature", type=EntityType.SCIENTIFIC_TERM)]
                                if "temperature" in test_claim.lower()
                                else []
                            ),
                        )
                    )
            mock_result.output = mock_claims
        else:
            mock_result.output = []

        mock_result.usage = {"prompt_tokens": 100, "completion_tokens": 50}
        return mock_result


@pytest.fixture
def claim_detector():
    """Create a ClaimDetector instance for testing."""
    with patch("src.agents.claim_detector.detector.Agent") as mock_agent:
        mock_agent.return_value = MagicMock()
        detector = ClaimDetector(min_check_worthiness=0.5)
        yield detector


@pytest.mark.asyncio
async def test_detect_claims(claim_detector):
    """Test the detect_claims method."""
    # Create test text with multiple claims
    test_text = " ".join(TEST_CLAIMS[:3])

    # Mock Runner.run to return predetermined claims
    with patch("src.agents.claim_detector.detector.Runner", MockRunner):
        # Call the method and verify results
        claims = await claim_detector.detect_claims(test_text)

        # Verify results
        assert len(claims) == 3
        assert all(isinstance(claim, Claim) for claim in claims)
        assert all(claim.check_worthiness >= 0.5 for claim in claims)


@pytest.mark.asyncio
async def test_detect_claims_with_threshold(claim_detector):
    """Test the detect_claims method with custom threshold."""
    # Create test text with multiple claims
    test_text = " ".join(TEST_CLAIMS[:3])

    # Set a high threshold that should filter out all claims
    threshold = 0.95

    # Mock Runner.run to return predetermined claims
    with patch("src.agents.claim_detector.detector.Runner", MockRunner):
        # Call the method
        results = await claim_detector.detect_claims(test_text, min_check_worthiness=threshold)

        # Verify no results due to high threshold
        assert len(results) == 0


@pytest.mark.asyncio
async def test_detect_claims_with_metrics(claim_detector):
    """Test the detect_claims method with metrics tracking."""
    # Create test text with one claim
    test_text = TEST_CLAIMS[0]

    # Create expected claims
    expected_claims = [{"text": TEST_CLAIMS[0], "check_worthiness": 0.9, "domain": "politics"}]

    # Mock metrics tracker
    mock_metrics = MagicMock()
    claim_detector.metrics = mock_metrics

    # Mock Runner.run to return predetermined claims
    with patch("src.agents.claim_detector.detector.Runner", MockRunner):
        # Call the method
        await claim_detector.detect_claims(test_text, expected_claims=expected_claims)

        # Verify metrics tracking was called
        mock_metrics.track_claim_detection.assert_called_once()


def test_score_check_worthiness(claim_detector):
    """Test the check-worthiness scoring algorithm."""
    # Test with highly specific claim
    specific_claim = "Global temperatures have risen by 1.1°C since pre-industrial times."
    specific_score = claim_detector.score_check_worthiness(specific_claim)

    # Test with opinion
    opinion = "I think global warming is a serious issue."
    opinion_score = claim_detector.score_check_worthiness(opinion)

    # Specific claim should score higher than opinion
    assert specific_score > opinion_score

    # Test with public interest claim
    public_claim = "The President signed a new climate bill yesterday."
    public_score = claim_detector.score_check_worthiness(public_claim)

    # Public interest claim should score high
    assert public_score > 0.6


def test_extract_entities(claim_detector):
    """Test entity extraction."""
    # Test with entities
    text_with_entities = "John Smith met with Apple CEO Tim Cook in New York on January 15, 2023."
    entities = claim_detector.extract_entities(text_with_entities)

    # Should extract people, organization, location, and date
    assert len(entities) >= 3

    # Verify entity types
    entity_types = [e.type for e in entities]
    assert EntityType.PERSON in entity_types

    # Test with no entities
    text_without_entities = "This text has no named entities."
    no_entities = claim_detector.extract_entities(text_without_entities)
    assert len(no_entities) == 0


def test_normalize_claim(claim_detector):
    """Test claim normalization."""
    # Test with abbreviations
    claim_with_abbr = "The US and UK are members of NATO."
    normalized = claim_detector.normalize_claim(claim_with_abbr)

    # Should expand abbreviations
    assert "United States" in normalized
    assert "United Kingdom" in normalized

    # Test with percentages
    claim_with_percent = "Inflation rose by 5% last year."
    normalized = claim_detector.normalize_claim(claim_with_percent)

    # Should standardize percentage format
    assert "5 percent" in normalized


def test_classify_domain(claim_detector):
    """Test domain classification."""
    # Test political claim
    political_claim = "The President announced a new policy for immigration."
    domain, subdomains = claim_detector.classify_domain(political_claim)
    assert domain == ClaimDomain.POLITICS

    # Test health claim
    health_claim = "The new drug reduces cholesterol by 30 percent."
    domain, subdomains = claim_detector.classify_domain(health_claim)
    assert domain == ClaimDomain.HEALTH

    # Test economic claim
    economic_claim = "The inflation rate has decreased to 3.2% this quarter."
    domain, subdomains = claim_detector.classify_domain(economic_claim)
    assert domain == ClaimDomain.ECONOMICS

    # Test scientific claim
    scientific_claim = "The average global temperature has increased by 1.1°C since 1880."
    domain, subdomains = claim_detector.classify_domain(scientific_claim)
    assert domain == ClaimDomain.SCIENCE


def test_split_compound_claim(claim_detector):
    """Test splitting compound claims."""
    # Test a compound claim with multiple factual assertions
    compound_claim = "The Earth is spherical and orbits the Sun, while Mars has two moons."
    split_claims = claim_detector.split_compound_claim(compound_claim)

    # Should split into multiple claims
    assert len(split_claims) > 1
    assert any("Earth is spherical" in claim for claim in split_claims)
    assert any("orbits the Sun" in claim for claim in split_claims)
    assert any("Mars has two moons" in claim for claim in split_claims)

    # Test a simple claim
    simple_claim = "Water freezes at 0 degrees Celsius."
    split_simple = claim_detector.split_compound_claim(simple_claim)

    # Should not split a simple claim
    assert len(split_simple) == 1
    assert split_simple[0] == simple_claim


def test_get_performance_metrics(claim_detector):
    """Test performance metrics calculation."""
    # Mock some data
    metrics = {
        "total_claims": 100,
        "true_positives": 80,
        "false_positives": 20,
        "false_negatives": 10,
    }

    # Set mock metrics on the detector
    claim_detector.metrics_data = metrics

    # Get performance metrics
    performance = claim_detector.get_performance_metrics()

    # Verify calculations
    assert "precision" in performance
    assert "recall" in performance
    assert "f1_score" in performance

    # Check values (precision = TP/(TP+FP), recall = TP/(TP+FN))
    assert performance["precision"] == 80 / (80 + 20)
    assert performance["recall"] == 80 / (80 + 10)
    assert performance["f1_score"] > 0  # F1 should be positive if precision and recall are positive
