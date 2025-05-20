"""
Model configuration utilities for VeriFact.

This module provides a centralized system for AI model configuration and management.

This module provides a unified configuration system for all agents,
including model selection, parameter management, API key handling,
caching, error handling, and fallback mechanisms.

All models are accessed through OpenRouter, which provides access to models
from multiple providers including OpenAI, Anthropic, Mistral, and others.
"""

import hashlib
import json
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Update imports
from src.utils.logging.logger import (
    get_component_logger,
    log_performance,
    performance_timer,
    request_context,
)

# Create a component logger for model configuration
logger = get_component_logger("model_config")

# Load environment variables
load_dotenv()

# Default models via OpenRouter
# Format: "provider/model" - e.g., "qwen/qwen3-8b:free",
# "meta-llama/llama-3.3-8b-instruct:free"
DEFAULT_MODELS = {
    # Qwen 3-8b: Optimized for structured JSON output and entity extraction
    "claim_detector": "qwen/qwen3-8b:free",

    # Google Gemma 3-27b-it: Optimized for RAG with 128k context window
    "evidence_hunter": "google/gemma-3-27b-it:free",

    # DeepSeek Chat: Best reasoning capabilities for evidence synthesis
    "verdict_writer": "deepseek/deepseek-chat:free",

    # Meta Llama 3: General purpose model for fallback operations
    "fallback": "meta-llama/llama-3.3-8b-instruct:free"
}

# Default model parameters
DEFAULT_PARAMETERS = {
    "temperature": 0.1,
    "max_tokens": 1000,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "request_timeout": 120,
    "stream": False
}

# OpenRouter API endpoint
OPENROUTER_API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Maximum retry attempts for API calls
MAX_RETRIES = 3

# Cache size for LRU cache
CACHE_SIZE = int(os.getenv("MODEL_CACHE_SIZE", "1000"))

# Flag to enable/disable caching
ENABLE_CACHING = os.getenv("ENABLE_MODEL_CACHING", "True").lower() == "true"


class ModelError(Exception):
    """Base exception class for model-related errors."""
    pass


class ModelRequestError(ModelError):
    """Exception raised for errors in API requests."""

    def __init__(self, message, status_code=None, request_id=None):
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(message)


class ModelAuthenticationError(ModelError):
    """Exception raised for authentication failures."""
    pass


class ModelTimeoutError(ModelError):
    """Exception raised when a request times out."""
    pass


class ModelRateLimitError(ModelError):
    """Exception raised when hitting rate limits."""

    def __init__(self, message, retry_after=None):
        self.retry_after = retry_after
        super().__init__(message)


class ModelUnavailableError(ModelError):
    """Exception raised when a model is unavailable."""
    pass


