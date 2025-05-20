"""
Integration tests for database operations.

These tests verify that database operations work correctly.
"""

import logging
import os

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.database import init_db
from src.db.models import ApiKey, Base, Claim, Evidence, SearchQuery, Verdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Skip all tests in this module if DB integration tests are not enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("TEST_DB_INTEGRATION") != "true",
    reason="Database integration tests are not enabled. Set TEST_DB_INTEGRATION=true to run."
)

# Test database URL (use SQLite in memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
# Alternative: Use a real PostgreSQL database for more complete testing
# TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/verifact_test"


@pytest.fixture(scope="function")
async def db_session():
    """Create a test database and session for each test."""
    # Create engine and tables
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    
    # Use the session in tests
    async with async_session() as session:
        yield session
    
    # Close connection
    await engine.dispose()


@pytest.mark.asyncio
async def test_db_connection(db_session):
    """Test that we can connect to the database and run a query."""
    # Execute a simple query
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar()
    
    # Check that we got a result
    assert value == 1


@pytest.mark.asyncio
async def test_create_tables(db_session):
    """Test that all tables were created correctly."""
    # Get engine from session
    engine = db_session.get_bind()
    
    # Check if tables exist
    async with engine.connect() as conn:
        inspector = inspect(conn)
        tables = await inspector.get_table_names()
        
        # Check for our tables
        expected_tables = ["claims", "evidence", "verdicts", "search_queries", "api_keys"]
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"


@pytest.mark.asyncio
async def test_create_and_query_claim(db_session):
    """Test creating and querying a claim."""
    # Create a claim
    new_claim = Claim(
        text="The Earth is approximately 4.54 billion years old.",
        checkworthiness=0.92,
        domain="science",
        source_text="The Earth is approximately 4.54 billion years old according to scientific studies."
    )
    
    # Add to session and commit
    db_session.add(new_claim)
    await db_session.commit()
    
    # Query the claim
    result = await db_session.execute(
        select(Claim).where(Claim.text.contains("Earth"))
    )
    claim = result.scalars().first()
    
    # Verify the claim was saved correctly
    assert claim is not None
    assert claim.id is not None
    assert claim.text == "The Earth is approximately 4.54 billion years old."
    assert claim.checkworthiness == 0.92
    assert claim.domain == "science"
    assert "4.54 billion years" in claim.source_text


@pytest.mark.asyncio
async def test_create_and_query_evidence(db_session):
    """Test creating and querying evidence."""
    # First create a claim
    claim = Claim(
        text="The Earth is approximately 4.54 billion years old.",
        checkworthiness=0.92,
        domain="science"
    )
    db_session.add(claim)
    await db_session.commit()
    
    # Now create evidence linked to the claim
    evidence = Evidence(
        text="Scientific studies have determined that the Earth is 4.54 billion years old.",
        source="https://example.com/earth-age",
        credibility=0.95,
        stance="supporting",
        claim_id=claim.id
    )
    db_session.add(evidence)
    await db_session.commit()
    
    # Query the evidence
    result = await db_session.execute(
        select(Evidence).where(Evidence.claim_id == claim.id)
    )
    evidence_items = result.scalars().all()
    
    # Verify the evidence was saved correctly
    assert len(evidence_items) == 1
    assert evidence_items[0].text.startswith("Scientific studies")
    assert evidence_items[0].source == "https://example.com/earth-age"
    assert evidence_items[0].credibility == 0.95
    assert evidence_items[0].stance == "supporting"


@pytest.mark.asyncio
async def test_create_and_query_verdict(db_session):
    """Test creating and querying a verdict."""
    # First create a claim
    claim = Claim(
        text="The Earth is approximately 4.54 billion years old.",
        checkworthiness=0.92,
        domain="science"
    )
    db_session.add(claim)
    await db_session.commit()
    
    # Create evidence
    evidence = Evidence(
        text="Scientific studies have determined that the Earth is 4.54 billion years old.",
        source="https://example.com/earth-age",
        credibility=0.95,
        stance="supporting",
        claim_id=claim.id
    )
    db_session.add(evidence)
    await db_session.commit()
    
    # Now create a verdict
    verdict = Verdict(
        claim_id=claim.id,
        verdict="true",
        confidence=0.95,
        explanation="The evidence strongly supports this claim.",
        sources=["https://example.com/earth-age"]
    )
    db_session.add(verdict)
    await db_session.commit()
    
    # Query the verdict
    result = await db_session.execute(
        select(Verdict).where(Verdict.claim_id == claim.id)
    )
    retrieved_verdict = result.scalars().first()
    
    # Verify the verdict was saved correctly
    assert retrieved_verdict is not None
    assert retrieved_verdict.verdict == "true"
    assert retrieved_verdict.confidence == 0.95
    assert retrieved_verdict.explanation == "The evidence strongly supports this claim."
    assert "https://example.com/earth-age" in retrieved_verdict.sources


