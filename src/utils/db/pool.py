"""Database connection pooling for VeriFact.

This module provides a database connection pool manager for efficient database access.
"""

import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

# Global pool variable
_pool = None


@lru_cache
def get_pool_config() -> dict[str, Any]:
    """Get database pool configuration from environment variables.

    Returns:
        Dictionary with pool configuration
    """
    return {
        "min_size": int(os.getenv("DB_POOL_MIN_SIZE", "2")),
        "max_size": int(os.getenv("DB_POOL_MAX_SIZE", "10")),
        "max_inactive_connection_lifetime": float(os.getenv("DB_POOL_MAX_IDLE_TIME", "300")),
        "command_timeout": float(os.getenv("DB_COMMAND_TIMEOUT", "60.0")),
    }


async def init_db_pool():
    """Initialize the database connection pool.

    Should be called during application startup.
    """
    global _pool
    if _pool is not None:
        logger.warning("Database pool already initialized")
        return

    # Get database URL from environmen
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise ValueError("SUPABASE_DB_URL environment variable is not set")

    # Get pool configuration
    pool_config = get_pool_config()
    logger.info(
        "Initializing database pool",
        extra={
            "min_size": pool_config["min_size"],
            "max_size": pool_config["max_size"],
            "max_idle_time": pool_config["max_inactive_connection_lifetime"],
        },
    )

    try:
        # Create connection pool
        _pool = await asyncpg.create_pool(dsn=db_url, **pool_config)

        # Test connection
        async with _pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"Connected to PostgreSQL: {version}")

    except Exception:
        logger.exception("Failed to initialize database pool")
        raise


async def close_db_pool():
    """Close the database connection pool.

    Should be called during application shutdown.
    """
    global _pool
    if _pool is None:
        logger.warning("No database pool to close")
        return

    logger.info("Closing database pool")
    await _pool.close()
    _pool = None


def get_db_pool():
    """Get the database connection pool.

    Returns:
        The database connection pool

    Raises:
        RuntimeError: If pool has not been initialized
    """
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool first.")
    return _pool


@asynccontextmanager
async def get_db_connection():
    """Context manager to get a database connection from the pool.

    Yields:
        A database connection

    Example:
        ```
        async with get_db_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")
        ```
    """
    pool = get_db_pool()
    async with pool.acquire() as connection:
        yield connection


async def get_db_metrics() -> dict[str, Any]:
    """Get metrics about the database connection pool.

    Returns:
        Dictionary with pool metrics
    """
    pool = get_db_pool()
    return {
        "size": pool.get_size(),
        "free_connections": pool.get_idle_size(),
        "used_connections": pool.get_size() - pool.get_idle_size(),
        "max_size": pool.get_max_size(),
    }
