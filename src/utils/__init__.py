"""
Utility modules for the VeriFact application.

This package contains helper functions used across the project,
including data processing, API integrations, and common operations.
"""

# Cache utilities
from src.utils.cache import Cache, claim_cache, entity_cache, search_cache, model_cache

# Logging and metrics
from src.utils.logging import MetricsTracker, claim_detector_metrics

# Model configuration
from src.utils.models import configure_openai_for_openrouter

# Database utilities
from src.utils.db import db

# Import directly from the modules to avoid 'async' keyword issue
from src.utils.async_processor import AsyncProcessor
from src.utils.priority_queue import PriorityQueue
from src.utils.retry import retry

# Search utilities
from src.utils.search import search_web, extract_sources

# Validation utilities
from src.utils.validation import validate_input, ValidationError

# Apply OpenRouter configuration when the utils module is imported
configure_openai_for_openrouter()

__all__ = [
    # Cache
    "Cache", 
    "claim_cache", 
    "entity_cache", 
    "search_cache", 
    "model_cache",
    
    # Logging and metrics
    "MetricsTracker",
    "claim_detector_metrics",
    
    # Database
    "db",
    
    # Async
    "AsyncProcessor",
    "PriorityQueue",
    "retry",
    
    # Search
    "search_web",
    "extract_sources",
    
    # Validation
    "validate_input",
    "ValidationError"
] 