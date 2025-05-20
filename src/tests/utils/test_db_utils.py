"""
Unit tests for database utility functions.

These tests verify that database utility functions work correctly.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Claim, Evidence, Verdict
from src.db.utils import (
    get_claim_by_id,
    get_claim_stats,
    get_claims_by_text,
    get_evidence_for_claim,
    get_recent_claims,
    get_similar_claims,
    get_verdict_for_claim,
    log_search_query,
    search_claims,
    store_claim,
    store_evidence,
    store_factcheck_result,
    store_verdict,
)


@pytest.fixture
def mock_db_session():
    """Return a mocked database session."""
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    # Configure execute to return different results based on the query
    def mock_execute_side_effect(query, *args, **kwargs):
        result = MagicMock()
        
        # For select queries returning individual models
        if hasattr(query, 'whereclause') and query.whereclause is not None:
            # Get the entity being queried (e.g., Claim, Evidence, etc.)
            entity = None
            if hasattr(query, '_raw_columns') and query._raw_columns:
                entity_class = getattr(query._raw_columns[0], 'entity', None)
                if entity_class:
                    entity = entity_class
            
            # Create appropriate mock result based on entity type
            if entity == Claim:
                mock_claim = MagicMock(spec=Claim)
                mock_claim.id = 1
                mock_claim.text = "Test claim"
                mock_claim.domain = "test"
                mock_claim.checkworthiness = 0.8
                result.scalars().first.return_value = mock_claim
                result.scalars().all.return_value = [mock_claim]
            elif entity == Evidence:
                mock_evidence = MagicMock(spec=Evidence)
                mock_evidence.id = 1
                mock_evidence.text = "Test evidence"
                mock_evidence.source = "https://example.com"
                mock_evidence.claim_id = 1
                result.scalars().first.return_value = mock_evidence
                result.scalars().all.return_value = [mock_evidence]
            elif entity == Verdict:
                mock_verdict = MagicMock(spec=Verdict)
                mock_verdict.id = 1
                mock_verdict.verdict = "true"
                mock_verdict.claim_id = 1
                result.scalars().first.return_value = mock_verdict
                result.scalars().all.return_value = [mock_verdict]
            else:
                # Default empty result
                result.scalars().first.return_value = None
                result.scalars().all.return_value = []
        
        # For aggregate queries
        elif hasattr(query, '_group_by_clause') and query._group_by_clause is not None:
            result.all.return_value = [(10, "science"), (5, "politics")]
        
        return AsyncMock(return_value=result)
    
    mock_session.execute.side_effect = mock_execute_side_effect
    
    return mock_session


@pytest.mark.asyncio
async def test_store_claim(mock_db_session):
    """Test storing a claim in the database."""
    # Test data
    claim_data = {
        "text": "The Earth is approximately 4.54 billion years old.",
        "checkworthiness": 0.92,
        "domain": "science",
        "source_text": "Sample source text"
    }
    
    # Store the claim
    claim = await store_claim(mock_db_session, **claim_data)
    
    # Verify the session was used correctly
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    
    # Verify the claim object
    assert claim is not None
    assert claim.text == claim_data["text"]
    assert claim.checkworthiness == claim_data["checkworthiness"]
    assert claim.domain == claim_data["domain"]
    assert claim.source_text == claim_data["source_text"]


@pytest.mark.asyncio
async def test_store_evidence(mock_db_session):
    """Test storing evidence in the database."""
    # Test data
    evidence_data = {
        "text": "Scientific studies have determined that the Earth is 4.54 billion years old.",
        "source": "https://example.com/earth-age",
        "credibility": 0.95,
        "stance": "supporting",
        "claim_id": 1
    }
    
    # Store the evidence
    evidence = await store_evidence(mock_db_session, **evidence_data)
    
    # Verify the session was used correctly
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    
    # Verify the evidence object
    assert evidence is not None
    assert evidence.text == evidence_data["text"]
    assert evidence.source == evidence_data["source"]
    assert evidence.credibility == evidence_data["credibility"]
    assert evidence.stance == evidence_data["stance"]
    assert evidence.claim_id == evidence_data["claim_id"]


@pytest.mark.asyncio
async def test_store_verdict(mock_db_session):
    """Test storing a verdict in the database."""
    # Test data
    verdict_data = {
        "claim_id": 1,
        "verdict": "true",
        "confidence": 0.95,
        "explanation": "The evidence strongly supports this claim.",
        "sources": ["https://example.com/earth-age"]
    }
    
    # Store the verdict
    verdict = await store_verdict(mock_db_session, **verdict_data)
    
    # Verify the session was used correctly
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    
    # Verify the verdict object
    assert verdict is not None
    assert verdict.claim_id == verdict_data["claim_id"]
    assert verdict.verdict == verdict_data["verdict"]
    assert verdict.confidence == verdict_data["confidence"]
    assert verdict.explanation == verdict_data["explanation"]
    assert verdict.sources == verdict_data["sources"]


@pytest.mark.asyncio
async def test_store_factcheck_result(mock_db_session):
    """Test storing a complete factcheck result (claim, evidence, verdict)."""
    # Test data
    factcheck_data = {
        "claim": {
            "text": "The Earth is approximately 4.54 billion years old.",
            "checkworthiness": 0.92,
            "domain": "science",
            "source_text": "Sample source text"
        },
        "evidence": [
            {
                "text": "Scientific studies have determined that the Earth is 4.54 billion years old.",
                "source": "https://example.com/earth-age",
                "credibility": 0.95,
                "stance": "supporting"
            },
            {
                "text": "Radiometric dating confirms the Earth's age as approximately 4.5 billion years.",
                "source": "https://example.org/radiometric-dating",
                "credibility": 0.92,
                "stance": "supporting"
            }
        ],
        "verdict": {
            "verdict": "true",
            "confidence": 0.95,
            "explanation": "The evidence strongly supports this claim.",
            "sources": ["https://example.com/earth-age", "https://example.org/radiometric-dating"]
        }
    }
    
    # Store the factcheck result
    result = await store_factcheck_result(mock_db_session, **factcheck_data)
    
    # Verify the result
    assert result is not None
    assert "claim" in result
    assert "evidence" in result
    assert "verdict" in result
    
    # Verify claim
    assert result["claim"].text == factcheck_data["claim"]["text"]
    assert result["claim"].domain == factcheck_data["claim"]["domain"]
    
    # Verify evidence (should be a list of Evidence objects)
    assert len(result["evidence"]) == len(factcheck_data["evidence"])
    
    # Verify verdict
    assert result["verdict"].verdict == factcheck_data["verdict"]["verdict"]
    assert result["verdict"].confidence == factcheck_data["verdict"]["confidence"]


@pytest.mark.asyncio
async def test_get_claim_by_id(mock_db_session):
    """Test retrieving a claim by ID."""
    # Retrieve a claim
    claim = await get_claim_by_id(mock_db_session, claim_id=1)
    
    # Verify the execute method was called with the correct query
    mock_db_session.execute.assert_called_once()
    
    # Check that a claim was returned
    assert claim is not None
    assert claim.id == 1


@pytest.mark.asyncio
async def test_get_claims_by_text(mock_db_session):
    """Test retrieving claims by text content."""
    # Retrieve claims containing "Earth"
    claims = await get_claims_by_text(mock_db_session, text="Earth")
    
    # Verify the execute method was called
    mock_db_session.execute.assert_called_once()
    
    # Check that claims were returned
    assert claims is not None
    assert len(claims) > 0
    assert claims[0].text == "Test claim"


@pytest.mark.asyncio
async def test_search_claims(mock_db_session):
    """Test searching for claims with various filters."""
    # Search with multiple filters
    claims = await search_claims(
        mock_db_session,
        text_search="Earth",
        domain="science",
        min_checkworthiness=0.7,
        verdict="true"
    )
    
    # Verify the execute method was called
    mock_db_session.execute.assert_called_once()
    
    # Check that claims were returned
    assert claims is not None


@pytest.mark.asyncio
async def test_get_evidence_for_claim(mock_db_session):
    """Test retrieving evidence for a specific claim."""
    # Get evidence for claim ID 1
    evidence = await get_evidence_for_claim(mock_db_session, claim_id=1)
    
    # Verify the execute method was called
    mock_db_session.execute.assert_called_once()
    
    # Check that evidence was returned
    assert evidence is not None
    assert len(evidence) > 0
    assert evidence[0].claim_id == 1


@pytest.mark.asyncio
async def test_get_verdict_for_claim(mock_db_session):
    """Test retrieving the verdict for a specific claim."""
    # Get verdict for claim ID 1
    verdict = await get_verdict_for_claim(mock_db_session, claim_id=1)
    
    # Verify the execute method was called
    mock_db_session.execute.assert_called_once()
    
    # Check that a verdict was returned
    assert verdict is not None
    assert verdict.claim_id == 1
    assert verdict.verdict == "true"


@pytest.mark.asyncio
async def test_log_search_query(mock_db_session):
    """Test logging a search query."""
    # Log a search query
    query = await log_search_query(
        mock_db_session,
        query="age of Earth",
        results_count=3,
        source="web"
    )
    
    # Verify the session was used correctly
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    
    # Verify the query object
    assert query is not None
    assert query.query == "age of Earth"
    assert query.results_count == 3
    assert query.source == "web"


@pytest.mark.asyncio
async def test_get_similar_claims(mock_db_session):
    """Test retrieving similar claims based on text similarity."""
    # Get claims similar to "The Earth is 4.5 billion years old"
    claims = await get_similar_claims(
        mock_db_session,
        text="The Earth is 4.5 billion years old",
        similarity_threshold=0.8,
        limit=5
    )
    
    # Verify the execute method was called
    mock_db_session.execute.assert_called_once()
    
    # Check that claims were returned
    assert claims is not None
    assert len(claims) > 0


@pytest.mark.asyncio
async def test_get_recent_claims(mock_db_session):
    """Test retrieving recent claims."""
    # Get the 10 most recent claims
    claims = await get_recent_claims(mock_db_session, limit=10)
    
    # Verify the execute method was called
    mock_db_session.execute.assert_called_once()
    
    # Check that claims were returned
    assert claims is not None
    assert len(claims) > 0


@pytest.mark.asyncio
async def test_get_claim_stats(mock_db_session):
    """Test retrieving claim statistics."""
    # Get claim statistics
    stats = await get_claim_stats(mock_db_session)
    
    # Verify the execute method was called
    assert mock_db_session.execute.call_count > 0
    
    # Check that stats were returned
    assert stats is not None
    assert "total_claims" in stats
    assert "claims_by_domain" in stats
    assert "claims_by_verdict" in stats 