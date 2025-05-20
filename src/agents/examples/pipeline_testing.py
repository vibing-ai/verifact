"""
Example of testing the factchecking pipeline with the new agent architecture.

This script demonstrates how to test agents and the pipeline using mocks,
showing how the new architecture supports proper unit testing.
"""

import asyncio
import unittest
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

from src.agents.dto import Claim, Evidence, Verdict
from src.agents.interfaces import ClaimDetector, EvidenceHunter, VerdictWriter
from src.agents.orchestrator import FactcheckPipeline


class MockClaimDetector:
    """Mock implementation of ClaimDetector for testing."""

    def __init__(self, claims_to_return: List[Claim] = None):
        self.claims_to_return = claims_to_return or []
        self.detect_claims_called = False
        self.last_text = ""
        self.last_min_check_worthiness = None
        self.last_max_claims = None

    async def detect_claims(
        self,
        text: str,
        min_check_worthiness: Optional[float] = None,
        expected_claims: Optional[List[dict]] = None,
        max_claims: Optional[int] = None,
    ) -> List[Claim]:
        """Mock implementation of detect_claims."""
        self.detect_claims_called = True
        self.last_text = text
        self.last_min_check_worthiness = min_check_worthiness
        self.last_max_claims = max_claims
        return self.claims_to_return

    async def process(self, input_data: str) -> List[Claim]:
        """Mock implementation of process."""
        return await self.detect_claims(input_data)


class MockEvidenceHunter:
    """Mock implementation of EvidenceHunter for testing."""

    def __init__(self, evidence_to_return: List[Evidence] = None):
        self.evidence_to_return = evidence_to_return or []
        self.gather_evidence_called = False
        self.last_claim = None

    async def gather_evidence(self, claim: Claim) -> List[Evidence]:
        """Mock implementation of gather_evidence."""
        self.gather_evidence_called = True
        self.last_claim = claim
        return self.evidence_to_return

    async def process(self, input_data: Claim) -> List[Evidence]:
        """Mock implementation of process."""
        return await self.gather_evidence(input_data)


class MockVerdictWriter:
    """Mock implementation of VerdictWriter for testing."""

    def __init__(self, verdict_to_return: Verdict = None):
        self.verdict_to_return = verdict_to_return
        self.generate_verdict_called = False
        self.last_claim = None
        self.last_evidence = None

    async def generate_verdict(
        self,
        claim: Claim,
        evidence: List[Evidence],
        explanation_detail: Optional[str] = None,
        citation_style: Optional[str] = None,
        include_alternative_perspectives: Optional[bool] = None,
    ) -> Verdict:
        """Mock implementation of generate_verdict."""
        self.generate_verdict_called = True
        self.last_claim = claim
        self.last_evidence = evidence
        return self.verdict_to_return

    async def process(self, input_data: tuple[Claim, List[Evidence]]) -> Verdict:
        """Mock implementation of process."""
        claim, evidence = input_data
        return await self.generate_verdict(claim, evidence)