class ModelManager:
    """
    Unified model manager class for handling all model interactions.

    This class provides a centralized interface for:
    - Model configuration and parameter management
    - API request handling with retry logic and error management
    - Response caching to reduce API costs
    - Token usage tracking for cost monitoring
    - Fallback mechanisms for model unavailability

    Default models used:
    - claim_detector: qwen/qwen3-8b:free - Best for structured JSON output
    - evidence_hunter: google/gemma-3-27b-it:free - RAG optimized with 128k context
    - verdict_writer: deepseek/deepseek-chat:free - Strong reasoning capabilities
    - fallback: meta-llama/llama-3.3-8b-instruct:free - General purpose

    These models are available through OpenRouter's free tier.
    Custom models can be specified through environment variables.
    """

    def __init__(self, agent_type: Optional[str] = None):
        """
        Initialize the ModelManager.

        Args:
            agent_type: Optional type of agent (claim_detector, evidence_hunter, verdict_writer)
        """
        self.agent_type = agent_type
        self.parameters = self._load_parameters()
        self.model_name = self._get_model_name()
        self.fallback_models = self._get_fallback_chain()
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        self.httpx_client = httpx.Client(
            timeout=self.parameters["request_timeout"])

    def _load_parameters(self) -> Dict[str, Any]:
        """
        Load model parameters from environment variables or defaults.

        Returns:
            Dictionary of model parameters
        """
        parameters = DEFAULT_PARAMETERS.copy()

        # Check for agent-specific parameters first
        prefix = f"{self.agent_type.upper()}_" if self.agent_type else ""

        # Try to load agent-specific parameters first, fall back to general
        # parameters
        for param, default in DEFAULT_PARAMETERS.items():
            env_var = f"{prefix}MODEL_{param.upper()}"
            general_env_var = f"MODEL_{param.upper()}"

            # Try agent-specific parameter first
            if os.getenv(env_var) is not None:
                value = os.getenv(env_var)
                parameters[param] = self._convert_parameter_value(param, value)
            # Then try general parameter
            elif os.getenv(general_env_var) is not None:
                value = os.getenv(general_env_var)
                parameters[param] = self._convert_parameter_value(param, value)

        # Apply model-specific parameter adjustments
        parameters = self._adjust_parameters_for_model(parameters)

        return parameters

    def _convert_parameter_value(self, param: str, value: str) -> Any:
        """
        Convert parameter value from string to appropriate type.

        Args:
            param: Parameter name
            value: Parameter value as string

        Returns:
            Converted parameter value
        """
        if param in [
            "temperature",
            "top_p",
            "frequency_penalty",
                "presence_penalty"]:
            return float(value)
        elif param in ["max_tokens", "request_timeout"]:
            return int(value)
        elif param == "stream":
            return value.lower() == "true"
        else:
            return value

    def _get_model_name(self) -> str:
        """
        Get the model name for the agent type.

        Returns:
            The appropriate model name to use with OpenRouter
        """
        # Check for agent-specific environment variable
        if self.agent_type:
            env_var = f"{self.agent_type.upper()}_MODEL"
            env_model = os.getenv(env_var)
            if env_model:
                return env_model

            # Use default for this agent type if available
            if self.agent_type.lower() in DEFAULT_MODELS:
                return DEFAULT_MODELS[self.agent_type.lower()]

        # Check for general model environment variable
        general_model = os.getenv("DEFAULT_MODEL")
        if general_model:
            return general_model

        # Fall back to the default fallback model
        return DEFAULT_MODELS["fallback"]

    def _get_fallback_chain(self) -> List[str]:
        """
        Get the chain of fallback models.

        Returns:
            List of model names to try in sequence
        """
        # Start with the primary model
        models = [self.model_name]

        # Add agent-specific fallbacks if defined
        if self.agent_type:
            env_var = f"{self.agent_type.upper()}_FALLBACK_MODELS"
            fallbacks = os.getenv(env_var)
            if fallbacks:
                models.extend(fallbacks.split(","))

        # Add general fallbacks
        general_fallbacks = os.getenv("FALLBACK_MODELS")
        if general_fallbacks:
            models.extend(general_fallbacks.split(","))

        # Always include the default fallback
        if DEFAULT_MODELS["fallback"] not in models:
            models.append(DEFAULT_MODELS["fallback"])

        return models

    def set_parameter(self, name: str, value: Any) -> None:
        """
        Set a model parameter.

        Args:
            name: Parameter name
            value: Parameter value
        """
        if name in DEFAULT_PARAMETERS:
            self.parameters[name] = value
        else:
            raise ValueError(f"Unknown parameter: {name}")

    def get_parameter(self, name: str) -> Any:
        """
        Get a model parameter value.

        Args:
            name: Parameter name

        Returns:
            Parameter value
        """
        return self.parameters.get(name)

    def update_parameters(self, **kwargs) -> None:
        """
        Update multiple parameters at once.

        Args:
            **kwargs: Parameter name-value pairs
        """
        for name, value in kwargs.items():
            self.set_parameter(name, value)

    def get_api_key(self, provider: str = "openrouter") -> str:
        """
        Get the API key for the specified provider.

        Args:
            provider: Name of the provider (openrouter, openai, anthropic, etc.)

        Returns:
            API key for the provider

        Raises:
            ModelAuthenticationError: If the API key is not found
        """
        env_var = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(env_var)

        if not api_key:
            if provider.lower() == "openrouter":
                raise ModelAuthenticationError(
                    "OpenRouter API key not found. Please set " + env_var + " environment variable.\n"
                    "You can get an API key from https://openrouter.ai/keys."
                )
            else:
                raise ModelAuthenticationError(
                    "API key for " + provider + " not found. Please set " + env_var + " environment variable.")

        return api_key

    def get_request_headers(self) -> Dict[str, str]:
        """
        Get the headers required for API calls.

        Returns:
            Dictionary of headers for API calls
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.get_api_key('openrouter')
        }

        # Add site URL if available
        site_url = os.getenv("OPENROUTER_SITE_URL")
        if site_url:
            headers["HTTP-Referer"] = site_url

        # Add site name if available
        site_name = os.getenv("OPENROUTER_SITE_NAME")
        if site_name:
            headers["X-Title"] = site_name

        return headers

    def _generate_cache_key(
            self, messages: List[Dict[str, str]], parameters: Dict[str, Any]) -> str:
        """
        Generate a cache key from messages and parameters.

        Args:
            messages: List of message dictionaries
            parameters: Dictionary of model parameters

        Returns:
            Cache key string
        """
        # Create a stable representation of messages and parameters
        cache_dict = {
            "messages": messages,
            "parameters": {
                k: v for k,
                v in parameters.items() if k != "stream" and k != "request_timeout"}}

        # Convert to a stable string and hash
        cache_str = json.dumps(cache_dict, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    @lru_cache(maxsize=CACHE_SIZE)
    def _cached_completion(self, cache_key: str, model: str) -> Dict[str, Any]:
        """
        LRU cache for model completions.

        This is a placeholder function that never gets called directly
        but is used to store cached results keyed by cache_key and model.
        The real implementation is in the completion method.

        Args:
            cache_key: Hash of the request messages and parameters
            model: Model name

        Returns:
            Cached completion result
        """
        # This will never be called directly, it's just for the lru_cache
        # decorator
        pass

    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Handle error responses from the API.

        Args:
            response: The API response

        Raises:
            Appropriate ModelError subclass
        """
        status_code = response.status_code
        request_id = response.headers.get("x-request-id")

        try:
            error_data = response.json()
            error_message = error_data.get(
                "error", {}).get(
                "message", "Unknown error")
        except Exception:
            error_message = response.text or "HTTP error " + str(status_code)

        if status_code == 401:
            raise ModelAuthenticationError(
                "Authentication error: " + error_message)
        elif status_code == 429:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = 5
            else:
                retry_after = 5

            raise ModelRateLimitError(
                "Rate limit exceeded: " + error_message,
                retry_after=retry_after
            )
        elif status_code == 404:
            raise ModelUnavailableError("Model not found: " + error_message)
        elif status_code == 408:
            raise ModelTimeoutError("Request timed out: " + error_message)
        elif 500 <= status_code < 600:
            raise ModelRequestError(
                "Server error: " + error_message,
                status_code=status_code,
                request_id=request_id
            )
        else:
            raise ModelRequestError(
                "API error: " + error_message,
                status_code=status_code,
                request_id=request_id
            )

    def _update_token_usage(self, response_data: Dict[str, Any]) -> None:
        """
        Update token usage statistics from a response.

        Args:
            response_data: The API response data
        """
        usage = response_data.get("usage", {})

        self.token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.token_usage["completion_tokens"] += usage.get(
            "completion_tokens", 0)
        self.token_usage["total_tokens"] += usage.get("total_tokens", 0)

        # Log token usage with structured logging
        logger.info(
            "Token usage statistics",
            extra={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "model": response_data.get("model", "unknown"),
                "component": self.agent_type or "general"
            }
        )

    def get_token_usage(self) -> Dict[str, int]:
        """
        Get current token usage statistics.

        Returns:
            Dictionary with token usage counts
        """
        return self.token_usage.copy()

    def reset_token_usage(self) -> None:
        """Reset token usage statistics."""
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }

    @retry(retry=retry_if_exception_type((httpx.TimeoutException,
                                          ModelTimeoutError,
                                          ModelRateLimitError)),
           stop=stop_after_attempt(MAX_RETRIES),
           wait=wait_exponential(multiplier=1,
                                 min=2,
                                 max=30),
           reraise=True)
    @log_performance(operation="model_completion_async", level="info")
    async def completion_async(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a completion from the model with fallback and caching (async version).

        Args:
            messages: List of message dictionaries
            **kwargs: Override parameters for this request

        Returns:
            Model completion response

        Raises:
            ModelError: If all models in the fallback chain fail
        """
        # Create a unique request ID for this completion
        with request_context(component=self.agent_type or "general") as request_id:
            # Add request context
            logger.info(
                "Starting async model completion request",
                extra={
                    "messages_count": len(messages),
                    "parameters": {
                        k: v for k,
                        v in kwargs.items() if k not in ["messages"]}})

            # Override parameters for this request only
            request_parameters = self.parameters.copy()
            request_parameters.update(kwargs)

            # Check cache if enabled
            if ENABLE_CACHING and not request_parameters.get("stream", False):
                cache_key = self._generate_cache_key(
                    messages, request_parameters)

                # Cached values are stored by model, so we need to check each
                # model in the chain
                for model in self.fallback_models:
                    try:
                        # Try to get from cache
                        if hasattr(
                                self._cached_completion,
                                "cache_info"):  # Check if cache is available
                            cache_dict = {
                                "cache_key": cache_key,
                                "model": model
                            }
                            cache_key_str = json.dumps(
                                cache_dict, sort_keys=True)
                            if cache_key_str in self._cached_completion.cache:
                                logger.info(
                                    "Cache hit for model " + model, extra={
                                        "model": model, "cached": True})
                                return self._cached_completion.cache[cache_key_str]
                    except Exception as e:
                        logger.warning(
                            "Cache lookup failed: " +
                            str(e), extra={
                                "error": str(e), "error_type": type(e).__name__})

            # Try each model in the fallback chain
            last_error = None

            for model in self.fallback_models:
                try:
                    with performance_timer("api_call_" + model, logger=logger, level="debug", model=model):
                        async with httpx.AsyncClient(timeout=request_parameters["request_timeout"]) as client:
                            headers = self.get_request_headers()

                            # Prepare the request payload
                            payload = {
                                "model": model,
                                "messages": messages,
                                **{k: v for k, v in request_parameters.items()
                                   if k not in ["request_timeout"]}
                            }

                            # Make the API request
                            logger.debug(
                                "Sending request to model " + model, extra={
                                    "model": model})
                            response = await client.post(
                                OPENROUTER_API_ENDPOINT,
                                json=payload,
                                headers=headers
                            )

                            # Handle error responses
                            if response.status_code != 200:
                                self._handle_error_response(response)

                            # Parse and process the response
                            response_data = response.json()

                            # Update token usage statistics
                            self._update_token_usage(response_data)

                            # Cache the result if caching is enabled
                            if ENABLE_CACHING and not request_parameters.get(
                                    "stream", False):
                                cache_key = self._generate_cache_key(
                                    messages, request_parameters)
                                try:
                                    self._cached_completion(cache_key, model)
                                    # Store in the cache manually
                                    cache_dict = {
                                        "cache_key": cache_key,
                                        "model": model
                                    }
                                    cache_key_str = json.dumps(
                                        cache_dict, sort_keys=True)
                                    if hasattr(
                                            self._cached_completion, "cache"):
                                        self._cached_completion.cache[cache_key_str] = response_data
                                        logger.debug(
                                            "Cached response for model " + model, extra={
                                                "model": model, "cache_key": cache_key})
                                except Exception as e:
                                    logger.warning(
                                        "Cache storage failed: " +
                                        str(e), extra={
                                            "error": str(e), "error_type": type(e).__name__})

                            logger.info(
                                "Successfully got completion from model " + model,
                                extra={
                                    "model": model,
                                    "status_code": response.status_code,
                                    "usage": response_data.get(
                                        "usage",
                                        {})})
                            return response_data

                except (ModelUnavailableError, ModelRequestError) as e:
                    # Log the error and try the next model
                    logger.warning(
                        "Model " + model + " failed: " + str(e),
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "model": model,
                            "fallback_available": len(self.fallback_models) > 1
                        }
                    )
                    last_error = e
                    continue

                except (ModelTimeoutError, ModelRateLimitError) as e:
                    # These errors should be retried by the @retry decorator
                    logger.warning(
                        "Retryable error with model " + model + ": " + str(e),
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "model": model,
                            "retry_after": getattr(e, "retry_after", None)
                        }
                    )
                    if isinstance(e, ModelRateLimitError) and e.retry_after:
                        time.sleep(e.retry_after)
                    raise e

                except ModelAuthenticationError as e:
                    # Authentication errors are fatal
                    logger.error(
                        "Authentication error: " + str(e),
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                    raise e

                except Exception as e:
                    # Unexpected errors
                    logger.error(
                        "Unexpected error with model " + model + ": " + str(e),
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "model": model
                        }
                    )
                    last_error = e
                    continue

            # If we get here, all models in the fallback chain failed
            error_msg = "All models in the fallback chain failed"
            if last_error:
                error_msg += ": " + str(last_error)

            logger.error(
                error_msg,
                extra={
                    "error": str(last_error) if last_error else "Unknown error",
                    "error_type": type(last_error).__name__ if last_error else "UnknownError",
                    "models_tried": self.fallback_models})
            raise ModelError(error_msg)

    @log_performance(operation="model_completion", level="info")
    def completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a completion from the model with fallback and caching (sync version).

        Args:
            messages: List of message dictionaries
            **kwargs: Override parameters for this request

        Returns:
            Model completion response

        Raises:
            ModelError: If all models in the fallback chain fail
        """
        # Create a unique request ID for this completion
        with request_context(component=self.agent_type or "general") as request_id:
            # Add request context
            logger.info(
                "Starting model completion request",
                extra={
                    "messages_count": len(messages),
                    "parameters": {
                        k: v for k,
                        v in kwargs.items() if k not in ["messages"]}})

            # Override parameters for this request only
            request_parameters = self.parameters.copy()
            request_parameters.update(kwargs)

            # Check cache if enabled
            if ENABLE_CACHING and not request_parameters.get("stream", False):
                cache_key = self._generate_cache_key(
                    messages, request_parameters)

                # Try to get from cache for each model in the chain
                for model in self.fallback_models:
                    try:
                        # Try to get from cache
                        if hasattr(
                                self._cached_completion,
                                "cache_info"):  # Check if cache is available
                            cache_dict = {
                                "cache_key": cache_key,
                                "model": model
                            }
                            cache_key_str = json.dumps(
                                cache_dict, sort_keys=True)
                            if cache_key_str in self._cached_completion.cache:
                                logger.info(
                                    "Cache hit for model " + model, extra={
                                        "model": model, "cached": True})
                                return self._cached_completion.cache[cache_key_str]
                    except Exception as e:
                        logger.warning(
                            "Cache lookup failed: " +
                            str(e), extra={
                                "error": str(e), "error_type": type(e).__name__})

            # Try each model in the fallback chain
            last_error = None

            for model in self.fallback_models:
                try:
                    with performance_timer("api_call_" + model, logger=logger, level="debug", model=model):
                        with httpx.Client(timeout=request_parameters["request_timeout"]) as client:
                            headers = self.get_request_headers()

                            # Prepare the request payload
                            payload = {
                                "model": model,
                                "messages": messages,
                                **{k: v for k, v in request_parameters.items()
                                   if k not in ["request_timeout"]}
                            }

                            # Make the API request
                            logger.debug(
                                "Sending request to model " + model, extra={
                                    "model": model})
                            response = client.post(
                                OPENROUTER_API_ENDPOINT,
                                json=payload,
                                headers=headers
                            )

                            # Handle error responses
                            if response.status_code != 200:
                                self._handle_error_response(response)

                            # Parse and process the response
                            response_data = response.json()

                            # Update token usage statistics
                            self._update_token_usage(response_data)

                            # Cache the result if caching is enabled
                            if ENABLE_CACHING and not request_parameters.get(
                                    "stream", False):
                                cache_key = self._generate_cache_key(
                                    messages, request_parameters)
                                try:
                                    # Store in the cache manually since we're
                                    # not actually calling the function
                                    cache_dict = {
                                        "cache_key": cache_key,
                                        "model": model
                                    }
                                    cache_key_str = json.dumps(
                                        cache_dict, sort_keys=True)
                                    if hasattr(
                                            self._cached_completion, "cache"):
                                        self._cached_completion.cache[cache_key_str] = response_data
                                        logger.debug(
                                            "Cached response for model " + model, extra={
                                                "model": model, "cache_key": cache_key})
                                except Exception as e:
                                    logger.warning(
                                        "Cache storage failed: " +
                                        str(e), extra={
                                            "error": str(e), "error_type": type(e).__name__})

                            logger.info(
                                "Successfully got completion from model " + model,
                                extra={
                                    "model": model,
                                    "status_code": response.status_code,
                                    "usage": response_data.get(
                                        "usage",
                                        {})})
                            return response_data

                except (ModelUnavailableError, ModelRequestError) as e:
                    # Log the error and try the next model
                    logger.warning(
                        "Model " + model + " failed: " + str(e),
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "model": model,
                            "fallback_available": len(self.fallback_models) > 1
                        }
                    )
                    last_error = e
                    continue

                except (ModelTimeoutError, ModelRateLimitError) as e:
                    # Retry with exponential backoff
                    retry_after = getattr(e, "retry_after", 2)
                    logger.warning(
                        "Rate limit or timeout with model " + model,
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "model": model,
                            "retry_after": retry_after
                        }
                    )

                    for attempt in range(MAX_RETRIES):
                        wait_time = min(retry_after * (2 ** attempt), 30)
                        logger.info(
                            "Retrying after " + str(wait_time) + "s due to " +
                            str(e),
                            extra={
                                "attempt": attempt + 1,
                                "max_retries": MAX_RETRIES,
                                "wait_time": wait_time})
                        time.sleep(wait_time)

                        try:
                            with performance_timer("api_call_" + model + "_retry_" + str(attempt + 1), logger=logger, level="debug", model=model):
                                with httpx.Client(timeout=request_parameters["request_timeout"]) as client:
                                    response = client.post(
                                        OPENROUTER_API_ENDPOINT,
                                        json=payload,
                                        headers=headers
                                    )

                                    if response.status_code == 200:
                                        response_data = response.json()
                                        self._update_token_usage(response_data)
                                        logger.info(
                                            "Successfully got completion from model " + model + " after retry", extra={
                                                "model": model, "attempt": attempt + 1})
                                        return response_data

                                    # If still failing, check the error
                                    self._handle_error_response(response)
                        except (ModelTimeoutError, ModelRateLimitError) as retry_error:
                            # Continue retrying
                            last_error = retry_error
                            logger.warning(
                                "Retry " +
                                str(attempt +
                                    1) + " failed with " +
                                str(retry_error),
                                extra={
                                    "attempt": attempt +
                                    1,
                                    "error": str(retry_error)})
                            continue
                        except Exception as retry_error:
                            # Other errors, try next model
                            last_error = retry_error
                            logger.error(
                                "Unexpected error during retry: " +
                                str(retry_error), extra={
                                    "error": str(retry_error), "error_type": type(retry_error).__name__})
                            break

                    # If we exhaust all retries, try the next model
                    continue

                except ModelAuthenticationError as e:
                    # Authentication errors are fatal
                    logger.error(
                        "Authentication error: " + str(e),
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                    raise e

                except Exception as e:
                    # Unexpected errors
                    logger.error(
                        "Unexpected error with model " + model + ": " + str(e),
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "model": model
                        }
                    )
                    last_error = e
                    continue

            # If we get here, all models in the fallback chain failed
            error_msg = "All models in the fallback chain failed"
            if last_error:
                error_msg += ": " + str(last_error)

            logger.error(
                error_msg,
                extra={
                    "error": str(last_error) if last_error else "Unknown error",
                    "error_type": type(last_error).__name__ if last_error else "UnknownError",
                    "models_tried": self.fallback_models})
            raise ModelError(error_msg)

    def create_openai_client(self):
        """
        Create an OpenAI client configured to use the selected model via OpenRouter.

        Returns:
            An OpenAI client configured for OpenRouter
        """
        try:
            from openai import OpenAI
            from openai._base_client import DEFAULT_MAX_RETRIES
            from openai._client import _configure_transport

            # Get headers for OpenRouter
            headers = self.get_request_headers()
            # Filter out content-type and authorization as they're handled by
            # the client
            custom_headers = {k: v for k, v in headers.items()
                              if k not in ["Content-Type", "Authorization"]}

            # Create a client with OpenRouter configuration
            client = OpenAI(
                api_key=self.get_api_key("openrouter"),
                base_url=OPENROUTER_BASE_URL,
                default_headers=custom_headers,
            )

            # Configure retry settings with tenacity via the client's transport
            timeout = self.parameters["request_timeout"]

            # Reconfigure the transport with custom retry settings
            client._transport = _configure_transport(
                timeout=timeout,
                max_retries=MAX_RETRIES,
                http_client=client._http_client,
            )

            return client

        except ImportError:
            raise ImportError(
                "OpenAI package is required. Install with 'pip install openai>=1.0.0'.")

    def configure_openai_for_agent(self):
        """
        Configure the OpenAI library and Agent SDK to use this model manager's settings.

        This adds proper configuration for OpenRouter, model selection, and parameters.
        """
        try:
            import openai

            # Set the API key
            openai.api_key = self.get_api_key("openrouter")

            # Set the base URL to OpenRouter's endpoint
            openai.base_url = OPENROUTER_API_ENDPOINT

            # Set the default headers
            headers = self.get_request_headers()
            # Keep content-type and authorization separate as they're handled
            # by OpenAI client directly
            custom_headers = {k: v for k, v in headers.items()
                              if k not in ["Content-Type", "Authorization"]}

            openai.default_headers = custom_headers

            # If using the agent SDK, we should also set these parameters
            if hasattr(openai, "Agent"):
                # Check if there are any additional agent settings to apply
                pass

            logger.info(
                "OpenAI configured to use " +
                self.model_name + " via OpenRouter")

        except ImportError:
            raise ImportError(
                "OpenAI package is required. Install with 'pip install openai>=1.0.0'.")

    def get_agent_client(self):
        """
        Get a properly configured client for the Agent SDK.

        Returns:
            Configured Agent client
        """
        # Configure the OpenAI library
        self.configure_openai_for_agent()

        # Return a client object for the agent
        return self.create_openai_client()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit that cleans up resources."""
        if hasattr(self, 'httpx_client') and self.httpx_client:
            self.httpx_client.close()

    def _adjust_parameters_for_model(
            self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust parameters based on the specific model's capabilities.

        Args:
            parameters: Current parameter dictionary

        Returns:
            Adjusted parameter dictionary
        """
        model_name = self.model_name.lower() if self.model_name else ""

        # Handle models with large context windows
        if "gemma-3-27b-it" in model_name:
            # Gemma has 128k context window, adjust max_tokens if needed
            if parameters["max_tokens"] < 4000:
                logger.info(
                    "Adjusting max_tokens for Gemma 3-27b model with 128k context window")
                parameters["max_tokens"] = min(
                    parameters.get("max_tokens", 1000) * 2, 4000)

        # Handle models optimized for structured output
        if "qwen3-8b" in model_name:
            # Qwen is good for structured output, might want lower temperature
            if parameters["temperature"] > 0.2:
                logger.info(
                    "Adjusting temperature for Qwen model for better structured outputs")
                parameters["temperature"] = min(parameters["temperature"], 0.2)

        # Handle reasoning-focused models
        if "deepseek-chat" in model_name:
            # DeepSeek might benefit from slightly higher temperature for
            # reasoning
            if parameters["temperature"] < 0.1:
                logger.info(
                    "Adjusting temperature for DeepSeek model for better reasoning")
                parameters["temperature"] = max(parameters["temperature"], 0.1)

        return parameters


