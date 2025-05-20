"""Tests for agent components.

This package contains tests for all agent components:
- ClaimDetector
- AgentDetector
- EvidenceHunter
- VerdictWriter
"""

# Import test modules for discovery
from .test_agent_detector import TestAgentDetector
from .test_claim_detector import TestClaimDetector
from .test_evidence_hunter import TestEvidenceHunter
from .test_verdict_writer import TestVerdictWriter

# Export test classes
__all__ = [
    "TestAgentDetector",
    "TestClaimDetector",
    "TestEvidenceHunter",
    "TestVerdictWriter",
]
