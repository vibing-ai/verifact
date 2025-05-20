"""
Logging utilities for VeriFact.

This module provides a comprehensive logging framework with support for structured JSON logging,
component-specific loggers, context tracking, and performance monitoring.
"""

from src.utils.logging.logger import (
    get_logger, 
    get_component_logger, 
    request_context, 
    performance_timer, 
    log_performance, 
    LogManager
)
from src.utils.logging.metrics import MetricsTracker, claim_detector_metrics

__all__ = [
    "get_logger",
    "get_component_logger",
    "request_context",
    "performance_timer",
    "log_performance",
    "LogManager",
    "MetricsTracker",
    "claim_detector_metrics"
] 