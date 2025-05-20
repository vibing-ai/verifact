"""
Model configuration utilities for VeriFact.

This module provides a unified configuration system for AI models, including
model selection, parameter management, API key handling, and token usage tracking.
"""

from src.utils.models.model_config import configure_openai_for_openrouter

__all__ = [
    "configure_openai_for_openrouter"
]
