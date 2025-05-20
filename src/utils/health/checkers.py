"""
Health check utilities for VeriFact.

This module provides functions for checking the health of various system dependencies.
"""

import os
import time
from typing import Any, Dict, Optional

import httpx
import redis

from src.utils.db.db import SupabaseClient


async def check_database() -> Dict[str, Any]:
    """Check Supabase database connection health."""
    start_time = time.time()
    result = {
        "status": "unknown",
        "latency_ms": 0,
    }

    try:
        # Create Supabase client
        client = SupabaseClient()

        if not client.supabase:
            result["status"] = "error"
            result["details"] = {
                "error": "Supabase client not initialized - check URL and API key",
                "error_type": "ConnectionError",
            }
            return result

        # Check if we can connect to the database
        with client.get_cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            # Check if pgvector is available
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            pgvector_available = cursor.fetchone()[0]

            # Get some database stats
            cursor.execute(
                """
                SELECT
                    count(*) as total_claims,
                    (SELECT count(*) FROM evidence) as total_evidence,
                    (SELECT count(*) FROM verdicts) as total_verdicts,
                    (SELECT count(*) FROM embeddings) as total_embeddings
                FROM claims
            """
            )
            stats_row = cursor.fetchone()

            # Build metrics dictionary
            metrics = {
                "version": version,
                "pgvector_available": pgvector_available,
                "stats": {
                    "claims": stats_row[0] if stats_row else 0,
                    "evidence": stats_row[1] if stats_row else 0,
                    "verdicts": stats_row[2] if stats_row else 0,
                    "embeddings": stats_row[3] if stats_row else 0,
                },
            }

        result["status"] = "ok"
        result["details"] = metrics
    except Exception as e:
        result["status"] = "error"
        result["details"] = {"error": str(e), "error_type": type(e).__name__}
    finally:
        result["latency_ms"] = int((time.time() - start_time) * 1000)

    return result


async def check_redis() -> Optional[Dict[str, Any]]:
    """Check Redis connection health."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None

    start_time = time.time()
    result = {
        "status": "unknown",
        "latency_ms": 0,
    }

    try:
        # Connect to Redis
        r = redis.from_url(redis_url)
        r.ping()

        # Get some stats
        info = r.info()
        result["status"] = "ok"
        result["details"] = {
            "version": info.get("redis_version"),
            "used_memory_mb": round(int(info.get("used_memory", 0)) / (1024 * 1024), 2),
            "clients_connected": info.get("connected_clients"),
        }
    except Exception as e:
        result["status"] = "error"
        result["details"] = {"error": str(e), "error_type": type(e).__name__}
    finally:
        result["latency_ms"] = int((time.time() - start_time) * 1000)

    return result


async def check_openrouter_api() -> Dict[str, Any]:
    """Check OpenRouter API health."""
    start_time = time.time()
    result = {
        "status": "unknown",
        "latency_ms": 0,
    }

    try:
        # We'll just check the API's availability without using the actual API
        # key for security
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://openrouter.ai/api/v1/auth/key")

        if response.status_code < 500:  # Any non-server error is considered "available"
            result["status"] = "ok"
            result["details"] = {
                "status_code": response.status_code,
            }
        else:
            result["status"] = "degraded"
            result["details"] = {
                "status_code": response.status_code,
            }
    except Exception as e:
        result["status"] = "error"
        result["details"] = {"error": str(e), "error_type": type(e).__name__}
    finally:
        result["latency_ms"] = int((time.time() - start_time) * 1000)

    return result
