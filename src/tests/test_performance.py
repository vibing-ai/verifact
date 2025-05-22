"""Tests for measuring and optimizing performance of the VeriFact pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import time

from src.verifact_manager import VerifactManager, ManagerConfig
from src.verifact_agents.claim_detector import Claim
from src.verifact_agents.evidence_hunter import Evidence
from src.verifact_agents.verdict_writer import Verdict

from src.tests.utils.mock_data_factory import MockDataFactory
from src.tests.utils.performance_utils import (
    PerformanceTracker,
    benchmark_pipeline,
    analyze_benchmark_results,
)


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


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_performance_tracking(mock_run, manager):
    """Test that performance tracking works correctly."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=2)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]

    # Configure mock with delays to simulate processing time
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]

        if agent.__dict__.get('name') == 'ClaimDetector':
            time.sleep(0.1)  # 100ms delay
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            time.sleep(0.2)  # 200ms delay

            # Extract claim text from the query
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            evidence = evidence_map.get(claim_text, [])

            return MockDataFactory.create_runner_result_mock(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            time.sleep(0.15)  # 150ms delay

            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            verdict = next((v for v in verdicts if v.claim == claim_text), verdicts[0])

            return MockDataFactory.create_runner_result_mock(verdict)
        return MockDataFactory.create_runner_result_mock([])

    mock_run.side_effect = mock_runner_side_effect

    # Create a performance tracker
    tracker = PerformanceTracker()
    tracker.start()

    # Monkey patch the manager's methods to track performance
    original_detect_claims = manager._detect_claims
    original_gather_evidence_for_claim = manager._gather_evidence_for_claim
    original_generate_verdict_for_claim = manager._generate_verdict_for_claim

    async def timed_detect_claims(text):
        return await tracker.timed_operation(
            "claim_detection",
            original_detect_claims,
            text,
        )

    async def timed_gather_evidence_for_claim(claim):
        return await tracker.timed_operation(
            "evidence_gathering",
            original_gather_evidence_for_claim,
            claim,
        )

    async def timed_generate_verdict_for_claim(claim, evidence):
        return await tracker.timed_operation(
            "verdict_generation",
            original_generate_verdict_for_claim,
            claim,
            evidence,
        )

    # Apply the monkey patches
    manager._detect_claims = timed_detect_claims
    manager._gather_evidence_for_claim = timed_gather_evidence_for_claim
    manager._generate_verdict_for_claim = timed_generate_verdict_for_claim

    try:
        # Run the pipeline
        results = await manager.run("Test text with claims")
    finally:
        # Restore the original methods
        manager._detect_claims = original_detect_claims
        manager._gather_evidence_for_claim = original_gather_evidence_for_claim
        manager._generate_verdict_for_claim = original_generate_verdict_for_claim

    tracker.stop()
    report = tracker.generate_report()

    # Verify results
    assert len(results) == 2

    # Verify performance tracking
    assert report.total_duration_ms > 0
    assert report.claim_detection_ms >= 100  # At least 100ms
    assert report.evidence_gathering_ms >= 400  # At least 2 * 200ms
    assert report.verdict_generation_ms >= 300  # At least 2 * 150ms

    # Verify counts
    assert report.claim_count == 1  # One call to detect_claims
    assert report.evidence_count == 2  # Two calls to gather_evidence_for_claim
    assert report.verdict_count == 2  # Two calls to generate_verdict_for_claim

    # Verify parallelism efficiency
    # The efficiency should be close to 1.0 because of parallelism in evidence gathering
    assert report.parallelism_efficiency > 0.9


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_parallelism_efficiency(mock_run):
    """Test the parallelism efficiency of the pipeline with different configurations."""
    # Create test data
    scenario = MockDataFactory.create_scenario("standard", claim_count=5)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]

    # Configure mock with delays to simulate processing time
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]

        if agent.__dict__.get('name') == 'ClaimDetector':
            time.sleep(0.1)  # 100ms delay
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            time.sleep(0.2)  # 200ms delay

            # Extract claim text from the query
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            evidence = evidence_map.get(claim_text, [])

            return MockDataFactory.create_runner_result_mock(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            time.sleep(0.15)  # 150ms delay

            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            verdict = next((v for v in verdicts if v.claim == claim_text), verdicts[0])

            return MockDataFactory.create_runner_result_mock(verdict)
        return MockDataFactory.create_runner_result_mock([])

    mock_run.side_effect = mock_runner_side_effect

    # Test with different configurations
    configs = [
        # Sequential processing
        ManagerConfig(
            min_checkworthiness=0.5,
            max_claims=5,
            evidence_per_claim=3,
            timeout_seconds=30.0,
            enable_fallbacks=True,
            retry_attempts=1,
            raise_exceptions=True,
            include_debug_info=True,
        ),
    ]

    reports = []
    for config in configs:
        manager = VerifactManager(config)

        # Benchmark the pipeline
        benchmark_results = await benchmark_pipeline(
            manager,
            ["Test text with claims"],
            iterations=1,
        )

        reports.append(benchmark_results[0])

    # Verify parallelism efficiency
    # The efficiency should be close to 1.0 because of parallelism in evidence gathering
    for report in reports:
        assert report.parallelism_efficiency > 0.9

    # Analyze the results
    stats = analyze_benchmark_results(reports)
    assert "total_duration" in stats
    assert "claim_detection" in stats
    assert "evidence_gathering" in stats
    assert "verdict_generation" in stats
    assert "parallelism_efficiency" in stats


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_high_volume_performance(mock_run):
    """Test the performance of the pipeline with a high volume of claims."""
    # Create test data with many claims
    scenario = MockDataFactory.create_scenario("high_volume", claim_count=10, evidence_per_claim=5)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]

    # Configure mock with minimal delays
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]

        if agent.__dict__.get('name') == 'ClaimDetector':
            time.sleep(0.05)  # 50ms delay
            return MockDataFactory.create_runner_result_mock(claims[:10])  # Limit to 10 claims
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            time.sleep(0.1)  # 100ms delay

            # Extract claim text from the query
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            evidence = evidence_map.get(claim_text, [])

            return MockDataFactory.create_runner_result_mock(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            time.sleep(0.1)  # 100ms delay

            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            verdict = next((v for v in verdicts if v.claim == claim_text), verdicts[0])

            return MockDataFactory.create_runner_result_mock(verdict)
        return MockDataFactory.create_runner_result_mock([])

    mock_run.side_effect = mock_runner_side_effect

    # Create managers with different max_claims settings
    configs = [
        ManagerConfig(max_claims=5, evidence_per_claim=3),
        ManagerConfig(max_claims=10, evidence_per_claim=3),
    ]

    reports = []
    for config in configs:
        manager = VerifactManager(config)

        # Benchmark the pipeline
        benchmark_results = await benchmark_pipeline(
            manager,
            ["Test text with many claims"],
            iterations=1,
        )

        reports.append(benchmark_results[0])

    # Verify that the second configuration processes more claims
    assert reports[1].claim_count >= reports[0].claim_count
    assert reports[1].evidence_count >= reports[0].evidence_count
    assert reports[1].verdict_count >= reports[0].verdict_count

    # But it should also take longer
    assert reports[1].total_duration_ms >= reports[0].total_duration_ms


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_optimization_suggestions(mock_run, manager):
    """Test to identify potential optimization opportunities."""
    # Create test data with varying processing times
    scenario = MockDataFactory.create_scenario("standard", claim_count=3)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]

    # Configure mock with varying delays to simulate bottlenecks
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]

        if agent.__dict__.get('name') == 'ClaimDetector':
            time.sleep(0.1)  # 100ms delay
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Simulate varying evidence gathering times
            query = args[1]
            claim_index = next((i for i, c in enumerate(claims) if c.text in query), 0)

            # Make the second claim take much longer
            if claim_index == 1:
                time.sleep(0.5)  # 500ms delay - bottleneck
            else:
                time.sleep(0.2)  # 200ms delay

            claim_text = claims[claim_index].text
            evidence = evidence_map.get(claim_text, [])

            return MockDataFactory.create_runner_result_mock(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            time.sleep(0.15)  # 150ms delay

            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            verdict = next((v for v in verdicts if v.claim == claim_text), verdicts[0])

            return MockDataFactory.create_runner_result_mock(verdict)
        return MockDataFactory.create_runner_result_mock([])

    mock_run.side_effect = mock_runner_side_effect

    # Benchmark the pipeline
    benchmark_results = await benchmark_pipeline(
        manager,
        ["Test text with claims"],
        iterations=1,
    )

    report = benchmark_results[0]

    # Verify that evidence gathering is the bottleneck
    assert report.evidence_gathering_ms > report.claim_detection_ms
    assert report.evidence_gathering_ms > report.verdict_generation_ms

    # Check individual evidence gathering times
    evidence_timings = [t.duration_ms for t in report.timings if t.operation == "evidence_gathering"]
    assert max(evidence_timings) > 2 * min(evidence_timings)  # The bottleneck is at least 2x slower

    # The bottleneck should be the second claim
    bottleneck_index = evidence_timings.index(max(evidence_timings))
    assert bottleneck_index == 1


@pytest.mark.asyncio
@patch("src.verifact_manager.Runner.run")
async def test_performance_target(mock_run):
    """Test that the pipeline meets the target performance of <30s end-to-end."""
    # Create test data with a realistic number of claims and evidence
    scenario = MockDataFactory.create_scenario("standard", claim_count=3, evidence_per_claim=5)
    claims = scenario["claims"]
    evidence_map = scenario["evidence_map"]
    verdicts = scenario["verdicts"]

    # Configure mock with realistic delays based on typical API response times
    def mock_runner_side_effect(*args, **kwargs):
        agent = args[0]

        if agent.__dict__.get('name') == 'ClaimDetector':
            # Claim detection typically takes 2-3 seconds
            time.sleep(2.5)
            return MockDataFactory.create_runner_result_mock(claims)
        elif agent.__dict__.get('name') == 'EvidenceHunter':
            # Evidence gathering typically takes 3-5 seconds per claim
            time.sleep(4.0)

            # Extract claim text from the query
            query = args[1]
            claim_text = next((c.text for c in claims if c.text in query), None)
            evidence = evidence_map.get(claim_text, [])

            return MockDataFactory.create_runner_result_mock(evidence)
        elif agent.__dict__.get('name') == 'VerdictWriter':
            # Verdict generation typically takes 2-4 seconds per claim
            time.sleep(3.0)

            # Extract claim text from the prompt
            prompt = args[1]
            claim_text = next((c.text for c in claims if c.text in prompt), None)
            verdict = next((v for v in verdicts if v.claim == claim_text), verdicts[0])

            return MockDataFactory.create_runner_result_mock(verdict)
        return MockDataFactory.create_runner_result_mock([])

    mock_run.side_effect = mock_runner_side_effect

    # Create a manager with default settings
    config = ManagerConfig(
        min_checkworthiness=0.5,
        max_claims=5,
        evidence_per_claim=5,
        timeout_seconds=30.0,
        enable_fallbacks=True,
        retry_attempts=1,
        raise_exceptions=True,
        include_debug_info=False,
    )
    manager = VerifactManager(config)

    # Benchmark the pipeline
    start_time = time.time()

    # Run the pipeline with a realistic input text
    results = await manager.run("""
    The United States has the largest military budget in the world.
    The Earth is flat and sits at the center of our solar system.
    Regular exercise reduces the risk of heart disease.
    """)

    end_time = time.time()
    total_duration_seconds = end_time - start_time

    # Verify results
    assert len(results) > 0

    # Verify that the pipeline completes in under 30 seconds
    assert total_duration_seconds < 30.0, f"Pipeline took {total_duration_seconds:.2f}s, which exceeds the 30s target"

    # Print the actual duration for reference
    print(f"Pipeline completed in {total_duration_seconds:.2f}s")

    # Verify that we processed all claims
    assert len(results) == len(claims)
