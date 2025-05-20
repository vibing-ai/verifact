"""
Data Transfer Objects for the agent system.

This module defines immutable data classes for inter-agent communication,
ensuring clean boundaries between agents.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

# Re-export original models for backward compatibility


@dataclass(frozen=True)
class Claim:
    """Immutable representation of a factual claim."""
    text: str
    original_text: str
    context: str = ""
    check_worthiness: float = 0.0
    confidence: float = 1.0
    domain: str = "other"
    sub_domains: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    source_location: Optional[Dict[str, Any]] = None
    normalized_text: Optional[str] = None
    compound_parts: List[str] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.now)
    rank: Optional[int] = None
    specificity_score: float = 0.0
    public_interest_score: float = 0.0
    impact_score: float = 0.0
    
    def __post_init__(self):
        """Validate claim data after initialization."""
        if not self.text.strip():
            raise ValueError("Claim text cannot be empty")
        if not 0.0 <= self.check_worthiness <= 1.0:
            raise ValueError("Check-worthiness must be between 0.0 and 1.0")


@dataclass(frozen=True)
class Evidence:
    """Immutable representation of evidence for a claim."""
    content: str
    source: str
    relevance: float = 1.0
    stance: str = "supporting"  # supporting, contradicting, neutral
    
    def __post_init__(self):
        """Validate evidence data after initialization."""
        if not self.content.strip():
            raise ValueError("Evidence content cannot be empty")
        if not self.source.strip():
            raise ValueError("Evidence source cannot be empty")
        if not 0.0 <= self.relevance <= 1.0:
            raise ValueError("Relevance must be between 0.0 and 1.0")


@dataclass(frozen=True)
class Verdict:
    """Immutable representation of a factchecking verdict."""
    claim: str
    verdict: Literal["true", "false", "partially true", "unverifiable"]
    confidence: float
    explanation: str
    sources: List[str]
    evidence_summary: Optional[str] = None
    alternative_perspectives: Optional[str] = None
    key_evidence: Optional[List[Dict]] = None
    citation_metadata: Optional[Dict] = None
    
    def __post_init__(self):
        """Validate verdict data after initialization."""
        if not self.claim.strip():
            raise ValueError("Verdict claim cannot be empty")
        if not self.explanation.strip():
            raise ValueError("Verdict explanation cannot be empty")
        if not self.sources:
            raise ValueError("Verdict must have at least one source")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


# Factory for creating DTOs from legacy models
class DTOFactory:
    """Factory for creating DTOs from legacy model instances."""
    
    @staticmethod
    def claim_from_legacy(legacy_claim) -> Claim:
        """Create a Claim DTO from a legacy Claim model."""
        return Claim(
            text=legacy_claim.text,
            original_text=legacy_claim.original_text,
            context=legacy_claim.context,
            check_worthiness=legacy_claim.check_worthiness,
            confidence=legacy_claim.confidence,
            domain=str(legacy_claim.domain),
            sub_domains=legacy_claim.sub_domains,
            entities=[e.dict() for e in legacy_claim.entities],
            source_location=legacy_claim.source_location,
            normalized_text=legacy_claim.normalized_text,
            compound_parts=legacy_claim.compound_parts,
            extracted_at=legacy_claim.extracted_at,
            rank=legacy_claim.rank,
            specificity_score=legacy_claim.specificity_score,
            public_interest_score=legacy_claim.public_interest_score,
            impact_score=legacy_claim.impact_score
        )
    
    @staticmethod
    def evidence_from_legacy(legacy_evidence) -> Evidence:
        """Create an Evidence DTO from a legacy Evidence model."""
        return Evidence(
            content=legacy_evidence.content,
            source=legacy_evidence.source,
            relevance=legacy_evidence.relevance,
            stance=legacy_evidence.stance
        )
    
    @staticmethod
    def verdict_from_legacy(legacy_verdict) -> Verdict:
        """Create a Verdict DTO from a legacy Verdict model."""
        return Verdict(
            claim=legacy_verdict.claim,
            verdict=legacy_verdict.verdict,
            confidence=legacy_verdict.confidence,
            explanation=legacy_verdict.explanation,
            sources=legacy_verdict.sources,
            evidence_summary=legacy_verdict.evidence_summary,
            alternative_perspectives=legacy_verdict.alternative_perspectives,
            key_evidence=legacy_verdict.key_evidence,
            citation_metadata=legacy_verdict.citation_metadata
        ) 