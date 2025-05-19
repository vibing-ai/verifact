"""
Database utilities for Supabase and PGVector integration.

This module provides functions and classes for:
- Connecting to Supabase databases
- Working with PGVector for vector embeddings storage
- Storing and retrieving factcheck results
"""

import os
from typing import Dict, List, Any, Optional, Union
import logging
from pydantic import BaseModel

# Import optional dependencies - these might not be available
# in all environments, so we use try/except
try:
    import psycopg2
    from psycopg2.extras import execute_values
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for interacting with Supabase and PGVector."""

    def __init__(self):
        """Initialize Supabase connection."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.pg_connection_string = os.getenv("SUPABASE_DB_URL")
        
        # Initialize Supabase client if credentials are available
        self.supabase: Optional[Client] = None
        
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase package not installed. Install with 'pip install supabase'")
            return
            
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Successfully connected to Supabase")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {str(e)}")
    
    def connect_pg(self):
        """Connect directly to PostgreSQL database."""
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 package not installed. Install with 'pip install psycopg2-binary'")
            return None
            
        if not self.pg_connection_string:
            logger.error("PostgreSQL connection string not provided")
            return None
        
        try:
            return psycopg2.connect(self.pg_connection_string)
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            return None
    
    def setup_pgvector(self) -> bool:
        """
        Set up pgvector extension if not already installed.
        
        Returns:
            bool: True if pgvector is set up successfully, False otherwise
        """
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 package not installed. Install with 'pip install psycopg2-binary'")
            return False
            
        if not self.pg_connection_string:
            logger.error("PostgreSQL connection string not provided")
            return False
            
        try:
            with self.connect_pg() as conn:
                if not conn:
                    return False
                    
                with conn.cursor() as cur:
                    # Check if pgvector is already installed
                    cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                    if not cur.fetchone()[0]:
                        # Install pgvector extension
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        conn.commit()
                        logger.info("Successfully installed pgvector extension")
                    else:
                        logger.info("pgvector extension already installed")
                    return True
        except Exception as e:
            logger.error(f"Failed to set up pgvector: {str(e)}")
            return False
    
    def store_factcheck_result(self, 
                              claim: str, 
                              verdict: str, 
                              confidence: float, 
                              explanation: str, 
                              sources: List[str]) -> Dict[str, Any]:
        """
        Store a factcheck result in the database.
        
        Args:
            claim: The claim text
            verdict: The verdict (true, false, etc.)
            confidence: Confidence score (0-1)
            explanation: Explanation text
            sources: List of source URLs
            
        Returns:
            Dict with operation result
        """
        if not SUPABASE_AVAILABLE:
            return {"success": False, "error": "Supabase package not installed"}
            
        if not self.supabase:
            return {"success": False, "error": "Supabase client not initialized"}
            
        try:
            # Insert the factcheck result into the factchecks table
            result = self.supabase.table("factchecks").insert({
                "claim": claim,
                "verdict": verdict,
                "confidence": confidence,
                "explanation": explanation,
                "sources": sources
            }).execute()
            
            return {"success": True, "data": result.data}
            
        except Exception as e:
            logger.error(f"Failed to store factcheck result: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_recent_factchecks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent factcheck results.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of factcheck results
        """
        if not self.supabase:
            logger.error("Supabase client not initialized")
            return []
            
        try:
            result = self.supabase.table("factchecks").select("*").order("created_at", desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to retrieve recent factchecks: {str(e)}")
            return []


# Create a singleton instance
db = SupabaseClient() 