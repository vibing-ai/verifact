"""
Database initialization for Supabase.

This module provides functions to initialize and verify the Supabase database schema.
"""

import logging
from typing import Any, Dict

from .db import SupabaseClient

logger = logging.getLogger(__name__)


async def initialize_database() -> Dict[str, Any]:
    """
    Initialize the Supabase database with required schema.

    Returns:
        Dict with initialization status information
    """
    logger.info("Initializing Supabase database schema")

    # Create Supabase client
    client = SupabaseClient()
    if not client.supabase:
        return {"status": "error", "message": "Failed to create Supabase client"}

    try:
        # Verify PGVector extension
        result = await verify_pgvector_extension(client)
        if not result["available"]:
            logger.warning(
                "PGVector extension not available in Supabase. Vector similarity search will not work."
            )

        # Initialize schema
        await create_tables(client)

        return {
            "status": "success",
            "message": "Database schema initialized successfully",
            "pgvector_status": result,
        }
    except Exception as e:
        logger.exception("Failed to initialize database schema")
        return {"status": "error", "message": f"Failed to initialize database schema: {str(e)}"}


async def verify_pgvector_extension(client: SupabaseClient) -> Dict[str, Any]:
    """
    Verify if the pgvector extension is enabled in Supabase.

    Args:
        client: SupabaseClient instance

    Returns:
        Dict with extension status information
    """
    try:
        # Check if pgvector extension is installed
        with client.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """
            )
            result = cursor.fetchone()
            is_installed = result[0] if result else False

            # Check pgvector version if installed
            if is_installed:
                cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                version_result = cursor.fetchone()
                version = version_result[0] if version_result else "unknown"

                # Check if the vector type exists and is usable
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'vector'
                    )
                """
                )
                type_exists = cursor.fetchone()[0]

                return {
                    "available": True,
                    "installed": True,
                    "version": version,
                    "type_exists": type_exists,
                }
            else:
                return {
                    "available": False,
                    "installed": False,
                    "message": "pgvector extension is not installed",
                }
    except Exception as e:
        logger.exception("Error checking pgvector extension")
        return {"available": False, "error": str(e)}


async def create_tables(client: SupabaseClient) -> None:
    """
    Create necessary tables in the Supabase database.

    Args:
        client: SupabaseClient instance
    """
    with client.get_cursor() as cursor:
        # Create claims table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS claims (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                text TEXT NOT NULL,
                context TEXT,
                checkworthy BOOLEAN DEFAULT TRUE,
                domain TEXT,
                entities JSONB DEFAULT '[]',
                extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                source_text TEXT,
                source_url TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        )

        # Create evidence table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                source_name TEXT,
                source_type TEXT DEFAULT 'unknown',
                relevance FLOAT NOT NULL,
                stance TEXT NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE,
                credibility FLOAT,
                excerpt_context TEXT,
                retrieval_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        )

        # Create verdicts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS verdicts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                verdict TEXT NOT NULL,
                confidence FLOAT NOT NULL,
                explanation TEXT NOT NULL,
                sources JSONB NOT NULL,
                evidence_summary TEXT,
                generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        )

        # Create embeddings table for vector storage (if pgvector is available)
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    embedding VECTOR(1536) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )
        except Exception as e:
            logger.warning(f"Could not create embeddings table: {str(e)}")

        # For backward compatibility (can be removed later)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS factchecks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                claim TEXT NOT NULL,
                verdict TEXT NOT NULL,
                confidence FLOAT NOT NULL,
                explanation TEXT NOT NULL,
                sources JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        )

        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS claims_domain_idx ON claims(domain)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS claims_created_at_idx ON claims(created_at DESC)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS evidence_claim_id_idx ON evidence(claim_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS verdicts_claim_id_idx ON verdicts(claim_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS verdicts_verdict_idx ON verdicts(verdict)")

        # Try to create vector index if pgvector is available
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings
                USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS embeddings_metadata_idx ON embeddings USING GIN (metadata)
            """
            )
        except Exception as e:
            logger.warning(f"Could not create vector indexes: {str(e)}")

        # Try to create functions for vector search if pgvector is available
        try:
            # Function for similarity search with filters
            cursor.execute(
                """
                CREATE OR REPLACE FUNCTION match_embeddings(
                    query_embedding VECTOR(1536),
                    match_threshold FLOAT,
                    match_count INT,
                    filter_metadata JSONB DEFAULT NULL
                )
                RETURNS TABLE (
                    id UUID,
                    content TEXT,
                    metadata JSONB,
                    similarity FLOAT
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    IF filter_metadata IS NULL THEN
                        RETURN QUERY
                        SELECT
                            e.id,
                            e.content,
                            e.metadata,
                            1 - (e.embedding <-> query_embedding) AS similarity
                        FROM
                            embeddings e
                        WHERE
                            1 - (e.embedding <-> query_embedding) > match_threshold
                        ORDER BY
                            similarity DESC
                        LIMIT
                            match_count;
                    ELSE
                        RETURN QUERY
                        SELECT
                            e.id,
                            e.content,
                            e.metadata,
                            1 - (e.embedding <-> query_embedding) AS similarity
                        FROM
                            embeddings e
                        WHERE
                            1 - (e.embedding <-> query_embedding) > match_threshold
                            AND e.metadata @> filter_metadata
                        ORDER BY
                            similarity DESC
                        LIMIT
                            match_count;
                    END IF;
                END;
                $$
            """
            )

            # Function for finding similar claims
            cursor.execute(
                """
                CREATE OR REPLACE FUNCTION find_similar_claims(
                    query_embedding VECTOR(1536),
                    match_threshold FLOAT DEFAULT 0.8,
                    match_count INT DEFAULT 10
                )
                RETURNS TABLE (
                    claim_id UUID,
                    claim_text TEXT,
                    verdict TEXT,
                    confidence FLOAT,
                    similarity FLOAT
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        (e.metadata->>'claim_id')::UUID AS claim_id,
                        e.content AS claim_text,
                        v.verdict,
                        v.confidence,
                        1 - (e.embedding <-> query_embedding) AS similarity
                    FROM
                        embeddings e
                    LEFT JOIN
                        verdicts v ON v.claim_id = (e.metadata->>'claim_id')::UUID
                    WHERE
                        1 - (e.embedding <-> query_embedding) > match_threshold
                        AND e.metadata->>'type' = 'claim'
                    ORDER BY
                        similarity DESC
                    LIMIT
                        match_count;
                END;
                $$
            """
            )
        except Exception as e:
            logger.warning(f"Could not create vector functions: {str(e)}")

        # Create view for factcheck results
        cursor.execute(
            """
            CREATE OR REPLACE VIEW factcheck_results AS
            SELECT
                c.id AS claim_id,
                c.text AS claim_text,
                c.domain,
                c.context,
                c.source_url,
                v.id AS verdict_id,
                v.verdict,
                v.confidence,
                v.explanation,
                v.sources,
                v.evidence_summary,
                v.generated_at,
                (
                    SELECT json_agg(json_build_object(
                        'id', e.id,
                        'text', e.text,
                        'source', e.source,
                        'source_name', e.source_name,
                        'relevance', e.relevance,
                        'stance', e.stance
                    ))
                    FROM evidence e
                    WHERE e.claim_id = c.id
                ) AS evidence,
                c.created_at
            FROM
                claims c
            LEFT JOIN
                verdicts v ON c.id = v.claim_id
        """
        )
