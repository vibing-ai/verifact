"""Integration tests for the VeriFact pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tests.fixtures.claims import POLITICAL_CLAIMS, HEALTH_CLAIMS, SAMPLE_TEXTS
from src.tests.fixtures.evidence import POLITICAL_EVIDENCE, HEALTH_EVIDENCE
from src.tests.fixtures.verdicts import POLITICAL_VERDICTS, HEALTH_VERDICTS

from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict
from src.verifact_manager import VerifactManager, ManagerConfig


class MockRunnerResult:
    """Mock for the result returned by Runner.run()."""

    def __init__(self, output_data):
        self.output_data = output_data
        self.final_output = str(output_data)

    def final_output_as(self, output_type):
        """Mock the final_output_as method."""
        return self.output_data


class MockClaimDetector:
    """Mock claim detector for testing."""

    def __init__(self, claims_to_return):
        self.claims_to_return = claims_to_return
        self.detect_claims = AsyncMock(return_value=claims_to_return)


class MockEvidenceHunter:
    """Mock evidence hunter for testing."""

    def __init__(self, evidence_to_return):
        self.evidence_to_return = evidence_to_return
        self.gather_evidence = AsyncMock(return_value=evidence_to_return)


class MockVerdictWriter:
    """Mock verdict writer for testing."""

    def __init__(self, verdict_to_return):
        self.verdict_to_return = verdict_to_return
        self.generate_verdict = AsyncMock(return_value=verdict_to_return)


@pytest.mark.asyncio
async def test_pipeline_with_mocks():
    """Test the factcheck pipeline with mock agents."""
    # Sample test data from fixtures
    sample_claim = POLITICAL_CLAIMS[0]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    sample_verdict = POLITICAL_VERDICTS[0]

    # Create mock agents
    mock_claim_detector = MockClaimDetector(claims_to_return=[sample_claim])
    mock_evidence_hunter = MockEvidenceHunter(evidence_to_return=sample_evidence)
    mock_verdict_writer = MockVerdictWriter(verdict_to_return=sample_verdict)

    # Verify that the mocks can be called
    detected_claims = await mock_claim_detector.detect_claims(SAMPLE_TEXTS[0])
    assert detected_claims == [sample_claim]

    gathered_evidence = await mock_evidence_hunter.gather_evidence(sample_claim)
    assert gathered_evidence == sample_evidence

    verdict = await mock_verdict_writer.generate_verdict(sample_claim, sample_evidence)
    assert verdict == sample_verdict


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_full_pipeline_integration(mock_run):
    """Test the full pipeline integration with mocked Runner."""
    # Setup test data
    sample_claims = POLITICAL_CLAIMS[:2]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    sample_verdict = POLITICAL_VERDICTS[0]

    # Configure mock to return different results for different agent calls
    def mock_runner_side_effect(*args, **kwargs):
        # Check which agent is being called based on the agent object (first arg)
        agent = args[0]
        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult(sample_claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            return MockRunnerResult(sample_evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            return MockRunnerResult(sample_verdict)
        return MockRunnerResult([])

    # Use side_effect to return different values based on input
    mock_run.side_effect = mock_runner_side_effect

    # Create manager and run the pipeline
    manager = VerifactManager()
    results = await manager.run(SAMPLE_TEXTS[0])

    # Verify results
    assert len(results) > 0
    assert isinstance(results[0], Verdict)
    assert results[0].claim == sample_verdict.claim
    assert results[0].verdict == sample_verdict.verdict

    # Verify the Runner.run was called for each agent
    assert mock_run.call_count >= 3  # At least once for each agent


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_pipeline_with_multiple_claims(mock_run):
    """Test the pipeline with multiple claims of different types."""
    # Setup test data - mix of political and health claims
    mixed_claims = POLITICAL_CLAIMS[:1] + HEALTH_CLAIMS[:1]

    # Configure mock for different agent calls
    call_count = 0
    def mock_runner_side_effect(*args, **kwargs):
        nonlocal call_count
        agent = args[0]

        if agent.__dict__.get('name') == 'ClaimDetector':
            return MockRunnerResult(mixed_claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Return different evidence based on which claim is being processed
            if call_count == 0:
                call_count += 1
                return MockRunnerResult(POLITICAL_EVIDENCE["US military budget"])
            else:
                return MockRunnerResult(HEALTH_EVIDENCE["Vaccines and autism"])
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Return different verdicts based on which claim is being processed
            if call_count == 1:
                call_count += 1
                return MockRunnerResult(POLITICAL_VERDICTS[0])
            else:
                return MockRunnerResult(HEALTH_VERDICTS[0])
        return MockRunnerResult([])

    mock_run.side_effect = mock_runner_side_effect

    # Create manager and run the pipeline
    manager = VerifactManager()
    results = await manager.run(SAMPLE_TEXTS[0])

    # Verify results
    assert len(results) == 2
    assert all(isinstance(verdict, Verdict) for verdict in results)

    # Verify the Runner.run was called multiple times
    # 1 for claim detection + 2 for evidence gathering + 2 for verdict generation
    assert mock_run.call_count >= 5


@pytest.mark.asyncio
@patch("src.verifact_agents.claim_detector.claim_detector_agent")
@patch("src.verifact_agents.evidence_hunter.evidence_hunter_agent")
@patch("src.verifact_agents.verdict_writer.verdict_writer_agent")
async def test_agent_integration(mock_claim_detector, mock_evidence_hunter, mock_verdict_writer):
    """Test the integration of the three main agents with the VerifactManager."""
    # Setup mock returns
    mock_claim_detector_result = MagicMock()
    mock_claim_detector_result.final_output_as.return_value = POLITICAL_CLAIMS[:1]
    mock_claim_detector.return_value = mock_claim_detector_result

    mock_evidence_hunter_result = MagicMock()
    mock_evidence_hunter_result.final_output_as.return_value = POLITICAL_EVIDENCE["US military budget"]
    mock_evidence_hunter.return_value = mock_evidence_hunter_result

    mock_verdict_writer_result = MagicMock()
    mock_verdict_writer_result.final_output_as.return_value = POLITICAL_VERDICTS[0]
    mock_verdict_writer.return_value = mock_verdict_writer_result

    # Create manager and run the pipeline
    manager = VerifactManager()
    results = await manager.run(SAMPLE_TEXTS[0])

    # Verify results
    assert len(results) == 1
    assert results[0] == POLITICAL_VERDICTS[0]

    # Verify each agent was called
    mock_claim_detector.assert_called_once()
    mock_evidence_hunter.assert_called_once()
    mock_verdict_writer.assert_called_once()

    # Verify the final_output_as method was called for each result
    mock_claim_detector_result.final_output_as.assert_called_once()
    mock_evidence_hunter_result.final_output_as.assert_called_once()
    mock_verdict_writer_result.final_output_as.assert_called_once()
