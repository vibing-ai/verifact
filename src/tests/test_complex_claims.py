"""Tests for handling complex claims in the VeriFact pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.verifact_manager import VerifactManager, ManagerConfig
from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict

from src.tests.fixtures.claims import SAMPLE_TEXTS


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
        max_claims=10,  # Allow more claims for complex tests
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
async def test_compound_claim(mock_run, manager):
    """Test the pipeline with a compound claim that should be broken down."""
    # A compound claim that contains multiple factual assertions
    compound_claim = Claim(
        text="The Earth is round and orbits the Sun, which is a star that is 93 million miles away.",
        context=0.9,
    )
    
    # Individual claims after breakdown
    individual_claims = [
        Claim(text="The Earth is round.", context=0.9),
        Claim(text="The Earth orbits the Sun.", context=0.9),
        Claim(text="The Sun is a star.", context=0.9),
        Claim(text="The Sun is 93 million miles away from Earth.", context=0.9),
    ]
    
    # Evidence for each claim
    evidence_sets = [
        [Evidence(
            content="The Earth is an oblate spheroid, slightly flattened at the poles and bulging at the equator.",
            source="https://example.com/earth-shape",
            relevance=0.95,
            stance="supporting",
        )],
        [Evidence(
            content="The Earth orbits the Sun once every 365.25 days, completing a full revolution.",
            source="https://example.com/earth-orbit",
            relevance=0.95,
            stance="supporting",
        )],
        [Evidence(
            content="The Sun is a G-type main-sequence star and is the largest object in our solar system.",
            source="https://example.com/sun-star",
            relevance=0.95,
            stance="supporting",
        )],
        [Evidence(
            content="The average distance from the Earth to the Sun is about 93 million miles (150 million kilometers).",
            source="https://example.com/sun-distance",
            relevance=0.95,
            stance="supporting",
        )],
    ]
    
    # Verdicts for each claim
    verdicts = [
        Verdict(
            claim="The Earth is round.",
            verdict="true",
            confidence=0.99,
            explanation="The Earth is indeed round, or more precisely, an oblate spheroid.",
            sources=["https://example.com/earth-shape"],
        ),
        Verdict(
            claim="The Earth orbits the Sun.",
            verdict="true",
            confidence=0.99,
            explanation="The Earth completes one orbit around the Sun every 365.25 days.",
            sources=["https://example.com/earth-orbit"],
        ),
        Verdict(
            claim="The Sun is a star.",
            verdict="true",
            confidence=0.99,
            explanation="The Sun is a G-type main-sequence star at the center of our solar system.",
            sources=["https://example.com/sun-star"],
        ),
        Verdict(
            claim="The Sun is 93 million miles away from Earth.",
            verdict="true",
            confidence=0.95,
            explanation="The average distance from Earth to the Sun is approximately 93 million miles.",
            sources=["https://example.com/sun-distance"],
        ),
    ]
    
    # Configure mock to return appropriate results
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            # Return individual claims instead of the compound claim
            return MockRunnerResult(individual_claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Return evidence for the appropriate claim
            current_evidence = evidence_sets[call_count % len(evidence_sets)]
            call_count += 1
            return MockRunnerResult(current_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Return the verdict for the appropriate claim
            claim_text = args[1].split("Claim to investigate: ")[1].split("\n")[0]
            for i, claim in enumerate(individual_claims):
                if claim.text == claim_text:
                    return MockRunnerResult(verdicts[i])
            return MockRunnerResult(verdicts[0])  # Fallback
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("The Earth is round and orbits the Sun, which is a star that is 93 million miles away.")
    
    # Verify results
    assert len(results) == 4
    assert all(isinstance(verdict, Verdict) for verdict in results)
    assert all(verdict.verdict == "true" for verdict in results)
    
    # Check that all individual claims were addressed
    claim_texts = [verdict.claim for verdict in results]
    for claim in individual_claims:
        assert claim.text in claim_texts


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_claim_with_context_dependency(mock_run, manager):
    """Test the pipeline with claims that have context dependencies."""
    # Claims with context dependencies
    context_claims = [
        Claim(text="The president signed the bill yesterday.", context=0.8),
        Claim(text="It will go into effect next month.", context=0.7),
    ]
    
    # Evidence for each claim
    evidence_sets = [
        [Evidence(
            content="President Biden signed the Infrastructure Investment and Jobs Act on November 15, 2021.",
            source="https://example.com/bill-signing",
            relevance=0.9,
            stance="supporting",
        )],
        [Evidence(
            content="The Infrastructure Investment and Jobs Act provisions will begin implementation in December 2021.",
            source="https://example.com/bill-implementation",
            relevance=0.8,
            stance="supporting",
        )],
    ]
    
    # Verdicts for each claim
    verdicts = [
        Verdict(
            claim="The president signed the bill yesterday.",
            verdict="unverifiable",
            confidence=0.7,
            explanation="This claim is time-dependent and lacks specific context about which president and which bill is being referenced. Without this context, the claim cannot be verified.",
            sources=["https://example.com/bill-signing"],
        ),
        Verdict(
            claim="It will go into effect next month.",
            verdict="unverifiable",
            confidence=0.6,
            explanation="This claim is context-dependent and lacks specific information about what 'it' refers to and when 'next month' is. Without this context, the claim cannot be verified.",
            sources=["https://example.com/bill-implementation"],
        ),
    ]
    
    # Configure mock to return appropriate results
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult(context_claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            current_evidence = evidence_sets[call_count % len(evidence_sets)]
            call_count += 1
            return MockRunnerResult(current_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            claim_text = args[1].split("Claim to investigate: ")[1].split("\n")[0]
            for i, claim in enumerate(context_claims):
                if claim.text == claim_text:
                    return MockRunnerResult(verdicts[i])
            return MockRunnerResult(verdicts[0])  # Fallback
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("The president signed the bill yesterday. It will go into effect next month.")
    
    # Verify results
    assert len(results) == 2
    assert all(isinstance(verdict, Verdict) for verdict in results)
    assert all(verdict.verdict == "unverifiable" for verdict in results)
    
    # Check that explanations mention context dependency
    for verdict in results:
        assert any(term in verdict.explanation.lower() for term in ["context", "specific", "lacks"])


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_claim_with_mixed_verdicts(mock_run, manager):
    """Test the pipeline with a text containing claims with different verdicts."""
    # Claims with different verdicts
    mixed_claims = [
        Claim(text="Water boils at 100 degrees Celsius at sea level.", context=0.9),
        Claim(text="The Great Wall of China is visible from the Moon.", context=0.8),
        Claim(text="Humans have explored less than 5% of the ocean.", context=0.85),
        Claim(text="There are exactly 1 million species of insects on Earth.", context=0.7),
    ]
    
    # Evidence for each claim
    evidence_sets = [
        [Evidence(
            content="Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure at sea level.",
            source="https://example.com/water-boiling",
            relevance=0.95,
            stance="supporting",
        )],
        [Evidence(
            content="The Great Wall of China is not visible from the Moon with the naked eye. This is a common misconception.",
            source="https://example.com/great-wall-visibility",
            relevance=0.9,
            stance="contradicting",
        )],
        [Evidence(
            content="According to NOAA, more than 80% of the ocean remains unmapped, unobserved, and unexplored.",
            source="https://example.com/ocean-exploration",
            relevance=0.85,
            stance="supporting",
        )],
        [Evidence(
            content="Scientists have described about 1 million insect species, but estimates of the total number range from 2 million to 30 million species.",
            source="https://example.com/insect-species",
            relevance=0.8,
            stance="contradicting",
        )],
    ]
    
    # Verdicts for each claim
    verdicts = [
        Verdict(
            claim="Water boils at 100 degrees Celsius at sea level.",
            verdict="true",
            confidence=0.98,
            explanation="Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure at sea level.",
            sources=["https://example.com/water-boiling"],
        ),
        Verdict(
            claim="The Great Wall of China is visible from the Moon.",
            verdict="false",
            confidence=0.95,
            explanation="The Great Wall of China is not visible from the Moon with the naked eye. This is a common misconception.",
            sources=["https://example.com/great-wall-visibility"],
        ),
        Verdict(
            claim="Humans have explored less than 5% of the ocean.",
            verdict="partially true",
            confidence=0.85,
            explanation="This claim is partially true. While the exact percentage varies by definition of 'explored', NOAA states that more than 80% of the ocean remains unmapped, unobserved, and unexplored.",
            sources=["https://example.com/ocean-exploration"],
        ),
        Verdict(
            claim="There are exactly 1 million species of insects on Earth.",
            verdict="false",
            confidence=0.8,
            explanation="This claim is false. While scientists have described about 1 million insect species, estimates of the total number range from 2 million to 30 million species.",
            sources=["https://example.com/insect-species"],
        ),
    ]
    
    # Configure mock to return appropriate results
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]
        
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult(mixed_claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            current_evidence = evidence_sets[call_count % len(evidence_sets)]
            call_count += 1
            return MockRunnerResult(current_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            claim_text = args[1].split("Claim to investigate: ")[1].split("\n")[0]
            for i, claim in enumerate(mixed_claims):
                if claim.text == claim_text:
                    return MockRunnerResult(verdicts[i])
            return MockRunnerResult(verdicts[0])  # Fallback
        return MockRunnerResult([])
    
    mock_run.side_effect = mock_runner_side_effect
    
    # Run the pipeline
    results = await manager.run("""
    Water boils at 100 degrees Celsius at sea level.
    The Great Wall of China is visible from the Moon.
    Humans have explored less than 5% of the ocean.
    There are exactly 1 million species of insects on Earth.
    """)
    
    # Verify results
    assert len(results) == 4
    
    # Check that we have one of each verdict type
    verdict_types = [result.verdict for result in results]
    assert "true" in verdict_types
    assert "false" in verdict_types
    assert "partially true" in verdict_types
    
    # Check that the verdicts match the expected claims
    for verdict in results:
        if verdict.claim == "Water boils at 100 degrees Celsius at sea level.":
            assert verdict.verdict == "true"
        elif verdict.claim == "The Great Wall of China is visible from the Moon.":
            assert verdict.verdict == "false"
        elif verdict.claim == "Humans have explored less than 5% of the ocean.":
            assert verdict.verdict == "partially true"
        elif verdict.claim == "There are exactly 1 million species of insects on Earth.":
            assert verdict.verdict == "false"
