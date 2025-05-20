"""Pytest configuration for utility tests.

This module contains fixtures specific to utility tests.
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_db_session():
    """Return a mock database session for testing."""
    mock_session = MagicMock()

    # Set up the mock session to handle common operations
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.all.return_value = []
    mock_session.first.return_value = None

    return mock_session


@pytest.fixture
def mock_async_db_session():
    """Return a mock async database session for testing."""
    mock_session = AsyncMock()

    # Set up the mock session to handle common operations
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.execute.return_value = AsyncMock()
    mock_session.execute.return_value.scalar.return_value = None
    mock_session.execute.return_value.scalars.return_value = AsyncMock()
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    mock_session.execute.return_value.scalars.return_value.first.return_value = None

    return mock_session


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
def sample_search_results():
    """Return sample search results for testing."""
    return [
        {
            "title": "Earth Age: 4.54 Billion Years - Science Today",
            "link": "https://example.com/earth-age",
            "snippet": "Scientists have determined that the Earth is approximately 4.54 billion years old based on radiometric dating of meteorites and Earth's oldest minerals.",
        },
        {
            "title": "Ocean Coverage Facts - World Geography",
            "link": "https://example.org/ocean-facts",
            "snippet": "Water covers about 71% of the Earth's surface, with oceans holding about 96.5% of all Earth's water.",
        },
        {
            "title": "Planet Earth Facts - NASA",
            "link": "https://example.nasa.gov/earth-facts",
            "snippet": "Earth is the third planet from the Sun and the only astronomical object known to harbor life. About 71% of Earth's surface is covered with water.",
        },
    ]


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
