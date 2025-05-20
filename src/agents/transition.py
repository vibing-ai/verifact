"""
Transition utilities for migrating from the old agent architecture to the new one.

This module provides adapter functions and utilities to ease the transition from
the old agent implementation to the new, more modular architecture with proper
separation of concerns.
"""

import warnings
from typing import List, Optional, Union

# Import from old implementation
from src.agents.claim_detector.models import Claim as LegacyClaim

# Import from new implementation
from src.agents.dto import Claim, DTOFactory, Evidence, Verdict
from src.agents.evidence_hunter.hunter import Evidence as LegacyEvidence
from src.agents.interfaces import (
    ClaimDetector,
    EvidenceHunter,
    IClaimDetector,
    IEvidenceHunter,
    IVerdictWriter,
    VerdictWriter,
)
from src.agents.verdict_writer.writer import Verdict as LegacyVerdict


def adapt_claim_detector(detector: Union[ClaimDetector, IClaimDetector]) -> ClaimDetector:
    """
    Adapt any claim detector implementation to the new ClaimDetector interface.
    
    Args:
        detector: A claim detector implementation (either new or legacy)
        
    Returns:
        ClaimDetector: An adapter that implements the new ClaimDetector interface
    """
    if isinstance(detector, ClaimDetector):
        return detector
    
    # Create an adapter for legacy detectors
    warnings.warn(
        "Using legacy IClaimDetector implementation. Consider migrating to the new ClaimDetector interface.",
        DeprecationWarning, stacklevel=2
    )
    
    class ClaimDetectorAdapter(ClaimDetector):
        async def detect_claims(self, text: str, min_check_worthiness: Optional[float] = None,
                               expected_claims: Optional[List[dict]] = None,
                               max_claims: Optional[int] = None) -> List[Claim]:
            # Call the legacy implementation
            legacy_claims = await detector.detect_claims(
                text, min_check_worthiness, expected_claims, max_claims
            )
            
            # Convert legacy claims to new DTOs
            return [DTOFactory.claim_from_legacy(claim) for claim in legacy_claims]
        
        async def process(self, input_data: str) -> List[Claim]:
            return await self.detect_claims(input_data)
    
    return ClaimDetectorAdapter()


def adapt_evidence_hunter(hunter: Union[EvidenceHunter, IEvidenceHunter]) -> EvidenceHunter:
    """
    Adapt any evidence hunter implementation to the new EvidenceHunter interface.
    
    Args:
        hunter: An evidence hunter implementation (either new or legacy)
        
    Returns:
        EvidenceHunter: An adapter that implements the new EvidenceHunter interface
    """
    if isinstance(hunter, EvidenceHunter):
        return hunter
    
    # Create an adapter for legacy hunters
    warnings.warn(
        "Using legacy IEvidenceHunter implementation. Consider migrating to the new EvidenceHunter interface.",
        DeprecationWarning, stacklevel=2
    )
    
    class EvidenceHunterAdapter(EvidenceHunter):
        async def gather_evidence(self, claim: Claim) -> List[Evidence]:
            # Convert new DTO to legacy claim for backward compatibility
            legacy_claim = convert_to_legacy_claim(claim)
            
            # Call the legacy implementation
            legacy_evidence = await hunter.gather_evidence(legacy_claim)
            
            # Convert legacy evidence to new DTOs
            return [DTOFactory.evidence_from_legacy(ev) for ev in legacy_evidence]
        
        async def process(self, input_data: Claim) -> List[Evidence]:
            return await self.gather_evidence(input_data)
    
    return EvidenceHunterAdapter()


