"""AI-driven claim detection for VeriFact.

This module provides a streamlined claim detection system that uses AI agents
for intelligent analysis instead of complex rule-based processing.
"""

import logging
import re
import html
from typing import List
from pydantic import BaseModel, Field, field_validator
from agents import Agent, function_tool, Runner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Length limits for text and claims
MAX_TEXT_LENGTH = 250
MIN_TEXT_LENGTH = 10
MAX_CLAIM_TEXT_LENGTH = 150
MAX_CONTEXT_LENGTH = 200
MAX_CLAIMS_PER_REQUEST = 2
DANGEROUS_PATTERNS = [
    r'<script.*?</script>',  # Script tags
    r'javascript:',  # JavaScript protocol
    r'data:text/html',  # Data URLs
    r'vbscript:',  # VBScript
    r'on\w+\s*=',  # Event handlers
    r'<iframe.*?</iframe>',  # Iframe tags
    r'<object.*?</object>',  # Object tags
    r'<embed.*?</embed>',  # Embed tags
]

PROMPT = """
You are an intelligent claim detection agent designed to identify factual claims from text that require verification.

IMPORTANT: Due to system constraints, you can only return a maximum of 2 claims per request. Focus on the most important and check-worthy claims.

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

## Context Extraction:
For each claim, provide relevant surrounding context that helps understand the claim's meaning and significance.

## Output Format:
You MUST return a list of Pydantic `Claim` objects. Each `Claim` object should have the following fields:
- text: The factual claim text (normalized and cleaned). Max length: 150 characters.
- context: Surrounding context that helps understand the claim. Max length: 200 characters.
- check_worthiness: Score from 0.0 to 1.0.
- domain: The relevant domain category.
- confidence: Your confidence in the claim being factual (0.0-1.0).
- entities: List of relevant entities mentioned (strings).

## Key Rule:
Only extract claims that can be factually verified. If a statement is a recommendation, opinion, suggestion, or speculation, do NOT include it as a claim.

Focus on claims that are specific, verifiable, and matter to public discourse.
"""

def _validate_text_input(text: str, min_length: int = MIN_TEXT_LENGTH, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Centralized text input validation.
    
    Args:
        text: Input text to validate
        min_length: Minimum allowed length (default: MIN_TEXT_LENGTH)
        max_length: Maximum allowed length (default: MAX_TEXT_LENGTH)
    
    Returns:
        Validated text string
        
    Raises:
        ValueError: If text is invalid
    """
    if not text or not isinstance(text, str):
        raise ValueError("Input text must be a non-empty string")
    
    if len(text) < min_length:
        raise ValueError(f"Text too short (minimum {min_length} characters)")
    
    if len(text) > max_length:
        raise ValueError(f"Text too long (maximum {max_length} characters)")
    
    return text.strip()

class Claim(BaseModel):
    """A factual claim that requires verification."""
    text: str
    context: str = Field(default="")
    check_worthiness: float = Field(default=0.0, ge=0.0, le=1.0)
    domain: str = Field(default="Other")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: list[str] = Field(default_factory=list)

    @field_validator('text')
    def validate_claim_text(cls, v):
        """Validate and sanitize claim text."""
        # Use centralized validation
        v = _validate_text_input(v, min_length=1, max_length=MAX_CLAIM_TEXT_LENGTH)
        
        # Sanitize the text
        sanitized = cls._sanitize_text(v)
        if sanitized != v:
            logger.warning("Claim text was sanitized due to potentially dangerous content")

        return sanitized

    @field_validator('context')
    def validate_context(cls, v):
        """Validate and sanitize context."""
        if v:  # Only validate if context is provided
            v = _validate_text_input(v, min_length=1, max_length=MAX_CONTEXT_LENGTH)
            return cls._sanitize_text(v)
        return v

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Sanitize text to remove potentially dangerous content."""
        # HTML escape
        text = html.escape(text)

        # Remove dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        # Normalize whitespace
        return " ".join(text.split())

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

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace: replace multiple spaces/tabs/newlines with single space."""
        return " ".join(text.split())

    def _preprocess_text(self, text: str) -> str:
        """Text preprocessing."""
        # Use centralized validation
        text = _validate_text_input(text)
        
        # Basic cleaning
        text = self._normalize_whitespace(text)

        # Normalize quotes and dashes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        text = re.sub(r'[—–−]', ' ', text)

        # Remove common noise patterns
        text = re.sub(r'\b(um|uh|er|ah)\b', '', text, flags=re.IGNORECASE)

        # Normalize common abbreviations
        text = re.sub(r'\bvs\.', 'versus', text, flags=re.IGNORECASE)
        text = re.sub(r'\betc\.', 'etcetera', text, flags=re.IGNORECASE)

        # Final cleanup after all substitutions
        return self._normalize_whitespace(text)

    def _deduplicate_claims(self, claims: List[Claim]) -> List[Claim]:
        """Remove duplicate or very similar claims.
        
        Args:
            claims: List of claims to deduplicate
            
        Returns:
            List of deduplicated claims, sorted by check-worthiness (highest first)
        """
        if not claims:
            return claims

        # Sort by check-worthiness (highest first) to prioritize more important claims
        # when duplicates are found
        sorted_claims = sorted(claims, key=lambda x: x.check_worthiness, reverse=True)

        unique_claims = []
        seen_texts = set()

        for claim in sorted_claims:
            normalized_text = claim.text.lower().strip()
            
            # Skip empty normalized text
            if not normalized_text:
                continue

            # Only consider exact matches as duplicates
            if normalized_text not in seen_texts:
                unique_claims.append(claim)
                seen_texts.add(normalized_text)

        logger.info(f"Deduplicated claims: {len(claims)} -> {len(unique_claims)}")
        return unique_claims

    async def detect_claims(self, text: str, min_checkworthiness: float = 0.5) -> List[Claim]:
        """Detect claims in text using AI agent analysis."""
        try:
            # Preprocess text
            cleaned_text = self._preprocess_text(text)
            logger.info(f"Processing text of length {len(cleaned_text)}")

            # Handle very short texts
            if len(cleaned_text) < MIN_TEXT_LENGTH:
                logger.warning("Text too short for meaningful claim detection")
                return []

            # Use AI agent to analyze and extract claims
            result = await Runner.run(self.agent, cleaned_text)
            claims = result.final_output_as(List[Claim])

            # Limit number of claims returned
            if len(claims) > MAX_CLAIMS_PER_REQUEST:
                logger.warning(f"Too many claims detected, limiting to {MAX_CLAIMS_PER_REQUEST}")
                claims = claims[:MAX_CLAIMS_PER_REQUEST]

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

# Function for direct calls (used by tests and other code)
async def process_claims(text: str, min_checkworthiness: float = 0.5) -> List[Claim]:
    """Process input text and extract claims."""
    return await claim_detector.detect_claims(text, min_checkworthiness)

# Tool function for pipeline integration
@function_tool(
    name_override="process_claims",
    description_override="Process text to extract and analyze factual claims"
)
async def process_claims_tool(text: str, min_checkworthiness: float = 0.5) -> List[Claim]:
    """Process input text and extract claims (tool version for pipeline)."""
    return await claim_detector.detect_claims(text, min_checkworthiness)