# Legacy functions for backward compatibility
def get_model_name(
        model_name: Optional[str] = None,
        agent_type: Optional[str] = None) -> str:
    """
    Legacy function to get the model name for backwards compatibility.

    Args:
        model_name: Explicitly provided model name
        agent_type: Type of agent

    Returns:
        The appropriate model name to use
    """
    manager = ModelManager(agent_type=agent_type)
    return manager._get_model_name() if model_name is None else model_name


def get_model_settings() -> Dict[str, Any]:
    """
    Legacy function to get model settings for backwards compatibility.

    Returns:
        Dictionary of model settings
    """
    manager = ModelManager()
    return manager.parameters


def get_api_key(provider: str = "openrouter") -> str:
    """
    Legacy function to get API key for backwards compatibility.

    Args:
        provider: Name of the provider

    Returns:
        API key for the provider
    """
    manager = ModelManager()
    return manager.get_api_key(provider)


def get_openrouter_headers() -> Dict[str, str]:
    """
    Legacy function to get OpenRouter headers for backwards compatibility.

    Returns:
        Dictionary of headers for OpenRouter API calls
    """
    manager = ModelManager()
    return manager.get_request_headers()


def create_openrouter_client():
    """
    Legacy function to create an OpenRouter client for backwards compatibility.

    Returns:
        An OpenAI client configured for OpenRouter
    """
    manager = ModelManager()
    return manager.create_openai_client()


def configure_openai_for_openrouter():
    """
    Legacy function to configure OpenAI for OpenRouter for backwards compatibility.
    """
    manager = ModelManager()
    manager.configure_openai_for_agent()


@retry(stop=stop_after_attempt(MAX_RETRIES),
       wait=wait_exponential(multiplier=1, min=2, max=30))
def make_openrouter_request(url, payload, headers):
    """
    Legacy function to make a request to OpenRouter with retry logic.

    Args:
        url: The API endpoint URL
        payload: The request payload
        headers: The request headers

    Returns:
        The API response
    """
    manager = ModelManager()

    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=manager.parameters["request_timeout"]
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        # Handle rate limiting (status code 429)
        if e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 5))
            time.sleep(retry_after)
            raise e  # Trigger retry
        else:
            raise e  # Will be caught by retry decorator if within retry conditions
