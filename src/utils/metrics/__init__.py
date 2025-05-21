"""Metrics utilities for VeriFact.

This module provides classes and functions for tracking and reporting performance metrics.
"""

from src.utils.metrics.db_metrics import ConnectionPoolMetrics
from src.utils.logging.metrics import ClaimDetectorMetrics

# Create metrics instances
claim_detector_metrics = ClaimDetectorMetrics()

__all__ = [
    "ConnectionPoolMetrics",
    "ClaimDetectorMetrics",
    "claim_detector_metrics",
]
