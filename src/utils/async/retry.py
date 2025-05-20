"""
VeriFact Retry Utilities

This module provides utilities for implementing retry logic
for handling recoverable errors in the VeriFact system.
"""

import time
import random
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast
from functools import wraps

from src.utils.exceptions import (
    VerifactError, RateLimitError, 
    ResourceUnavailableError, ExternalServiceError
)

logger = logging.getLogger("verifact.retry")

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Any])


# Decorator for synchronous functions
def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: List[Type[Exception]] = None
) -> Callable[[F], F]:
    """
    Decorator that retries a function on specified exceptions.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor by which delay increases after each attempt
        jitter: Whether to add random jitter to delay
        exceptions: List of exception types to retry on (defaults to RateLimitError and ResourceUnavailableError)
        
    Returns:
        Decorated function with retry logic
    """
    if exceptions is None:
        exceptions = [RateLimitError, ResourceUnavailableError]
    
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    
                    # Special handling for rate limit errors with retry-after info
                    if isinstance(e, RateLimitError) and e.details.get("retry_after"):
                        retry_after = e.details["retry_after"]
                        actual_delay = retry_after
                    else:
                        actual_delay = delay
                        if jitter:
                            actual_delay = actual_delay * (1 + random.random() * 0.1)
                    
                    # Log retry attempt
                    if attempt < max_attempts:
                        service_info = ""
                        if hasattr(e, 'details') and e.details.get('service'):
                            service_info = f" for service '{e.details['service']}'"
                            
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed{service_info}: {str(e)}. "
                            f"Retrying in {actual_delay:.2f}s..."
                        )
                        time.sleep(actual_delay)
                        delay *= backoff_factor
                except Exception as e:
                    # Don't retry on other exceptions
                    raise
            
            # If we get here, all retries failed
            logger.error(f"All {max_attempts} retry attempts failed")
            if last_exception:
                raise last_exception
            
            # This should never happen but just in case
            raise ExternalServiceError(message="Retry attempts exhausted")
            
        return cast(F, wrapper)
    return decorator


# Decorator for async functions
def with_async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: List[Type[Exception]] = None
) -> Callable[[AsyncF], AsyncF]:
    """
    Decorator that retries an async function on specified exceptions.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor by which delay increases after each attempt
        jitter: Whether to add random jitter to delay
        exceptions: List of exception types to retry on (defaults to RateLimitError and ResourceUnavailableError)
        
    Returns:
        Decorated async function with retry logic
    """
    if exceptions is None:
        exceptions = [RateLimitError, ResourceUnavailableError]
    
    def decorator(func: AsyncF) -> AsyncF:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    
                    # Special handling for rate limit errors with retry-after info
                    if isinstance(e, RateLimitError) and e.details.get("retry_after"):
                        retry_after = e.details["retry_after"]
                        actual_delay = retry_after
                    else:
                        actual_delay = delay
                        if jitter:
                            actual_delay = actual_delay * (1 + random.random() * 0.1)
                    
                    # Log retry attempt
                    if attempt < max_attempts:
                        service_info = ""
                        if hasattr(e, 'details') and e.details.get('service'):
                            service_info = f" for service '{e.details['service']}'"
                            
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed{service_info}: {str(e)}. "
                            f"Retrying in {actual_delay:.2f}s..."
                        )
                        await asyncio.sleep(actual_delay)
                        delay *= backoff_factor
                except Exception as e:
                    # Don't retry on other exceptions
                    raise
            
            # If we get here, all retries failed
            logger.error(f"All {max_attempts} retry attempts failed")
            if last_exception:
                raise last_exception
            
            # This should never happen but just in case
            raise ExternalServiceError(message="Retry attempts exhausted")
            
        return cast(AsyncF, wrapper)
    return decorator


async def async_retry_context(
    func: Callable[..., Any],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: List[Type[Exception]] = None,
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    Context for retrying an async function or coroutine.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor by which delay increases after each attempt
        jitter: Whether to add random jitter to delay
        exceptions: List of exception types to retry on
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the function call
        
    Raises:
        Exception: If all retry attempts fail
    """
    if exceptions is None:
        exceptions = [RateLimitError, ResourceUnavailableError]
        
    last_exception = None
    delay = initial_delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            elif asyncio.iscoroutine(func):
                return await func
            else:
                return func(*args, **kwargs)
        except tuple(exceptions) as e:
            last_exception = e
            
            # Special handling for rate limit errors with retry-after info
            if isinstance(e, RateLimitError) and e.details.get("retry_after"):
                retry_after = e.details["retry_after"]
                actual_delay = retry_after
            else:
                actual_delay = delay
                if jitter:
                    actual_delay = actual_delay * (1 + random.random() * 0.1)
            
            # Log retry attempt
            if attempt < max_attempts:
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                    f"Retrying in {actual_delay:.2f}s..."
                )
                await asyncio.sleep(actual_delay)
                delay *= backoff_factor
        except Exception as e:
            # Don't retry on other exceptions
            raise
    
    # If we get here, all retries failed
    logger.error(f"All {max_attempts} retry attempts failed")
    if last_exception:
        raise last_exception
    
    # This should never happen but just in case
    raise ExternalServiceError(message="Retry attempts exhausted") 