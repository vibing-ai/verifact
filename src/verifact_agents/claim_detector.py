"""Claim detection agent for VeriFact.

This module provides the claim detection agent that identifies factual claims
in text using rule-based processing and pattern matching.
"""
import os
import logging
import re
from pydantic import BaseModel, Field

from agents import Agent, function_tool
from .text_processor import TextProcessor
from .claim_rules import ClaimRules, calculate_scores

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keep the original PROMPT as a constant
PROMPT = """
You are a claim detection agent designed to identify factual claims from text that require verification.
Your task is to:
1. Identify explicit and implicit factual claims in the input text
2. Return the claims in a structured format

The system will automatically:
- Score claims for check-worthiness, specificity, public interest, and impact
- Extract and categorize entities
- Classify claims by domain
- Filter out non-factual claims

For each claim, return:
The original claim text
"""


class Claim(BaseModel):
    """A factual claim that requires verification."""
    text: str
    check_worthiness: float = Field(default=0.0, ge=0.0, le=1.0)
    domain: str = Field(default="Other")
    specificity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    public_interest_score: float = Field(default=0.0, ge=0.0, le=1.0)
    impact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: list[str] = Field(default_factory=list)
    # rank: int = Field(default=0)
    # is_compound: bool = Field(default=False)
    # sub_claims: list['Claim'] = Field(default_factory=list)

def calculate_confidence(
    normalized_text: str,
    domain: str,
    entities: list[str],
    specificity: float
) -> float:
    """Calculate confidence score based on multiple factors."""
    base_confidence = 0.7

    # Adjust based on domain
    domain_confidence = {
        "science": 1.1,
        "nature": 1.1,
        "health": 1.2,
        "technology": 1.0,
        "statistics": 1.2,
        "general": 0.9,
        "Other": 0.8
    }
    base_confidence *= domain_confidence.get(domain, 0.8)

    # Adjust based on entity presence
    if entities:
        base_confidence *= min(1.2, 1.0 + (len(entities) * 0.1))

    # Adjust based on specificity
    base_confidence *= (0.8 + (specificity * 0.4))  # Range: 0.8 to 1.2

    # Check for opinion indicators
    for indicator, _ in ClaimRules.SCORING_RULES["opinion_indicators"]:
        if re.search(indicator, normalized_text.lower()):
            base_confidence *= 0.8
            break

    return min(1.0, base_confidence)

async def process_claims(text: str) -> list[Claim]:
    """Process input text and extract claims.

    Args:
        text: The input text to process

    Returns:
        list[Claim]: A list of detected claims

    Raises:
        ValueError: If the input text is empty or invalid
    """
    text_processor = TextProcessor()
    rules = ClaimRules.get_default_rules()
    logger.info("Claim detection initialized with %d rules", len(rules))
    try:
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string")

        logger.info("Processing text of length %d", len(text))

        # Use TextProcessor for sentence splitting
        sentences = text_processor.split_sentences(text)
        claims: list[Claim] = []

        for sentence in sentences:
            normalized_text = text_processor.normalize_text(sentence)
            entities = text_processor.extract_entities(normalized_text)

            # Determine domain using ClaimRules
            domain = "Other"
            for rule in rules:
                if re.search(rule.pattern, normalized_text.lower()):
                    domain = rule.domain
                    break
            specificity, public_interest, impact, check_worthiness = calculate_scores(
                normalized_text, domain
            )

            # Calculate confidence based on multiple factors
            confidence = calculate_confidence(
                normalized_text=normalized_text,
                domain=domain,
                entities=entities,
                specificity=specificity
            )

            claim = Claim(
                text=normalized_text,
                domain=domain,
                specificity_score=specificity,
                public_interest_score=public_interest,
                impact_score=impact,
                check_worthiness=check_worthiness,
                confidence=confidence,
                entities=entities,
                # rank=0,
                # is_compound=False,
                # sub_claims=[]
            )
            claims.append(claim)

        logger.info("Extracted %d claims from text", len(claims))
        return claims

    except Exception as e:
        logger.error("Error processing text: %s", str(e), exc_info=True)
        raise

@function_tool(
    name_override="process_claims",
    description_override="Process text to extract and analyze factual claims"
)
async def process_claims_tool(text: str) -> list[Claim]:
    """Process input text and extract claims."""
    return await process_claims(text)

claim_detector_agent = Agent(
    name="ClaimDetector",
    instructions=PROMPT,
    output_type=list[Claim],
    tools=[process_claims_tool],
    model=os.getenv("CLAIM_DETECTOR_MODEL")
)
