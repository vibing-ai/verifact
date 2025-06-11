"""VeriFact Factcheck Manager.

This module provides a unified pipeline that orchestrates the three agents:
1. ClaimDetector: Identifies factual claims in text
2. EvidenceHunter: Gathers evidence for claims
3. VerdictWriter: Analyzes evidence and generates verdicts

The pipeline handles data transformation between agents, error recovery,
and provides both synchronous and asynchronous operation modes.
"""

import asyncio
from re import A, I
from signal import raise_signal
import chainlit as cl
from pydantic import BaseModel, Field
from agents import Runner, gen_trace_id, trace
from verifact_agents.claim_detector import claim_detector_agent, Claim
from verifact_agents.evidence_hunter import evidence_hunter_agent, Evidence
from verifact_agents.verdict_writer import verdict_writer_agent, Verdict
import logging

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
    def __init__(self, config: ManagerConfig = None):
        self.config = config or ManagerConfig()

    # Replace the run method with this one
    async def run(self, query: str, progress_callback=None) -> list:
        trace_id = gen_trace_id()
        with trace("VeriFact trace", trace_id=trace_id):
            logger.info(f"Starting factchecking pipeline for trace {trace_id}...")

            # Step 1: Detect claims
            if progress_callback:
                await progress_callback(
                    type="step_start", data={"title": "Claim Detection"}
                )

            try:
                claims = await self._detect_claims(query)
                if progress_callback:
                    await progress_callback(
                        type="step_end",
                        data={"output": f"Detected {len(claims)} claim(s)."},
                    )
            except Exception as e:
                logger.error("Error in claim detection: %s", str(e), exc_info=True)
                if progress_callback:
                    await progress_callback(
                        type="step_error",
                        data={"title": "Claim Detection", "output": f"Error: {e}"},
                    )
                raise

            if not claims:
                return []

            # This event signals the UI to create the collapsible sections for each claim
            if progress_callback:
                await progress_callback(type="claims_detected", data={"claims": claims})

            # Step 2 & 3: Process each claim individually
            final_verdicts = []
            for idx, claim in enumerate(claims):
                claim_id = f"claim_{idx+1}"  # A unique ID for this claim's parent step
                claim_text_short = getattr(claim, "text", str(claim))[:60]

                # --- Evidence Gathering Step ---
                if progress_callback:
                    await progress_callback(
                        type="step_start",
                        data={"title": "Evidence Gathering", "parent_id": claim_id},
                    )

                evidence = None
                try:
                    evidence = await self._gather_evidence_for_claim(claim)
                    if progress_callback:
                        await progress_callback(
                            type="step_end",
                            data={"output": f"Found {len(evidence)} evidence items."},
                        )
                except Exception as e:
                    logger.error(
                        f"Error gathering evidence for '{claim_text_short}...': {e}",
                        exc_info=True,
                    )
                    if progress_callback:
                        await progress_callback(
                            type="step_error", data={"output": f"Error: {e}"}
                        )
                    continue

                if not evidence:
                    continue

                # --- Verdict Generation Step ---
                if progress_callback:
                    await progress_callback(
                        type="step_start",
                        data={"title": "Verdict Generation", "parent_id": claim_id},
                    )

                try:
                    verdict = await self._generate_verdict_for_claim(claim, evidence)
                    if progress_callback:
                        await progress_callback(
                            type="step_end",
                            data={"output": f"Verdict: {verdict.verdict}"},
                        )
                    final_verdicts.append((claim, evidence, verdict))
                except Exception as e:
                    logger.error(
                        f"Error generating verdict for '{claim_text_short}...': {e}",
                        exc_info=True,
                    )
                    if progress_callback:
                        await progress_callback(
                            type="step_error", data={"output": f"Error: {e}"}
                        )
                    continue

            logger.info(
                "Factchecking pipeline completed. Generated %d verdicts.",
                len(final_verdicts),
            )
            return final_verdicts

    async def _detect_claims(self, text: str) -> list[Claim]:
        logger.info("_detect_claims(), Detecting claims...")
        result = await Runner.run(claim_detector_agent, text)

        claims = result.final_output_as(list[Claim])
        logger.info(f"_detect_claims(), Detected {len(claims)} claims")

        return claims

    async def _gather_evidence_for_claim(self, claim: Claim) -> list[Evidence]:
        logger.info(f"Gathering evidence for claim {claim.text[:50]}...")

        query = f"""
        Claim to investigate: {claim.text}
        Context of the claim: {claim.context if hasattr(claim, "context") and claim.context else "No additional context provided"}
        """

        query = f"""
        Claim to investigate: {claim.text}
        Context of the claim: No additional context provided
        """

        result = await Runner.run(evidence_hunter_agent, query)
        logger.info(f"Evidence gathered for claim: {claim.text[:50]}")

        return result.final_output_as(list[Evidence])

    async def _gather_evidence(
        self, claims: list[Claim]
    ) -> list[tuple[Claim, list[Evidence] | None]]:
        tasks = [self._gather_evidence_for_claim(claim) for claim in claims]
        """ *** Todos (GPT suggests) ***
        asyncio.gather
        - This is the right way to run the evidence-hunting step in parallel for multiple claims.
        - However, the main run method currently gathers evidence serially in a for loop. This is a great opportunity for a future performance improvement.
        """
        results = await asyncio.gather(*tasks, return_exceptions=True)
        claim_evidence_pairs = []

        for claim, result in zip(claims, results):
            if isinstance(result, Exception):
                logger.error(
                    f"Error gathering evidence for claim: {claim.text[:50]}: {result.message}",
                    exc_info=True,
                )
                claim_evidence_pairs.append((claim, None))
            elif result is None:
                logger.warning(f"No evidence found for claim: {claim.text[:50]}")
                claim_evidence_pairs.append((claim, None))
            else:
                # logger.info(f"DEBUG: Evidence gathered for claim: {result}")
                claim_evidence_pairs.append((claim, result))

        return claim_evidence_pairs

    async def _generate_verdict_for_claim(
        self, claim: Claim, evidence: list[Evidence]
    ) -> Verdict:
        logger.info(f"Generating verdict for claim {claim.text[:50]}...")
        # TODO: add formatting of evidence and citations before creating the prompt

        prompt = f"""
        Claim to investigate: {claim.text}
        Evidence: {evidence}
        """

        result = await Runner.run(verdict_writer_agent, prompt)
        return result.final_output_as(Verdict)

    async def _generate_verdicts(
        self, claims_with_evidence: list[tuple[Claim, list[Evidence]]]
    ) -> list[Verdict]:
        logger.info("Generating verdicts for claims...")
        verdicts = []
        for claim, evidence in claims_with_evidence:
            verdict = await Runner.run(verdict_writer_agent, claim, evidence)
            verdicts.append(verdict.final_output_as(Verdict))
        logger.info(f"Generated verdicts for {len(claims_with_evidence)} claims")

    async def _generate_all_verdicts(
        self, claims_with_evidence: list[tuple[Claim, list[Evidence]]]
    ) -> list[Verdict]:
        logger.info("Generating verdicts...")
        verdicts = []
        for claim, evidence in claims_with_evidence:
            logger.info(f"Claim: {claim.text[:50]}")
            if not evidence:
                logger.warning(f"Skipping claim - no evidence found")
                continue

            logger.info(f"Evidence: {evidence} | {type(evidence)}")
            logger.info(
                "Generating verdict for claim with %d evidence pieces", len(evidence)
            )
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

    # async def test_claims():
    #     #query = "The sky is blue and the grass is green"
    #     query = "The Eiffel Tower is 330 meters tall and was completed in 1889."
    #     claims_output = await Runner.run(claim_detector_agent, query)
    #     print("------->verifact_manager.py claims_output.final_output_as():", claims_output.final_output_as(list[Claim]))
    #     return claims_output
    #
    # claims_output = asyncio.run(test_claims())

    # query = "The Eiffel Tower is 330 meters tall and was completed in 1889."
    query = "The sky is blue"
    manager = VerifactManager()
    verdicts = asyncio.run(manager.run(query))
    print("Verdicts:", verdicts)
