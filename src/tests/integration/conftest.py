"""Pytest configuration for integration tests.

This module contains fixtures specific to integration tests.
"""

import pytest


@pytest.fixture
def mock_pipeline_config():
    """Return a mock pipeline configuration for testing."""
    return {
        "model": "test-model",
        "claim_detector": {"min_check_worthiness": 0.7, "max_claims_per_text": 5},
        "evidence_hunter": {
            "search_strategy": "web_search",
            "max_results": 5,
            "credibility_threshold": 0.6,
        },
        "verdict_writer": {"max_sources": 3, "confidence_threshold": 0.8},
    }


@pytest.fixture
def vcr_search_results():
    """Return pre-recorded search results for integration tests."""
    return {
        "earth_age": [
            {
                "title": "Earth Age: 4.54 Billion Years - Science Today",
                "link": "https://example.com/earth-age",
                "snippet": "Scientists have determined that the Earth is approximately 4.54 billion years old based on radiometric dating of meteorites and Earth's oldest minerals.",
            },
            {
                "title": "How Old is the Earth? - NASA Space Place",
                "link": "https://example.nasa.gov/earth-age",
                "snippet": "The Earth is approximately 4.54 billion years old. Scientists know this through radiometric age dating of meteorites and the oldest rocks on Earth.",
            },
        ],
        "water_coverage": [
            {
                "title": "Ocean Coverage Facts - World Geography",
                "link": "https://example.org/ocean-facts",
                "snippet": "Water covers about 71% of the Earth's surface, with oceans holding about 96.5% of all Earth's water.",
            },
            {
                "title": "Earth's Water - USGS",
                "link": "https://example.usgs.gov/water",
                "snippet": "About 71 percent of the Earth's surface is water-covered. The oceans hold about 96.5 percent of all Earth's water.",
            },
        ],
    }


# Add integration-specific fixtures here
