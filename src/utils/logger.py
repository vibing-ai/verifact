"""
Logging utilities for the VeriFact application.

This module provides a standardized logging setup for the application,
with support for various outputs (console, file) and log levels.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, Dict, Any

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Log levels mapping
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO, 
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}


def setup_logger(
    name: str = "verifact",
    level: Union[str, int] = "info",
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    Args:
        name: Logger name
        level: Log level (debug, info, warning, error, critical)
        log_file: Optional path to log file
        log_format: Log message format
        max_file_size: Maximum size of each log file in bytes
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    # Convert string level to logging level constant
    if isinstance(level, str):
        level = LOG_LEVELS.get(level.lower(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # If the logger already has handlers, return it to avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if specified
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "verifact") -> logging.Logger:
    """
    Get a logger for the specified name, creating it if necessary.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    # Get environment variables for logging configuration
    log_level = os.getenv("LOG_LEVEL", "info")
    log_file = os.getenv("LOG_FILE")
    
    # Get or create the logger
    logger = logging.getLogger(name)
    
    # If the logger hasn't been configured yet, set it up
    if not logger.handlers:
        return setup_logger(name, log_level, log_file)
    
    return logger


# Create default logger
logger = get_logger() 