"""Tests for error recovery in the VeriFact pipeline."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.verifact_manager import VerifactManager, ManagerConfig
from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict

from src.tests.utils.mock_data_factory import MockDataFactory


@pytest.fixture
def manager():
    """Create a VerifactManager instance for testing."""
    config = ManagerConfig(
        min_checkworthiness=0.5,
        max_claims=5,
        evidence_per_claim=3,
        timeout_seconds=5.0,  # Short timeout for testing
        enable_fallbacks=True,
        retry_attempts=2,
        raise_exceptions=False,  # Don't raise exceptions for error recovery testing
        include_debug_info=True,
    )
    return VerifactManager(config)


@pytest.fixture
def strict_manager():
    """Create a VerifactManager instance that raises exceptions."""
    config = ManagerConfig(
        min_checkworthiness=0.5,
        max_claims=5,
        evidence_per_claim=3,
        timeout_seconds=5.0,
        enable_fallbacks=False,
        retry_attempts=1,
        raise_exceptions=True,  # Raise exceptions for error testing
        include_debug_info=True,
    )
    return VerifactManager(config)


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_timeout_recovery(mock_run, manager):
    """Test recovery from timeouts in the pipeline."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=2)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]
    
    # Configure mock to simulate a timeout for the second evidence gathering
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            call_count += 1
            if call_count == 2:
                # Simulate timeout for the second claim
                raise asyncio.TimeoutError("Evidence gathering timed out")
            return MockDataFactory.create_runner_result_mock(evidence_map[claims[0].text])
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockDataFactory.create_runner_result_mock(verdicts[0])
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with claims")
    
    # Verify results - should have one verdict despite the timeout
    assert len(results) == 1
    assert results[0].claim == claims[0].text


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_retry_mechanism(mock_run, manager):
    """Test the retry mechanism for failed API calls."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=1)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]
    
    # Configure mock to fail on first attempt but succeed on retry
    attempt_counts = {"evidence": 0, "verdict": 0}
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            attempt_counts["evidence"] += 1
            if attempt_counts["evidence"] == 1:
                # Fail on first attempt
                raise Exception("Evidence gathering failed")
            # Succeed on retry
            return MockDataFactory.create_runner_result_mock(evidence_map[claims[0].text])
        elif agent.__dict__.get('name') == 'VerdictWriter':
            attempt_counts["verdict"] += 1
            if attempt_counts["verdict"] == 1:
                # Fail on first attempt
                raise Exception("Verdict generation failed")
            # Succeed on retry
            return MockDataFactory.create_runner_result_mock(verdicts[0])
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with claims")
    
    # Verify results - should have one verdict after retries
    assert len(results) == 1
    assert results[0].claim == claims[0].text
    
    # Verify retry counts
    assert attempt_counts["evidence"] == 2  # Initial attempt + 1 retry
    assert attempt_counts["verdict"] == 2  # Initial attempt + 1 retry


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_partial_evidence_failure(mock_run, manager):
    """Test handling of partial evidence gathering failures."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=3)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]
    
    # Configure mock to fail evidence gathering for the second claim
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Extract claim text from the query
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            
            if claim_text == claims[1].text:
                # Fail for the second claim
                raise Exception("Evidence gathering failed for second claim")
            
            # Return evidence for other claims
            return MockDataFactory.create_runner_result_mock(evidence_map.get(claim_text, []))
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            
            # Return verdict for the matching claim
            for verdict in verdicts:
                if verdict.claim == claim_text:
                    return MockDataFactory.create_runner_result_mock(verdict)
            
            return MockDataFactory.create_runner_result_mock(verdicts[0])
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with claims")
    
    # Verify results - should have verdicts for claims 1 and 3, but not for claim 2
    assert len(results) == 2
    result_claims = [result.claim for result in results]
    assert claims[0].text in result_claims
    assert claims[2].text in result_claims
    assert claims[1].text not in result_claims


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_malformed_evidence(mock_run, manager):
    """Test handling of malformed evidence."""
    # Create test data with malformed evidence
    scenario = MockDataFactory.create_scenario("error_prone", claim_count=2)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]
    
    # Configure mock to return the test data
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Extract claim text from the query
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            
            # Return evidence for the claim
            return MockDataFactory.create_runner_result_mock(evidence_map.get(claim_text, []))
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            
            # Return verdict for the matching claim
            for verdict in verdicts:
                if verdict.claim == claim_text:
                    return MockDataFactory.create_runner_result_mock(verdict)
            
            # If no matching verdict, return a default one
            return MockDataFactory.create_runner_result_mock(
                Verdict(
                    claim=claim_text or "Unknown claim",
                    verdict="unverifiable",
                    confidence=0.5,
                    explanation="Could not verify due to malformed evidence.",
                    sources=["https://example.com/source"],
                )
            )
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with claims")
    
    # Verify results - should have at least one verdict
    assert len(results) > 0
    
    # Check that malformed evidence was handled gracefully
    for result in results:
        assert isinstance(result, Verdict)
        assert result.claim in [claim.text for claim in claims]


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_empty_evidence(mock_run, manager):
    """Test handling of empty evidence sets."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=2)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]
    
    # Configure mock to return empty evidence for the first claim
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Extract claim text from the query
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            
            if claim_text == claims[0].text:
                # Return empty evidence for the first claim
                return MockDataFactory.create_runner_result_mock([])
            
            # Return evidence for other claims
            return MockDataFactory.create_runner_result_mock(evidence_map.get(claim_text, []))
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            
            # Return verdict for the matching claim
            for verdict in verdicts:
                if verdict.claim == claim_text:
                    return MockDataFactory.create_runner_result_mock(verdict)
            
            return MockDataFactory.create_runner_result_mock(verdicts[0])
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with claims")
    
    # Verify results - should have one verdict (for the second claim)
    assert len(results) == 1
    assert results[0].claim == claims[1].text


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_invalid_verdict(mock_run, manager):
    """Test handling of invalid verdicts."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=1)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    
    # Configure mock to return invalid verdict
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockDataFactory.create_runner_result_mock(evidence_map[claims[0].text])
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Return an invalid verdict (missing required fields)
            return MockDataFactory.create_runner_result_mock({
                "claim": claims[0].text,
                # Missing verdict, confidence, explanation, sources
            })
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with claims")
    
    # Verify results - should be empty due to invalid verdict
    assert len(results) == 0


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_exception_propagation(mock_run, strict_manager):
    """Test that exceptions are properly propagated when raise_exceptions is True."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=1)
    claims = scenario["claims"]
    
    # Configure mock to raise an exception
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            raise Exception("Test exception")
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline and expect an exception
    with pytest.raises(Exception) as excinfo:
        await strict_manager.run("Test text with claims")
    
    # Verify the exception
    assert "Test exception" in str(excinfo.value)
