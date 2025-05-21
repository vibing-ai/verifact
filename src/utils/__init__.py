"""Utility modules for the VeriFact application.

This package contains helper functions used across the project,
including data processing, API integrations, and common operations.
"""

# Import using importlib to avoid the 'async' keyword issue
import importlib
async_module = importlib.import_module('src.utils.async.async_processor')
AsyncProcessor = async_module.AsyncProcessor

priority_queue_module = importlib.import_module('src.utils.async.priority_queue')
PriorityQueue = priority_queue_module.PriorityQueue

retry_module = importlib.import_module('src.utils.async.retry')
with_retry = retry_module.with_retry
with_async_retry = retry_module.with_async_retry
async_retry_context = retry_module.async_retry_context

# Cache utilities
from src.utils.cache import Cache, claim_cache, entity_cache, model_cache, search_cache

# Database utilities
from src.utils.db import db

# Logging and metrics
from src.utils.logging import MetricsTracker, claim_detector_metrics

# Model configuration
from src.utils.models import configure_openai_for_openrouter

# Search utilities
from src.utils.search import extract_sources, search_web

# Validation utilities
from src.utils.validation import ValidationError, validate_input

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
    "with_retry",
    "with_async_retry",
    "async_retry_context",
    # Search
    "search_web",
    "extract_sources",
    # Validation
    "validate_input",
    "ValidationError",
]