def adapt_verdict_writer(writer: Union[VerdictWriter, IVerdictWriter]) -> VerdictWriter:
    """
    Adapt any verdict writer implementation to the new VerdictWriter interface.
    
    Args:
        writer: A verdict writer implementation (either new or legacy)
        
    Returns:
        VerdictWriter: An adapter that implements the new VerdictWriter interface
    """
    if isinstance(writer, VerdictWriter):
        return writer
    
    # Create an adapter for legacy writers
    warnings.warn(
        "Using legacy IVerdictWriter implementation. Consider migrating to the new VerdictWriter interface.",
        DeprecationWarning, stacklevel=2
    )
    
    class VerdictWriterAdapter(VerdictWriter):
        async def generate_verdict(self, claim: Claim, evidence: List[Evidence],
                            explanation_detail: Optional[str] = None,
                            citation_style: Optional[str] = None,
                            include_alternative_perspectives: Optional[bool] = None) -> Verdict:
            # Convert new DTOs to legacy models for backward compatibility
            legacy_claim = convert_to_legacy_claim(claim)
            legacy_evidence = [convert_to_legacy_evidence(ev) for ev in evidence]
            
            # Call the legacy implementation
            legacy_verdict = await writer.generate_verdict(
                legacy_claim, legacy_evidence,
                explanation_detail, citation_style, include_alternative_perspectives
            )
            
            # Convert legacy verdict to new DTO
            return DTOFactory.verdict_from_legacy(legacy_verdict)
        
        async def process(self, input_data: tuple[Claim, List[Evidence]]) -> Verdict:
            claim, evidence = input_data
            return await self.generate_verdict(claim, evidence)
    
    return VerdictWriterAdapter()


def convert_to_legacy_claim(claim: Claim) -> LegacyClaim:
    """Convert a new Claim DTO to a legacy Claim model."""
    # Import here to avoid circular imports
    from src.agents.claim_detector.models import ClaimDomain, Entity, EntityType

    # Create entities list
    entities = []
    for entity_dict in claim.entities:
        # Convert entity dictionary to Entity object
        entity_type = entity_dict.get("type", "other")
        try:
            # Try to convert to EntityType enum
            entity_type_enum = EntityType(entity_type)
        except ValueError:
            # Default to OTHER if not a valid enum value
            entity_type_enum = EntityType.OTHER
            
        entity = Entity(
            text=entity_dict.get("text", ""),
            type=entity_type_enum,
            normalized_text=entity_dict.get("normalized_text"),
            relevance=entity_dict.get("relevance", 1.0)
        )
        entities.append(entity)
    
    # Create domain
    try:
        domain = ClaimDomain(claim.domain)
    except ValueError:
        domain = ClaimDomain.OTHER
    
    # Create and return the legacy claim
    return LegacyClaim(
        text=claim.text,
        original_text=claim.original_text,
        context=claim.context,
        check_worthiness=claim.check_worthiness,
        confidence=claim.confidence,
        domain=domain,
        sub_domains=claim.sub_domains,
        entities=entities,
        source_location=claim.source_location,
        normalized_text=claim.normalized_text,
        compound_parts=claim.compound_parts,
        extracted_at=claim.extracted_at,
        rank=claim.rank,
        specificity_score=claim.specificity_score,
        public_interest_score=claim.public_interest_score,
        impact_score=claim.impact_score
    )


def convert_to_legacy_evidence(evidence: Evidence) -> LegacyEvidence:
    """Convert a new Evidence DTO to a legacy Evidence model."""
    return LegacyEvidence(
        content=evidence.content,
        source=evidence.source,
        relevance=evidence.relevance,
        stance=evidence.stance
    )


def convert_to_legacy_verdict(verdict: Verdict) -> LegacyVerdict:
    """Convert a new Verdict DTO to a legacy Verdict model."""
    return LegacyVerdict(
        claim=verdict.claim,
        verdict=verdict.verdict,
        confidence=verdict.confidence,
        explanation=verdict.explanation,
        sources=verdict.sources,
        evidence_summary=verdict.evidence_summary,
        alternative_perspectives=verdict.alternative_perspectives,
        key_evidence=verdict.key_evidence,
        citation_metadata=verdict.citation_metadata
    ) 