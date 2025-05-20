"""Integration tests.

This package contains integration tests:
- Database integration tests
- Pipeline integration tests
- Factcheck pipeline tests
"""

# Import test modules for discovery
from .test_db_integration import TestDBIntegration
from .test_factcheck_pipeline import TestFactcheckPipeline
from .test_pipeline_integration import TestPipelineIntegration

# Export test classes
__all__ = [
    "TestDBIntegration",
    "TestFactcheckPipeline",
    "TestPipelineIntegration"
]
