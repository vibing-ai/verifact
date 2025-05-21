"""Backwards compatibility module for logging.

This module re-exports the necessary functions and classes from the new
logging modules to maintain compatibility with existing code.
"""

# Re-export from structured logger
from src.utils.logging.structured_logger import (
    configure_logging,
    get_structured_logger as get_component_logger,
    set_component_context,
)

# Re-export from logger
from src.utils.logging.logger import (
    get_logger,
    log_performance,
    request_context,
    performance_timer,
    set_log_level,
)

# Re-export from metrics
from src.utils.logging.metrics import (
    MetricsTracker, 
    ClaimDetectorMetrics,
    create_performance_report,
    reset_metrics,
)

# Create logger instances for common components
logger = get_logger("verifact")

__all__ = [
    "logger",
    "get_logger",
    "get_component_logger",
    "configure_logging",
    "log_performance",
    "request_context", 
    "performance_timer",
    "set_component_context",
    "set_log_level",
    "MetricsTracker",
    "ClaimDetectorMetrics",
    "create_performance_report",
    "reset_metrics",
] 