"""AI-driven claim detection for VeriFact.

This module provides a streamlined claim detection system that uses AI agents
for intelligent analysis instead of complex rule-based processing.
"""

import os
import logging
import re
from typing import List
from pydantic import BaseModel, Field

from agents import Agent, function_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keep the original PROMPT as a constant
PROMPT = """
You are an intelligent claim detection agent designed to identify factual claims from text that require verification.

Your task is to analyze input text and identify factual claims that should be fact-checked. You must distinguish between:
- FACTUAL CLAIMS: Statements that make specific, verifiable assertions about reality
- OPINIONS: Personal views, beliefs, or subjective statements
- QUESTIONS: Interrogative statements
- COMMANDS: Instructions or requests
- RECOMMENDATIONS: Suggestions, advice, or calls for action that cannot be verified

## What Makes a Claim Worth Fact-Checking:
1. **Specificity**: Contains concrete facts, numbers, dates, or specific assertions
2. **Verifiability**: Can be proven true or false with evidence
3. **Public Interest**: Matters to public discourse, health, safety, or policy
4. **Impact**: Could influence decisions, beliefs, or actions if believed

## What is NOT a Factual Claim:
- "The results suggest that further research is needed" (recommendation)
- "I think this is a good idea" (opinion)
- "What do you think about this?" (question)
- "Please review this document" (command)
- "The weather might be nice tomorrow" (speculation)
- "We should investigate this further" (suggestion)
- "More studies are needed" (recommendation)

## What IS a Factual Claim:
- "The study found that 75% of participants showed improvement" (specific result)
- "The researchers noted that the sample size was small" (factual observation)
- "Company X reported $2.3 billion in revenue" (specific financial data)
- "The new policy will affect 1.2 million people" (specific impact)

## Domain Classification:
Automatically classify claims into relevant domains:
- **Science**: Research, studies, scientific findings, medical claims
- **Health**: Medical treatments, health effects, disease information
- **Technology**: Software, hardware, tech products, digital claims
- **Statistics**: Numbers, percentages, data, surveys, polls
- **Politics**: Government, policy, political statements, elections
- **Business**: Companies, economy, financial claims, market data
- **Environment**: Climate, weather, environmental effects
- **Other**: General factual claims not fitting above categories

## Entity Extraction:
Identify relevant named entities, organizations, people, places, dates, and key concepts that are central to the claim.

## Scoring Guidelines:
- **Check-worthiness (0.0-1.0)**: How important it is to verify this claim
  - 0.8-1.0: High-stakes claims with broad impact
  - 0.5-0.7: Moderate importance claims
  - 0.0-0.4: Low-priority or already well-established claims

- **Confidence (0.0-1.0)**: Your confidence in the claim being factual vs opinion
  - 0.8-1.0: Clearly factual, specific, verifiable
  - 0.5-0.7: Likely factual but some ambiguity
  - 0.0-0.4: Unclear if factual or opinion

## Context Extraction:
For each claim, provide relevant surrounding context that helps understand the claim's meaning and significance.

## Output Format:
Return a list of Claim objects with:
- text: The factual claim text (normalized and cleaned)
- context: Surrounding context that helps understand the claim
- check_worthiness: Score from 0.0 to 1.0
- domain: The relevant domain category
- confidence: Your confidence in the claim being factual
- entities: List of relevant entities mentioned

## Key Rule:
Only extract claims that can be factually verified. If a statement is a recommendation, opinion, suggestion, or speculation, do NOT include it as a claim.

Focus on claims that are specific, verifiable, and matter to public discourse.
"""

