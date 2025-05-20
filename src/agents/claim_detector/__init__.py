"""
ClaimDetector agent for identifying factual claims in text.

This module is responsible for extracting check-worthy factual claims
from user-submitted text.
"""

from src.agents.claim_detector.detector import ClaimDetector
from src.agents.claim_detector.domain_classifier import DomainClassifier
from src.agents.claim_detector.entity_extractor import EntityExtractor
from src.agents.claim_detector.models import Claim, ClaimDomain, Entity, EntityType

__all__ = [
    "ClaimDetector",
    "Claim",
    "Entity",
    "EntityType",
    "ClaimDomain",
    "DomainClassifier",
    "EntityExtractor",
]
