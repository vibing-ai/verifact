"""
Pytest configuration for VeriFact tests.

This module contains fixtures and configuration for pytest.
"""
import os
from unittest.mock import MagicMock

import pytest


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
def mock_openai_client():
    """Return a mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Mocked response content"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


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