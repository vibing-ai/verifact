"""
Database module for VeriFact.

This module provides database connection and query utilities for Supabase and PGVector integration.
"""

from src.utils.db.db import (
    SupabaseClient, 
    db,
    store_factcheck_result,
    get_recent_factchecks
)
from src.utils.db.pool import (
    close_db_pool,
    get_db_pool,
    init_db_pool,
)

__all__ = [
    "db",
    "store_factcheck_result",
    "get_recent_factchecks",
    "init_db_pool",
    "close_db_pool",
    "get_db_pool",
    "SupabaseClient",
]
