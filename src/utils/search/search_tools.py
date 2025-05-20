"""
Search tools for VeriFact.

This module provides utilities for searching the web for information.
"""

import os
import json
import time
import logging
import hashlib
import aiohttp
from typing import Any, Dict, List, Optional, Union, Callable

from openai.agents.tools import Tool

from src.utils.logging.logger import get_component_logger

# Create a logger for this module
logger = get_component_logger("search_tools")


class SerperSearchTool(Tool):
    """Serper.dev search integration for Agent SDK."""

    def __init__(self):
        """Initialize the SerperSearchTool."""
        super().__init__(
            name="serper_search",
            description="Search the web using Serper.dev API to find current information on any topic",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find information about"},
                    "num_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of results to return (1-10)"},
                    "search_type": {
                        "type": "string",
                        "enum": [
                            "search",
                            "news",
                            "images"],
                        "default": "search",
                        "description": "Type of search to perform: general search, news, or images"}},
                "required": ["query"]},
            output_schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string"},
                        "snippet": {
                            "type": "string"},
                        "url": {
                            "type": "string"},
                        "position": {
                            "type": "integer"},
                        "source": {
                            "type": "string"}}}})

        # Get API key from environment variable
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            logger.warning("SERPER_API_KEY not found in environment variables")

        # Set up API parameters
        self.api_url = "https://google.serper.dev"

    async def call(self, params: Dict[str, Any],
                   **kwargs) -> List[Dict[str, Any]]:
        """
        Call the Serper.dev API to search for information.

        Args:
            params: Dictionary containing search parameters

        Returns:
            List of search results with information about each hit
        """
        query = params.get("query")
        num_results = min(10, max(1, params.get("num_results", 5)))
        search_type = params.get("search_type", "search")

        if not self.api_key:
            return [{"error": "SERPER_API_KEY not set in environment variables"}]

        try:
            # Determine endpoint based on search type
            endpoint = "/search" if search_type == "search" else f"/{search_type}"

            # Set up the request headers and payload
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "q": query,
                "num": num_results
            }

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}{endpoint}",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"Serper API error: {
                                response.status} - {error_text}")
                        return [
                            {"error": f"API returned status code {response.status}"}]

                    data = await response.json()

            # Process the results based on search type
            results = []

            if search_type == "search":
                organic_results = data.get("organic", [])
                for i, result in enumerate(organic_results[:num_results]):
                    results.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "url": result.get("link", ""),
                        "position": i + 1,
                        "source": "serper.dev"
                    })

            elif search_type == "news":
                news_results = data.get("news", [])
                for i, result in enumerate(news_results[:num_results]):
                    results.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "url": result.get("link", ""),
                        "position": i + 1,
                        "date": result.get("date", ""),
                        "source": "serper.dev"
                    })

            elif search_type == "images":
                image_results = data.get("images", [])
                for i, result in enumerate(image_results[:num_results]):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "image_url": result.get("imageUrl", ""),
                        "position": i + 1,
                        "source": "serper.dev"
                    })

            logger.info(
                f"Serper search for '{query}' returned {
                    len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error in SerperSearchTool: {str(e)}")
            return [{"error": f"Error performing search: {str(e)}"}]


# Factory function to get the configured search tool
def get_search_tool():
    """
    Get the configured search tool based on environment variables.

    Returns:
        An instance of a search tool (WebSearchTool or SerperSearchTool)
    """
    use_serper = os.getenv("USE_SERPER", "false").lower() == "true"

    if use_serper:
        logger.info("Using SerperSearchTool for web searches")
        return SerperSearchTool()
    else:
        # Fall back to OpenAI's WebSearchTool
        from openai.agents.tools import WebSearchTool
        logger.info("Using WebSearchTool for web searches")
        return WebSearchTool()
