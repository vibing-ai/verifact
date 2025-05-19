"""
ClaimDetector agent for identifying factual claims in text.

This module is responsible for extracting check-worthy factual claims
from user-submitted text.
"""

from src.agents.claim_detector.detector import ClaimDetector, Claim

__all__ = ["ClaimDetector", "Claim"] 