"""VeriFact Factcheck Manager using OpenRouter.

This module provides a unified pipeline that orchestrates the three agents:
1. ClaimDetector: Identifies factual claims in text
2. EvidenceHunter: Gathers evidence for claims
3. VerdictWriter: Analyzes evidence and generates verdicts

This version uses OpenRouter directly instead of the OpenAI Agents SDK.
"""

import asyncio
import os
import json
import logging
from typing import Optional, List, Any
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
CLAIM_DETECTOR_MODEL = os.getenv("CLAIM_DETECTOR_MODEL", "gpt-4o-mini")
EVIDENCE_HUNTER_MODEL = os.getenv("EVIDENCE_HUNTER_MODEL", "gpt-4o-mini")
VERDICT_WRITER_MODEL = os.getenv("VERDICT_WRITER_MODEL", "gpt-4o-mini")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.1"))
MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "1000"))

# Define data models
class Claim(BaseModel):
    """A factual claim that requires verification."""
    text: str
    context: float = 0.0

class Evidence(BaseModel):
    """Evidence related to a claim."""
    content: str
    source: str
    relevance: float = 1.0
    stance: str = "supporting"  # supporting, contradicting, neutral

class Verdict(BaseModel):
    """A verdict on a claim based on evidence."""
    claim: str
    verdict: str
    confidence: float
    explanation: str
    sources: List[str]

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
        self.client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://verifact.ai",  # Replace with your site URL
                "X-Title": "VeriFact",  # Replace with your site name
            },
            timeout=self.config.timeout_seconds,
        )

    async def run(self, query: str) -> List[Verdict]:
        """Process text through the full factchecking pipeline."""
        logger.info("Starting factchecking pipeline...")

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

    async def _call_openrouter(self, prompt: str, model: str = DEFAULT_MODEL) -> str:
        """Call OpenRouter API with the given prompt."""
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": MODEL_TEMPERATURE,
                "max_tokens": MODEL_MAX_TOKENS,
            },
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def _detect_claims(self, text: str) -> List[Claim]:
        """Detect claims in the given text."""
        logger.info("Detecting claims...")
        
        prompt = """
        You are a claim detection agent designed to identify factual claims from text that require verification.
        Your task is to identify explicit and implicit factual claims from the following text.
        
        For each claim, return:
        1. The original claim text
        2. A context score (0.0-1.0)
        
        Format your response as a JSON array of objects with 'text' and 'context' properties.
        
        Text to analyze:
        {text}
        """.format(text=text)
        
        response_text = await self._call_openrouter(prompt, CLAIM_DETECTOR_MODEL)
        
        try:
            # Extract JSON from the response
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            
            claims_data = json.loads(json_str)
            claims = [Claim(**claim) for claim in claims_data]
            logger.info(f"Detected {len(claims)} claims")
            return claims
        except Exception as e:
            logger.error(f"Error parsing claims: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback: try to extract claims manually
            return [Claim(text=text, context=1.0)]

    async def _gather_evidence_for_claim(self, claim: Claim) -> List[Evidence]:
        """Gather evidence for the given claim."""
        logger.info(f"Gathering evidence for claim: {claim.text[:50]}...")
        
        prompt = """
        You are an evidence gathering agent tasked with finding and evaluating evidence related to factual claims.
        
        For the following claim, provide evidence that supports or contradicts it.
        
        For each piece of evidence, provide:
        - content: The relevant text passage that addresses the claim
        - source: The source URL
        - relevance: A score from 0.0 to 1.0 indicating how relevant this evidence is to the claim
        - stance: "supporting", "contradicting", or "neutral" based on how the evidence relates to the claim
        
        Format your response as a JSON array of objects with 'content', 'source', 'relevance', and 'stance' properties.
        
        Claim to investigate: {claim}
        Context of the claim: {context}
        """.format(claim=claim.text, context=claim.context)
        
        response_text = await self._call_openrouter(prompt, EVIDENCE_HUNTER_MODEL)
        
        try:
            # Extract JSON from the response
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            
            evidence_data = json.loads(json_str)
            evidence = [Evidence(**ev) for ev in evidence_data]
            logger.info(f"Gathered {len(evidence)} pieces of evidence")
            return evidence
        except Exception as e:
            logger.error(f"Error parsing evidence: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback: return empty evidence
            return []

    async def _gather_evidence(self, claims: List[Claim]) -> List[tuple[Claim, Optional[List[Evidence]]]]:
        """Gather evidence for all claims in parallel."""
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

    async def _generate_verdict_for_claim(self, claim: Claim, evidence: List[Evidence]) -> Verdict:
        """Generate a verdict for the given claim based on the evidence."""
        logger.info(f"Generating verdict for claim: {claim.text[:50]}...")
        
        evidence_text = "\n".join([
            f"- Source: {ev.source}\n  Content: {ev.content}\n  Stance: {ev.stance}\n  Relevance: {ev.relevance}"
            for ev in evidence
        ])
        
        prompt = """
        You are a verdict writing agent tasked with analyzing evidence and generating verdicts for factual claims.
        
        Based on the evidence provided, determine whether the claim is true, false, partially true, or unverifiable.
        
        Provide:
        - claim: The claim text
        - verdict: "true", "false", "partially true", or "unverifiable"
        - confidence: A score from 0.0 to 1.0 indicating your confidence in the verdict
        - explanation: A detailed explanation of your reasoning
        - sources: A list of sources used to reach the verdict
        
        Format your response as a JSON object with 'claim', 'verdict', 'confidence', 'explanation', and 'sources' properties.
        
        Claim to investigate: {claim}
        
        Evidence:
        {evidence}
        """.format(claim=claim.text, evidence=evidence_text)
        
        response_text = await self._call_openrouter(prompt, VERDICT_WRITER_MODEL)
        
        try:
            # Extract JSON from the response
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            
            verdict_data = json.loads(json_str)
            return Verdict(**verdict_data)
        except Exception as e:
            logger.error(f"Error parsing verdict: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback: return a default verdict
            return Verdict(
                claim=claim.text,
                verdict="unverifiable",
                confidence=0.5,
                explanation="Unable to determine the veracity of this claim due to processing errors.",
                sources=[ev.source for ev in evidence if hasattr(ev, 'source')]
            )

    async def _generate_all_verdicts(self, claims_with_evidence: List[tuple[Claim, Optional[List[Evidence]]]]) -> List[Verdict]:
        """Generate verdicts for all claims."""
        logger.info("Generating verdicts...")
        verdicts = []
        for claim, evidence in claims_with_evidence:
            if not evidence:
                logger.warning(f"Skipping claim - no evidence found")
                continue

            verdict = await self._generate_verdict_for_claim(claim, evidence)
            verdicts.append(verdict)
            logger.info(f"Generated verdict: {verdict.verdict}")

        return verdicts

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Testing
if __name__ == "__main__":
    async def main():
        manager = VerifactManager()
        query = "The sky is blue and the grass is green"
        try:
            verdicts = await manager.run(query)
            print(json.dumps([verdict.dict() for verdict in verdicts], indent=2))
        finally:
            await manager.close()

    asyncio.run(main())
