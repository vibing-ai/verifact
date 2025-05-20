"""Integration tests for the complete factchecking pipeline.

These tests verify the entire pipeline from claim detection to verdict generation.
"""

import os
import time

import pytest

from src.agents.verdict_writer.writer import Verdict
from src.pipeline.factcheck_pipeline import (
    FactcheckPipeline,
    PipelineConfig,
    PipelineEvent,
)

# Skip all tests in this module if the integration tests are not enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("ENABLE_INTEGRATION_TESTS") != "true",
    reason="Integration tests are not enabled. Set ENABLE_INTEGRATION_TESTS=true to run.",
)


@pytest.fixture
def pipeline():
    """Fixture for creating a pipeline instance."""
    config = PipelineConfig(
        min_checkworthiness=0.5,
        max_claims=3,
        evidence_per_claim=3,
        timeout_seconds=60.0,
        enable_fallbacks=True,
        retry_attempts=1,
        include_debug_info=True,
    )
    from src.pipeline.factcheck_pipeline import create_default_pipeline

    return create_default_pipeline(config=config)


@pytest.fixture
def event_collector():
    """Fixture for collecting pipeline events."""
    events = []

    def collect_event(event_type, data):
        events.append((event_type, data))

    return events, collect_event


@pytest.mark.asyncio
async def test_pipeline_e2e_simple_claim(pipeline, event_collector):
    """Test end-to-end pipeline processing for a simple, factual claim."""
    # Get event collector
    events, collect_event = event_collector

    # Register event handlers
    for event in PipelineEvent:
        pipeline.register_event_handler(event, collect_event)

    # Input text with a clear factual claim
    input_text = "The Earth orbits around the Sun."

    # Process the text
    verdicts = await pipeline.process_text(input_text)

    # Verify we got at least one verdict
    assert len(verdicts) > 0

    # Verify the structure of the verdict
    verdict = verdicts[0]
    assert isinstance(verdict, Verdict)
    assert verdict.verdict == "true"
    assert verdict.confidence > 0.8
    assert verdict.explanation, "Explanation should not be empty"
    assert verdict.sources, "Sources should not be empty"

    # Verify we received events for all pipeline stages
    event_types = [e[0] for e in events]
    assert PipelineEvent.STARTED in event_types
    assert PipelineEvent.CLAIM_DETECTED in event_types
    assert PipelineEvent.EVIDENCE_GATHERED in event_types
    assert PipelineEvent.VERDICT_GENERATED in event_types
    assert PipelineEvent.COMPLETED in event_types

    # Verify pipeline stats
    assert pipeline.stats["claims_detected"] > 0
    assert pipeline.stats["evidence_gathered"] > 0
    assert pipeline.stats["verdicts_generated"] > 0
    assert pipeline.stats["total_processing_time"] is not None


@pytest.mark.asyncio
async def test_pipeline_e2e_multiple_claims(pipeline):
    """Test end-to-end pipeline processing for text with multiple claims."""
    # Input text with multiple factual claims
    input_text = """
    There are several interesting facts about our solar system:
    1. The Earth is the third planet from the Sun.
    2. Mars has two moons, Phobos and Deimos.
    3. Jupiter is the largest planet in our solar system.
    4. Venus is the hottest planet in our solar system, despite not being the closest to the Sun.
    """

    # Process the text
    verdicts = await pipeline.process_text(input_text)

    # Verify we got multiple verdicts (up to the max_claims in config)
    assert 1 <= len(verdicts) <= pipeline.config.max_claims

    # Verify each verdict
    for verdict in verdicts:
        assert isinstance(verdict, Verdict)
        assert verdict.verdict in ["true", "false", "partially true", "unverifiable"]
        assert 0 <= verdict.confidence <= 1
        assert verdict.explanation, "Explanation should not be empty"
        assert verdict.sources, "Sources should not be empty"


@pytest.mark.asyncio
async def test_pipeline_e2e_controversial_claim(pipeline):
    """Test end-to-end pipeline processing for a controversial claim."""
    # Input text with a controversial claim
    input_text = "The COVID-19 vaccine is completely safe with no side effects."

    # Process the text
    verdicts = await pipeline.process_text(input_text)

    # Verify we got a verdict
    assert len(verdicts) > 0

    # For controversial claims, the verdict should be nuanced
    verdict = verdicts[0]
    assert verdict.verdict in ["partially true", "unverifiable"]  # It's not simply true or false

    # Should include alternative perspectives
    assert verdict.alternative_perspectives is not None, (
        "Should include alternative perspectives for controversial claims"
    )


@pytest.mark.asyncio
async def test_pipeline_performance_benchmarks(pipeline):
    """Test performance benchmarks for the pipeline."""
    # Input text with a simple claim
    input_text = "The Moon orbits the Earth."

    # Process the text and measure time
    start_time = time.time()
    verdicts = await pipeline.process_text(input_text)
    end_time = time.time()

    # Calculate total processing time
    total_time = end_time - start_time

    # Verify we got a verdict
    assert len(verdicts) > 0

    # Verify stage processing times are tracked
    assert pipeline.stats["claim_detection_time"] is not None
    assert pipeline.stats["evidence_gathering_time"] is not None
    assert pipeline.stats["verdict_generation_time"] is not None

    # Verify total processing time meets target (adjust based on realistic expectations)
    # For a simple claim, entire pipeline should complete in under 30 seconds
    assert total_time < 30, f"Pipeline took {total_time:.2f} seconds, which exceeds the target"

    # Log performance metrics
    print(f"Claim detection: {pipeline.stats['claim_detection_time']:.2f}s")
    print(f"Evidence gathering: {pipeline.stats['evidence_gathering_time']:.2f}s")
    print(f"Verdict generation: {pipeline.stats['verdict_generation_time']:.2f}s")
    print(f"Total pipeline time: {total_time:.2f}s")


