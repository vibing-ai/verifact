"""Tests for edge cases in claim handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.verifact_manager import VerifactManager, ManagerConfig
from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict

from src.tests.fixtures.claims import POLITICAL_CLAIMS, SAMPLE_TEXTS
from src.tests.fixtures.evidence import POLITICAL_EVIDENCE
from src.tests.fixtures.verdicts import POLITICAL_VERDICTS


class MockRunnerResult:
    """Mock for the result returned by Runner.run()."""
    
    def __init__(self, output_data):
        self.output_data = output_data
        self.final_output = str(output_data)
    
    def final_output_as(self, output_type):
        """Mock the final_output_as method."""
        return self.output_data


@pytest.fixture
def manager():
    """Create a VerifactManager instance for testing."""
    config = ManagerConfig(
        min_checkworthiness=0.5,
        max_claims=5,
        evidence_per_claim=3,
        timeout_seconds=30.0,
        enable_fallbacks=True,
        retry_attempts=1,
        raise_exceptions=True,
        include_debug_info=False,
    )
    return VerifactManager(config)


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_no_claims_detected(mock_run, manager):
    """Test the pipeline when no claims are detected."""
    # Configure mock to return empty list for claim detection
    mock_run.return_value = MockRunnerResult([])
    
    # Run the pipeline
    results = await manager.run("Text with no factual claims")
    
    # Verify results
    assert results == []
    mock_run.assert_called_once()


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_no_evidence_found(mock_run, manager):
    """Test the pipeline when no evidence is found for a claim."""
    # Sample claim
    sample_claim = POLITICAL_CLAIMS[0]
    
    # Configure mock to return different results for different agent calls
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([sample_claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Return empty list for evidence
            return MockRunnerResult([])
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run(SAMPLE_TEXTS[0])
    
    # Verify results - should be empty since no evidence was found
    assert results == []
    assert mock_run.call_count >= 2  # Called for claim detection and evidence gathering


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_evidence_gathering_error(mock_run, manager):
    """Test the pipeline when evidence gathering raises an error."""
    # Sample claim
    sample_claim = POLITICAL_CLAIMS[0]
    
    # Configure mock to return different results for different agent calls
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([sample_claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Raise an exception for evidence gathering
            raise Exception("Evidence gathering error")
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline and expect an exception
    with pytest.raises(Exception):
        await manager.run(SAMPLE_TEXTS[0])
    
    # Verify the mock was called
    assert mock_run.call_count >= 1


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_low_confidence_verdict(mock_run, manager):
    """Test the pipeline with a verdict that has low confidence."""
    # Sample claim and evidence
    sample_claim = POLITICAL_CLAIMS[0]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    
    # Create a low confidence verdict
    low_confidence_verdict = Verdict(
        claim=sample_claim.text,
        verdict="partially true",
        confidence=0.3,  # Low confidence
        explanation="This is a low confidence verdict due to limited evidence.",
        sources=["https://example.com/source1"],
    )
    
    # Configure mock to return appropriate results
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([sample_claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(sample_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(low_confidence_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run(SAMPLE_TEXTS[0])
    
    # Verify results
    assert len(results) == 1
    assert results[0].verdict == "partially true"
    assert results[0].confidence == 0.3
    assert "low confidence" in results[0].explanation.lower()


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_conflicting_evidence(mock_run, manager):
    """Test the pipeline with conflicting evidence for a claim."""
    # Sample claim
    sample_claim = POLITICAL_CLAIMS[0]
    
    # Create conflicting evidence
    conflicting_evidence = [
        Evidence(
            content="The United States has the largest military budget in the world, spending over $800 billion annually.",
            source="https://example.com/source1",
            relevance=0.9,
            stance="supporting",
        ),
        Evidence(
            content="China has surpassed the United States in military spending according to alternative metrics.",
            source="https://example.com/source2",
            relevance=0.8,
            stance="contradicting",
        ),
    ]
    
    # Create a verdict based on conflicting evidence
    conflicting_verdict = Verdict(
        claim=sample_claim.text,
        verdict="partially true",
        confidence=0.6,
        explanation="There is conflicting evidence about this claim. While traditional metrics show the US has the largest military budget, alternative calculations suggest China may have surpassed it.",
        sources=["https://example.com/source1", "https://example.com/source2"],
    )
    
    # Configure mock to return appropriate results
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([sample_claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(conflicting_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(conflicting_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run(SAMPLE_TEXTS[0])
    
    # Verify results
    assert len(results) == 1
    assert results[0].verdict == "partially true"
    assert "conflicting evidence" in results[0].explanation.lower()
    assert len(results[0].sources) == 2


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_claim_with_no_context(mock_run, manager):
    """Test the pipeline with a claim that has no context."""
    # Create a claim with no context
    claim_no_context = Claim(text="The Moon orbits the Earth.")
    
    # Sample evidence and verdict
    sample_evidence = [
        Evidence(
            content="The Moon orbits the Earth at an average distance of 384,400 kilometers.",
            source="https://example.com/source1",
            relevance=0.95,
            stance="supporting",
        ),
    ]
    
    sample_verdict = Verdict(
        claim=claim_no_context.text,
        verdict="true",
        confidence=0.99,
        explanation="This is a basic astronomical fact that is well-established.",
        sources=["https://example.com/source1"],
    )
    
    # Configure mock to return appropriate results
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([claim_no_context])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(sample_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(sample_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("The Moon orbits the Earth.")
    
    # Verify results
    assert len(results) == 1
    assert results[0].verdict == "true"
    assert results[0].confidence > 0.9


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_multiple_claims_one_fails(mock_run, manager):
    """Test the pipeline when one claim fails during evidence gathering."""
    # Sample claims
    claim1 = POLITICAL_CLAIMS[0]
    claim2 = POLITICAL_CLAIMS[1]
    
    # Sample evidence and verdict
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    sample_verdict = POLITICAL_VERDICTS[0]
    
    # Configure mock to return different results for different agent calls
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([claim1, claim2])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # First evidence gathering succeeds, second fails
            if call_count == 0:
                call_count += 1
                return MockRunnerResult(sample_evidence)
            else:
                raise Exception("Evidence gathering error for second claim")
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(sample_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline - should continue despite one claim failing
    with pytest.raises(Exception):
        await manager.run(SAMPLE_TEXTS[0])
    
    # Verify the mock was called multiple times
    assert mock_run.call_count >= 3
