"""Unit tests for the VerifactManager class."""

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
async def test_detect_claims(mock_run, manager):
    """Test the _detect_claims method."""
    # Setup mock
    sample_claims = POLITICAL_CLAIMS[:2]
    mock_run.return_value = MockRunnerResult(sample_claims)
    
    # Call the method
    result = await manager._detect_claims(SAMPLE_TEXTS[0])
    
    # Verify results
    assert result == sample_claims
    mock_run.assert_called_once()
    # Verify the text was passed to the agent
    assert mock_run.call_args[0][1] == SAMPLE_TEXTS[0]


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_gather_evidence_for_claim(mock_run, manager):
    """Test the _gather_evidence_for_claim method."""
    # Setup mock
    sample_claim = POLITICAL_CLAIMS[0]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    mock_run.return_value = MockRunnerResult(sample_evidence)
    
    # Call the method
    result = await manager._gather_evidence_for_claim(sample_claim)
    
    # Verify results
    assert result == sample_evidence
    mock_run.assert_called_once()
    # Verify the claim was included in the query
    assert sample_claim.text in mock_run.call_args[0][1]


@pytest.mark.asyncio
@patch("src.verifact_manager.VerifactManager._gather_evidence_for_claim")
async def test_gather_evidence(mock_gather, manager):
    """Test the _gather_evidence method."""
    # Setup mock
    sample_claims = POLITICAL_CLAIMS[:2]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    mock_gather.side_effect = [sample_evidence, Exception("Test error")]
    
    # Call the method
    result = await manager._gather_evidence(sample_claims)
    
    # Verify results
    assert len(result) == 2
    assert result[0][0] == sample_claims[0]
    assert result[0][1] == sample_evidence
    assert result[1][0] == sample_claims[1]
    assert result[1][1] is None  # Should be None due to the exception
    assert mock_gather.call_count == 2


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_generate_verdict_for_claim(mock_run, manager):
    """Test the _generate_verdict_for_claim method."""
    # Setup mock
    sample_claim = POLITICAL_CLAIMS[0]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    sample_verdict = POLITICAL_VERDICTS[0]
    mock_run.return_value = MockRunnerResult(sample_verdict)
    
    # Call the method
    result = await manager._generate_verdict_for_claim(sample_claim, sample_evidence)
    
    # Verify results
    assert result == sample_verdict
    mock_run.assert_called_once()
    # Verify the claim and evidence were included in the prompt
    assert sample_claim.text in mock_run.call_args[0][1]
    assert "Evidence" in mock_run.call_args[0][1]


@pytest.mark.asyncio
@patch("src.verifact_manager.VerifactManager._generate_verdict_for_claim")
async def test_generate_all_verdicts(mock_generate, manager):
    """Test the _generate_all_verdicts method."""
    # Setup mock
    sample_claims = POLITICAL_CLAIMS[:2]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    sample_verdicts = POLITICAL_VERDICTS[:2]
    
    # Create claim-evidence pairs
    claim_evidence_pairs = [
        (sample_claims[0], sample_evidence),
        (sample_claims[1], None),  # This should be skipped
    ]
    
    mock_generate.return_value = sample_verdicts[0]
    
    # Call the method
    result = await manager._generate_all_verdicts(claim_evidence_pairs)
    
    # Verify results
    assert len(result) == 1  # Only one verdict should be generated (second claim has no evidence)
    assert result[0] == sample_verdicts[0]
    mock_generate.assert_called_once_with(sample_claims[0], sample_evidence)


@pytest.mark.asyncio
@patch("src.verifact_manager.VerifactManager._detect_claims")
@patch("src.verifact_manager.VerifactManager._gather_evidence")
@patch("src.verifact_manager.VerifactManager._generate_all_verdicts")
async def test_run_success(mock_generate_verdicts, mock_gather_evidence, mock_detect_claims, manager):
    """Test the run method with successful execution."""
    # Setup mocks
    sample_claims = POLITICAL_CLAIMS[:2]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    sample_verdicts = POLITICAL_VERDICTS[:2]
    
    mock_detect_claims.return_value = sample_claims
    mock_gather_evidence.return_value = [(sample_claims[0], sample_evidence)]
    mock_generate_verdicts.return_value = sample_verdicts
    
    # Call the method
    result = await manager.run(SAMPLE_TEXTS[0])
    
    # Verify results
    assert result == sample_verdicts
    mock_detect_claims.assert_called_once_with(SAMPLE_TEXTS[0])
    mock_gather_evidence.assert_called_once_with(sample_claims)
    mock_generate_verdicts.assert_called_once()


@pytest.mark.asyncio
@patch("src.verifact_manager.VerifactManager._detect_claims")
async def test_run_no_claims(mock_detect_claims, manager):
    """Test the run method when no claims are detected."""
    # Setup mock
    mock_detect_claims.return_value = []
    
    # Call the method
    result = await manager.run(SAMPLE_TEXTS[0])
    
    # Verify results
    assert result == []
    mock_detect_claims.assert_called_once_with(SAMPLE_TEXTS[0])


@pytest.mark.asyncio
@patch("src.verifact_manager.VerifactManager._detect_claims")
async def test_run_claim_detection_error(mock_detect_claims, manager):
    """Test the run method when claim detection raises an exception."""
    # Setup mock
    mock_detect_claims.side_effect = Exception("Test error")
    
    # Call the method and expect an exception
    with pytest.raises(Exception):
        await manager.run(SAMPLE_TEXTS[0])
    
    # Verify the mock was called
    mock_detect_claims.assert_called_once_with(SAMPLE_TEXTS[0])


@pytest.mark.asyncio
@patch("src.verifact_manager.VerifactManager._detect_claims")
@patch("src.verifact_manager.VerifactManager._gather_evidence")
async def test_run_evidence_gathering_error(mock_gather_evidence, mock_detect_claims, manager):
    """Test the run method when evidence gathering raises an exception."""
    # Setup mocks
    sample_claims = POLITICAL_CLAIMS[:2]
    mock_detect_claims.return_value = sample_claims
    mock_gather_evidence.side_effect = Exception("Test error")
    
    # Call the method and expect an exception
    with pytest.raises(Exception):
        await manager.run(SAMPLE_TEXTS[0])
    
    # Verify the mocks were called
    mock_detect_claims.assert_called_once_with(SAMPLE_TEXTS[0])
    mock_gather_evidence.assert_called_once_with(sample_claims)


@pytest.mark.asyncio
@patch("src.verifact_manager.VerifactManager._detect_claims")
@patch("src.verifact_manager.VerifactManager._gather_evidence")
@patch("src.verifact_manager.VerifactManager._generate_all_verdicts")
async def test_run_verdict_generation_error(mock_generate_verdicts, mock_gather_evidence, mock_detect_claims, manager):
    """Test the run method when verdict generation raises an exception."""
    # Setup mocks
    sample_claims = POLITICAL_CLAIMS[:2]
    sample_evidence = POLITICAL_EVIDENCE["US military budget"]
    
    mock_detect_claims.return_value = sample_claims
    mock_gather_evidence.return_value = [(sample_claims[0], sample_evidence)]
    mock_generate_verdicts.side_effect = Exception("Test error")
    
    # Call the method and expect an exception
    with pytest.raises(Exception):
        await manager.run(SAMPLE_TEXTS[0])
    
    # Verify the mocks were called
    mock_detect_claims.assert_called_once_with(SAMPLE_TEXTS[0])
    mock_gather_evidence.assert_called_once_with(sample_claims)
    mock_generate_verdicts.assert_called_once()
