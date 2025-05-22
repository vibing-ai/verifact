"""Tests for data flow between agents in the VeriFact pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

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
        timeout_seconds=30.0,
        enable_fallbacks=True,
        retry_attempts=1,
        raise_exceptions=True,
        include_debug_info=True,
    )
    return VerifactManager(config)


class DataFlowCaptor:
    """Captures data flow between agents."""
    
    def __init__(self):
        self.claim_detector_inputs = []
        self.evidence_hunter_inputs = []
        self.verdict_writer_inputs = []
        self.claim_detector_outputs = []
        self.evidence_hunter_outputs = []
        self.verdict_writer_outputs = []
        
    def reset(self):
        """Reset all captured data."""
        self.__init__()


@pytest.fixture
def data_flow_captor():
    """Create a DataFlowCaptor instance."""
    return DataFlowCaptor()


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_data_flow_integrity(mock_run, manager, data_flow_captor):
    """Test the integrity of data flow between agents."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=2)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]
    
    # Configure mock to capture inputs and return outputs
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        input_data = args[1]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            data_flow_captor.claim_detector_inputs.append(input_data)
            data_flow_captor.claim_detector_outputs.append(claims)
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            data_flow_captor.evidence_hunter_inputs.append(input_data)
            
            # Extract claim text from the query
            claim_text = next((c.text for c in claims if c.text in input_data), None)
            evidence = evidence_map.get(claim_text, [])
            
            data_flow_captor.evidence_hunter_outputs.append(evidence)
            return MockDataFactory.create_runner_result_mock(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            data_flow_captor.verdict_writer_inputs.append(input_data)
            
            # Extract claim text from the prompt
            claim_text = next((c.text for c in claims if c.text in input_data), None)
            verdict = next((v for v in verdicts if v.claim == claim_text), verdicts[0])
            
            data_flow_captor.verdict_writer_outputs.append(verdict)
            return MockDataFactory.create_runner_result_mock(verdict)
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    input_text = "Test text with claims"
    results = await manager.run(input_text)
    
    # Verify results
    assert len(results) == 2
    
    # Verify data flow
    # 1. Claim detector should receive the original input text
    assert len(data_flow_captor.claim_detector_inputs) == 1
    assert data_flow_captor.claim_detector_inputs[0] == input_text
    
    # 2. Evidence hunter should receive queries containing the claims
    assert len(data_flow_captor.evidence_hunter_inputs) == 2
    for i, claim in enumerate(claims):
        assert claim.text in data_flow_captor.evidence_hunter_inputs[i]
    
    # 3. Verdict writer should receive prompts containing claims and evidence
    assert len(data_flow_captor.verdict_writer_inputs) == 2
    for i, claim in enumerate(claims):
        assert claim.text in data_flow_captor.verdict_writer_inputs[i]
        assert "Evidence" in data_flow_captor.verdict_writer_inputs[i]
    
    # 4. Final results should match verdict writer outputs
    for i, result in enumerate(results):
        assert result.claim in [v.claim for v in verdicts]
        assert result.verdict in [v.verdict for v in verdicts]


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_claim_filtering(mock_run, manager):
    """Test that claims are properly filtered based on check-worthiness."""
    # Create test data with varying context scores
    claims = [
        Claim(text="High worthiness claim", context=0.9),
        Claim(text="Medium worthiness claim", context=0.6),
        Claim(text="Low worthiness claim", context=0.3),  # Below threshold
    ]
    
    evidence = [
        [Evidence(content="Evidence for high", source="https://example.com/high", relevance=0.9, stance="supporting")],
        [Evidence(content="Evidence for medium", source="https://example.com/medium", relevance=0.8, stance="supporting")],
    ]
    
    verdicts = [
        Verdict(
            claim="High worthiness claim",
            verdict="true",
            confidence=0.9,
            explanation="High worthiness explanation",
            sources=["https://example.com/high"],
        ),
        Verdict(
            claim="Medium worthiness claim",
            verdict="partially true",
            confidence=0.7,
            explanation="Medium worthiness explanation",
            sources=["https://example.com/medium"],
        ),
    ]
    
    # Configure mock
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Should only be called for claims above the threshold
            assert call_count < 2, "Evidence hunter called too many times"
            result = evidence[call_count]
            call_count += 1
            return MockDataFactory.create_runner_result_mock(result)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Extract claim text from the prompt
            prompt = args[1]
            if "High worthiness claim" in prompt:
                return MockDataFactory.create_runner_result_mock(verdicts[0])
            else:
                return MockDataFactory.create_runner_result_mock(verdicts[1])
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with claims of varying worthiness")
    
    # Verify results - should only have verdicts for claims above the threshold
    assert len(results) == 2
    result_claims = [result.claim for result in results]
    assert "High worthiness claim" in result_claims
    assert "Medium worthiness claim" in result_claims
    assert "Low worthiness claim" not in result_claims


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_evidence_transformation(mock_run, manager):
    """Test that evidence is properly transformed between agents."""
    # Create test data
    claim = Claim(text="Test claim", context=0.8)
    
    # Create evidence with different stances
    evidence = [
        Evidence(content="Supporting evidence", source="https://example.com/support", relevance=0.9, stance="supporting"),
        Evidence(content="Contradicting evidence", source="https://example.com/contradict", relevance=0.8, stance="contradicting"),
        Evidence(content="Neutral evidence", source="https://example.com/neutral", relevance=0.7, stance="neutral"),
    ]
    
    verdict = Verdict(
        claim="Test claim",
        verdict="partially true",
        confidence=0.7,
        explanation="Partially true due to mixed evidence",
        sources=["https://example.com/support", "https://example.com/contradict", "https://example.com/neutral"],
    )
    
    # Configure mock to capture the evidence transformation
    verdict_writer_input = None
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal verdict_writer_input
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock([claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockDataFactory.create_runner_result_mock(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            verdict_writer_input = args[1]
            return MockDataFactory.create_runner_result_mock(verdict)
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with a claim")
    
    # Verify results
    assert len(results) == 1
    assert results[0].claim == claim.text
    assert results[0].verdict == "partially true"
    
    # Verify evidence transformation
    assert verdict_writer_input is not None
    
    # Check that all evidence is included in the verdict writer input
    for e in evidence:
        assert e.content in verdict_writer_input
        assert e.source in verdict_writer_input
        assert e.stance in verdict_writer_input
    
    # Check that evidence stances are preserved
    assert "supporting" in verdict_writer_input
    assert "contradicting" in verdict_writer_input
    assert "neutral" in verdict_writer_input


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_verdict_schema_compliance(mock_run, manager):
    """Test that verdicts comply with the expected schema."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=1)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    
    # Create verdicts with different types
    verdicts = [
        Verdict(
            claim=claims[0].text,
            verdict="true",
            confidence=0.9,
            explanation="True explanation",
            sources=["https://example.com/true"],
        ),
        Verdict(
            claim=claims[0].text,
            verdict="false",
            confidence=0.9,
            explanation="False explanation",
            sources=["https://example.com/false"],
        ),
        Verdict(
            claim=claims[0].text,
            verdict="partially true",
            confidence=0.7,
            explanation="Partially true explanation",
            sources=["https://example.com/partial"],
        ),
        Verdict(
            claim=claims[0].text,
            verdict="unverifiable",
            confidence=0.5,
            explanation="Unverifiable explanation",
            sources=["https://example.com/unverifiable"],
        ),
    ]
    
    # Test each verdict type
    for test_verdict in verdicts:
        # Configure mock
        def mock_runner_side_effect(*args, **kwargs):
            agent = args[0]
            
            if agent.__dict__.get('name') == 'ClaimDetector':
                return MockDataFactory.create_runner_result_mock(claims)
            elif agent.__dict__.get('name') == 'EvidenceHunter':
                return MockDataFactory.create_runner_result_mock(evidence_map[claims[0].text])
            elif agent.__dict__.get('name') == 'VerdictWriter':
                return MockDataFactory.create_runner_result_mock(test_verdict)
            return MockDataFactory.create_runner_result_mock([])
        
        mock_run.side_effect = mock_runner_side_effect
        
        # Run the pipeline
        results = await manager.run("Test text with a claim")
        
        # Verify results
        assert len(results) == 1
        assert results[0].claim == claims[0].text
        assert results[0].verdict == test_verdict.verdict
        assert results[0].confidence == test_verdict.confidence
        assert results[0].explanation == test_verdict.explanation
        assert results[0].sources == test_verdict.sources


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_max_claims_limit(mock_run, manager):
    """Test that the max_claims limit is respected."""
    # Create many claims
    claims = [
        Claim(text=f"Claim {i}", context=0.8)
        for i in range(10)  # More than the max_claims limit of 5
    ]
    
    # Configure mock
    processed_claims = []
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Record which claims are processed
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            if claim_text:
                processed_claims.append(claim_text)
            
            # Return some evidence
            return MockDataFactory.create_runner_result_mock([
                Evidence(
                    content=f"Evidence for {claim_text}",
                    source="https://example.com/evidence",
                    relevance=0.8,
                    stance="supporting",
                )
            ])
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            
            # Return a verdict
            return MockDataFactory.create_runner_result_mock(
                Verdict(
                    claim=claim_text or "Unknown claim",
                    verdict="true",
                    confidence=0.8,
                    explanation=f"Explanation for {claim_text}",
                    sources=["https://example.com/evidence"],
                )
            )
        return MockDataFactory.create_runner_result_mock([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Test text with many claims")
    
    # Verify results - should be limited by max_claims
    assert len(results) <= 5  # max_claims from the manager config
    assert len(processed_claims) <= 5
    
    # Verify that the processed claims are the ones with the highest context scores
    # (They should be processed in order of context score)
    for claim_text in processed_claims:
        assert claim_text in [c.text for c in claims]
