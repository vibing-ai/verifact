"""
Tests package for the VeriFact application.

This package contains tests for all components of the VeriFact application, including:
- Agent tests (ClaimDetector, EvidenceHunter, VerdictWriter)
- API tests
- Model tests
- Utility tests
"""

# Export test functions for discovery
from src.tests.test_claim_detector import *
from src.tests.test_evidence_hunter import *
from src.tests.test_verdict_writer import *
from src.tests.test_api import * 