@pytest.mark.asyncio
async def test_pipeline_error_recovery(pipeline):
    """Test pipeline error recovery and retry mechanisms."""
    # Create a minimal config with retry attempts
    config = PipelineConfig(
        min_checkworthiness=0.5,
        max_claims=1,
        retry_attempts=2,
        enable_fallbacks=True,
    )
    from src.pipeline.factcheck_pipeline import create_default_pipeline

    pipeline_with_retries = create_default_pipeline(config=config)

    # Patch the _gather_evidence method to fail once then succeed
    original_gather_evidence = pipeline_with_retries._gather_evidence

    # Counter to track call attempts
    call_count = {"count": 0}

    async def mock_gather_evidence(claim):
        call_count["count"] += 1
        if call_count["count"] == 1:  # First call fails
            raise Exception("Simulated API error")
        else:  # Subsequent calls succeed
            return await original_gather_evidence(claim)

    # Replace the method with our mock
    pipeline_with_retries._gather_evidence = mock_gather_evidence

    # Input text with a simple claim
    input_text = "The Earth orbits around the Sun."

    # Process the text and expect successful retry
    verdicts = await pipeline_with_retries.process_text(input_text)

    # Verify we got a verdict
    assert len(verdicts) > 0

    # Verify the method was called more than once (i.e., retry happened)
    assert call_count["count"] > 1

    # Clean up
    pipeline_with_retries._gather_evidence = original_gather_evidence


@pytest.mark.asyncio
async def test_pipeline_streaming(pipeline):
    """Test pipeline in streaming mode."""
    # Input text with multiple claims
    input_text = """
    The Earth is the third planet from the Sun. Mars has two moons.
    Jupiter is the largest planet in our solar system.
    """

    # Create a list to collect results from the stream
    stream_results = []

    # Process the text in streaming mode
    async for event_type, data in pipeline.process_text_streaming(input_text):
        stream_results.append((event_type, data))

    # Verify we received key events
    event_types = [e[0] for e in stream_results]
    assert PipelineEvent.STARTED in event_types
    assert PipelineEvent.CLAIM_DETECTED in event_types
    assert PipelineEvent.EVIDENCE_GATHERED in event_types
    assert PipelineEvent.VERDICT_GENERATED in event_types
    assert PipelineEvent.COMPLETED in event_types

    # Extract verdicts from the completed event
    verdicts = next(
        data for event_type, data in stream_results if event_type == PipelineEvent.COMPLETED
    )["verdicts"]

    # Verify we have verdicts
    assert len(verdicts) > 0


@pytest.mark.asyncio
async def test_pipeline_model_fallbacks(pipeline):
    """Test pipeline model fallback mechanisms."""
    # Create a config with fallbacks enabled
    config = PipelineConfig(
        min_checkworthiness=0.5,
        max_claims=2,
        enable_fallbacks=True,
    )
    pipeline_with_fallbacks = FactcheckPipeline(config=config)

    # Mock the primary model to fail and force fallback
    original_call_model = pipeline_with_fallbacks._call_model

    call_count = {"primary": 0, "fallback": 0}

    async def mock_call_model(model_name, messages, *args, **kwargs):
        if "primary" in model_name:
            call_count["primary"] += 1
            # Primary model fails after first call
            if call_count["primary"] > 1:
                raise Exception("Simulated API error in primary model")
        else:
            call_count["fallback"] += 1

        # Call the original method (which will use the fallback model after failure)
        return await original_call_model(model_name, messages, *args, **kwargs)

    # Replace the method with our mock
    pipeline_with_fallbacks._call_model = mock_call_model

    # Input text with a simple claim
    input_text = "The Moon orbits the Earth. Mars has two moons."

    # Process the text (should trigger fallback)
    verdicts = await pipeline_with_fallbacks.process_text(input_text)

    # Verify we got verdicts
    assert len(verdicts) > 0

    # Verify both primary and fallback models were used
    assert call_count["primary"] > 0
    assert call_count["fallback"] > 0

    # Clean up
    pipeline_with_fallbacks._call_model = original_call_model


@pytest.mark.asyncio
async def test_pipeline_sync_interface(pipeline):
    """Test the synchronous interface of the pipeline."""
    # Input text with a simple claim
    input_text = "The Earth orbits around the Sun."

    # Use the synchronous interface
    verdicts = pipeline.process_text_sync(input_text)

    # Verify we got verdicts
    assert len(verdicts) > 0

    # Verify the structure of the verdict
    verdict = verdicts[0]
    assert isinstance(verdict, Verdict)
    assert verdict.claim, "Claim should not be empty"
    assert verdict.verdict in ["true", "false", "partially true", "unverifiable"]
    assert 0 <= verdict.confidence <= 1
    assert verdict.explanation, "Explanation should not be empty"
    assert verdict.sources, "Sources should not be empty"
