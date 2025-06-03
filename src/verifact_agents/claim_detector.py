import os
from typing import Optional
from pydantic import BaseModel, Field
from agents import Agent

class Claim(BaseModel):
    """A factual claim that requires verification."""
    
    # Add model configuration for strict schema compliance
    model_config = {"extra": "forbid"}
    
    text: str = Field(..., description="The original claim text as it appeared in the input.")

    normalized_text: str = Field(..., description="A normalized version of the claim, with standardized formatting and phrasing.")
    
    check_worthiness_score: float = Field(..., ge=0.0, le=1.0, description="Overall check-worthiness score (0.0-1.0).")
    
    specificity_score: float = Field(..., ge=0.0, le=1.0, description="Specificity of the claim (0.0-1.0).")
    
    public_interest_score: float = Field(..., ge=0.0, le=1.0, description="Public interest score (0.0-1.0).")
    
    impact_score: float = Field(..., ge=0.0, le=1.0, description="Potential impact score if true/false (0.0-1.0).")
    
    detection_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the detection of this claim (0.0-1.0).")
    
    domain: str = Field(..., description="The domain classification of the claim (e.g., Politics, Science, Health).")
    
    entities: Optional[list[dict[str, str]]] = Field(default_factory=[], description="A list of extracted entities with their types.")
    
    compound_claim_parts: Optional[list[str]] = Field(default=None, description="If a compound claim, the separate checkable statements.")
    
    rank: int = Field(..., description="Rank of the claim in order of importance for fact-checking.")


PROMPT = """
You are a claim detection agent designed to identify factual claims from text that require verification.
Your task is to:
1. Identify explicit and implicit factual claims
2. Score each claim's check-worthiness, specificity, public interest, and impact
3. Extract and categorize entities mentioned in claims
4. Classify claims by domain (politics, science, health, etc.)
5. Normalize claims to a standard format
6. Split compound claims into separate checkable statements
7. Rank claims by overall importance for fact-checking

FACTUAL CLAIMS:
- Are statements presented as facts
- Can be verified with evidence
- Make specific, measurable assertions
- Examples: statistical claims, historical facts, scientific statements

NOT FACTUAL CLAIMS:
- Personal opinions ("I think pizza is delicious")
- Subjective judgments ("This is the best movie")
- Hypotheticals ("If it rains tomorrow...")
- Pure predictions about future events ("Next year's winner will be...")
- Questions ("Is climate change real?")

DISTINCTNESS:
Ensure each claim is distinct and doesn't substantially overlap with other claims.
If a statement contains multiple related but distinct claims, separate them.

CHECK-WORTHINESS SCORING:
Rate claims from 0.0-1.0 based on:
- Specificity (specificity_score): How specific and measurable the claim is (0.0-1.0)
- Public interest (public_interest_score): Relevance to public figures/institutions (0.0-1.0)
- Potential impact (impact_score): Significance of consequences if true/false (0.0-1.0)
- Overall check_worthiness should be a weighted combination of these factors

RANKING CRITERIA:
Rank claims in order of importance for fact-checking, considering:
1. Check-worthiness score (primary factor)
2. Specificity of the claim (easier to verify)
3. Domain importance (health/safety claims prioritized)
4. Public interest value
5. Potential impact if the claim is true/false

ENTITY EXTRACTION:
Identify entities such as:
- People, organizations, locations
- Dates, times, numbers, statistics, percentages
- Products, technologies, scientific terms

DOMAIN CLASSIFICATION:
Assign claims to the most relevant domain:
- Politics, Economics, Health, Science, Technology
- Environment, Education, Entertainment, Sports, Other

CLAIM NORMALIZATION:
- Standardize formatting and phrasing
- Resolve pronouns to their antecedents
- Expand abbreviations and acronyms
- Standardize numerical expressions

COMPOUND CLAIMS:
If a statement contains multiple verifiable claims, break it down into separate checkable statements.

For each claim, return:
1. The original claim text
2. A normalized version of the claim
3. Check-worthiness score (0.0-1.0)
4. Specificity score (0.0-1.0)
5. Public interest score (0.0-1.0)
6. Impact score (0.0-1.0)
7. Confidence in detection (0.0-1.0)
8. Domain classification
9. Extracted entities with types
10. Parts of compound claims (if applicable)
11. Rank (relative to other claims)

For each claim, return a JSON object adhering to the following Pydantic model structure (example):

{
  "text": "The Eiffel Tower is 330 meters tall and was completed in 1889.",
  "normalized_text": "The Eiffel Tower has a height of 330 meters and its construction was finished in the year 1889.",
  "check_worthiness_score": 0.9,
  "specificity_score": 0.95,
  "public_interest_score": 0.7,
  "impact_score": 0.5,
  "detection_confidence": 0.98,
  "domain": "History",
  "entities": [
    {"text": "Eiffel Tower", "type": "Landmark"},
    {"text": "330 meters", "type": "Measurement"},
    {"text": "1889", "type": "Date"}
  ],
  "compound_claim_parts": [
    "The Eiffel Tower is 330 meters tall.",
    "The Eiffel Tower was completed in 1889."
  ],
  "rank": 1
}
"""

claim_detector_agent = Agent(
    name="ClaimDetector",
    instructions=PROMPT,
    output_type=list[Claim],
    tools=[],
    model=os.getenv("CLAIM_DETECTOR_MODEL"),
)