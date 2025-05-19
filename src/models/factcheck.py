"""
Pydantic models for the VeriFact factchecking system.

This module contains the data models used throughout the application for:
- Claims: Factual statements identified for verification
- Evidence: Supporting or contradicting information for claims
- Verdicts: Final assessment of claim truthfulness
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class Claim(BaseModel):
    """A factual claim identified from text."""
    text: str = Field(..., description="The exact text of the claim")
    context: str = Field("", description="Surrounding context of the claim")
    checkworthy: bool = Field(True, description="Whether the claim is worth checking")
    domain: Optional[str] = Field(None, description="Domain/category of the claim (politics, health, etc.)")
    entities: List[str] = Field(default_factory=list, description="Named entities mentioned in the claim")


class Evidence(BaseModel):
    """Evidence related to a factual claim."""
    text: str = Field(..., description="The evidence text")
    source: str = Field(..., description="Source of the evidence (URL, document, etc.)")
    source_name: Optional[str] = Field(None, description="Name of the source")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    stance: Literal["supporting", "contradicting", "neutral"] = Field(..., 
                                                                      description="Whether evidence supports or contradicts the claim")
    timestamp: Optional[str] = Field(None, description="Publication date/time of the evidence")
    credibility: Optional[float] = Field(None, ge=0.0, le=1.0, description="Source credibility score (0-1)")


class Verdict(BaseModel):
    """Verdict on a factual claim."""
    claim: str = Field(..., description="The claim being verified")
    verdict: Literal["true", "false", "partially true", "unverifiable"] = Field(...,
                                                                                description="Final assessment of claim truthfulness")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict (0-1)")
    explanation: str = Field(..., description="Detailed explanation of the verdict")
    sources: List[str] = Field(..., description="Sources used for verification")


class FactcheckRequest(BaseModel):
    """Request model for factchecking API."""
    text: str = Field(..., description="Text containing claims to verify")
    options: Optional[dict] = Field(default_factory=dict, description="Optional configuration parameters")


class FactcheckResponse(BaseModel):
    """Response model for factchecking API."""
    claims: List[Verdict] = Field(..., description="Verified claims with verdicts")
    metadata: dict = Field(default_factory=dict, description="Processing metadata and statistics") 