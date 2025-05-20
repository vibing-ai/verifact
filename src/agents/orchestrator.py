"""
Orchestrator for the factchecking pipeline.

This module defines the orchestrator for coordinating the workflow between the
different agents in the factchecking pipeline, with explicit dependency injection
and clear error boundaries.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from src.agents.dto import Claim, Evidence, Verdict
from src.agents.factory import AgentFactory
from src.agents.interfaces import ClaimDetector, EvidenceHunter, VerdictWriter
from src.utils.logger import get_component_logger

# Create logger for the orchestrator
logger = get_component_logger("factcheck_pipeline")


class FactcheckPipeline:
    """
    Orchestrates the factchecking workflow.
    
    This class coordinates the flow between different agents in the factchecking
    pipeline, ensuring proper separation of concerns and clear error boundaries.
    Each agent is injected as a dependency, making the pipeline testable and
    maintainable.
    """
    
    def __init__(
        self,
        claim_detector: ClaimDetector,
        evidence_hunter: EvidenceHunter,
        verdict_writer: VerdictWriter,
        parallelism: int = 5,
        min_check_worthiness: float = 0.5,
        max_claims: int = 10
    ):
        """
        Initialize the factchecking pipeline with explicit dependencies.
        
        Args:
            claim_detector: Agent for detecting claims in text
            evidence_hunter: Agent for gathering evidence for claims
            verdict_writer: Agent for generating verdicts based on evidence
            parallelism: Maximum number of concurrent evidence gathering tasks
            min_check_worthiness: Minimum threshold for claim check-worthiness
            max_claims: Maximum number of claims to process
        """
        self.claim_detector = claim_detector
        self.evidence_hunter = evidence_hunter
        self.verdict_writer = verdict_writer
        self.parallelism = parallelism
        self.min_check_worthiness = min_check_worthiness
        self.max_claims = max_claims
        
        logger.info("FactcheckPipeline initialized with min_check_worthiness=%f, max_claims=%d",
                   self.min_check_worthiness, self.max_claims)
    
    async def process_text(self, text: str) -> List[Verdict]:
        """
        Process text through the full factchecking pipeline.
        
        Args:
            text: The text to factcheck
            
        Returns:
            List[Verdict]: A list of verdicts for claims in the text
        """
        logger.info("Starting factchecking pipeline for text (%d chars)", len(text))
        
        # Step 1: Detect claims
        try:
            claims = await self._detect_claims(text)
            if not claims:
                logger.info("No check-worthy claims detected in the text")
                return []
        except Exception as e:
            logger.error("Error in claim detection: %s", str(e), exc_info=True)
            raise
        
        # Step 2: Gather evidence for each claim (with parallelism)
        try:
            claims_with_evidence = await self._gather_evidence_for_claims(claims)
        except Exception as e:
            logger.error("Error in evidence gathering: %s", str(e), exc_info=True)
            raise
        
        # Step 3: Generate verdicts for each claim
        try:
            verdicts = await self._generate_verdicts(claims_with_evidence)
        except Exception as e:
            logger.error("Error in verdict generation: %s", str(e), exc_info=True)
            raise
        
        logger.info("Factchecking pipeline completed. Generated %d verdicts.", len(verdicts))
        return verdicts
    
    async def _detect_claims(self, text: str) -> List[Claim]:
        """
        Detect check-worthy claims in the text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List[Claim]: A list of detected claims
        """
        logger.info("Detecting claims in text")
        claims = await self.claim_detector.detect_claims(
            text,
            min_check_worthiness=self.min_check_worthiness,
            max_claims=self.max_claims
        )
        logger.info("Detected %d claims with check-worthiness >= %f",
                   len(claims), self.min_check_worthiness)
        return claims
    
    async def _gather_evidence_for_claims(self, claims: List[Claim]) -> List[Tuple[Claim, List[Evidence]]]:
        """
        Gather evidence for multiple claims with controlled parallelism.
        
        Args:
            claims: List of claims to gather evidence for
            
        Returns:
            List[Tuple[Claim, List[Evidence]]]: Claims paired with their evidence
        """
        logger.info("Gathering evidence for %d claims with parallelism %d",
                   len(claims), self.parallelism)
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.parallelism)
        
        async def gather_with_limit(claim: Claim) -> Tuple[Claim, List[Evidence]]:
            async with semaphore:
                logger.info("Gathering evidence for claim: '%s'", claim.text[:50] + "...")
                evidence = await self.evidence_hunter.gather_evidence(claim)
                logger.info("Found %d pieces of evidence for claim", len(evidence))
                return claim, evidence
        
        # Create tasks for each claim
        tasks = [gather_with_limit(claim) for claim in claims]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        logger.info("Evidence gathering completed for all claims")
        return results
    
    async def _generate_verdicts(self, claims_with_evidence: List[Tuple[Claim, List[Evidence]]]) -> List[Verdict]:
        """
        Generate verdicts for claims based on gathered evidence.
        
        Args:
            claims_with_evidence: List of claims paired with their evidence
            
        Returns:
            List[Verdict]: Generated verdicts for each claim
        """
        logger.info("Generating verdicts for %d claims", len(claims_with_evidence))
        
        verdicts = []
        for claim, evidence in claims_with_evidence:
            if not evidence:
                logger.warning("No evidence found for claim: '%s'", claim.text[:50] + "...")
                continue
            
            logger.info("Generating verdict for claim with %d evidence pieces", len(evidence))
            verdict = await self.verdict_writer.generate_verdict(claim, evidence)
            verdicts.append(verdict)
            logger.info("Generated verdict: %s", verdict.verdict)
        
        return verdicts


class FactcheckPipelineFactory:
    """Factory for creating configured FactcheckPipeline instances."""
    
    @staticmethod
    def create_pipeline(config: Optional[Dict[str, Any]] = None) -> FactcheckPipeline:
        """
        Create a configured FactcheckPipeline instance.
        
        Args:
            config: Optional configuration dictionary for the pipeline
            
        Returns:
            A configured FactcheckPipeline instance
        """
        config = config or {}
        
        # Extract pipeline configuration
        parallelism = config.get("parallelism", 5)
        min_check_worthiness = config.get("min_check_worthiness", 0.5)
        max_claims = config.get("max_claims", 10)
        
        # Extract agent-specific configurations
        claim_detector_config = config.get("claim_detector", {})
        evidence_hunter_config = config.get("evidence_hunter", {})
        verdict_writer_config = config.get("verdict_writer", {})
        
        # Create agents using the factory
        claim_detector = AgentFactory.create_claim_detector(claim_detector_config)
        evidence_hunter = AgentFactory.create_evidence_hunter(evidence_hunter_config)
        verdict_writer = AgentFactory.create_verdict_writer(verdict_writer_config)
        
        # Create and return the pipeline with injected dependencies
        return FactcheckPipeline(
            claim_detector=claim_detector,
            evidence_hunter=evidence_hunter,
            verdict_writer=verdict_writer,
            parallelism=parallelism,
            min_check_worthiness=min_check_worthiness,
            max_claims=max_claims
        ) 