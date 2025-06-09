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
    context: str = Field(default="")
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

def _determine_domain(normalized_text: str, rules: list) -> str:
    """Determine the domain for a given text using claim rules."""
    for rule in rules:
        if re.search(rule.pattern, normalized_text.lower()):
            return rule.domain
    return "Other"

def _extract_entities_from_text(text_processor: TextProcessor, normalized_text: str) -> list[str]:
    """Extract entity names from normalized text."""
    entity_dicts = text_processor.extract_entities(normalized_text)
    return [entity["text"] for entity in entity_dicts]

def _process_single_sentence(
    sentence: str, 
    text: str, 
    text_processor: TextProcessor, 
    rules: list,
    min_checkworthiness: float = 0.5
) -> Claim | None:
    """Process a single sentence and return a Claim if it meets criteria."""
    normalized_text = text_processor.normalize_text(sentence)
    entities = _extract_entities_from_text(text_processor, normalized_text)
    domain = _determine_domain(normalized_text, rules)
    
    specificity, public_interest, impact, check_worthiness = calculate_scores(
        normalized_text, domain
    )
    
    confidence = calculate_confidence(
        normalized_text=normalized_text,
        domain=domain,
        entities=entities,
        specificity=specificity
    )
    
    if check_worthiness >= min_checkworthiness:
        context = extract_context(text, sentence)
        return Claim(
            text=normalized_text,
            context=context,
            domain=domain,
            specificity_score=specificity,
            public_interest_score=public_interest,
            impact_score=impact,
            check_worthiness=check_worthiness,
            confidence=confidence,
            entities=entities,
        )
    
    logger.debug("Filtered out claim with check-worthiness %.2f: %s", check_worthiness, normalized_text[:50])
    return None

def _validate_input(text: str) -> None:
    """Validate input text."""
    if not text or not isinstance(text, str):
        raise ValueError("Input text must be a non-empty string")

def extract_context(text: str, sentence: str, window_size: int = 2) -> str:
    """Extract context around a sentence from the original text.
    
    Args:
        text: The original full text
        sentence: The specific sentence being processed as a claim
        window_size: Number of sentences to include before and after (default: 2)
    
    Returns:
        str: Context around the sentence
    """
    text_processor = TextProcessor()
    all_sentences = text_processor.split_sentences(text)
    
    try:
        # Normalize the input sentence once for consistent comparison
        normalized_sentence = text_processor.normalize_text(sentence)

        # Find the index of the current sentence
        sentence_index = -1
        for i, sent in enumerate(all_sentences):
            if text_processor.normalize_text(sent) == sentence:
                sentence_index = i
                break
        
        if sentence_index == -1:
            return ""
        
        # Extract context window
        start_idx = max(0, sentence_index - window_size)
        end_idx = min(len(all_sentences), sentence_index + window_size + 1)
        
        context_sentences = all_sentences[start_idx:end_idx]
        # Remove the current sentence from context to avoid duplication
        context_sentences = [s for s in context_sentences if text_processor.normalize_text(s) != sentence]
        
        return " ".join(context_sentences).strip()
    
    except Exception as e:
        logger.warning(f"Error extracting context: {e}")
        return ""

async def process_claims(text: str, min_checkworthiness: float = 0.5) -> list[Claim]:
    """Process input text and extract claims.

    Args:
        text: The input text to process
        min_checkworthiness: Minimum check-worthiness score to include a claim

    Returns:
        list[Claim]: A list of detected claims

    Raises:
        ValueError: If the input text is empty or invalid
    """
    text_processor = TextProcessor()
    rules = ClaimRules.get_default_rules()
    logger.info("Claim detection initialized with %d rules", len(rules))
    try:
        _validate_input(text)

        logger.info("Processing text of length %d", len(text))

        # Use TextProcessor for sentence splitting
        sentences = text_processor.split_sentences(text)
        claims: list[Claim] = []

        for sentence in sentences:
            claim = _process_single_sentence(sentence, text, text_processor, rules, min_checkworthiness)
            if claim:
                claims.append(claim)
                logger.debug("Added claim with check-worthiness %.2f: %s", claim.check_worthiness, claim.text[:50])
        
        logger.info("Extracted %d claims from text (filtered from %d sentences)", len(claims), len(sentences))
        return claims

    except Exception as e:
        logger.error("Error processing text: %s", str(e), exc_info=True)
        raise

@function_tool(
    name_override="process_claims",
    description_override="Process text to extract and analyze factual claims"
)
async def process_claims_tool(text: str, min_checkworthiness: float = 0.5) -> list[Claim]:
    """Process input text and extract claims."""
    return await process_claims(text, min_checkworthiness)

claim_detector_agent = Agent(
    name="ClaimDetector",
    instructions=PROMPT,
    output_type=list[Claim],
    tools=[process_claims_tool],
    model=os.getenv("CLAIM_DETECTOR_MODEL")
)
