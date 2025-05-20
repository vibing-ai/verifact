"""
Global pytest configuration for VeriFact tests.

This module contains global fixtures and configuration for pytest 
that are used across multiple test domains.
"""
import logging
import os
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def pytest_addoption(parser):
    """Add custom command-line options for pytest."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that call external APIs"
    )
    
    parser.addoption(
        "--model",
        action="store",
        default=None,
        help="Specify which LLM model to use for integration tests"
    )

def pytest_configure(config):
    """Configure pytest based on command-line options."""
    # Configure integration tests
    if config.getoption("--run-integration"):
        os.environ["TEST_INTEGRATION"] = "true"
    
    # Configure model for testing
    model = config.getoption("--model")
    if model:
        os.environ["TEST_MODEL"] = model
    
    # Register custom markers
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "slow: mark tests that take a long time to run")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment before all tests."""
    # Use testing-specific settings
    os.environ["ENVIRONMENT"] = "test"
    os.environ["REDIS_ENABLED"] = "false"  # Use in-memory cache for tests
    
    yield
    
    # Clean up after all tests
    # (Add any cleanup code here if needed)


@pytest.fixture
def sample_text():
    """Return a sample text with multiple factual claims for testing."""
    return (
        "The Earth is approximately 4.54 billion years old. Water covers about 71% of the "
        "Earth's surface. Mount Everest is the highest mountain on Earth with a height of "
        "8,848.86 meters above sea level. I think chocolate ice cream is the best flavor, "
        "but some people prefer vanilla."
    )


@pytest.fixture
def mock_openai_client():
    """Return a mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Mocked response content"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


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
def mock_web_search():
    """Return a mock web search function for testing."""
    def mock_search(query, max_results=5):
        """Mock web search function."""
        return [
            {
                "title": f"Result for {query} - Example Site",
                "link": f"https://example.com/result?q={query.replace(' ', '+')}",
                "snippet": f"This is a sample result for the query: {query}. It contains information relevant to the search.",
            }
            for i in range(max_results)
        ]
    
    return mock_search


@pytest.fixture
def env_setup():
    """Set up environment variables for testing and restore them afterward."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["OPENAI_API_KEY"] = "test_api_key"
    os.environ["SEARCH_API_KEY"] = "test_search_key"
    os.environ["DEBUG"] = "True"
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Integration testing fixtures

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
            "text": "In the heliocentric model of the solar system, the Earth and other planets orbit around the Sun.",
            "source": "https://example.edu/astronomy/solar-system",
            "credibility": 0.95,
            "stance": "supporting",
        },
        {
            "text": "The Earth completes one orbit around the Sun every 365.25 days, which we measure as one year.",
            "source": "https://example.org/astronomy/earth-orbit",
            "credibility": 0.92,
            "stance": "supporting",
        },
    ]


@pytest.fixture
def false_claim_evidence():
    """Return evidence contradicting a false claim."""
    return [
        {
            "text": "The geocentric model which claimed the Sun orbits the Earth was disproven by Copernicus, Galileo, and other astronomers.",
            "source": "https://example.edu/history-of-astronomy",
            "credibility": 0.97,
            "stance": "refuting",
        },
        {
            "text": "All modern astronomical observations confirm that the Earth orbits the Sun, not vice versa.",
            "source": "https://example.nasa.gov/astronomy/basics",
            "credibility": 0.99,
            "stance": "refuting",
        },
        {
            "text": "No recent scientific studies have concluded that the Sun orbits the Earth.",
            "source": "https://example.org/fact-check/astronomy",
            "credibility": 0.93,
            "stance": "refuting",
        },
    ]


@pytest.fixture
def partially_true_claim_evidence():
    """Return mixed evidence for a partially true claim."""
    return [
        {
            "text": "COVID-19 vaccines have shown high efficacy rates, typically between 70-95% in preventing symptomatic disease.",
            "source": "https://example.cdc.gov/vaccine-efficacy",
            "credibility": 0.96,
            "stance": "partially_supporting",
        },
        {
            "text": "Vaccine effectiveness varies by variant and tends to wane over time.",
            "source": "https://example.org/covid-research/variants",
            "credibility": 0.92,
            "stance": "partially_refuting",
        },
        {
            "text": "No vaccine provides 100% protection against all variants.",
            "source": "https://example.who.int/covid-vaccines",
            "credibility": 0.98,
            "stance": "refuting",
        },
    ]


@pytest.fixture
def unverifiable_claim_evidence():
    """Return evidence for an unverifiable claim."""
    return [
        {
            "text": "Scientists estimate there may be billions of planets capable of supporting life in our galaxy.",
            "source": "https://example.nasa.gov/exoplanets",
            "credibility": 0.90,
            "stance": "neutral",
        },
        {
            "text": "No conclusive evidence of extraterrestrial civilizations has been found to date.",
            "source": "https://example.seti.org/search-results",
            "credibility": 0.95,
            "stance": "neutral",
        },
        {
            "text": "Current technology limits our ability to detect alien civilizations beyond our solar system.",
            "source": "https://example.astro.org/limitations",
            "credibility": 0.88,
            "stance": "neutral",
        },
    ]


