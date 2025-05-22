"""VeriFact Factcheck Manager.

This module provides a unified pipeline that orchestrates the three agents:
1. ClaimDetector: Identifies factual claims in text
2. EvidenceHunter: Gathers evidence for claims
3. VerdictWriter: Analyzes evidence and generates verdicts

The pipeline handles data transformation between agents, error recovery,
and provides both synchronous and asynchronous operation modes.
"""

import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from agents import Runner, gen_trace_id, trace
from src.verifact_agents.claim_detector import claim_detector_agent, Claim
from src.verifact_agents.evidence_hunter import evidence_hunter_agent, Evidence
from src.verifact_agents.verdict_writer import verdict_writer_agent, Verdict
import logging

logger = logging.getLogger(__name__)

class ManagerConfig(BaseModel):
    """Configuration options for the factcheck pipeline."""

    min_checkworthiness: float = Field(0.5, ge=0.0, le=1.0)
    max_claims: Optional[int] = None
    evidence_per_claim: int = Field(5, ge=1)
    timeout_seconds: float = 120.0
    enable_fallbacks: bool = True
    retry_attempts: int = 2
    raise_exceptions: bool = False
    include_debug_info: bool = False


class VerifactManager:
    def __init__(self, config: ManagerConfig = None):
        self.config = config or ManagerConfig()

    async def run(self, query: str) -> List[Verdict]:
        """Process text through the full factchecking pipeline.

        Args:
            text: The text to factcheck

        Returns:
            List[Verdict]: A list of verdicts for claims in the text
        """
        trace_id = gen_trace_id()
        with trace("VeriFact trace", trace_id=trace_id):
            logger.info(f"Starting factchecking pipeline for trace {trace_id}...")

            # Step 1: Detect claims
            try:
                claims = await self._detect_claims(query)
                if not claims:
                    logger.info("No check-worthy claims detected in the text")
                    return []
            except Exception as e:
                logger.error("Error in claim detection: %s", str(e), exc_info=True)
                raise

            # Step 2: Gather evidence for each claim (with parallelism)
            try:
                claim_evidence_pairs = await self._gather_evidence(claims)
            except Exception as e:
                logger.error("Error in evidence gathering: %s", str(e), exc_info=True)
                raise

            # Step 3: Generate verdicts for each claim
            try:
                verdicts = await self._generate_all_verdicts(claim_evidence_pairs)
            except Exception as e:
                logger.error("Error in verdict generation: %s", str(e), exc_info=True)
                raise

            logger.info("Factchecking pipeline completed. Generated %d verdicts.", len(verdicts))
            return verdicts

    async def _detect_claims(self, text: str) -> List[Claim]:
        logger.info("Detecting claims...")
        result = await Runner.run(claim_detector_agent, text)

        claims = result.final_output_as(List[Claim])
        logger.info(f"Detected {len(claims)} claims")
        logger.info(f"Claims: {claims}")
        return result.final_output_as(List[Claim])

    async def _gather_evidence_for_claim(self, claim: Claim) -> List[Evidence]:
        logger.info(f"Gathering evidence for claim {claim.text[:50]}...")

        query = f"""
        Claim to investigate: {claim.text}
        Context of the claim: {claim.context if hasattr(claim, "context") and claim.context else "No additional context provided"}
        """

        result = await Runner.run(evidence_hunter_agent, query)
        logger.info(f"Evidence gathered for claim: {result}")

        return result.final_output_as(List[Evidence])

    async def _gather_evidence(self, claims: List[Claim]) -> List[tuple[Claim, Optional[List[Evidence]]]]:
        tasks = [self._gather_evidence_for_claim(claim) for claim in claims]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        claim_evidence_pairs = []

        for claim, result in zip(claims, results):
            if isinstance(result, Exception):
                logger.error(f"Error gathering evidence for claim: {claim.text[:50]}: {result}", exc_info=True)
                claim_evidence_pairs.append((claim, None))
            elif result is None:
                logger.warning(f"No evidence found for claim: {claim.text[:50]}")
                claim_evidence_pairs.append((claim, None))
            else:
                #logger.info(f"DEBUG: Evidence gathered for claim: {result}")
                claim_evidence_pairs.append((claim, result))

        return claim_evidence_pairs

    async def _generate_verdict_for_claim(self, claim: Claim, evidence: List[Evidence]) -> Verdict:
        logger.info(f"Generating verdict for claim {claim.text[:50]}...")
        # TODO: add formatting of evidence and citations before creating the prompt

        prompt = f"""
        Claim to investigate: {claim.text}
        Evidence: {evidence}
        """

        result = await Runner.run(verdict_writer_agent, prompt)
        return result.final_output_as(Verdict)

    async def _generate_all_verdicts(self, claims_with_evidence: List[tuple[Claim, Optional[List[Evidence]]]]) -> List[Verdict]:
        logger.info("Generating verdicts...")
        verdicts = []
        for claim, evidence in claims_with_evidence:
            logger.info(f"Claim: {claim.text[:50]}")
            if not evidence:
                logger.warning(f"Skipping claim - no evidence found")
                continue

            logger.info(f"Evidence: {evidence} | {type(evidence)}")
            logger.info("Generating verdict for claim with %d evidence pieces", len(evidence))
            verdict = await self._generate_verdict_for_claim(claim, evidence)

            verdicts.append(verdict)
            logger.info("Generated verdict: %s", verdict.verdict)

        return verdicts

# testing
if __name__ == "__main__":
    # load env
    from dotenv import load_dotenv
    load_dotenv()
    from utils.logging.logging_config import setup_logging
    setup_logging()
    manager = VerifactManager()
    query = "The sky is blue and the grass is green"
    verdicts = asyncio.run(manager.run(query))
    print(verdicts)