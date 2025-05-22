"""Tests for different claim types in the VeriFact pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.verifact_manager import VerifactManager, ManagerConfig
from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict

from src.tests.fixtures.claims import POLITICAL_CLAIMS, HEALTH_CLAIMS, SCIENCE_CLAIMS
from src.tests.fixtures.evidence import POLITICAL_EVIDENCE, HEALTH_EVIDENCE, SCIENCE_EVIDENCE
from src.tests.fixtures.verdicts import (
    POLITICAL_VERDICTS,
    HEALTH_VERDICTS,
    SCIENCE_VERDICTS,
    ALL_VERDICTS,
)


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


def get_verdict_by_type(verdict_type):
    """Get a verdict of the specified type from the fixtures."""
    for verdict in ALL_VERDICTS:
        if verdict.verdict == verdict_type:
            return verdict
    raise ValueError(f"No verdict of type '{verdict_type}' found in fixtures")


def get_claim_and_evidence_for_verdict(verdict):
    """Get a matching claim and evidence for the given verdict."""
    # Find a claim that matches the verdict
    claim_text = verdict.claim
    claim = None
    
    # Search in all claim collections
    for claim_list in [POLITICAL_CLAIMS, HEALTH_CLAIMS, SCIENCE_CLAIMS]:
        for c in claim_list:
            if c.text == claim_text:
                claim = c
                break
        if claim:
            break
    
    if not claim:
        # Create a new claim if not found
        claim = Claim(text=claim_text, context=0.8)
    
    # Find or create evidence
    evidence = []
    if "United States" in claim_text and "military" in claim_text:
        evidence = POLITICAL_EVIDENCE["US military budget"]
    elif "vaccine" in claim_text.lower() and "autism" in claim_text.lower():
        evidence = HEALTH_EVIDENCE["Vaccines and autism"]
    elif "Earth" in claim_text and "flat" in claim_text:
        evidence = SCIENCE_EVIDENCE["Flat Earth"]
    elif "brain" in claim_text.lower():
        evidence = SCIENCE_EVIDENCE["10% of brain"]
    else:
        # Create generic evidence if no specific evidence is found
        evidence = [
            Evidence(
                content=f"Evidence related to: {claim_text}",
                source="https://example.com/evidence",
                relevance=0.8,
                stance="supporting" if verdict.verdict == "true" else "contradicting",
            )
        ]
    
    return claim, evidence


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_true_claim(mock_run, manager):
    """Test the pipeline with a true claim."""
    # Get a true verdict from fixtures
    true_verdict = get_verdict_by_type("true")
    claim, evidence = get_claim_and_evidence_for_verdict(true_verdict)
    
    # Configure mock to return appropriate results
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(true_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run(f"Text containing the claim: {claim.text}")
    
    # Verify results
    assert len(results) == 1
    assert results[0].verdict == "true"
    assert results[0].confidence > 0.8  # High confidence for true claims
    assert len(results[0].explanation) > 0
    assert len(results[0].sources) > 0


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_false_claim(mock_run, manager):
    """Test the pipeline with a false claim."""
    # Get a false verdict from fixtures
    false_verdict = get_verdict_by_type("false")
    claim, evidence = get_claim_and_evidence_for_verdict(false_verdict)
    
    # Configure mock to return appropriate results
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(false_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run(f"Text containing the claim: {claim.text}")
    
    # Verify results
    assert len(results) == 1
    assert results[0].verdict == "false"
    assert results[0].confidence > 0.8  # High confidence for false claims
    assert len(results[0].explanation) > 0
    assert len(results[0].sources) > 0


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_partially_true_claim(mock_run, manager):
    """Test the pipeline with a partially true claim."""
    # Get a partially true verdict from fixtures
    partially_true_verdict = get_verdict_by_type("partially true")
    claim, evidence = get_claim_and_evidence_for_verdict(partially_true_verdict)
    
    # Configure mock to return appropriate results
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(partially_true_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run(f"Text containing the claim: {claim.text}")
    
    # Verify results
    assert len(results) == 1
    assert results[0].verdict == "partially true"
    assert 0.5 <= results[0].confidence <= 0.9  # Moderate confidence for partially true claims
    assert len(results[0].explanation) > 0
    assert len(results[0].sources) > 0


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_unverifiable_claim(mock_run, manager):
    """Test the pipeline with an unverifiable claim."""
    # Get an unverifiable verdict from fixtures
    unverifiable_verdict = get_verdict_by_type("unverifiable")
    claim, evidence = get_claim_and_evidence_for_verdict(unverifiable_verdict)
    
    # Configure mock to return appropriate results
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult([claim])
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(unverifiable_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run(f"Text containing the claim: {claim.text}")
    
    # Verify results
    assert len(results) == 1
    assert results[0].verdict == "unverifiable"
    assert results[0].confidence < 0.8  # Lower confidence for unverifiable claims
    assert len(results[0].explanation) > 0
    assert len(results[0].sources) > 0


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_mixed_claim_types(mock_run, manager):
    """Test the pipeline with a mix of different claim types."""
    # Get verdicts of different types
    true_verdict = get_verdict_by_type("true")
    false_verdict = get_verdict_by_type("false")
    partially_true_verdict = get_verdict_by_type("partially true")
    unverifiable_verdict = get_verdict_by_type("unverifiable")
    
    # Get claims and evidence
    true_claim, true_evidence = get_claim_and_evidence_for_verdict(true_verdict)
    false_claim, false_evidence = get_claim_and_evidence_for_verdict(false_verdict)
    partially_true_claim, partially_true_evidence = get_claim_and_evidence_for_verdict(partially_true_verdict)
    unverifiable_claim, unverifiable_evidence = get_claim_and_evidence_for_verdict(unverifiable_verdict)
    
    # All claims to be detected
    all_claims = [true_claim, false_claim, partially_true_claim, unverifiable_claim]
    
    # Configure mock to return appropriate results
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult(all_claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Return different evidence based on which claim is being processed
            claim_text = args[1].split("Claim to investigate: ")[1].split("\n")[0]
            if claim_text == true_claim.text:
                return MockRunnerResult(true_evidence)
            elif claim_text == false_claim.text:
                return MockRunnerResult(false_evidence)
            elif claim_text == partially_true_claim.text:
                return MockRunnerResult(partially_true_evidence)
            else:
                return MockRunnerResult(unverifiable_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Return different verdicts based on which claim is being processed
            claim_text = args[1].split("Claim to investigate: ")[1].split("\n")[0]
            if claim_text == true_claim.text:
                return MockRunnerResult(true_verdict)
            elif claim_text == false_claim.text:
                return MockRunnerResult(false_verdict)
            elif claim_text == partially_true_claim.text:
                return MockRunnerResult(partially_true_verdict)
            else:
                return MockRunnerResult(unverifiable_verdict)
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("Text containing multiple claims of different types")
    
    # Verify results
    assert len(results) == 4
    
    # Check that we have one of each verdict type
    verdict_types = [result.verdict for result in results]
    assert "true" in verdict_types
    assert "false" in verdict_types
    assert "partially true" in verdict_types
    assert "unverifiable" in verdict_types
    
    # Verify the Runner.run was called multiple times
    # 1 for claim detection + 4 for evidence gathering + 4 for verdict generation
    assert mock_run.call_count >= 9
