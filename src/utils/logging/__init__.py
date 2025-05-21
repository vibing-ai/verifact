"""Logging utilities for VeriFact.

This module provides logging configuration and utilities for the VeriFact application.
"""

from src.utils.logging.logger import (
    get_component_logger,
    get_logger,
    log_performance,
    set_log_level,
)
from src.utils.logging.structured_logger import configure_logging
from src.utils.logging.metrics import (
    ClaimDetectorMetrics,
    MetricsTracker,
    create_performance_report,
    reset_metrics,
)

# Convenience re-exports
# Create logger instances for common components
logger = get_logger("verifact")
claim_detector_metrics = ClaimDetectorMetrics()

# Add alias for backward compatibility
from src.utils.logging.logger import get_component_logger, log_performance

__all__ = [
    "logger",
    "get_logger",
    "get_component_logger",
    "configure_logging",
    "set_log_level",
    "log_performance",
    "MetricsTracker",
    "ClaimDetectorMetrics",
    "claim_detector_metrics",
    "create_performance_report",
    "reset_metrics",
]
