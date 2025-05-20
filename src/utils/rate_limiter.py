"""Rate Limiting Utilities

This module provides utilities for rate limiting API requests.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.utils.cache import Cache
from src.utils.validation.config import validation_config

logger = logging.getLogger("verifact.rate_limiter")


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool  # Whether the request is allowed
    limit: int  # The rate limit
    remaining: int  # Remaining requests
    reset: int  # Seconds until the rate limit resets
    retry_after: int | None = None  # Seconds to wait before retrying


class RateLimitStore(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def increment(self, key: str, window_seconds: int) -> tuple[int, list[float]]:
        """Increment request count for a key and return the count and timestamps.

        Args:
            key: Rate limit key
            window_seconds: Time window in seconds

        Returns:
            Tuple[int, List[float]]: Count and list of timestamps
        """
        pass

    @abstractmethod
    async def get_count(self, key: str, window_seconds: int) -> tuple[int, list[float]]:
        """Get the current request count for a key.

        Args:
            key: Rate limit key
            window_seconds: Time window in seconds

        Returns:
            Tuple[int, List[float]]: Count and list of timestamps
        """
        pass

    @abstractmethod
    async def reset(self, key: str) -> bool:
        """Reset the request count for a key.

        Args:
            key: Rate limit key

        Returns:
            bool: True if reset was successful, False otherwise
        """
        pass


class MemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit storage using Cache."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600 * 2):
        """Initialize the in-memory rate limit store.

        Args:
            max_size: Maximum number of keys to store
            ttl_seconds: Time-to-live in seconds for cache entries
        """
        self.cache = Cache(max_size=max_size, ttl_seconds=ttl_seconds)

    async def increment(self, key: str, window_seconds: int) -> tuple[int, list[float]]:
        """Increment request count for a key and return the count and timestamps.

        Args:
            key: Rate limit key
            window_seconds: Time window in seconds

        Returns:
            Tuple[int, List[float]]: Count and list of timestamps
        """
        # Get current time
        current_time = time.time()
        window_start = current_time - window_seconds

        # Get current data
        data = self.cache.get(key, {"count": 0, "timestamps": []})

        # Filter out old timestamps
        timestamps = [ts for ts in data.get("timestamps", []) if ts > window_start]

        # Add current timestamp
        timestamps.append(current_time)

        # Update data
        data = {"count": len(timestamps), "timestamps": timestamps}

        # Store updated data
        self.cache.set(key, data)

        return len(timestamps), timestamps

    async def get_count(self, key: str, window_seconds: int) -> tuple[int, list[float]]:
        """Get the current request count for a key.

        Args:
            key: Rate limit key
            window_seconds: Time window in seconds

        Returns:
            Tuple[int, List[float]]: Count and list of timestamps
        """
        # Get current time
        current_time = time.time()
        window_start = current_time - window_seconds

        # Get current data
        data = self.cache.get(key, {"count": 0, "timestamps": []})

        # Filter out old timestamps
        timestamps = [ts for ts in data.get("timestamps", []) if ts > window_start]

        return len(timestamps), timestamps

    async def reset(self, key: str) -> bool:
        """Reset the request count for a key.

        Args:
            key: Rate limit key

        Returns:
            bool: True if reset was successful, False otherwise
        """
        self.cache.set(key, {"count": 0, "timestamps": []})
        return True


class DatabaseRateLimitStore(RateLimitStore):
    """Database-backed rate limit storage using Supabase."""

    def __init__(self):
        """Initialize the database rate limit store."""
        # Lazy-loaded pool to avoid circular imports
        self._pool = None

    async def _get_pool(self):
        """Get the database connection pool."""
        if self._pool is None:
            # Import here to avoid circular imports
            from src.utils.db.db import get_pool

            self._pool = await get_pool()

        return self._pool

    async def increment(self, key: str, window_seconds: int) -> tuple[int, list[float]]:
        """Increment request count for a key and return the count and timestamps.

        Args:
            key: Rate limit key
            window_seconds: Time window in seconds

        Returns:
            Tuple[int, List[float]]: Count and list of timestamps
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Create table if it doesn't exist
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limits (
                    key TEXT PRIMARY KEY,
                    timestamps JSONB NOT NULL DEFAULT '[]'::jsonb,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )

            # Get current time
            current_time = time.time()
            window_start = current_time - window_seconds

            # Get current timestamps
            result = await conn.fetchval("SELECT timestamps FROM rate_limits WHERE key = $1", key)

            timestamps = result or []

            # Filter out old timestamps
            timestamps = [ts for ts in timestamps if ts > window_start]

            # Add current timestamp
            timestamps.append(current_time)

            # Update timestamps
            await conn.execute(
                """
                INSERT INTO rate_limits (key, timestamps, last_updated)
                VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE
                SET timestamps = $2, last_updated = NOW()
                """,
                key,
                timestamps,
            )

            return len(timestamps), timestamps

    async def get_count(self, key: str, window_seconds: int) -> tuple[int, list[float]]:
        """Get the current request count for a key.

        Args:
            key: Rate limit key
            window_seconds: Time window in seconds

        Returns:
            Tuple[int, List[float]]: Count and list of timestamps
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Get current time
            current_time = time.time()
            window_start = current_time - window_seconds

            # Get current timestamps
            result = await conn.fetchval("SELECT timestamps FROM rate_limits WHERE key = $1", key)

            timestamps = result or []

            # Filter out old timestamps
            timestamps = [ts for ts in timestamps if ts > window_start]

            return len(timestamps), timestamps

    async def reset(self, key: str) -> bool:
        """Reset the request count for a key.

        Args:
            key: Rate limit key

        Returns:
            bool: True if reset was successful, False otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Update timestamps
            await conn.execute(
                """
                INSERT INTO rate_limits (key, timestamps, last_updated)
                VALUES ($1, '[]'::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                SET timestamps = '[]'::jsonb, last_updated = NOW()
                """,
                key,
            )

            return True


