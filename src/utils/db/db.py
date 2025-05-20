"""
Database utilities for Supabase and PGVector integration.

This module provides functions and classes for:
- Connecting to Supabase databases
- Working with PGVector for vector embeddings storage
- Storing and retrieving factcheck results
- Semantic similarity search for claims
"""

import contextlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

# Import Pydantic for model validation
from pydantic import BaseModel

# Import optional dependencies - these might not be available
# in all environments, so we use try/except
try:
    from psycopg2.extras import DictCursor, execute_values
    from psycopg2.pool import ThreadedConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.models.factcheck import Claim, Evidence, Verdict
from src.utils.security.credentials import get_credential
from src.utils.security.encryption import EncryptionError, decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

# Generic type for query results
T = TypeVar('T')

# Constants
DEFAULT_VECTOR_DIMENSION = 1536  # OpenAI embedding dimension
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_SIMILARITY_THRESHOLD = 0.8
DEFAULT_MAX_RESULTS = 10
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


class ConnectionError(Exception):
    """Exception raised for database connection errors."""
    pass


class QueryError(Exception):
    """Exception raised for database query errors."""
    pass


class EmbeddingError(Exception):
    """Exception raised for embedding generation errors."""
    pass


@dataclass
class QueryOptions:
    """Options for database queries."""
    limit: int = 10
    offset: int = 0
    order_by: str = "created_at"
    order_direction: str = "desc"
    filters: Dict[str, Any] = None


