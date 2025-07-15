"""VeriFact Factcheck Manager.

This module provides a unified pipeline that orchestrates the three agents:
1. ClaimDetector: Identifies factual claims in text
2. EvidenceHunter: Gathers evidence for claims
3. VerdictWriter: Analyzes evidence and generates verdicts

The pipeline handles data transformation between agents, error recovery,
and provides both synchronous and asynchronous operation modes.
"""

import asyncio
from pydantic import BaseModel, Field
from agents import Runner, gen_trace_id, trace
from src.verifact_agents.claim_detector import claim_detector_agent, Claim
from src.verifact_agents.evidence_hunter import evidence_hunter_agent, Evidence
from src.verifact_agents.verdict_writer import verdict_writer_agent, Verdict
from src.utils.db import db_manager, SimilarClaimResult
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
        self.db = db_manager

    async def run(self, query: str, progress_callback=None, progress_msg=None) -> list:
        """Process text through the full factchecking pipeline with database integration.

        Args:
            query: The text to factcheck
            progress_callback: Optional function to call with progress messages
            progress_msg: The Chainlit message object to update

        Returns:
            List[Tuple[Claim, List[Evidence], Verdict]]: A list of tuples containing claims, evidence, and verdicts
        """
        trace_id = gen_trace_id()
        with trace("VeriFact trace", trace_id=trace_id):
            logger.info(f"Starting factchecking pipeline for trace {trace_id}...")
            
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
                        await progress_callback(progress_msg, "No factual claims detected in your message.")
                    return []
                
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Detected {len(claims)} claim(s). Checking for similar claims...")
                
                # Step 1.5: Check for similar claims in database
                processed_claims = []
                for claim in claims:
                    similar_claims = await self.db.find_similar_claims(claim.text, similarity_threshold=0.85)
                    
                    if similar_claims:
                        # Use existing verdict if similar claim found
                        similar_result = similar_claims[0]  # Get the most similar
                        if similar_result.verdict:
                            logger.info(f"Found similar claim: {similar_result.claim.text[:50]}... (similarity: {similar_result.similarity_score:.2f})")
                            if progress_callback and progress_msg:
                                await progress_callback(progress_msg, f"Found similar claim in database (similarity: {similar_result.similarity_score:.2f}). Using existing verdict...")
                            
                            # Convert to agent models for consistency
                            agent_claim = Claim(text=similar_result.claim.text)
                            agent_verdict = Verdict(
                                claim=similar_result.claim.text,
                                verdict=similar_result.verdict.verdict,
                                confidence=similar_result.verdict.confidence_score,
                                explanation=similar_result.verdict.explanation,
                                sources=similar_result.verdict.sources
                            )
                            
                            # Get evidence for the similar claim
                            _, evidence_list, _ = await self.db.get_claim_with_evidence_and_verdict(similar_result.claim.id)
                            agent_evidence = [
                                Evidence(
                                    content=ev.content,
                                    source=ev.source_url,
                                    relevance=ev.relevance_score,
                                    stance=ev.stance
                                ) for ev in evidence_list
                            ]
                            
                            processed_claims.append((agent_claim, agent_evidence, agent_verdict))
                            continue
                    
                    # No similar claim found, process normally
                    processed_claims.append((claim, None, None))
                
                # Filter out claims that were found in database
                new_claims = [claim for claim, evidence, verdict in processed_claims if evidence is None]
                
                if not new_claims:
                    logger.info("All claims found in database")
                    if progress_callback and progress_msg:
                        await progress_callback(progress_msg, "All claims found in database. Returning existing verdicts.")
                    return processed_claims
                
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Processing {len(new_claims)} new claim(s). Gathering evidence...")
                    
            except Exception as e:
                logger.error("Error in claim detection: %s", str(e), exc_info=True)
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Error in claim detection: {str(e)}")
                raise

            # Step 2: Gather evidence for new claims only
            try:
                for idx, (claim, evidence, verdict) in enumerate(processed_claims):
                    if evidence is None:  # Only process claims not found in database
                        if progress_callback and progress_msg:
                            await progress_callback(progress_msg, f"Gathering evidence for claim: '{claim.text[:60]}'...")
                        try:
                            evidence = await self._gather_evidence_for_claim(claim)
                            # Update the processed_claims list with evidence
                            processed_claims[idx] = (claim, evidence, None)
                        except Exception as e:
                            logger.error(f"Error gathering evidence for claim: {e}")
                            processed_claims[idx] = (claim, None, None)
                
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, "Evidence gathering complete. Generating verdicts...")
                    
            except Exception as e:
                logger.error("Error in evidence gathering: %s", str(e), exc_info=True)
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Error in evidence gathering: {str(e)}")
                raise

            # Step 3: Generate verdicts for new claims only
            try:
                for idx, (claim, evidence, verdict) in enumerate(processed_claims):
                    if verdict is None:  # Only generate verdicts for claims not found in database
                        if not evidence:
                            logger.warning(f"Skipping claim - no evidence found")
                            if progress_callback and progress_msg:
                                await progress_callback(progress_msg, f"No evidence found for claim: '{claim.text[:60]}'. Skipping verdict.")
                            continue
                        
                        if progress_callback and progress_msg:
                            await progress_callback(progress_msg, f"Generating verdict for claim: '{claim.text[:60]}'...")
                        
                        try:
                            verdict = await self._generate_verdict_for_claim(claim, evidence)
                            # Update the processed_claims list with verdict
                            processed_claims[idx] = (claim, evidence, verdict)
                        except Exception as e:
                            logger.error(f"Error generating verdict for claim: {e}")
                            processed_claims[idx] = (claim, evidence, None)
                
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, "Factchecking pipeline completed.")
                    
            except Exception as e:
                logger.error("Error in verdict generation: %s", str(e), exc_info=True)
                if progress_callback and progress_msg:
                    await progress_callback(progress_msg, f"Error in verdict generation: {str(e)}")
                raise

            # Step 4: Store new results in database
            try:
                for claim, evidence, verdict in processed_claims:
                    if evidence and verdict:  # Only store if we have complete data
                        claim_id = await self.db.store_claim(claim)
                        if claim_id:
                            await self.db.store_evidence(claim_id, evidence)
                            await self.db.store_verdict(claim_id, verdict)
                            logger.info(f"Stored claim '{claim.text[:50]}...' in database")
                
                logger.info("Factchecking pipeline completed. Generated %d verdicts.", len(processed_claims))
                return processed_claims
                
            except Exception as e:
                logger.error("Error storing results in database: %s", str(e), exc_info=True)
                # Don't fail the entire pipeline if database storage fails
                logger.info("Factchecking pipeline completed. Generated %d verdicts.", len(processed_claims))
                return processed_claims

    async def _detect_claims(self, text: str) -> list[Claim]:
        """Detect claims in the given text."""
        logger.info("Detecting claims...")
        result = await Runner.run(claim_detector_agent, text)
        claims = result.final_output_as(list[Claim])
        logger.info(f"Detected {len(claims)} claims")
        return claims

    async def _gather_evidence_for_claim(self, claim: Claim) -> list[Evidence]:
        """Gather evidence for a specific claim."""
        logger.info(f"Gathering evidence for claim {claim.text[:50]}...")

        query = f"""
        Claim to investigate: {claim.text}
        Context of the claim: {claim.context if hasattr(claim, "context") and claim.context else "No additional context provided"}
        """

        result = await Runner.run(evidence_hunter_agent, query)
        logger.info(f"Evidence gathered for claim: {claim.text[:50]}")
        return result.final_output_as(list[Evidence])
        
    async def _gather_evidence(self, claims: list[Claim]) -> list[tuple[Claim, list[Evidence] | None]]:
        """Gather evidence for multiple claims in parallel."""
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
                claim_evidence_pairs.append((claim, result))

        return claim_evidence_pairs

    async def _generate_verdict_for_claim(self, claim: Claim, evidence: list[Evidence]) -> Verdict:
        """Generate a verdict for a claim based on evidence."""
        logger.info(f"Generating verdict for claim {claim.text[:50]}...")

        prompt = f"""
        Claim to investigate: {claim.text}
        Evidence: {evidence}
        """

        result = await Runner.run(verdict_writer_agent, prompt)
        return result.final_output_as(Verdict)

    async def _generate_all_verdicts(self, claims_with_evidence: list[tuple[Claim, list[Evidence]]]) -> list[Verdict]:
        """Generate verdicts for multiple claims with evidence."""
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

# Testing
if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Setup logging
    from utils.logging_utils.logging_config import setup_logging
    setup_logging()
    
    # Test the manager
    async def test_manager():
        manager = VerifactManager()
        query = "The sky is blue and the grass is green"
        verdicts = await manager.run(query)
        print(verdicts)
    
    asyncio.run(test_manager())