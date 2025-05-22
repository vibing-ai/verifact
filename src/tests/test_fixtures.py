"""Tests for the test fixtures."""

import pytest

from src.tests.fixtures.claims import (
    ALL_CLAIMS,
    POLITICAL_CLAIMS,
    HEALTH_CLAIMS,
    SCIENCE_CLAIMS,
    ECONOMIC_CLAIMS,
    SAMPLE_TEXTS,
)
from src.tests.fixtures.evidence import (
    ALL_EVIDENCE,
    POLITICAL_EVIDENCE,
    HEALTH_EVIDENCE,
    SCIENCE_EVIDENCE,
    ECONOMIC_EVIDENCE,
)
from src.tests.fixtures.verdicts import (
    ALL_VERDICTS,
    POLITICAL_VERDICTS,
    HEALTH_VERDICTS,
    SCIENCE_VERDICTS,
    ECONOMIC_VERDICTS,
)

from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict


def test_claims_fixtures():
    """Test that the claims fixtures are valid."""
    # Check that all claims are instances of the Claim class
    for claim in ALL_CLAIMS:
        assert isinstance(claim, Claim)
    
    # Check that the combined list contains all individual lists
    assert len(ALL_CLAIMS) == (
        len(POLITICAL_CLAIMS) + 
        len(HEALTH_CLAIMS) + 
        len(SCIENCE_CLAIMS) + 
        len(ECONOMIC_CLAIMS)
    )
    
    # Check that sample texts are non-empty
    for text in SAMPLE_TEXTS:
        assert isinstance(text, str)
        assert len(text) > 0


def test_evidence_fixtures():
    """Test that the evidence fixtures are valid."""
    # Check that all evidence items are instances of the Evidence class
    for category, evidence_list in ALL_EVIDENCE.items():
        for evidence_item in evidence_list:
            assert isinstance(evidence_item, Evidence)
    
    # Check that the combined dictionary contains all individual dictionaries
    assert len(ALL_EVIDENCE) == (
        len(POLITICAL_EVIDENCE) + 
        len(HEALTH_EVIDENCE) + 
        len(SCIENCE_EVIDENCE) + 
        len(ECONOMIC_EVIDENCE)
    )
    
    # Check evidence attributes
    for category, evidence_list in ALL_EVIDENCE.items():
        for evidence in evidence_list:
            assert isinstance(evidence.content, str)
            assert isinstance(evidence.source, str)
            assert 0.0 <= evidence.relevance <= 1.0
            assert evidence.stance in ["supporting", "contradicting", "neutral"]


def test_verdicts_fixtures():
    """Test that the verdicts fixtures are valid."""
    # Check that all verdicts are instances of the Verdict class
    for verdict in ALL_VERDICTS:
        assert isinstance(verdict, Verdict)
    
    # Check that the combined list contains all individual lists
    assert len(ALL_VERDICTS) == (
        len(POLITICAL_VERDICTS) + 
        len(HEALTH_VERDICTS) + 
        len(SCIENCE_VERDICTS) + 
        len(ECONOMIC_VERDICTS)
    )
    
    # Check verdict attributes
    for verdict in ALL_VERDICTS:
        assert isinstance(verdict.claim, str)
        assert verdict.verdict in ["true", "false", "partially true", "unverifiable"]
        assert 0.0 <= verdict.confidence <= 1.0
        assert isinstance(verdict.explanation, str)
        assert len(verdict.sources) > 0
        for source in verdict.sources:
            assert isinstance(source, str)


def test_fixture_relationships():
    """Test the relationships between fixtures."""
    # Check that there's evidence for at least some claims
    for claim in POLITICAL_CLAIMS:
        # Find evidence that might match this claim
        found_evidence = False
        for category, evidence_list in POLITICAL_EVIDENCE.items():
            if claim.text.lower() in category.lower():
                found_evidence = True
                break
        
        # Not all claims need evidence, but at least some should have it
        if claim.text == "The United States has the largest military budget in the world.":
            assert found_evidence, f"No evidence found for key claim: {claim.text}"
    
    # Check that there's a verdict for at least some claims
    for claim in POLITICAL_CLAIMS:
        found_verdict = False
        for verdict in POLITICAL_VERDICTS:
            if claim.text == verdict.claim:
                found_verdict = True
                break
        
        # Not all claims need verdicts, but at least some should have them
        if claim.text == "The United States has the largest military budget in the world.":
            assert found_verdict, f"No verdict found for key claim: {claim.text}"
