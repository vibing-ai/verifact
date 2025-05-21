"""Search utilities for VeriFact.

This module contains tools for web search and search result processing.
"""

from src.utils.search.search_tools import get_search_tool

# Create re-exports of useful functions for easier imports
def search_web(query: str, num_results: int = 5):
    """Search the web for information.
    
    Args:
        query: Search query string
        num_results: Number of results to return
        
    Returns:
        List of search results
    """
    tool = get_search_tool()
    return tool.call({"query": query, "num_results": num_results})

def extract_sources(search_results):
    """Extract source information from search results.
    
    Args:
        search_results: Results from search_web
        
    Returns:
        Dict mapping URLs to titles
    """
    sources = {}
    for result in search_results:
        if "url" in result and "title" in result:
            sources[result["url"]] = result["title"]
    return sources

def filter_results(search_results, min_keyword_match=1, excluded_domains=None):
    """Filter search results based on criteria.
    
    Args:
        search_results: Results from search_web
        min_keyword_match: Minimum number of keywords that must match
        excluded_domains: List of domains to exclude
        
    Returns:
        Filtered search results
    """
    if not excluded_domains:
        excluded_domains = []
        
    filtered = []
    for result in search_results:
        # Skip results from excluded domains
        if any(domain in result.get("url", "") for domain in excluded_domains):
            continue
            
        filtered.append(result)
        
    return filtered

__all__ = ["search_web", "extract_sources", "filter_results", "get_search_tool"]
