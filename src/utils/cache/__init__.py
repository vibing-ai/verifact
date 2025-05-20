"""
Caching utilities for VeriFact.

This module provides caching mechanisms for storing and retrieving frequently accessed data.
"""

from src.utils.cache.cache import (
    Cache,
    claim_cache,
    entity_cache,
    model_cache,
    search_cache,
)

__all__ = [
    "Cache",
    "claim_cache",
    "entity_cache",
    "search_cache",
    "model_cache"
]
