"""
Caching utilities for VeriFact.

This module provides a simple in-memory caching mechanism with TTL support.
"""

import os
import time
import json
import threading
import redis
import pickle
import hashlib
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

# Update imports
from src.utils.logging.logger import get_component_logger

# Get logger
logger = get_component_logger("cache")

# Redis connection
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_ENABLED = os.environ.get("REDIS_ENABLED", "true").lower() == "true"

# Default TTL values
DEFAULT_CACHE_TTL = int(os.environ.get("DEFAULT_CACHE_TTL", 3600))  # 1 hour in seconds

# Initialize Redis pool
if REDIS_ENABLED:
    try:
        redis_pool = redis.ConnectionPool.from_url(
            REDIS_URL, 
            password=REDIS_PASSWORD,
            decode_responses=False  # We'll handle serialization/deserialization ourselves
        )
        logger.info(f"Redis cache initialized with URL: {REDIS_URL}")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {str(e)}")
        redis_pool = None
        REDIS_ENABLED = False
else:
    redis_pool = None
    logger.info("Redis cache disabled by configuration")


class Cache:
    """Redis-backed cache with fallback to in-memory cache when Redis is unavailable."""
    
    def __init__(self, namespace: str = "default"):
        """
        Initialize a cache instance.
        
        Args:
            namespace: A namespace to prefix all cache keys with
        """
        self.namespace = namespace
        self.ttl = DEFAULT_CACHE_TTL
        self._local_cache = {}  # Fallback in-memory cache
        
        # Create Redis client if enabled
        if REDIS_ENABLED and redis_pool:
            self.redis = redis.Redis(connection_pool=redis_pool)
        else:
            self.redis = None
            logger.warning(f"Using in-memory cache for namespace '{namespace}'")
    
    def _make_key(self, key: str) -> str:
        """Create a namespaced cache key."""
        return f"verifact:{self.namespace}:{key}"
    
    def _hash_key(self, complex_key: Any) -> str:
        """Hash complex objects to use as keys."""
        if isinstance(complex_key, str):
            return complex_key
        
        # For complex objects, create a deterministic hash
        key_str = json.dumps(complex_key, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: Any, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key (string or hashable object)
            default: Default value to return if key not found
            
        Returns:
            The cached value or default if not found
        """
        hashed_key = self._hash_key(key)
        namespaced_key = self._make_key(hashed_key)
        
        # Try Redis first if available
        if self.redis:
            try:
                cached_data = self.redis.get(namespaced_key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis error in get operation: {str(e)}")
        
        # Fall back to in-memory cache
        return self._local_cache.get(namespaced_key, default)
    
    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key (string or hashable object)
            value: The value to cache
            ttl: Time-to-live in seconds (None for default TTL)
            
        Returns:
            bool: True if successful, False otherwise
        """
        hashed_key = self._hash_key(key)
        namespaced_key = self._make_key(hashed_key)
        ttl = ttl if ttl is not None else self.ttl
        
        # Store in Redis if available
        if self.redis:
            try:
                serialized = pickle.dumps(value)
                return self.redis.setex(namespaced_key, ttl, serialized)
            except Exception as e:
                logger.warning(f"Redis error in set operation: {str(e)}")
        
        # Fall back to in-memory cache
        self._local_cache[namespaced_key] = value
        return True
    
    def delete(self, key: Any) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key to delete
            
        Returns:
            bool: True if deleted, False otherwise
        """
        hashed_key = self._hash_key(key)
        namespaced_key = self._make_key(hashed_key)
        
        # Delete from Redis if available
        redis_success = False
        if self.redis:
            try:
                redis_success = bool(self.redis.delete(namespaced_key))
            except Exception as e:
                logger.warning(f"Redis error in delete operation: {str(e)}")
        
        # Delete from in-memory cache
        if namespaced_key in self._local_cache:
            del self._local_cache[namespaced_key]
            return True
        
        return redis_success
    
    def clear_namespace(self) -> bool:
        """
        Clear all keys in this cache namespace.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pattern = f"verifact:{self.namespace}:*"
        
        # Clear Redis if available
        if self.redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = self.redis.scan(cursor, pattern, 100)
                    if keys:
                        self.redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis error in clear_namespace operation: {str(e)}")
                return False
        
        # Clear in-memory cache keys in this namespace
        keys_to_delete = [k for k in self._local_cache.keys() if k.startswith(f"verifact:{self.namespace}:")]
        for k in keys_to_delete:
            del self._local_cache[k]
            
        return True
    
    def exists(self, key: Any) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: The cache key to check
            
        Returns:
            bool: True if it exists, False otherwise
        """
        hashed_key = self._hash_key(key)
        namespaced_key = self._make_key(hashed_key)
        
        # Check Redis if available
        if self.redis:
            try:
                return bool(self.redis.exists(namespaced_key))
            except Exception as e:
                logger.warning(f"Redis error in exists operation: {str(e)}")
        
        # Fall back to in-memory cache
        return namespaced_key in self._local_cache


# Global cache instances for common components
claim_cache = Cache("claims")
entity_cache = Cache("entities")
search_cache = Cache("search_results")
model_cache = Cache("model_responses")
evidence_cache = Cache("evidence") 