class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(self, store: RateLimitStore | None = None):
        """Initialize the rate limiter.

        Args:
            store: Storage backend for rate limits
        """
        self.store = store or MemoryRateLimitStore()

        # Load configuration
        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.default_limit = validation_config.get("api.rate_limit", 100)
        self.authenticated_limit = validation_config.get("api.authenticated_rate_limit", 1000)
        self.default_window = 3600  # 1 hour in seconds

        # Tier configuration
        self.tiers = {
            "free": self.default_limit,
            "basic": self.authenticated_limit,
            "premium": self.authenticated_limit * 2,
            "enterprise": self.authenticated_limit * 10,
        }

    def _get_limit_for_key(self, key: str, api_key_data: dict[str, Any] | None = None) -> int:
        """Get the rate limit for a key.

        Args:
            key: Rate limit key
            api_key_data: API key data

        Returns:
            int: Rate limit
        """
        # If API key data is available, use the tier limit
        if api_key_data:
            tier = api_key_data.get("tier", "free")
            return self.tiers.get(tier, self.default_limit)

        # Default limit for unauthenticated requests
        return self.default_limit

    async def check(
        self,
        identifier: str,
        api_key_data: dict[str, Any] | None = None,
        window_seconds: int | None = None,
    ) -> RateLimitResult:
        """Check if a request is allowed or rate limited.

        Args:
            identifier: Request identifier (e.g., IP address or API key)
            api_key_data: API key data
            window_seconds: Time window in seconds

        Returns:
            RateLimitResult: Rate limit check result
        """
        if not self.enabled:
            # Rate limiting is disabled
            return RateLimitResult(allowed=True, limit=0, remaining=0, reset=0)

        # Get configuration
        window = window_seconds or self.default_window
        limit = self._get_limit_for_key(identifier, api_key_data)

        # Create cache key
        key = f"rate_limit:{identifier}"

        # Get current count
        count, timestamps = await self.store.get_count(key, window)

        # Check if limit exceeded
        if count >= limit:
            # Calculate retry-after time
            current_time = time.time()
            window_start = current_time - window
            oldest_timestamp = min(timestamps) if timestamps else current_time
            retry_after = max(1, int(oldest_timestamp - window_start))

            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset=int(window_start + window),
                retry_after=retry_after,
            )

        # Increment count
        count, _ = await self.store.increment(key, window)

        # Calculate remaining requests
        remaining = max(0, limit - count)

        return RateLimitResult(
            allowed=True, limit=limit, remaining=remaining, reset=int(time.time() + window)
        )

    async def reset(self, identifier: str) -> bool:
        """Reset the rate limit for an identifier.

        Args:
            identifier: Request identifier to reset

        Returns:
            bool: True if reset was successful, False otherwise
        """
        key = f"rate_limit:{identifier}"
        return await self.store.reset(key)


# Create a singleton instance
rate_limiter = RateLimiter()
