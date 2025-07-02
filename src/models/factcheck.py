from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source information for fact-checking."""
    url: str
    credibility: float = Field(ge=0.0, le=1.0)
    quote: str

class Claim(BaseModel):
    """Factual claim with verification results."""
    text: str
    context: str = Field(default="")
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    sources: list[Source]

class FactCheckOptions(BaseModel):
    """Configuration options for fact-checking."""
    min_check_worthiness: float = Field(default=0.7, ge=0.0, le=1.0)
    domains: list[str] = Field(default=["politics", "health"])
    max_claims: int = Field(default=5, gt=0)
    explanation_detail: str = Field(default="detailed")

class FactCheckRequest(BaseModel):
    """Request model for fact-checking."""
    text: str
    options: FactCheckOptions | None = FactCheckOptions()

class FactCheckResponse(BaseModel):
    """Response model for fact-checking."""
    claims: list[Claim]
    metadata: dict[str, Any]
