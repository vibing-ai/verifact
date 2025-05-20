"""Integration tests for the VeriFact factchecking pipeline.

These tests verify that the entire pipeline functions correctly from claim detection
through evidence gathering to verdict generation, and that all components work together seamlessly.

Combines both unit tests and standalone testing script functionality.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.claim_detector import ClaimDetector
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.verdict_writer import VerdictWriter
from src.pipeline.factcheck_pipeline import PipelineConfig


class TestPipelineIntegration:
    """Integration tests for the factchecking pipeline."""

    @pytest.fixture
    def patched_pipeline(
        self, mock_claim_detector, mock_evidence_hunter, mock_verdict_writer, mock_pipeline_config
    ):
        """Return a pipeline with patched components for testing."""
        with (
            patch(
                "src.pipeline.factcheck_pipeline.ClaimDetector", return_value=mock_claim_detector
            ),
            patch(
                "src.pipeline.factcheck_pipeline.EvidenceHunter", return_value=mock_evidence_hunter
            ),
            patch(
                "src.pipeline.factcheck_pipeline.VerdictWriter", return_value=mock_verdict_writer
            ),
        ):
            # Create the pipeline with default components
            from src.pipeline import FactcheckPipeline

            pipeline = FactcheckPipeline(
                claim_detector=mock_claim_detector,
                evidence_hunter=mock_evidence_hunter,
                verdict_writer=mock_verdict_writer,
                config=PipelineConfig(**mock_pipeline_config),
            )
            # Force initialization of components
            pipeline._claim_detector = mock_claim_detector
            pipeline._evidence_hunter = mock_evidence_hunter
            pipeline._verdict_writer = mock_verdict_writer

            yield pipeline

    @pytest.mark.asyncio
    async def test_full_pipeline_true_claim(self, patched_pipeline, true_claim_text):
        """Test the full pipeline with a definitively true claim."""
        # Process the text through the pipeline
        results = await patched_pipeline.process_text(true_claim_text)

        # Verify results
        assert results, "Pipeline should return results"
        assert len(results) == 1, "Pipeline should detect one claim"

        verdict = results[0]
        assert verdict["verdict"] == "TRUE", "Verdict should be TRUE"
        assert verdict["confidence"] >= 0.9, "Confidence should be high for a true claim"
        assert "Earth orbits" in verdict["claim"]["text"], "Claim text should be preserved"

        # Verify each component was called correctly
        patched_pipeline.claim_detector.detect_claims.assert_called_once_with(true_claim_text)
        patched_pipeline.evidence_hunter.gather_evidence.assert_called_once()
        patched_pipeline.verdict_writer.generate_verdict.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_pipeline_false_claim(self, patched_pipeline, false_claim_text):
        """Test the full pipeline with a definitively false claim."""
        # Process the text through the pipeline
        results = await patched_pipeline.process_text(false_claim_text)

        # Verify results
        assert results, "Pipeline should return results"
        assert len(results) == 1, "Pipeline should detect one claim"

        verdict = results[0]
        assert verdict["verdict"] == "FALSE", "Verdict should be FALSE"
        assert verdict["confidence"] >= 0.9, "Confidence should be high for a false claim"
        assert "Sun orbits" in verdict["claim"]["text"], "Claim text should be preserved"

        # Verify each component was called correctly
        patched_pipeline.claim_detector.detect_claims.assert_called_once_with(false_claim_text)
        patched_pipeline.evidence_hunter.gather_evidence.assert_called_once()
        patched_pipeline.verdict_writer.generate_verdict.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_pipeline_partially_true_claim(
        self, patched_pipeline, partially_true_claim_text
    ):
        """Test the full pipeline with a partially true claim."""
        # Process the text through the pipeline
        results = await patched_pipeline.process_text(partially_true_claim_text)

        # Verify results
        assert results, "Pipeline should return results"
        assert len(results) == 1, "Pipeline should detect one claim"

        verdict = results[0]
        assert verdict["verdict"] == "PARTLY_TRUE", "Verdict should be PARTLY_TRUE"
        assert "COVID-19 vaccines" in verdict["claim"]["text"], "Claim text should be preserved"

        # Verify each component was called correctly
        patched_pipeline.claim_detector.detect_claims.assert_called_once_with(
            partially_true_claim_text
        )
        patched_pipeline.evidence_hunter.gather_evidence.assert_called_once()
        patched_pipeline.verdict_writer.generate_verdict.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_pipeline_unverifiable_claim(
        self, patched_pipeline, unverifiable_claim_text
    ):
        """Test the full pipeline with an unverifiable claim."""
        # Process the text through the pipeline
        results = await patched_pipeline.process_text(unverifiable_claim_text)

        # Verify results
        assert results, "Pipeline should return results"
        assert len(results) == 1, "Pipeline should detect one claim"

        verdict = results[0]
        assert verdict["verdict"] == "UNVERIFIABLE", "Verdict should be UNVERIFIABLE"
        assert "alien civilizations" in verdict["claim"]["text"], "Claim text should be preserved"

        # Verify each component was called correctly
        patched_pipeline.claim_detector.detect_claims.assert_called_once_with(
            unverifiable_claim_text
        )
        patched_pipeline.evidence_hunter.gather_evidence.assert_called_once()
        patched_pipeline.verdict_writer.generate_verdict.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_pipeline_multiple_claims(self, patched_pipeline, mixed_claims_text):
        """Test the full pipeline with multiple claims of varying truth values."""
        # Process the text through the pipeline
        results = await patched_pipeline.process_text(mixed_claims_text)

        # Verify results
        assert results, "Pipeline should return results"
        assert len(results) == 5, "Pipeline should detect five claims"

        # Map of expected verdicts by claim content
        expected_verdicts = {
            "COVID-19 pandemic began": "TRUE",
            "created in a lab": "UNCERTAIN",
            "Vaccines have been shown": "TRUE",
            "New York City is the capital": "FALSE",
            "Climate change": "TRUE",
        }

        # Check each verdict matches expectations
        for verdict in results:
            claim_text = verdict["claim"]["text"]
            for key, expected_verdict in expected_verdicts.items():
                if key in claim_text:
                    assert verdict["verdict"] == expected_verdict, (
                        f"Verdict for '{claim_text}' should be {expected_verdict}"
                    )

        # Verify each component was called correctly
        patched_pipeline.claim_detector.detect_claims.assert_called_once_with(mixed_claims_text)
        assert patched_pipeline.evidence_hunter.gather_evidence.call_count == 5, (
            "EvidenceHunter should be called for each claim"
        )
        assert patched_pipeline.verdict_writer.generate_verdict.call_count == 5, (
            "VerdictWriter should be called for each claim"
        )

    @pytest.mark.asyncio
    async def test_pipeline_no_claims(self, patched_pipeline):
        """Test pipeline behavior when no claims are detected."""
        # Mock the claim detector to return no claims
        patched_pipeline.claim_detector.detect_claims.return_value = []

        # Process a text with no claims
        results = await patched_pipeline.process_text(
            "This is a text with no factual claims, just opinions and descriptions."
        )

        # Verify results
        assert results == [], "Pipeline should return empty list when no claims are detected"

        # Verify ClaimDetector was called but not the other components
        patched_pipeline.claim_detector.detect_claims.assert_called_once()
        patched_pipeline.evidence_hunter.gather_evidence.assert_not_called()
        patched_pipeline.verdict_writer.generate_verdict.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_no_evidence(self, patched_pipeline, true_claim_text):
        """Test pipeline behavior when no evidence is found."""
        # Mock the evidence hunter to return no evidence
        patched_pipeline.evidence_hunter.gather_evidence.return_value = []

        # Process the text through the pipeline
        results = await patched_pipeline.process_text(true_claim_text)

        # Verify results
        assert results, "Pipeline should return results even with no evidence"
        assert len(results) == 1, "Pipeline should detect one claim"

        verdict = results[0]
        assert verdict["verdict"] == "UNCERTAIN", (
            "Verdict should be UNCERTAIN when no evidence is found"
        )
        assert "Earth orbits" in verdict["claim"]["text"], "Claim text should be preserved"

        # Verify each component was called correctly
        patched_pipeline.claim_detector.detect_claims.assert_called_once()
        patched_pipeline.evidence_hunter.gather_evidence.assert_called_once()
        patched_pipeline.verdict_writer.generate_verdict.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_streaming(self, patched_pipeline, mixed_claims_text):
        """Test the streaming interface of the pipeline."""
        # Process the text through the streaming pipeline
        verdicts = []
        async for verdict in patched_pipeline.process_text_streaming(mixed_claims_text):
            verdicts.append(verdict)

        # Verify results
        assert len(verdicts) == 5, "Streaming should yield five verdicts"

        # Verify expected claims are present
        claim_texts = [v["claim"]["text"] for v in verdicts]
        expected_snippets = [
            "COVID-19 pandemic",
            "created in a lab",
            "Vaccines",
            "New York City",
            "Climate change",
        ]

        for snippet in expected_snippets:
            assert any(snippet in text for text in claim_texts), (
                f"Expected to find a claim containing '{snippet}'"
            )

    def test_pipeline_sync(self, patched_pipeline, true_claim_text):
        """Test the synchronous interface of the pipeline."""
        # Process the text through the synchronous pipeline
        results = patched_pipeline.process_text_sync(true_claim_text)

        # Verify results
        assert results, "Pipeline should return results"
        assert len(results) == 1, "Pipeline should detect one claim"

        verdict = results[0]
        assert verdict["verdict"] == "TRUE", "Verdict should be TRUE"
        assert "Earth orbits" in verdict["claim"]["text"], "Claim text should be preserved"

    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self, patched_pipeline, true_claim_text):
        """Test pipeline error recovery when a component fails."""
        # Make the evidence hunter fail on first call, then succeed
        fail_once_hunter = MagicMock()
        call_count = 0

        def fail_once(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated failure")
            return [
                {
                    "text": "Evidence text",
                    "source": "https://example.com",
                    "credibility": 0.9,
                    "stance": "supporting",
                }
            ]

        fail_once_hunter.gather_evidence.side_effect = fail_once

        # Replace the evidence hunter
        patched_pipeline._evidence_hunter = fail_once_hunter

        # Process the text through the pipeline
        results = await patched_pipeline.process_text(true_claim_text)

        # Verify results
        assert results, "Pipeline should return results despite temporary failure"
        assert len(results) == 1, "Pipeline should detect one claim"

        # Verify evidence hunter was called twice (first fails, second succeeds)
        assert call_count == 2, "Evidence hunter should be called twice due to retry"

    @pytest.mark.asyncio
    async def test_pipeline_performance(self, patched_pipeline, mixed_claims_text):
        """Test pipeline performance and measure processing time."""
        # Add timing to components to simulate realistic processing delays
        original_detect = patched_pipeline.claim_detector.detect_claims
        original_gather = patched_pipeline.evidence_hunter.gather_evidence
        original_generate = patched_pipeline.verdict_writer.generate_verdict

        async def timed_detect(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate 100ms processing time
            return original_detect(*args, **kwargs)

        async def timed_gather(*args, **kwargs):
            await asyncio.sleep(0.2)  # Simulate 200ms processing time
            return original_gather(*args, **kwargs)

        async def timed_generate(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate 100ms processing time
            return original_generate(*args, **kwargs)

        patched_pipeline.claim_detector.detect_claims = timed_detect
        patched_pipeline.evidence_hunter.gather_evidence = timed_gather
        patched_pipeline.verdict_writer.generate_verdict = timed_generate

        # Measure total processing time
        start_time = time.time()
        results = await patched_pipeline.process_text(mixed_claims_text)
        end_time = time.time()

        processing_time = end_time - start_time

        # Verify results
        assert results, "Pipeline should return results"
        assert len(results) == 5, "Pipeline should detect five claims"

        # Verify processing time is reasonable
        # In a real implementation, we'd set an actual threshold based on requirements
        # For now, we'll just log the time and assert it's under 30 seconds as per requirements
        assert processing_time < 30.0, (
            f"Processing time ({processing_time:.2f}s) exceeds 30s threshold"
        )

        # We'd also assert the pipeline stats have reasonable values
        assert patched_pipeline.stats["claim_detection_time"] is not None
        assert patched_pipeline.stats["evidence_gathering_time"] is not None
        assert patched_pipeline.stats["verdict_generation_time"] is not None
        assert patched_pipeline.stats["total_processing_time"] is not None

    @pytest.mark.asyncio
    async def test_pipeline_with_real_components(
        self, mock_openai_client, mock_web_search, env_setup
    ):
        """Test the pipeline with actual component implementations (not mocks)."""
        with (
            patch("src.agents.claim_detector.openai.OpenAI", return_value=mock_openai_client),
            patch("src.agents.evidence_hunter.search.web_search", mock_web_search),
            patch("src.agents.verdict_writer.openai.OpenAI", return_value=mock_openai_client),
        ):
            # Create a pipeline with real components
            from src.pipeline.factcheck_pipeline import create_default_pipeline

            pipeline = create_default_pipeline()

            # Configure the mock OpenAI client to return appropriate responses for each agent
            responses = {
                "claim_detection": """
                [
                    {"text": "The Earth orbits around the Sun.", "context": "The text discusses basic astronomy facts.", "checkworthy": true}
                ]
                """,
                "evidence_gathering": """
                [
                    {"text": "The Earth orbits the Sun at an average distance of about 93 million miles.", "source": "https://example.com/earth", "credibility": 0.95, "stance": "supporting"},
                    {"text": "The Earth completes one orbit around the Sun every 365.25 days.", "source": "https://example.org/orbit", "credibility": 0.92, "stance": "supporting"}
                ]
                """,
                "verdict_generation": """
                {
                    "verdict": "TRUE",
                    "confidence": 0.95,
                    "explanation": "This claim is definitively true. Multiple reliable sources confirm that the Earth orbits around the Sun.",
                    "evidence_summary": "Strong scientific consensus supports this claim."
                }
                """,
            }

            def mock_completion(**kwargs):
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]

                # Determine which component is calling based on the prompt
                prompt = kwargs.get("messages", [{}])[0].get("content", "")

                if "identify factual claims" in prompt:
                    mock_response.choices[0].message.content = responses["claim_detection"]
                elif "gather evidence" in prompt:
                    mock_response.choices[0].message.content = responses["evidence_gathering"]
                elif "analyze the evidence" in prompt:
                    mock_response.choices[0].message.content = responses["verdict_generation"]
                else:
                    mock_response.choices[0].message.content = "{}"

                return mock_response

            mock_openai_client.chat.completions.create.side_effect = mock_completion

            # Process a simple text
            test_text = "The Earth orbits around the Sun."
            results = await pipeline.process_text(test_text)

            # Verify results
            assert results, "Pipeline should return results"
            assert len(results) == 1, "Pipeline should detect one claim"

            verdict = results[0]
            assert verdict["verdict"] == "TRUE", "Verdict should be TRUE"
            assert verdict["confidence"] >= 0.9, "Confidence should be high for a true claim"

    def test_data_flow_integrity(self, patched_pipeline, true_claim_text):
        """Test that data flows correctly between pipeline components with proper transformations."""
        # Process a text synchronously
        patched_pipeline.process_text_sync(true_claim_text)

        # Extract the arguments passed between components
        claim_detector_output = patched_pipeline.claim_detector.detect_claims.return_value
        evidence_hunter_input = patched_pipeline.evidence_hunter.gather_evidence.call_args[0][0]

        evidence_hunter_output = patched_pipeline.evidence_hunter.gather_evidence.return_value
        verdict_writer_input_claim = patched_pipeline.verdict_writer.generate_verdict.call_args[0][
            0
        ]
        verdict_writer_input_evidence = patched_pipeline.verdict_writer.generate_verdict.call_args[
            0
        ][1]

        # Verify data integrity
        assert evidence_hunter_input == claim_detector_output[0], (
            "Claim passed to EvidenceHunter should match ClaimDetector output"
        )
        assert verdict_writer_input_claim == claim_detector_output[0], (
            "Claim passed to VerdictWriter should match ClaimDetector output"
        )
        assert verdict_writer_input_evidence == evidence_hunter_output, (
            "Evidence passed to VerdictWriter should match EvidenceHunter output"
        )

    @pytest.mark.asyncio
    async def test_pipeline_configuration(
        self, mock_claim_detector, mock_evidence_hunter, mock_verdict_writer
    ):
        """Test that pipeline configuration options properly affect the pipeline behavior."""
        with (
            patch(
                "src.pipeline.factcheck_pipeline.ClaimDetector", return_value=mock_claim_detector
            ),
            patch(
                "src.pipeline.factcheck_pipeline.EvidenceHunter", return_value=mock_evidence_hunter
            ),
            patch(
                "src.pipeline.factcheck_pipeline.VerdictWriter", return_value=mock_verdict_writer
            ),
        ):
            # Create pipeline with custom configuration
            custom_config = PipelineConfig(
                max_claims=2,  # Only process top 2 claims
                evidence_per_claim=1,  # Only gather 1 piece of evidence per claim
                timeout_seconds=10.0,  # Short timeout
            )

            # Create pipeline with default agents
            from src.pipeline.factcheck_pipeline import create_default_pipeline

            pipeline = create_default_pipeline(config=custom_config)
            pipeline._claim_detector = mock_claim_detector
            pipeline._evidence_hunter = mock_evidence_hunter
            pipeline._verdict_writer = mock_verdict_writer

            # Process text with multiple claims but config limits to 2
            await pipeline.process_text("Sample text with multiple claims")

            # Check that configuration was respected
            # Verify EvidenceHunter was called with the right parameters
            assert (
                mock_evidence_hunter.gather_evidence.call_args[1].get("max_results", None) == 1
            ), "EvidenceHunter should be configured to gather only 1 piece of evidence"


# Standalone test function merged from root test_pipeline_integration.py
@pytest.mark.skip("Manual standalone test script - run directly if needed")
async def test_pipeline_integration_standalone():
    """Test the complete factchecking pipeline (standalone version)."""
    print("\n=== Testing Complete Factchecking Pipeline ===\n")

    # Initialize the components
    print("Initializing agents...")
    detector = ClaimDetector()
    hunter = EvidenceHunter()
    writer = VerdictWriter()

    # Test with different inputs
    test_inputs = [
        {
            "name": "Basic factual statements",
            "text": "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface.",
        },
        {
            "name": "Historical and political claims",
            "text": "World War II ended in 1945. The United States has had 46 presidents. The Great Wall of China is visible from space.",
        },
        {
            "name": "Current events and mixed accuracy",
            "text": "Climate change is causing rising sea levels. COVID-19 vaccines contain microchips for tracking people. Renewable energy sources are becoming cheaper than fossil fuels.",
        },
    ]

    # Process each test input
    results = []

    for test in test_inputs:
        print(f"\n\nTesting: {test['name']}")
        print(f'Text: "{test["text"]}"')

        test_result = {
            "name": test["name"],
            "text": test["text"],
            "timestamp": datetime.now().isoformat(),
            "steps": {},
            "claims": [],
        }

        total_start_time = time.time()

        try:
            # Step 1: Detect claims
            print("\nStep 1: Detecting claims...")
            step1_start = time.time()
            claims = await detector.detect_claims(test["text"])
            step1_duration = time.time() - step1_start

            test_result["steps"]["claim_detection"] = {
                "duration": step1_duration,
                "claims_found": len(claims),
            }

            print(f"Found {len(claims)} claims in {step1_duration:.2f} seconds")

            # Process each checkworthy claim
            checkworthy_claims = [claim for claim in claims if claim.checkworthy]
            print(f"Processing {len(checkworthy_claims)} checkworthy claims")

            for i, claim in enumerate(checkworthy_claims):
                claim_result = {"claim_text": claim.text, "evidence": [], "steps": {}}

                print(f"\nProcessing claim {i + 1}: {claim.text}")

                # Step 2: Gather evidence
                print("Step 2: Gathering evidence...")
                step2_start = time.time()
                evidence = await hunter.gather_evidence(claim)
                step2_duration = time.time() - step2_start

                claim_result["steps"]["evidence_gathering"] = {
                    "duration": step2_duration,
                    "evidence_found": len(evidence),
                }

                print(f"Found {len(evidence)} pieces of evidence in {step2_duration:.2f} seconds")

                # Add evidence details
                for e in evidence:
                    claim_result["evidence"].append(
                        {
                            "content": e.content[:200] + ("..." if len(e.content) > 200 else ""),
                            "source": e.source,
                            "relevance": e.relevance,
                            "stance": e.stance,
                        }
                    )

                # Step 3: Generate verdict
                print("Step 3: Generating verdict...")
                step3_start = time.time()
                verdict = await writer.generate_verdict(claim, evidence)
                step3_duration = time.time() - step3_start

                claim_result["steps"]["verdict_generation"] = {"duration": step3_duration}

                claim_result["verdict"] = {
                    "judgment": verdict.verdict,
                    "confidence": verdict.confidence,
                    "explanation": verdict.explanation[:300]
                    + ("..." if len(verdict.explanation) > 300 else ""),
                    "sources": verdict.sources,
                }

                print(f"Generated verdict in {step3_duration:.2f} seconds:")
                print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence})")

                # Add this claim's results to the test results
                test_result["claims"].append(claim_result)

            total_duration = time.time() - total_start_time
            test_result["total_duration"] = total_duration

            print(f"\nTotal processing time for this test: {total_duration:.2f} seconds")

            # Check for performance targets
            if total_duration > 30 and len(checkworthy_claims) == 1:
                print("⚠️ Warning: Processing time exceeds 30 second target for a single claim")

        except Exception as e:
            print(f"Error in pipeline: {e}")
            test_result["error"] = str(e)

        # Add this test's results to overall results
        results.append(test_result)

    # Save the results
    save_results(results)

    print("\n=== Pipeline Integration Test Complete ===")


def save_results(results):
    """Save test results to a file."""
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"pipeline_test_{timestamp}.json"

    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nTest results saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(test_pipeline_integration_standalone())
