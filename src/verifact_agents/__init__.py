"""VeriFact agent module for factchecking.

This package contains the three main agents:
- ClaimDetector: Identifies factual claims in text
- EvidenceHunter: Gathers evidence for claims
- VerdictWriter: Analyzes evidence and generates verdicts

Note: This module was renamed from 'agents' to 'verifact_agents' to avoid
namespace conflicts with the OpenAI Agents SDK.
"""

# Add a flag to indicate this is the local agents module, not the OpenAI one
IS_LOCAL_AGENTS_MODULE = True

# Export public components
from src.verifact_agents.claim_detector import ClaimDetector
from src.verifact_agents.evidence_hunter import EvidenceHunter
from src.verifact_agents.verdict_writer import VerdictWriter

__all__ = ["ClaimDetector", "EvidenceHunter", "VerdictWriter"]
