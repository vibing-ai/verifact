"""VeriFact Factcheck Manager.

This module provides a unified pipeline that orchestrates the three agents:
1. ClaimDetector: Identifies factual claims in text
2. EvidenceHunter: Gathers evidence for claims
3. VerdictWriter: Analyzes evidence and generates verdicts

The pipeline handles data transformation between agents, error recovery,
and provides both synchronous and asynchronous operation modes.
"""

import asyncio
import logging

from agents import Runner, gen_trace_id, trace
from pydantic import BaseModel, Field

from src.verifact_agents.claim_detector import Claim, claim_detector_agent
from src.verifact_agents.evidence_hunter import Evidence, evidence_hunter_agent
from src.verifact_agents.verdict_writer import Verdict, verdict_writer_agent

logger = logging.getLogger(__name__)


class ManagerConfig(BaseModel):
    """Configuration options for the factcheck pipeline."""

    min_checkworthiness: float = Field(0.5, ge=0.0, le=1.0)
    max_claims: int | None = None
    evidence_per_claim: int = Field(5, ge=1)
    timeout_seconds: float = 120.0
    enable_fallbacks: bool = True
    retry_attempts: int = 2
    raise_exceptions: bool = False
    include_debug_info: bool = False


class VerifactManager:
    """Orchestrates the full fact-checking pipeline."""

    def __init__(self, config: ManagerConfig = None):
        """Initialize VeriFact manager with optional configuration."""
        self.config = config or ManagerConfig()

    async def run(self, query: str, progress_callback=None, progress_msg=None) -> None:
        """Process text through the full factchecking pipeline.

        Args:
            query (str): The text to factcheck.
            progress_callback: Optional function to call with progress messages
            progress_msg: The Chainlit message object to update

        Returns:
            List[Verdict]: A list of verdicts for claims in the text
        """
        trace_id = gen_trace_id()
        with trace("VeriFact trace", trace_id=trace_id):
            logger.info("Starting factchecking pipeline for trace %s...", trace_id)
            if progress_callback and progress_msg:
                await progress_callback(progress_msg, "Starting factchecking pipeline...")

            # Step 1: Detect claims
            try:
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, "Detecting factual claims...")
                claims = await self._detect_claims(query)
                if not claims:
                    logger.info("No check-worthy claims detected in the text")
                    if progress_callback and progress_msg:
                        await progress_callback(
                            progress_msg, "No factual claims detected in your message."
                        )
                    return []
                if progress_callback and progress_msg:
                    await progress_callback(
                        progress_msg, f"Detected {len(claims)} claim(s). Gathering evidence..."
                    )
            except Exception as e:
                logger.exception("Error in claim detection")
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Error in claim detection: {e!s}")
                raise

            # Step 2: Gather evidence for each claim (with parallelism)
            try:
                claim_evidence_pairs = []
                for idx, claim in enumerate(claims):
                    if progress_callback and progress_msg:
                        await progress_callback(
                            progress_msg,
                            f"Gathering evidence for claim {idx + 1}/{len(claims)}: '{getattr(claim, 'text', str(claim))[:60]}'...",
                        )
                    try:
                        evidence = await self._gather_evidence_for_claim(claim)
                    except Exception:
                        evidence = None
                    claim_evidence_pairs.append((claim, evidence))
                if progress_callback and progress_msg:
                    await progress_callback(
                        progress_msg, "Evidence gathering complete. Generating verdicts..."
                    )
            except Exception as e:
                logger.exception("Error in evidence gathering")
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Error in evidence gathering: {e!s}")
                raise

            # Step 3: Generate verdicts for each claim
            try:
                verdicts = []
                for idx, (claim, evidence) in enumerate(claim_evidence_pairs):
                    if not evidence:
                        logger.warning("Skipping claim - no evidence found")
                        if progress_callback and progress_msg:
                            await progress_callback(
                                progress_msg,
                                f"No evidence found for claim {idx + 1}: '{getattr(claim, 'text', str(claim))[:60]}'. Skipping verdict.",
                            )
                        continue
                    if progress_callback and progress_msg:
                        await progress_callback(
                            progress_msg, f"Generating verdict for claim {idx + 1}/{len(claims)}..."
                        )
                    verdict = await self._generate_verdict_for_claim(claim, evidence)
                    verdicts.append((claim, evidence, verdict))
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, "Factchecking pipeline completed.")
            except Exception as e:
                logger.exception("Error in verdict generation")
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Error in verdict generation: {e!s}")
                raise

            logger.info("Factchecking pipeline completed. Generated %d verdicts.", len(verdicts))
            return verdicts

    async def _detect_claims(self, text: str) -> list[Claim]:
        logger.info("Detecting claims...")
        result = await Runner.run(claim_detector_agent, text)

        claims = result.final_output_as(list[Claim])
        logger.info("Detected %d claims", len(claims))

        return claims

    async def _gather_evidence_for_claim(self, claim: Claim) -> list[Evidence]:
        logger.info("Gathering evidence for claim %s...", claim.text[:50])

        query = f"""
        Claim to investigate: {claim.text}
        Context of the claim: {claim.context if hasattr(claim, "context") and claim.context else "No additional context provided"}
        """

        result = await Runner.run(evidence_hunter_agent, query)
        logger.info("Evidence gathered for claim: %s", claim.text[:50])

        return result.final_output_as(list[Evidence])

    async def _gather_evidence(
        self, claims: list[Claim]
    ) -> list[tuple[Claim, list[Evidence] | None]]:
        tasks = [self._gather_evidence_for_claim(claim) for claim in claims]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        claim_evidence_pairs = []

        for claim, result in zip(claims, results, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    "Error gathering evidence for claim: %s: %s", claim.text[:50], result.message
                )
                claim_evidence_pairs.append((claim, None))
            elif result is None:
                logger.warning("No evidence found for claim: %s", claim.text[:50])
                claim_evidence_pairs.append((claim, None))
            else:
                claim_evidence_pairs.append((claim, result))

        return claim_evidence_pairs

    async def _generate_verdict_for_claim(self, claim: Claim, evidence: list[Evidence]) -> Verdict:
        logger.info("Generating verdict for claim %s...", claim.text[:50])
        # TODO: add formatting of evidence and citations before creating the prompt

        prompt = f"""
        Claim to investigate: {claim.text}
        Evidence: {evidence}
        """

        result = await Runner.run(verdict_writer_agent, prompt)
        return result.final_output_as(Verdict)

    async def _generate_all_verdicts(
        self, claims_with_evidence: list[tuple[Claim, list[Evidence]]]
    ) -> list[Verdict]:
        logger.info("Generating verdicts...")
        verdicts = []
        for claim, evidence in claims_with_evidence:
            logger.info("Claim: %s", claim.text[:50])
            if not evidence:
                logger.warning("Skipping claim - no evidence found")
                continue

            logger.info("Evidence: %s | %s", evidence, type(evidence))
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
