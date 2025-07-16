import logging
import os

# Try to import json_log_formatter, but don't fail if it's not available
try:
    import json_log_formatter  # type: ignore[import-untyped]

    JSON_FORMATTER_AVAILABLE = True
except ImportError:
    JSON_FORMATTER_AVAILABLE = False


def setup_logging():
    """Configure logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    log_file = os.getenv("LOG_FILE")

    if log_format == "json":
        if JSON_FORMATTER_AVAILABLE:
            formatter = json_log_formatter.JSONFormatter()
        else:
            formatter = logging.Formatter(
                '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
            )
    else:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    handlers = []

    # Always log to console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    # Optionally log to file
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = handlers
    root_logger.propagate = False
