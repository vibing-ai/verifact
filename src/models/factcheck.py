from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Source(BaseModel):
    url: str
    credibility: float = Field(ge=0.0, le=1.0)
    quote: str

class Claim(BaseModel):
    text: str
    context: str = Field(default="")
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    sources: List[Source]

class FactCheckOptions(BaseModel):
    min_check_worthiness: float = Field(default=0.7, ge=0.0, le=1.0)
    domains: List[str] = Field(default=["politics", "health"])
    max_claims: int = Field(default=5, gt=0)
    explanation_detail: str = Field(default="detailed")

class FactCheckRequest(BaseModel):
    text: str
    options: Optional[FactCheckOptions] = FactCheckOptions()

class FactCheckResponse(BaseModel):
    claims: List[Claim]
    metadata: Dict[str, Any] 