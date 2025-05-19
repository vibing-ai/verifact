"""
Model configuration utilities for VeriFact.

This module provides functions to manage model settings and configurations,
including model selection, parameter management, and API key handling.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default models
DEFAULT_MODELS = {
    "claim_detector": "openai/gpt-4o",
    "evidence_hunter": "anthropic/claude-3-opus",
    "verdict_writer": "openai/gpt-4o",
    "fallback": "openai/gpt-3.5-turbo"
}

# Default model settings
DEFAULT_SETTINGS = {
    "temperature": 0.1,
    "max_tokens": 1000,
    "request_timeout": 120
}


def get_model_name(model_name: Optional[str] = None, agent_type: Optional[str] = None) -> str:
    """
    Get the model name for a given agent, using environment variables or defaults.
    
    Args:
        model_name: Explicitly provided model name (highest priority)
        agent_type: Type of agent (claim_detector, evidence_hunter, verdict_writer)
        
    Returns:
        The appropriate model name to use
    """
    # If model_name is explicitly provided, use it
    if model_name:
        return model_name
    
    # Check for agent-specific environment variable
    if agent_type:
        env_var = f"{agent_type.upper()}_MODEL"
        env_model = os.getenv(env_var)
        if env_model:
            return env_model
        
        # Use default for this agent type if available
        if agent_type.lower() in DEFAULT_MODELS:
            return DEFAULT_MODELS[agent_type.lower()]
    
    # Check for general model environment variable
    general_model = os.getenv("DEFAULT_MODEL")
    if general_model:
        return general_model
    
    # Fall back to the default fallback model
    return DEFAULT_MODELS["fallback"]


def get_model_settings() -> Dict[str, Any]:
    """
    Get model settings from environment variables or defaults.
    
    Returns:
        Dictionary of model settings
    """
    settings = DEFAULT_SETTINGS.copy()
    
    # Override with environment variables if available
    if os.getenv("MODEL_TEMPERATURE"):
        settings["temperature"] = float(os.getenv("MODEL_TEMPERATURE"))
    
    if os.getenv("MODEL_MAX_TOKENS"):
        settings["max_tokens"] = int(os.getenv("MODEL_MAX_TOKENS"))
    
    if os.getenv("MODEL_REQUEST_TIMEOUT"):
        settings["request_timeout"] = int(os.getenv("MODEL_REQUEST_TIMEOUT"))
    
    return settings


def get_api_key(provider: str = "openrouter") -> str:
    """
    Get the API key for the specified provider.
    
    Args:
        provider: Name of the provider (openrouter, openai, anthropic, etc.)
        
    Returns:
        API key for the provider
    
    Raises:
        ValueError: If the API key is not found
    """
    env_var = f"{provider.upper()}_API_KEY"
    api_key = os.getenv(env_var)
    
    if not api_key:
        raise ValueError(f"API key for {provider} not found. Please set {env_var} environment variable.")
    
    return api_key 