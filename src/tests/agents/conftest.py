"""
Pytest configuration for agent tests.

This module contains fixtures specific to agent component tests.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_claim():
    """Return a sample claim for testing."""
    return {
        "text": "The Earth is approximately 4.54 billion years old.",
        "context": "Scientific statement about Earth's age.",
        "checkworthy": True,
    }


@pytest.fixture
def sample_evidence():
    """Return sample evidence for testing."""
    return [
        {
            "text": "Scientists determined that the Earth is 4.54 billion years old.",
            "source": "https://example.com/earth-age",
            "credibility": 0.95,
            "stance": "supporting",
        },
        {
            "text": "Research suggests the Earth formed 4.5 billion years ago, with an uncertainty of 1%.",
            "source": "https://example.org/earth-formation",
            "credibility": 0.90,
            "stance": "supporting",
        },
    ]


@pytest.fixture
def mock_claim_detector():
    """Return a mock ClaimDetector for testing."""
    mock_detector = MagicMock()

    async def mock_detect_claims(text):
        """Mock claim detection."""
        return [
            {"text": "The Earth is approximately 4.54 billion years old.", "check_worthiness": 0.9},
            {"text": "Water covers about 71% of the Earth's surface.", "check_worthiness": 0.8},
        ]

    mock_detector.detect_claims = mock_detect_claims
    return mock_detector


@pytest.fixture
def mock_evidence_hunter():
    """Return a mock EvidenceHunter for testing."""
    mock_hunter = MagicMock()

    async def mock_gather_evidence(claim):
        """Mock evidence gathering."""
        return [
            {
                "text": f"Evidence for: {claim['text']}",
                "source": "https://example.com/evidence",
                "credibility": 0.9,
                "stance": "supporting",
            },
            {
                "text": f"More evidence for: {claim['text']}",
                "source": "https://example.org/more-evidence",
                "credibility": 0.85,
                "stance": "supporting",
            },
        ]

    mock_hunter.gather_evidence = mock_gather_evidence
    return mock_hunter


@pytest.fixture
def mock_verdict_writer():
    """Return a mock VerdictWriter for testing."""
    mock_writer = MagicMock()

    async def mock_generate_verdict(claim, evidence):
        """Mock verdict generation."""
        return {
            "claim": claim["text"],
            "verdict": "TRUE" if len(evidence) >= 2 else "INCONCLUSIVE",
            "confidence": 0.85,
            "explanation": f"Based on the evidence, the claim that '{claim['text']}' appears to be true.",
            "sources": [e["source"] for e in evidence],
        }

    mock_writer.generate_verdict = mock_generate_verdict
    return mock_writer


@pytest.fixture
def true_claim_text():
    """Return a text with a definitively true claim."""
    return "The Earth orbits around the Sun. This is known as a heliocentric model of our solar system."


@pytest.fixture
def false_claim_text():
    """Return a text with a definitively false claim."""
    return "The Sun orbits around the Earth. This was proven conclusively in recent studies."


@pytest.fixture
def partially_true_claim_text():
    """Return a text with a partially true claim."""
    return "COVID-19 vaccines are 100% effective against all variants and prevent all transmission."


@pytest.fixture
def unverifiable_claim_text():
    """Return a text with an unverifiable claim."""
    return "There are exactly 12,415 alien civilizations in our galaxy that have developed space travel."


@pytest.fixture
def mixed_claims_text():
    """Return a text with multiple claims of varying truth values."""
    return (
        "The COVID-19 pandemic began in late 2019. Some have claimed it was created in a lab, "
        "but most evidence points to a natural origin. Vaccines have been shown to reduce "
        "severity of symptoms and hospitalizations. New York City is the capital of the United States. "
        "Climate change is causing rising global temperatures."
    )


@pytest.fixture
def true_claim_evidence():
    """Return evidence supporting a true claim."""
    return [
        {
            "text": "The Earth orbits the Sun at an average distance of about 93 million miles (150 million kilometers).",
            "source": "https://example.nasa.gov/solar-system/earth",
            "credibility": 0.98,
            "stance": "supporting",
        },
        {
            "text": "All planets in our solar system, including Earth, revolve around the Sun in elliptical orbits.",
            "source": "https://example.edu/astronomy/solar-system",
            "credibility": 0.95,
            "stance": "supporting",
        },
    ]


@pytest.fixture
def false_claim_evidence():
    """Return evidence refuting a false claim."""
    return [
        {
            "text": "The geocentric model (Earth at center) was disproven centuries ago by observations and calculations.",
            "source": "https://example.edu/astronomy/history",
            "credibility": 0.97,
            "stance": "refuting",
        },
        {
            "text": "The Sun does not orbit the Earth. Rather, the Earth and all other planets in our solar system orbit the Sun.",
            "source": "https://example.nasa.gov/solar-system",
            "credibility": 0.99,
            "stance": "refuting",
        },
    ]


@pytest.fixture
def partially_true_claim_evidence():
    """Return evidence for a partially true claim."""
    return [
        {
            "text": "COVID-19 vaccines are highly effective at preventing severe disease and hospitalization.",
            "source": "https://example.cdc.gov/covid-vaccines",
            "credibility": 0.96,
            "stance": "partially_supporting",
        },
        {
            "text": "While COVID-19 vaccines reduce transmission, they do not completely prevent it.",
            "source": "https://example.who.int/covid-research",
            "credibility": 0.95,
            "stance": "partially_refuting",
        },
    ]


@pytest.fixture
def unverifiable_claim_evidence():
    """Return evidence for an unverifiable claim."""
    return [
        {
            "text": "Scientists estimate there could be thousands of civilizations in our galaxy, but the exact number is unknown.",
            "source": "https://example.edu/astronomy/extraterrestrial-life",
            "credibility": 0.7,
            "stance": "neutral",
        },
        {
            "text": "Current scientific methods cannot determine the exact number of alien civilizations.",
            "source": "https://example.org/seti-research",
            "credibility": 0.8,
            "stance": "neutral",
        },
    ]


# Add agent-specific fixtures here