class PaginatedResult(Generic[T], BaseModel):
    """A paginated result set."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def retry_on_error(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Decorator to retry functions on error."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, QueryError) as e:
                    attempts += 1
                    if attempts == max_retries:
                        logger.error(
                            f"Failed after {max_retries} attempts: {str(e)}")
                        raise
                    logger.warning(
                        f"Attempt {attempts} failed: {str(e)}. Retrying in {delay} seconds...")
                    time.sleep(delay)
        return wrapper
    return decorator


class SupabaseClient:
    """Client for interacting with Supabase and PGVector."""

    def __init__(self, min_conn=1, max_conn=10):
        """
        Initialize Supabase connection with connection pooling.

        Args:
            min_conn: Minimum connections in the pool
            max_conn: Maximum connections in the pool
        """
        # Get credentials securely
        self.supabase_url = get_credential("SUPABASE_URL")
        self.supabase_key = get_credential("SUPABASE_KEY")
        self.pg_connection_string = get_credential("SUPABASE_DB_URL")
        self.openai_api_key = get_credential("OPENAI_API_KEY")
        self.embedding_model = get_credential(
            "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

        # Initialize connection pools
        self.connection_pool = None
        self.min_conn = min_conn
        self.max_conn = max_conn

        # Initialize Supabase client if credentials are available
        self.supabase: Optional[Client] = None

        if not SUPABASE_AVAILABLE:
            logger.warning(
                "Supabase package not installed. Install with 'pip install supabase'")
            return

        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(
                    self.supabase_url, self.supabase_key)
                logger.info("Successfully connected to Supabase")

                # Initialize connection pool if connection string is available
                if self.pg_connection_string and PSYCOPG2_AVAILABLE:
                    self._init_connection_pool()
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {str(e)}")

        # Check for OpenAI API key if we're using embeddings
        if not self.openai_api_key and OPENAI_AVAILABLE:
            logger.warning(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable for embedding functionality.")

    def _init_connection_pool(self):
        """Initialize the connection pool for PostgreSQL."""
        if not PSYCOPG2_AVAILABLE:
            logger.warning(
                "psycopg2 package not installed. Install with 'pip install psycopg2-binary'")
            return

        if not self.pg_connection_string:
            logger.error("PostgreSQL connection string not provided")
            return

        try:
            self.connection_pool = ThreadedConnectionPool(
                self.min_conn,
                self.max_conn,
                self.pg_connection_string
            )
            logger.info(
                f"Created PostgreSQL connection pool (min={self.min_conn}, max={self.max_conn})")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {str(e)}")

    @contextlib.contextmanager
    def get_connection(self):
        """
        Get a connection from the pool with context management.

        Yields:
            A database connection from the pool

        Raises:
            ConnectionError: If connection cannot be established
        """
        conn = None
        try:
            if self.connection_pool is None:
                self._init_connection_pool()

            if self.connection_pool is None:
                raise ConnectionError("Connection pool not initialized")

            conn = self.connection_pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            raise ConnectionError(
                f"Failed to get database connection: {str(e)}")
        finally:
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)

    @contextlib.contextmanager
    def get_cursor(self, cursor_factory=DictCursor):
        """
        Get a database cursor with context management.

        Args:
            cursor_factory: The cursor factory to use (default: DictCursor)

        Yields:
            A database cursor

        Raises:
            ConnectionError: If connection cannot be established
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database query error: {str(e)}")
                raise QueryError(f"Query execution failed: {str(e)}")
            finally:
                cursor.close()

    def close(self):
        """Close all connections and clean up resources."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Closed all database connections")

    def setup_pgvector(self) -> bool:
        """
        Set up pgvector extension if not already installed.

        Returns:
            bool: True if pgvector is set up successfully, False otherwise
        """
        if not PSYCOPG2_AVAILABLE:
            logger.warning(
                "psycopg2 package not installed. Install with 'pip install psycopg2-binary'")
            return False

        try:
            with self.get_cursor() as cur:
                # Check if pgvector is already installed
                cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                if not cur.fetchone()[0]:
                    # Install pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    logger.info("Successfully installed pgvector extension")
                else:
                    logger.info("pgvector extension already installed")
                return True
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to set up pgvector: {str(e)}")
            return False

    @retry_on_error()
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using OpenAI's API.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not OPENAI_AVAILABLE:
            raise EmbeddingError("OpenAI package not installed")

        if not self.openai_api_key:
            raise EmbeddingError("OpenAI API key not provided")

        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            response = client.embeddings.create(
                model=self.embedding_model,
                # Truncate to max token length and replace newlines
                input=text.replace("\n", " ")[:8191]
            )

            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

    @retry_on_error()
    def store_embedding(self,
                        content: str,
                        embedding: List[float],
                        metadata: Dict[str,
                                       Any] = None) -> Dict[str,
                                                            Any]:
        """
        Store a vector embedding in the database.

        Args:
            content: The original text content
            embedding: The vector embedding
            metadata: Additional metadata to store

        Returns:
            Dict with operation result including the embedding ID

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
        """
        try:
            with self.get_cursor() as cur:
                query = """
                INSERT INTO embeddings (content, embedding, metadata)
                VALUES (%s, %s, %s)
                RETURNING id, created_at
                """

                metadata_json = json.dumps(metadata) if metadata else None
                embedding_array = np.array(
                    embedding) if NUMPY_AVAILABLE else embedding

                cur.execute(query, (content, embedding_array, metadata_json))
                result = cur.fetchone()

                return {
                    "success": True,
                    "id": result["id"],
                    "created_at": result["created_at"]
                }
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            raise

    @retry_on_error()
    def find_similar_content(
        self,
        query_text: str,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        limit: int = DEFAULT_MAX_RESULTS,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar content using vector similarity search.

        Args:
            query_text: Text to find similar content for
            threshold: Similarity threshold (0-1)
            limit: Maximum number of results
            filter_metadata: Filter results by metadata fields

        Returns:
            List of similar content items with similarity scores

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
            EmbeddingError: If embedding generation fails
        """
        # Generate embedding for query text
        query_embedding = self.generate_embedding(query_text)

        try:
            with self.get_cursor() as cur:
                query_parts = [
                    "SELECT id, content, metadata, 1 - (embedding <-> %s) AS similarity",
                    "FROM embeddings",
                    "WHERE 1 - (embedding <-> %s) > %s"]

                params = [query_embedding, query_embedding, threshold]

                # Add metadata filters if provided
                if filter_metadata and isinstance(filter_metadata, dict):
                    for key, value in filter_metadata.items():
                        query_parts.append(f"AND metadata->>{key!r} = %s")
                        params.append(value)

                query_parts.append("ORDER BY similarity DESC")
                query_parts.append("LIMIT %s")
                params.append(limit)

                query = " ".join(query_parts)
                cur.execute(query, params)

                return [dict(row) for row in cur.fetchall()]
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to find similar content: {str(e)}")
            raise

    @retry_on_error()
    def find_similar_claims(
        self,
        claim_text: str,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        limit: int = DEFAULT_MAX_RESULTS
    ) -> List[Dict[str, Any]]:
        """
        Find similar previously checked claims.

        Args:
            claim_text: The claim text to find similar claims for
            threshold: Similarity threshold (0-1)
            limit: Maximum number of results

        Returns:
            List of similar claims with verdicts and similarity scores

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
            EmbeddingError: If embedding generation fails
        """
        return self.find_similar_content(
            query_text=claim_text,
            threshold=threshold,
            limit=limit,
            filter_metadata={"type": "claim"}
        )

    @retry_on_error()
    def store_claim_with_embedding(
            self, claim: Union[Claim, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store a claim with its vector embedding.

        Args:
            claim: The claim to store (Pydantic model or dict)

        Returns:
            Dict with operation result

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
            EmbeddingError: If embedding generation fails
        """
        if isinstance(claim, Claim):
            claim_dict = claim.model_dump()
        else:
            claim_dict = claim

        claim_text = claim_dict.get("text", "")
        if not claim_text:
            raise ValueError("Claim text cannot be empty")

        # Generate embedding for claim text
        embedding = self.generate_embedding(claim_text)

        # Store claim in factchecks table
        try:
            with self.get_cursor() as cur:
                query = """
                INSERT INTO claims (text, context, checkworthy, domain, entities, extracted_at, source_text, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
                """

                entities_json = json.dumps(
                    claim_dict.get(
                        "entities",
                        [])) if claim_dict.get("entities") else '[]'
                extracted_at = claim_dict.get("extracted_at", datetime.now())

                cur.execute(query, (
                    claim_text,
                    claim_dict.get("context", ""),
                    claim_dict.get("checkworthy", True),
                    claim_dict.get("domain"),
                    entities_json,
                    extracted_at,
                    claim_dict.get("source_text"),
                    claim_dict.get("source_url")
                ))

                result = cur.fetchone()
                claim_id = result["id"]

                # Store embedding with claim metadata
                embedding_result = self.store_embedding(
                    content=claim_text,
                    embedding=embedding,
                    metadata={
                        "type": "claim",
                        "claim_id": str(claim_id),
                        "checkworthy": claim_dict.get("checkworthy", True),
                        "domain": claim_dict.get("domain")
                    }
                )

                return {
                    "success": True,
                    "claim_id": claim_id,
                    "embedding_id": embedding_result["id"],
                    "created_at": result["created_at"]
                }
        except (ConnectionError, QueryError, EmbeddingError) as e:
            logger.error(f"Failed to store claim with embedding: {str(e)}")
            raise

    @retry_on_error()
    def store_evidence(
            self, evidence: Union[Evidence, Dict[str, Any]], claim_id: str) -> Dict[str, Any]:
        """
        Store evidence for a claim.

        Args:
            evidence: The evidence to store (Pydantic model or dict)
            claim_id: ID of the claim this evidence relates to

        Returns:
            Dict with operation result

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
        """
        if isinstance(evidence, Evidence):
            evidence_dict = evidence.model_dump()
        else:
            evidence_dict = evidence

        try:
            with self.get_cursor() as cur:
                query = """
                INSERT INTO evidence (
                    claim_id, text, source, source_name, source_type, relevance,
                    stance, timestamp, credibility, excerpt_context, retrieval_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
                """

                retrieval_date = evidence_dict.get(
                    "retrieval_date", datetime.now())

                cur.execute(query, (
                    claim_id,
                    evidence_dict.get("text", ""),
                    evidence_dict.get("source", ""),
                    evidence_dict.get("source_name"),
                    evidence_dict.get("source_type", "unknown"),
                    evidence_dict.get("relevance", 0.0),
                    evidence_dict.get("stance", "neutral"),
                    evidence_dict.get("timestamp"),
                    evidence_dict.get("credibility"),
                    evidence_dict.get("excerpt_context"),
                    retrieval_date
                ))

                result = cur.fetchone()

                return {
                    "success": True,
                    "evidence_id": result["id"],
                    "created_at": result["created_at"]
                }
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to store evidence: {str(e)}")
            raise

    @retry_on_error()
    def store_verdict(
            self, verdict: Union[Verdict, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store a verdict for a claim.

        Args:
            verdict: The verdict to store (Pydantic model or dict)

        Returns:
            Dict with operation result

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
        """
        if isinstance(verdict, Verdict):
            verdict_dict = verdict.model_dump()
        else:
            verdict_dict = verdict

        try:
            with self.get_cursor() as cur:
                query = """
                INSERT INTO verdicts (
                    claim_id, verdict, confidence, explanation, sources,
                    evidence_summary, generated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
                """

                sources_json = json.dumps(
                    verdict_dict.get(
                        "sources",
                        [])) if verdict_dict.get("sources") else '[]'
                generated_at = verdict_dict.get("generated_at", datetime.now())

                cur.execute(query, (
                    verdict_dict.get("claim_id"),
                    verdict_dict.get("verdict", "unverifiable"),
                    verdict_dict.get("confidence", 0.0),
                    verdict_dict.get("explanation", ""),
                    sources_json,
                    verdict_dict.get("evidence_summary"),
                    generated_at
                ))

                result = cur.fetchone()

                return {
                    "success": True,
                    "verdict_id": result["id"],
                    "created_at": result["created_at"]
                }
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to store verdict: {str(e)}")
            raise

    @retry_on_error()
    def store_factcheck_result(
        self,
        claim: Union[Claim, Dict[str, Any]],
        evidence_list: List[Union[Evidence, Dict[str, Any]]],
        verdict: Union[Verdict, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store a complete factcheck result (claim, evidence, and verdict).

        Args:
            claim: The claim to store
            evidence_list: List of evidence to store
            verdict: The verdict to store

        Returns:
            Dict with operation result

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
            EmbeddingError: If embedding generation fails
        """
        try:
            # Store claim with embedding
            claim_result = self.store_claim_with_embedding(claim)
            claim_id = claim_result["claim_id"]

            # Store all evidence
            evidence_ids = []
            for evidence in evidence_list:
                evidence_result = self.store_evidence(evidence, claim_id)
                evidence_ids.append(evidence_result["evidence_id"])

            # Update verdict with claim_id if not set
            if isinstance(verdict, Verdict):
                verdict_dict = verdict.model_dump()
                verdict_dict["claim_id"] = claim_id
                verdict = verdict_dict
            elif isinstance(verdict, dict):
                verdict["claim_id"] = claim_id

            # Store verdict
            verdict_result = self.store_verdict(verdict)

            return {
                "success": True,
                "claim_id": claim_id,
                "evidence_ids": evidence_ids,
                "verdict_id": verdict_result["verdict_id"],
                "embedding_id": claim_result["embedding_id"]
            }
        except (ConnectionError, QueryError, EmbeddingError) as e:
            logger.error(f"Failed to store factcheck result: {str(e)}")
            raise

    @retry_on_error()
    def get_factcheck_by_id(self, factcheck_id: str) -> Dict[str, Any]:
        """
        Retrieve a complete factcheck by ID.

        Args:
            factcheck_id: ID of the factcheck to retrieve

        Returns:
            Dict containing claim, evidence, and verdict

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
        """
        try:
            with self.get_cursor() as cur:
                # Get claim
                cur.execute("""
                SELECT * FROM claims WHERE id = %s
                """, (factcheck_id,))
                claim = cur.fetchone()

                if not claim:
                    return {"success": False, "error": "Factcheck not found"}

                # Get evidence
                cur.execute("""
                SELECT * FROM evidence WHERE claim_id = %s
                """, (factcheck_id,))
                evidence = cur.fetchall()

                # Get verdict
                cur.execute("""
                SELECT * FROM verdicts WHERE claim_id = %s
                """, (factcheck_id,))
                verdict = cur.fetchone()

                return {
                    "success": True,
                    "claim": dict(claim) if claim else None,
                    "evidence": [dict(e) for e in evidence],
                    "verdict": dict(verdict) if verdict else None
                }
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to get factcheck: {str(e)}")
            raise

    @retry_on_error()
    def get_recent_factchecks(
        self,
        limit: int = 10,
        offset: int = 0,
        domain: Optional[str] = None,
        verdict_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve recent factcheck results with pagination and filtering.

        Args:
            limit: Maximum number of results to return
            offset: Offset for pagination
            domain: Filter by domain
            verdict_type: Filter by verdict type

        Returns:
            Dict with factcheck results and pagination info

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
        """
        try:
            with self.get_cursor() as cur:
                # Build the query
                query = """
                SELECT c.id, c.text, c.domain, v.verdict, v.confidence, v.explanation,
                       v.sources, c.created_at
                FROM claims c
                LEFT JOIN verdicts v ON c.id = v.claim_id
                WHERE 1=1
                """

                params = []

                # Add filters
                if domain:
                    query += " AND c.domain = %s"
                    params.append(domain)

                if verdict_type:
                    query += " AND v.verdict = %s"
                    params.append(verdict_type)

                # Count total results
                count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"
                cur.execute(count_query, params)
                total = cur.fetchone()[0]

                # Add order and pagination
                query += " ORDER BY c.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cur.execute(query, params)
                results = cur.fetchall()

                # Calculate pagination info
                total_pages = (total + limit - 1) // limit if limit > 0 else 1
                current_page = (offset // limit) + 1 if limit > 0 else 1

                return {
                    "success": True,
                    "results": [dict(r) for r in results],
                    "pagination": {
                        "total": total,
                        "page": current_page,
                        "page_size": limit,
                        "total_pages": total_pages
                    }
                }
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to get recent factchecks: {str(e)}")
            raise

    @retry_on_error()
    def batch_store_factchecks(
        self,
        factchecks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store multiple factchecks in batch.

        Args:
            factchecks: List of factcheck data (each containing claim, evidence, verdict)

        Returns:
            Dict with operation results

        Raises:
            ConnectionError: If database connection fails
            QueryError: If query execution fails
        """
        results = {
            "success": True,
            "factcheck_ids": [],
            "errors": []
        }

        for i, factcheck in enumerate(factchecks):
            try:
                claim = factcheck.get("claim")
                evidence_list = factcheck.get("evidence", [])
                verdict = factcheck.get("verdict")

                if not claim or not verdict:
                    results["errors"].append({
                        "index": i,
                        "error": "Missing claim or verdict"
                    })
                    continue

                result = self.store_factcheck_result(
                    claim, evidence_list, verdict)
                results["factcheck_ids"].append(result["claim_id"])
            except Exception as e:
                results["errors"].append({
                    "index": i,
                    "error": str(e)
                })

        if results["errors"]:
            results["success"] = False

        return results

    def check_database_health(self) -> Dict[str, Any]:
        """
        Check the health of the database connection.

        Returns:
            Dict with health check results
        """
        results = {
            "supabase_connection": False,
            "pg_connection": False,
            "pgvector_extension": False,
            "tables_exist": False,
            "overall_health": "unhealthy"
        }

        # Check Supabase connection
        if self.supabase:
            try:
                # Simple query to check connection
                self.supabase.table("claims").select("id").limit(1).execute()
                results["supabase_connection"] = True
            except Exception as e:
                logger.error(f"Supabase health check failed: {str(e)}")

        # Check PostgreSQL connection and pgvector
        try:
            with self.get_cursor() as cur:
                results["pg_connection"] = True

                # Check pgvector extension
                cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                if cur.fetchone()[0]:
                    results["pgvector_extension"] = True

                # Check tables
                cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name IN ('claims', 'evidence', 'verdicts', 'embeddings')
                    AND table_schema = 'public'
                    HAVING COUNT(*) = 4
                )
                """)
                if cur.fetchone()[0]:
                    results["tables_exist"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")

        # Determine overall health
        if (results["supabase_connection"]
                or results["pg_connection"]) and results["tables_exist"]:
            results["overall_health"] = "healthy"

        return results

    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """
        Clean up old data from the database.

        Args:
            days_to_keep: Number of days of data to keep

        Returns:
            Dict with cleanup results
        """
        if days_to_keep < 1:
            return {
                "success": False,
                "error": "Days to keep must be at least 1"}

        try:
            with self.get_cursor() as cur:
                # Calculate cutoff date
                cur.execute("SELECT NOW() - INTERVAL %s DAY", (days_to_keep,))
                cutoff_date = cur.fetchone()[0]

                # Delete old verdicts
                cur.execute(
                    "DELETE FROM verdicts WHERE created_at < %s RETURNING id", (cutoff_date,))
                deleted_verdicts = cur.rowcount

                # Delete old evidence
                cur.execute(
                    "DELETE FROM evidence WHERE created_at < %s RETURNING id", (cutoff_date,))
                deleted_evidence = cur.rowcount

                # Delete old embeddings
                cur.execute(
                    "DELETE FROM embeddings WHERE created_at < %s RETURNING id", (cutoff_date,))
                deleted_embeddings = cur.rowcount

                # Delete old claims
                cur.execute(
                    "DELETE FROM claims WHERE created_at < %s RETURNING id", (cutoff_date,))
                deleted_claims = cur.rowcount

                return {
                    "success": True,
                    "deleted_counts": {
                        "claims": deleted_claims,
                        "evidence": deleted_evidence,
                        "verdicts": deleted_verdicts,
                        "embeddings": deleted_embeddings
                    },
                    "cutoff_date": cutoff_date
                }
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to clean up old data: {str(e)}")
            return {"success": False, "error": str(e)}

    def reindex_embeddings(self) -> Dict[str, Any]:
        """
        Reindex vector embeddings for improved performance.

        Returns:
            Dict with reindexing results
        """
        try:
            with self.get_cursor() as cur:
                # Drop existing index
                cur.execute("DROP INDEX IF EXISTS embeddings_vector_idx")

                # Create new index
                cur.execute("""
                CREATE INDEX embeddings_vector_idx ON embeddings
                USING ivfflat (embedding vector_l2_ops)
                """)

                return {
                    "success": True,
                    "message": "Successfully reindexed embeddings"}
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to reindex embeddings: {str(e)}")
            return {"success": False, "error": str(e)}

    def optimize_database(self) -> Dict[str, Any]:
        """
        Perform database maintenance and optimization.

        Returns:
            Dict with optimization results
        """
        try:
            with self.get_cursor() as cur:
                # Vacuum analyze tables
                cur.execute("VACUUM ANALYZE claims")
                cur.execute("VACUUM ANALYZE evidence")
                cur.execute("VACUUM ANALYZE verdicts")
                cur.execute("VACUUM ANALYZE embeddings")

                return {
                    "success": True,
                    "message": "Successfully optimized database"}
        except (ConnectionError, QueryError) as e:
            logger.error(f"Failed to optimize database: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_error()
    def store_feedback(
            self, feedback: Union['Feedback', Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store user feedback in the database.

        Args:
            feedback: Feedback instance or dictionary with feedback data

        Returns:
            Dictionary with stored feedback info

        Raises:
            ConnectionError: If database connection fails
            QueryError: If the query fails
        """
        # Import here to avoid circular imports
        from src.models.feedback import Feedback

        try:
            # Convert to dict if Feedback instance
            if isinstance(feedback, Feedback):
                feedback_dict = feedback.dict(exclude_none=True)
            else:
                feedback_dict = feedback

            # Handle metadata
            metadata = feedback_dict.get('metadata', {})

            # Ensure IDs are UUIDs
            if 'feedback_id' not in feedback_dict or not feedback_dict['feedback_id']:
                import uuid
                feedback_dict['feedback_id'] = str(uuid.uuid4())

            # Set created_at timestamp if not provided
            if 'created_at' not in feedback_dict:
                from datetime import datetime
                feedback_dict['created_at'] = datetime.now().isoformat()

            # Store in Supabase if client is available
            if self.supabase:
                result = self.supabase.table(
                    'feedback').insert(feedback_dict).execute()

                if 'data' in result and result['data']:
                    logger.info(
                        f"Stored feedback: {feedback_dict['feedback_id']}")
                    return result['data'][0]
                else:
                    logger.error(f"Failed to store feedback: {result}")
                    raise QueryError(f"Failed to store feedback: {result}")

            # If no Supabase client, try direct PostgreSQL
            with self.get_cursor() as cursor:
                query = """
                INSERT INTO feedback (
                    feedback_id, claim_id, user_id, session_id,
                    accuracy_rating, helpfulness_rating, comment,
                    created_at, metadata
                ) VALUES (
                    %(feedback_id)s, %(claim_id)s, %(user_id)s, %(session_id)s,
                    %(accuracy_rating)s, %(helpfulness_rating)s, %(comment)s,
                    %(created_at)s, %(metadata)s
                ) RETURNING *;
                """
                cursor.execute(query, feedback_dict)
                result = cursor.fetchone()
                logger.info(f"Stored feedback: {feedback_dict['feedback_id']}")
                return dict(result)

        except Exception as e:
            logger.error(f"Error storing feedback: {str(e)}")
            raise QueryError(f"Failed to store feedback: {str(e)}")

    @retry_on_error()
    def get_feedback_for_claim(
            self, claim_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific claim.

        Args:
            claim_id: ID of the claim to get feedback for
            limit: Maximum number of feedback items to return
            offset: Offset for pagination

        Returns:
            List of feedback dictionaries

        Raises:
            ConnectionError: If database connection fails
            QueryError: If the query fails
        """
        try:
            # Use Supabase if available
            if self.supabase:
                result = (self.supabase.table('feedback')
                          .select('*')
                          .eq('claim_id', claim_id)
                          .order('created_at', desc=True)
                          .limit(limit)
                          .offset(offset)
                          .execute())

                if 'data' in result:
                    return result['data']
                else:
                    logger.error(f"Failed to get feedback for claim: {result}")
                    return []

            # Direct PostgreSQL query
            with self.get_cursor() as cursor:
                query = """
                SELECT * FROM feedback
                WHERE claim_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
                """
                cursor.execute(query, (claim_id, limit, offset))
                return cursor.fetchall()

        except Exception as e:
            logger.error(
                f"Error getting feedback for claim {claim_id}: {
                    str(e)}")
            raise QueryError(f"Failed to get feedback for claim: {str(e)}")

    @retry_on_error()
    def get_feedback_statistics(
            self, claim_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregated feedback statistics.

        Args:
            claim_id: Optional claim ID to filter statistics by

        Returns:
            Dictionary with feedback statistics

        Raises:
            ConnectionError: If database connection fails
            QueryError: If the query fails
        """
        try:
            # Common query parts
            select_clause = """
                COUNT(*) as total_feedback,
                AVG(accuracy_rating) as average_accuracy,
                AVG(helpfulness_rating) as average_helpfulness
            """

            # Use Supabase if available
            if self.supabase:
                query = f"SELECT {select_clause} FROM feedback"
                params = {}

                if claim_id:
                    query += " WHERE claim_id = :claim_id"
                    params['claim_id'] = claim_id

                result = self.supabase.rpc(
                    'get_feedback_stats', params).execute()

                if 'data' in result and result['data']:
                    stats = result['data'][0]

                    # Get rating distribution
                    rating_counts = self._get_rating_distribution(claim_id)
                    stats['feedback_count_by_rating'] = rating_counts

                    # Get recent comments
                    comments = self._get_recent_comments(claim_id, limit=5)
                    stats['recent_comments'] = comments

                    return stats

            # Direct PostgreSQL query
            with self.get_cursor() as cursor:
                query = f"SELECT {select_clause} FROM feedback"
                params = []

                if claim_id:
                    query += " WHERE claim_id = %s"
                    params.append(claim_id)

                cursor.execute(query, params)
                stats = dict(cursor.fetchone())

                # Get rating distribution
                rating_counts = self._get_rating_distribution(claim_id)
                stats['feedback_count_by_rating'] = rating_counts

                # Get recent comments
                comments = self._get_recent_comments(claim_id, limit=5)
                stats['recent_comments'] = comments

                return stats

        except Exception as e:
            logger.error(f"Error getting feedback statistics: {str(e)}")
            raise QueryError(f"Failed to get feedback statistics: {str(e)}")

    @retry_on_error()
    def _get_rating_distribution(
            self, claim_id: Optional[str] = None) -> Dict[str, Dict[int, int]]:
        """
        Get distribution of ratings.

        Args:
            claim_id: Optional claim ID to filter by

        Returns:
            Dictionary with rating distributions
        """
        try:
            result = {
                'accuracy': {},
                'helpfulness': {}
            }

            if self.supabase:
                # Accuracy ratings
                query = "SELECT accuracy_rating, COUNT(*) FROM feedback"
                params = {}

                if claim_id:
                    query += " WHERE claim_id = :claim_id"
                    params['claim_id'] = claim_id

                query += " GROUP BY accuracy_rating"

                acc_result = self.supabase.rpc(
                    'get_accuracy_distribution', params).execute()
                if 'data' in acc_result:
                    for row in acc_result['data']:
                        result['accuracy'][row['accuracy_rating']] = row['count']

                # Helpfulness ratings
                query = "SELECT helpfulness_rating, COUNT(*) FROM feedback"

                if claim_id:
                    query += " WHERE claim_id = :claim_id"

                query += " GROUP BY helpfulness_rating"

                help_result = self.supabase.rpc(
                    'get_helpfulness_distribution', params).execute()
                if 'data' in help_result:
                    for row in help_result['data']:
                        result['helpfulness'][row['helpfulness_rating']
                                              ] = row['count']

                return result

            # Direct PostgreSQL query
            with self.get_cursor() as cursor:
                # Accuracy ratings
                query = "SELECT accuracy_rating, COUNT(*) FROM feedback"
                params = []

                if claim_id:
                    query += " WHERE claim_id = %s"
                    params.append(claim_id)

                query += " GROUP BY accuracy_rating"

                cursor.execute(query, params)
                for row in cursor.fetchall():
                    result['accuracy'][row['accuracy_rating']] = row['count']

                # Helpfulness ratings
                query = "SELECT helpfulness_rating, COUNT(*) FROM feedback"

                if claim_id:
                    query += " WHERE claim_id = %s"
                    params = [claim_id]
                else:
                    params = []

                query += " GROUP BY helpfulness_rating"

                cursor.execute(query, params)
                for row in cursor.fetchall():
                    result['helpfulness'][row['helpfulness_rating']] = row['count']

                return result

        except Exception as e:
            logger.error(f"Error getting rating distribution: {str(e)}")
            return {'accuracy': {}, 'helpfulness': {}}

    @retry_on_error()
    def _get_recent_comments(
            self, claim_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent comments from feedback.

        Args:
            claim_id: Optional claim ID to filter by
            limit: Maximum number of comments to return

        Returns:
            List of comment dictionaries
        """
        try:
            if self.supabase:
                query = "SELECT feedback_id, claim_id, comment, created_at FROM feedback WHERE comment IS NOT NULL"
                params = {}

                if claim_id:
                    query += " AND claim_id = :claim_id"
                    params['claim_id'] = claim_id

                query += " ORDER BY created_at DESC LIMIT :limit"
                params['limit'] = limit

                result = self.supabase.rpc(
                    'get_recent_comments', params).execute()
                if 'data' in result:
                    return result['data']
                return []

            # Direct PostgreSQL query
            with self.get_cursor() as cursor:
                query = "SELECT feedback_id, claim_id, comment, created_at FROM feedback WHERE comment IS NOT NULL"
                params = []

                if claim_id:
                    query += " AND claim_id = %s"
                    params.append(claim_id)

                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)

                cursor.execute(query, params)
                return cursor.fetchall()

        except Exception as e:
            logger.error(f"Error getting recent comments: {str(e)}")
            return []

    @retry_on_error()
    def get_all_feedback(self, limit: int = 100,
                         offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all feedback with pagination.

        Args:
            limit: Maximum number of feedback items to return
            offset: Offset for pagination

        Returns:
            List of feedback dictionaries

        Raises:
            ConnectionError: If database connection fails
            QueryError: If the query fails
        """
        try:
            # Use Supabase if available
            if self.supabase:
                result = (self.supabase.table('feedback')
                          .select('*')
                          .order('created_at', desc=True)
                          .limit(limit)
                          .offset(offset)
                          .execute())

                if 'data' in result:
                    return result['data']
                else:
                    logger.error(f"Failed to get all feedback: {result}")
                    return []

            # Direct PostgreSQL query
            with self.get_cursor() as cursor:
                query = """
                SELECT * FROM feedback
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
                """
                cursor.execute(query, (limit, offset))
                return cursor.fetchall()

        except Exception as e:
            logger.error(f"Error getting all feedback: {str(e)}")
            raise QueryError(f"Failed to get all feedback: {str(e)}")

    def _encrypt_sensitive_fields(
            self, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a dictionary.

        Args:
            data: The data dictionary
            sensitive_fields: List of field names to encrypt

        Returns:
            The dictionary with encrypted fields
        """
        result = data.copy()

        for field in sensitive_fields:
            if field in result and result[field] is not None:
                try:
                    result[field] = encrypt_value(str(result[field]))
                except EncryptionError as e:
                    logger.warning(
                        f"Failed to encrypt field {field}: {
                            str(e)}")

        return result

    def _decrypt_sensitive_fields(
            self, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in a dictionary.

        Args:
            data: The data dictionary
            sensitive_fields: List of field names to decrypt

        Returns:
            The dictionary with decrypted fields
        """
        result = data.copy()

        for field in sensitive_fields:
            if field in result and result[field] is not None:
                try:
                    result[field] = decrypt_value(str(result[field]))
                except EncryptionError as e:
                    logger.warning(
                        f"Failed to decrypt field {field}: {
                            str(e)}")

        return result


# Create a singleton instance
db = SupabaseClient()
