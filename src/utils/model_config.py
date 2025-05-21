"""Backwards compatibility module for model configuration.

This module re-exports the necessary classes and functions from the 
new models module to maintain compatibility with existing code.
"""

# Re-export from models.model_config
from src.utils.models.model_config import (
    ModelManager,
    get_model_name,
    get_model_settings,
    get_api_key,
    create_openrouter_client,
    get_openrouter_headers,
    ModelError,
    ModelTimeoutError,
    ModelRateLimitError,
    ModelAuthenticationError,
    ModelRequestError,
    ModelUnavailableError,
    configure_openai_for_openrouter,
    make_openrouter_request
)

__all__ = [
    "ModelManager",
    "get_model_name",
    "get_model_settings",
    "get_api_key",
    "create_openrouter_client",
    "get_openrouter_headers",
    "ModelError",
    "ModelTimeoutError",
    "ModelRateLimitError",
    "ModelAuthenticationError",
    "ModelRequestError",
    "ModelUnavailableError",
    "configure_openai_for_openrouter",
    "make_openrouter_request"
] 