class Claim(BaseModel):
    """A factual claim that requires verification."""
    text: str
    context: str = Field(default="")
    check_worthiness: float = Field(default=0.0, ge=0.0, le=1.0)
    domain: str = Field(default="Other")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: list[str] = Field(default_factory=list)

    def is_checkworthy(self, threshold: float = 0.5) -> bool:
        """Check if this claim meets the minimum check-worthiness threshold."""
        return self.check_worthiness >= threshold

    def get_summary(self) -> str:
        """Get a brief summary of the claim."""
        return f"{self.text[:50]}... (Domain: {self.domain}, Score: {self.check_worthiness:.2f})"

    def has_entities(self) -> bool:
        """Check if the claim has any entities."""
        return len(self.entities) > 0

    def get_entity_names(self) -> list[str]:
        """Get the names of entities in the claim."""
        return self.entities.copy()

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if the claim has high confidence."""
        return self.confidence >= threshold

class ClaimDetector:
    """AI-driven claim detection system that replaces complex rule-based processing."""
    
    def __init__(self):
        """Initialize the claim detector with AI agent."""
        self.agent = claim_detector_agent

    def _preprocess_text(self, text: str) -> str:
        """Text preprocessing."""
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string")
        
        # Basic cleaning
        text = text.strip()
        text = " ".join(text.split())  # Remove extra whitespace
        
        # Normalize quotes and dashes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        text = re.sub(r'[—–−]', ' ', text)
        
        # Remove common noise patterns
        text = re.sub(r'\b(um|uh|er|ah)\b', '', text, flags=re.IGNORECASE)
        
        # Normalize common abbreviations
        text = re.sub(r'\bvs\.\b', 'versus', text, flags=re.IGNORECASE)
        text = re.sub(r'\betc\.\b', 'etcetera', text, flags=re.IGNORECASE)
        
        return text

    def _deduplicate_claims(self, claims: List[Claim]) -> List[Claim]:
        """Remove duplicate or very similar claims."""
        if not claims:
            return claims

        # Sort by check-worthiness (highest first)
        sorted_claims = sorted(claims, key=lambda x: x.check_worthiness, reverse=True)
        
        unique_claims = []
        seen_texts = set()

        for claim in sorted_claims:
            normalized_text = claim.text.lower().strip()
            
            # Check for duplicates
            is_duplicate = False
            for seen_text in seen_texts:
                if (normalized_text in seen_text or seen_text in normalized_text or 
                    len(set(normalized_text.split()) & set(seen_text.split())) / 
                    max(len(normalized_text.split()), len(seen_text.split())) > 0.8):
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_claims.append(claim)
                seen_texts.add(normalized_text)

        logger.info(f"Deduplicated claims: {len(claims)} -> {len(unique_claims)}")
        return unique_claims

    def _entity_extraction(self, claims: List[Claim]) -> List[Claim]:
        """Enhance entity extraction with additional validation."""
        for claim in claims:
            # Ensure entities are not empty if claim has specific patterns
            if not claim.entities and any(word in claim.text.lower() for word in ['study', 'research', 'company', 'government']):
                # Could add fallback entity extraction here
                pass
        return claims

    def _validate_checkworthiness_scores(self, claims: List[Claim]) -> List[Claim]:
        """Validate and potentially adjust check-worthiness scores."""
        for claim in claims:
            # Ensure scores are within reasonable bounds
            if claim.check_worthiness > 0.9 and len(claim.text) < 20:
                # Very short claims shouldn't have very high scores
                claim.check_worthiness = min(claim.check_worthiness, 0.8)
        return claims

    async def detect_claims(self, text: str, min_checkworthiness: float = 0.5) -> List[Claim]:
        """Detect claims in text using AI agent analysis."""
        try:
            # Preprocess text
            cleaned_text = self._preprocess_text(text)
            logger.info(f"Processing text of length {len(cleaned_text)}")

            # Handle very short texts
            if len(cleaned_text) < 10:
                logger.warning("Text too short for meaningful claim detection")
                return []

            # Use AI agent to analyze and extract claims
            from agents import Runner
            result = await Runner.run(self.agent, cleaned_text)
            claims = result.final_output_as(List[Claim])

            # Validate and enhance results
            claims = self._validate_checkworthiness_scores(claims)
            claims = self._entity_extraction(claims)

            # Filter by minimum check-worthiness
            filtered_claims = [claim for claim in claims if claim.check_worthiness >= min_checkworthiness]
            
            # Deduplicate claims
            final_claims = self._deduplicate_claims(filtered_claims)
            
            logger.info(f"Extracted {len(final_claims)} claims from text")
            return final_claims

        except Exception as e:
            logger.error(f"Error processing text: {str(e)}", exc_info=True)
            raise

# Create the agent instance as a constant (like the original)
claim_detector_agent = Agent(
    name="ClaimDetector",
    instructions=PROMPT,
    output_type=List[Claim],
    model="gpt-4o-mini"
)

# Create singleton instance
claim_detector = ClaimDetector()

# Backward compatibility functions
async def process_claims(text: str, min_checkworthiness: float = 0.5) -> List[Claim]:
    """Process input text and extract claims (backward compatibility)."""
    return await claim_detector.detect_claims(text, min_checkworthiness)

# Add this to ensure proper integration
@function_tool(
    name_override="process_claims",
    description_override="Process text to extract and analyze factual claims"
)
async def process_claims_tool(text: str, min_checkworthiness: float = 0.5) -> List[Claim]:
    """Process input text and extract claims (tool version for pipeline)."""
    return await process_claims(text, min_checkworthiness)