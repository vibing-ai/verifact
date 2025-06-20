"""Search tools for VeriFact.

This module provides utilities for searching the web for information using
multiple search providers with the OpenAI Agents SDK.
"""

import logging
import os
from typing import Any

import httpx
from agents import WebSearchTool, function_tool

# Create a logger for this module
logger = logging.getLogger(__name__)

@function_tool
async def serper_search(query: str, num_results: int = 10, search_type: str = "search") -> list[dict[str, Any]]:
    """
    Search the web using Serper.dev API to find current information on any topic.

    Args:
        query: The search query to find information about.
        num_results: Number of results to return (1-10).
        search_type: Type of search to perform: 'search', 'news', or 'images'.

    Returns:
        List of search results with information about each hit.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        logger.warning("SERPER_API_KEY not found in environment variables")
        return [{"error": "SERPER_API_KEY not set in environment variables"}]

    api_url = "https://google.serper.dev"
    endpoint = "/search" if search_type == "search" else f"/{search_type}"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    
    payload = {
        "q": query,
        "num": min(10, max(1, num_results)),
        "gl": "us", 
        "hl": "en", 
        "type": search_type,
        "tbs": "qdr:y" 
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{api_url}{endpoint}", headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Serper API error: {response.status_code} - {response.text}")
                return [{"error": f"API returned status code {response.status_code}"}]
            
            data = response.json()
    except Exception as e:
        logger.error(f"Error in serper_search: {str(e)}")
        return [{"error": f"Error performing search: {str(e)}"}]

    results = []
    
    if search_type == "search":
        for i, result in enumerate(data.get("organic", [])[:num_results]):
            results.append({
                "content": result.get("snippet", ""),
                "source": result.get("link", ""),
            })
    elif search_type == "news":
        for i, result in enumerate(data.get("news", [])[:num_results]):
            results.append({
                "content": result.get("snippet", ""),
                "source": result.get("link", ""),
            })
    elif search_type == "images":
        for i, result in enumerate(data.get("images", [])[:num_results]):
            results.append({
                "content": result.get("snippet", ""),
                "source": result.get("link", ""),
            })
    
    # print(results)
    return results

def get_websearch_tool(user_location: dict[str, Any] | None = None) -> WebSearchTool:
    """
    Get OpenAI's WebSearchTool instance with optional location configuration.
    
    Args:
        user_location: Optional location configuration for search results.
                      Should contain 'country', 'city', 'region', and/or 'timezone'.
    
    Returns:
        Configured WebSearchTool instance for use in Agent configurations.
    """
    try:
        return WebSearchTool()
    except ImportError:
        logger.error("WebSearchTool not available. Make sure you're using OpenAI Agents SDK.")
        raise ImportError("WebSearchTool not available.")

def get_search_tools(tool_names: list[str] = None) -> list[Any]:
    """
    Get multiple configured search tool instances.

    Args:
        tool_names: List of search tool names to use ('serper', 'openai_web').
                   If None, uses environment variable USE_SERPER to determine tools.

    Returns:
        List of requested search tool functions or WebSearchTool instances.
    """
    if tool_names is None:
        use_serper = os.getenv("USE_SERPER", "false").lower() == "true"
        tool_names = ["serper"] if use_serper else ["openai_web"]
    
    tools = []
    for tool_name in tool_names:
        tool_name = tool_name.lower()
        if tool_name == "serper":
            logger.info("Using Serper search tool")
            tools.append(serper_search)
        elif tool_name == "openai_web":
            logger.info("Using OpenAI WebSearchTool")
            tools.append(get_websearch_tool())
        else:
            logger.warning(f"Unknown search tool '{tool_name}', skipping")
    
    if not tools:
        logger.warning("No valid search tools found, defaulting to OpenAI WebSearchTool")
        tools.append(get_websearch_tool())
    
    return tools
