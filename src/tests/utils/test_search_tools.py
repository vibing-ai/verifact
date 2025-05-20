"""
Tests for search tools.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

from src.utils.search_tools import SerperSearchTool, get_search_tool


@pytest.fixture
def serper_search_tool():
    """Create a SerperSearchTool instance for testing."""
    os.environ["SERPER_API_KEY"] = "test_api_key"
    tool = SerperSearchTool()
    yield tool
    # Clean up
    if "SERPER_API_KEY" in os.environ:
        del os.environ["SERPER_API_KEY"]


@pytest.fixture
def mock_search_response():
    """Mock response data from Serper.dev API."""
    return {
        "searchParameters": {
            "q": "test query"
        },
        "organic": [
            {
                "title": "Test Result 1",
                "link": "https://example.com/1",
                "snippet": "This is the first test result snippet.",
                "position": 1
            },
            {
                "title": "Test Result 2",
                "link": "https://example.com/2",
                "snippet": "This is the second test result snippet.",
                "position": 2
            }
        ],
        "news": [
            {
                "title": "Test News 1",
                "link": "https://example.com/news/1",
                "snippet": "This is a news article snippet.",
                "date": "2023-06-15"
            }
        ]
    }


def test_get_search_tool_with_serper():
    """Test get_search_tool when Serper is enabled."""
    os.environ["USE_SERPER"] = "true"
    tool = get_search_tool()
    assert isinstance(tool, SerperSearchTool)
    # Clean up
    if "USE_SERPER" in os.environ:
        del os.environ["USE_SERPER"]


def test_get_search_tool_with_web_search():
    """Test get_search_tool with WebSearchTool."""
    os.environ["USE_SERPER"] = "false"
    with patch("src.utils.search_tools.WebSearchTool") as mock_web_search:
        mock_web_search.return_value = "mock_web_search_tool"
        tool = get_search_tool()
        assert tool == "mock_web_search_tool"
    # Clean up
    if "USE_SERPER" in os.environ:
        del os.environ["USE_SERPER"]


@pytest.mark.asyncio
async def test_serper_search_tool_call(serper_search_tool, mock_search_response):
    """Test SerperSearchTool.call method with mocked response."""
    # Mock the aiohttp ClientSession
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_search_response)
    mock_session.__aenter__.return_value = mock_session
    mock_session.post = AsyncMock(return_value=mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await serper_search_tool.call({"query": "test query", "num_results": 2})
        
        # Verify the results
        assert len(results) == 2
        assert results[0]["title"] == "Test Result 1"
        assert results[0]["url"] == "https://example.com/1"
        assert results[0]["snippet"] == "This is the first test result snippet."
        assert results[0]["source"] == "serper.dev"


@pytest.mark.asyncio
async def test_serper_search_tool_api_error(serper_search_tool):
    """Test SerperSearchTool.call method with API error."""
    # Mock the aiohttp ClientSession
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Bad Request")
    mock_session.__aenter__.return_value = mock_session
    mock_session.post = AsyncMock(return_value=mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        results = await serper_search_tool.call({"query": "test query"})
        
        # Verify the error response
        assert len(results) == 1
        assert "error" in results[0]
        assert "API returned status code 400" in results[0]["error"]


@pytest.mark.asyncio
async def test_serper_search_tool_missing_api_key():
    """Test SerperSearchTool.call method with missing API key."""
    # Ensure no API key is set
    if "SERPER_API_KEY" in os.environ:
        del os.environ["SERPER_API_KEY"]
    
    tool = SerperSearchTool()
    results = await tool.call({"query": "test query"})
    
    # Verify the error response
    assert len(results) == 1
    assert "error" in results[0]
    assert "SERPER_API_KEY not set" in results[0]["error"] 