class PipelineTest(unittest.TestCase):
    """Tests for the factchecking pipeline using mocks."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample DTOs for testing
        self.sample_claim = Claim(
            text="The Earth is flat", original_text="The Earth is flat", check_worthiness=0.9
        )

        self.sample_evidence = [
            Evidence(
                content="The Earth is approximately spherical",
                source="https://nasa.gov/earth",
                relevance=0.95,
                stance="contradicting",
            ),
            Evidence(
                content="Satellite images show Earth's curvature",
                source="https://space.com/satellites",
                relevance=0.9,
                stance="contradicting",
            ),
        ]

        self.sample_verdict = Verdict(
            claim="The Earth is flat",
            verdict="false",
            confidence=0.95,
            explanation="The claim is false based on overwhelming scientific evidence",
            sources=["https://nasa.gov/earth", "https://space.com/satellites"],
        )

        # Create mock agents
        self.mock_claim_detector = MockClaimDetector(claims_to_return=[self.sample_claim])
        self.mock_evidence_hunter = MockEvidenceHunter(evidence_to_return=self.sample_evidence)
        self.mock_verdict_writer = MockVerdictWriter(verdict_to_return=self.sample_verdict)

        # Create pipeline with mock agents
        self.pipeline = FactcheckPipeline(
            claim_detector=self.mock_claim_detector,
            evidence_hunter=self.mock_evidence_hunter,
            verdict_writer=self.mock_verdict_writer,
            min_check_worthiness=0.5,
            max_claims=5,
        )

    async def async_test_full_pipeline(self):
        """Test the full pipeline with mocks."""
        # Process a text through the pipeline
        text = "The Earth is flat according to some conspiracy theorists."
        verdicts = await self.pipeline.process_text(text)

        # Assert the claim detector was called with the right arguments
        self.assertTrue(self.mock_claim_detector.detect_claims_called)
        self.assertEqual(self.mock_claim_detector.last_text, text)
        self.assertEqual(self.mock_claim_detector.last_min_check_worthiness, 0.5)
        self.assertEqual(self.mock_claim_detector.last_max_claims, 5)

        # Assert the evidence hunter was called with the right claim
        self.assertTrue(self.mock_evidence_hunter.gather_evidence_called)
        self.assertEqual(self.mock_evidence_hunter.last_claim, self.sample_claim)

        # Assert the verdict writer was called with the right claim and evidence
        self.assertTrue(self.mock_verdict_writer.generate_verdict_called)
        self.assertEqual(self.mock_verdict_writer.last_claim, self.sample_claim)
        self.assertEqual(self.mock_verdict_writer.last_evidence, self.sample_evidence)

        # Assert the result is as expected
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0], self.sample_verdict)

    def test_full_pipeline(self):
        """Run the async test."""
        asyncio.run(self.async_test_full_pipeline())

    async def async_test_empty_claims(self):
        """Test the pipeline when no claims are detected."""
        # Set up mock to return no claims
        empty_claim_detector = MockClaimDetector(claims_to_return=[])

        # Create pipeline with this mock
        pipeline = FactcheckPipeline(
            claim_detector=empty_claim_detector,
            evidence_hunter=self.mock_evidence_hunter,
            verdict_writer=self.mock_verdict_writer,
        )

        # Process text
        text = "This text contains no check-worthy claims."
        verdicts = await pipeline.process_text(text)

        # Assert claim detector was called but evidence hunter and verdict writer were not
        self.assertTrue(empty_claim_detector.detect_claims_called)
        self.assertFalse(self.mock_evidence_hunter.gather_evidence_called)
        self.assertFalse(self.mock_verdict_writer.generate_verdict_called)

        # Assert no verdicts were returned
        self.assertEqual(len(verdicts), 0)

    def test_empty_claims(self):
        """Run the async test for empty claims."""
        asyncio.run(self.async_test_empty_claims())

    async def async_test_empty_evidence(self):
        """Test the pipeline when no evidence is found for a claim."""
        # Set up mock to return no evidence
        empty_evidence_hunter = MockEvidenceHunter(evidence_to_return=[])

        # Create pipeline with this mock
        pipeline = FactcheckPipeline(
            claim_detector=self.mock_claim_detector,
            evidence_hunter=empty_evidence_hunter,
            verdict_writer=self.mock_verdict_writer,
        )

        # Process text
        text = "The Earth is flat."
        verdicts = await pipeline.process_text(text)

        # Assert claim detector and evidence hunter were called, but verdict writer was not
        self.assertTrue(self.mock_claim_detector.detect_claims_called)
        self.assertTrue(empty_evidence_hunter.gather_evidence_called)
        self.assertFalse(self.mock_verdict_writer.generate_verdict_called)

        # Assert no verdicts were returned since there was no evidence
        self.assertEqual(len(verdicts), 0)

    def test_empty_evidence(self):
        """Run the async test for empty evidence."""
        asyncio.run(self.async_test_empty_evidence())


# Example with unittest.mock
class PipelineTestWithUnitTestMock(unittest.TestCase):
    """
    Tests for the factchecking pipeline using unittest.mock.

    This demonstrates an alternative approach using standard Python mocking tools.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Create sample DTOs for testing
        self.sample_claim = Claim(
            text="Vaccines cause autism",
            original_text="Vaccines cause autism",
            check_worthiness=0.8,
        )

        self.sample_evidence = [
            Evidence(
                content="Scientific studies have consistently shown no link between vaccines and autism",
                source="https://cdc.gov/vaccines",
                relevance=0.95,
                stance="contradicting",
            )
        ]

        self.sample_verdict = Verdict(
            claim="Vaccines cause autism",
            verdict="false",
            confidence=0.98,
            explanation="The claim is false based on extensive scientific research",
            sources=["https://cdc.gov/vaccines"],
        )

        # Create mock agents using unittest.mock
        self.mock_claim_detector = MagicMock(spec=ClaimDetector)
        self.mock_evidence_hunter = MagicMock(spec=EvidenceHunter)
        self.mock_verdict_writer = MagicMock(spec=VerdictWriter)

        # Configure the mock behaviors
        self.mock_claim_detector.detect_claims = AsyncMock(return_value=[self.sample_claim])
        self.mock_claim_detector.process = AsyncMock(return_value=[self.sample_claim])

        self.mock_evidence_hunter.gather_evidence = AsyncMock(return_value=self.sample_evidence)
        self.mock_evidence_hunter.process = AsyncMock(return_value=self.sample_evidence)

        self.mock_verdict_writer.generate_verdict = AsyncMock(return_value=self.sample_verdict)
        self.mock_verdict_writer.process = AsyncMock(return_value=self.sample_verdict)

        # Create pipeline with mock agents
        self.pipeline = FactcheckPipeline(
            claim_detector=self.mock_claim_detector,
            evidence_hunter=self.mock_evidence_hunter,
            verdict_writer=self.mock_verdict_writer,
        )

    async def async_test_pipeline_with_unittest_mock(self):
        """Test the pipeline using unittest.mock."""
        # Process a text through the pipeline
        text = "Vaccines cause autism according to some conspiracy theories."
        verdicts = await self.pipeline.process_text(text)

        # Assert the claim detector was called with the right arguments
        self.mock_claim_detector.detect_claims.assert_called_once()
        call_args = self.mock_claim_detector.detect_claims.call_args[0]
        self.assertEqual(call_args[0], text)

        # Assert the evidence hunter was called with the right claim
        self.mock_evidence_hunter.gather_evidence.assert_called_once_with(self.sample_claim)

        # Assert the verdict writer was called with the right claim and evidence
        self.mock_verdict_writer.generate_verdict.assert_called_once()
        writer_call_args = self.mock_verdict_writer.generate_verdict.call_args[0]
        self.assertEqual(writer_call_args[0], self.sample_claim)
        self.assertEqual(writer_call_args[1], self.sample_evidence)

        # Assert the result is as expected
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0], self.sample_verdict)

    def test_pipeline_with_unittest_mock(self):
        """Run the async test with unittest.mock."""
        asyncio.run(self.async_test_pipeline_with_unittest_mock())


if __name__ == "__main__":
    unittest.main()