@pytest.mark.asyncio
async def test_relationships(db_session):
    """Test relationships between models."""
    # Create a claim
    claim = Claim(
        text="The Earth is approximately 4.54 billion years old.",
        checkworthiness=0.92,
        domain="science"
    )
    db_session.add(claim)
    await db_session.commit()
    
    # Create multiple evidence items
    evidence1 = Evidence(
        text="Scientific studies have determined that the Earth is 4.54 billion years old.",
        source="https://example.com/earth-age",
        credibility=0.95,
        stance="supporting",
        claim_id=claim.id
    )
    evidence2 = Evidence(
        text="Radiometric dating confirms the Earth's age as approximately 4.5 billion years.",
        source="https://example.org/radiometric-dating",
        credibility=0.92,
        stance="supporting",
        claim_id=claim.id
    )
    db_session.add_all([evidence1, evidence2])
    await db_session.commit()
    
    # Create verdict
    verdict = Verdict(
        claim_id=claim.id,
        verdict="true",
        confidence=0.95,
        explanation="The evidence strongly supports this claim.",
        sources=["https://example.com/earth-age", "https://example.org/radiometric-dating"]
    )
    db_session.add(verdict)
    await db_session.commit()
    
    # Query the claim with relationships
    result = await db_session.execute(
        select(Claim).where(Claim.id == claim.id)
    )
    claim_with_relationships = result.scalars().first()
    
    # Refresh relationships
    await db_session.refresh(claim_with_relationships, ["evidence", "verdict"])
    
    # Verify relationships
    assert len(claim_with_relationships.evidence) == 2
    assert claim_with_relationships.verdict is not None
    assert claim_with_relationships.verdict.verdict == "true"


@pytest.mark.asyncio
async def test_search_query_storage(db_session):
    """Test storing and retrieving search queries."""
    # Create a search query
    query = SearchQuery(
        query="age of Earth",
        results_count=3,
        source="web"
    )
    db_session.add(query)
    await db_session.commit()
    
    # Retrieve the query
    result = await db_session.execute(
        select(SearchQuery).where(SearchQuery.query == "age of Earth")
    )
    retrieved_query = result.scalars().first()
    
    # Verify
    assert retrieved_query is not None
    assert retrieved_query.query == "age of Earth"
    assert retrieved_query.results_count == 3
    assert retrieved_query.source == "web"
    assert retrieved_query.created_at is not None


@pytest.mark.asyncio
async def test_api_key_management(db_session):
    """Test API key creation and validation."""
    # Create an API key
    api_key = ApiKey(
        name="Test Client",
        description="API key for testing",
        enabled=True
    )
    db_session.add(api_key)
    await db_session.commit()
    
    # Verify the key was created with a value
    assert api_key.key is not None
    assert len(api_key.key) > 20  # Should be a reasonably long key
    
    # Retrieve and verify
    result = await db_session.execute(
        select(ApiKey).where(ApiKey.name == "Test Client")
    )
    retrieved_key = result.scalars().first()
    
    assert retrieved_key is not None
    assert retrieved_key.enabled is True
    assert retrieved_key.key == api_key.key


@pytest.mark.asyncio
async def test_init_db():
    """Test the init_db function."""
    # Use our test URL
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    
    # Call init_db
    engine = await init_db()
    
    # Verify tables were created
    async with engine.connect() as conn:
        inspector = inspect(conn)
        tables = await inspector.get_table_names()
        
        # Check for our tables
        expected_tables = ["claims", "evidence", "verdicts", "search_queries", "api_keys"]
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose() 