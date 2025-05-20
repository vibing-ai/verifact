"""
Database utilities for VeriFact.

This module provides database connection and query utilities for Supabase and PGVector integration.
"""

from src.utils.db.db import *
from src.utils.db.pool import (
    init_db_pool,
    close_db_pool,
    get_db_pool,
    get_db_connection,
    get_db_metrics
)

__all__ = [
    "db", 
    "store_factcheck_result", 
    "get_recent_factchecks",
    "init_db_pool",
    "close_db_pool",
    "get_db_pool",
    "get_db_connection",
    "get_db_metrics"
] 