@pytest.fixture
def mock_claim_detector():
    """Return a mock ClaimDetector that returns predetermined claims."""
    mock = MagicMock()
    
    async def mock_detect_claims(text):
        """Mock the detect_claims method."""
        if "Earth" in text:
            return [
                {
                    "text": "The Earth is approximately 4.54 billion years old.",
                    "check_worthiness": 0.95,
                    "domain": "science"
                }
            ]
        elif "COVID" in text:
            return [
                {
                    "text": "COVID-19 vaccines are effective at preventing severe illness.",
                    "check_worthiness": 0.90,
                    "domain": "health"
                }
            ]
        else:
            return []
    
    mock.detect_claims = mock_detect_claims
    return mock


@pytest.fixture
def mock_evidence_hunter():
    """Return a mock EvidenceHunter that returns predetermined evidence."""
    mock = MagicMock()
    
    async def mock_gather_evidence(claim):
        """Mock the gather_evidence method."""
        if "Earth" in claim:
            return [
                {
                    "text": "Scientific evidence suggests Earth formed about 4.54 billion years ago.",
                    "source": "https://example.com/earth-age",
                    "credibility": 0.95,
                    "stance": "supporting"
                },
                {
                    "text": "Radiometric dating confirms Earth is several billion years old.",
                    "source": "https://example.org/geological-evidence",
                    "credibility": 0.92,
                    "stance": "supporting"
                }
            ]
        elif "vaccine" in claim.lower() or "covid" in claim.lower():
            return [
                {
                    "text": "Studies show COVID-19 vaccines reduce risk of severe illness by 90%+.",
                    "source": "https://example.gov/vaccine-studies",
                    "credibility": 0.96,
                    "stance": "supporting"
                },
                {
                    "text": "Vaccine effectiveness may vary by variant and age group.",
                    "source": "https://example.org/variant-studies",
                    "credibility": 0.90,
                    "stance": "partially_supporting"
                }
            ]
        else:
            return []
    
    mock.gather_evidence = mock_gather_evidence
    return mock


@pytest.fixture
def mock_verdict_writer():
    """Return a mock VerdictWriter that returns predetermined verdicts."""
    mock = MagicMock()
    
    async def mock_generate_verdict(claim, evidence):
        """Mock the generate_verdict method."""
        if any(e.get("stance") == "supporting" for e in evidence):
            return {
                "claim": claim,
                "verdict": "true",
                "confidence": 0.92,
                "explanation": "The evidence strongly supports this claim.",
                "sources": [e.get("source") for e in evidence]
            }
        elif any(e.get("stance") == "refuting" for e in evidence):
            return {
                "claim": claim,
                "verdict": "false",
                "confidence": 0.88,
                "explanation": "The evidence contradicts this claim.",
                "sources": [e.get("source") for e in evidence]
            }
        elif any(e.get("stance") == "partially_supporting" for e in evidence):
            return {
                "claim": claim,
                "verdict": "partially true",
                "confidence": 0.75,
                "explanation": "The evidence partially supports this claim with some caveats.",
                "sources": [e.get("source") for e in evidence]
            }
        else:
            return {
                "claim": claim,
                "verdict": "unverifiable",
                "confidence": 0.60,
                "explanation": "There is insufficient evidence to verify this claim.",
                "sources": [e.get("source") for e in evidence] if evidence else []
            }
    
    mock.generate_verdict = mock_generate_verdict
    return mock


@pytest.fixture
def mock_pipeline_config():
    """Return a mock pipeline configuration for testing."""
    return {
        "min_checkworthiness": 0.7,
        "max_claims": 3,
        "evidence_per_claim": 3,
        "timeout_seconds": 30.0,
        "enable_fallbacks": True,
        "retry_attempts": 1,
        "include_debug_info": True
    }


@pytest.fixture
def vcr_search_results():
    """Return mock search results for testing."""
    return [
        {
            "title": "Earth's age determined to be 4.54 billion years",
            "link": "https://example.com/earth-age",
            "snippet": "Scientific studies using radiometric dating have determined the Earth is approximately 4.54 billion years old, with an uncertainty of less than 1 percent."
        },
        {
            "title": "How scientists measure the age of Earth",
            "link": "https://example.org/dating-methods",
            "snippet": "Geologists use multiple methods including uranium-lead dating of zircon crystals to establish that Earth formed about 4.5 billion years ago."
        },
        {
            "title": "History of Earth's formation",
            "link": "https://example.edu/earth-formation",
            "snippet": "The Earth formed approximately 4.54 billion years ago by accretion from the solar nebula. This age has been confirmed by multiple dating methods."
        }
    ] 