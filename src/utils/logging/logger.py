"""
Comprehensive logging framework for VeriFact.

This module provides a unified logging system with support for:
1. Structured JSON logging
2. Component-specific loggers
3. Context tracking across components
4. Log rotation
5. Performance tracking
6. Secure logging (filtering sensitive data)

The framework supports different environments (development, production)
with appropriate log levels and outputs.
"""

import json
import logging
import os
import re
import sys
import uuid
import time
from contextlib import contextmanager
from functools import wraps
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

# For performance timing

# For JSON logging
try:
    import pythonjsonlogger.jsonlogger as jsonlogger
except ImportError:
    # Create fallback JSON logging implementation
    class JsonFormatter(logging.Formatter):
        """Simple JSON formatter if python-json-logger is not available."""

        def format(self, record):
            log_data = {
                'timestamp': self.formatTime(record, self.datefmt),
                'name': record.name,
                'level': record.levelname,
                'message': record.getMessage(),
            }

            # Add exception info if available
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)

            # Add custom fields from record
            for key, value in record.__dict__.items():
                if key not in [
                    'args',
                    'asctime',
                    'created',
                    'exc_info',
                    'exc_text',
                    'filename',
                    'funcName',
                    'id',
                    'levelname',
                    'levelno',
                    'lineno',
                    'module',
                    'msecs',
                    'message',
                    'msg',
                    'name',
                    'pathname',
                    'process',
                    'processName',
                    'relativeCreated',
                    'stack_info',
                    'thread',
                        'threadName']:
                    log_data[key] = value

            return json.dumps(log_data)

    jsonlogger = type('jsonlogger', (), {'JsonFormatter': JsonFormatter})

# Default log formats
DEFAULT_TEXT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_JSON_FORMAT = "%(timestamp)s %(name)s %(levelname)s %(message)s"

# Environment detection
ENVIRONMENT = os.getenv("VERIFACT_ENV", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

# Log levels mapping
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Default log level based on environment
DEFAULT_LOG_LEVEL = "info" if IS_PRODUCTION else "debug"

# Sensitive data patterns to mask (API keys, auth tokens, etc.)
SENSITIVE_PATTERNS = [
    re.compile(
        r'(["\'](sk-|api[_-]?key|token|secret|password|auth|key)["\']:\s*["\']).+?(["\'])',
        re.IGNORECASE),
    re.compile(
        r'(bearer\s+)(\S+)',
        re.IGNORECASE),
    re.compile(
        r'(authorization:\s*bearer\s+)(\S+)',
        re.IGNORECASE),
    re.compile(
        r'(api[_-]?key[=:]\s*)(\S+)',
        re.IGNORECASE),
    re.compile(
        r'((openrouter|openai|anthropic|mistral|google|azure|cohere)[_-]?api[_-]?key[=:]\s*)(\S+)',
        re.IGNORECASE),
]

# Cache of created loggers
_LOGGERS = {}

# Thread-local storage for request context
try:
    from contextvars import ContextVar

    # Context variables for tracking request context across async boundaries
    request_id_var: ContextVar[str] = ContextVar('request_id', default='')
    component_var: ContextVar[str] = ContextVar('component', default='')
    context_data_var: ContextVar[Dict[str, Any]
                                 ] = ContextVar('context_data', default={})
except ImportError:
    # Fallback for older Python versions
    request_id_var = None
    component_var = None
    context_data_var = None
    import threading
    _thread_local = threading.local()
    _thread_local.request_id = ''
    _thread_local.component = ''
    _thread_local.context_data = {}


class SensitiveFilter(logging.Filter):
    """Filter to remove sensitive information from logs."""

    def filter(self, record):
        # Don't modify the original record if it doesn't have a message
        if not hasattr(record, 'msg') or not record.msg:
            return True

        # Convert message to string if it's not already
        if not isinstance(record.msg, str):
            # If it's a dict or other serializable object, convert safely
            try:
                if isinstance(record.msg, dict):
                    # Clone the dictionary to avoid modifying the original
                    record.msg = self._redact_dict(record.msg.copy())
                    return True
                record.msg = str(record.msg)
            except Exception:
                # If conversion fails, let it pass through
                return True

        # Apply each pattern to redact sensitive data
        for pattern in SENSITIVE_PATTERNS:
            if isinstance(record.msg, dict):
                record.msg = self._redact_dict(record.msg)
            else:
                record.msg = pattern.sub(r'\1*****\3', record.msg)

        return True

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive values in a dictionary."""
        sensitive_keys = {
            'api_key',
            'key',
            'secret',
            'password',
            'token',
            'authorization'}

        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = self._redact_dict(v)
            elif isinstance(v, str) and (
                any(sensitive in k.lower() for sensitive in sensitive_keys) or
                any(pattern.search(v) for pattern in SENSITIVE_PATTERNS)
            ):
                data[k] = '*****'

        return data


class ContextFilter(logging.Filter):
    """Filter that adds request context to log records."""

    def filter(self, record):
        # Add request ID if available
        if request_id_var is not None:
            record.request_id = request_id_var.get('')
        else:
            record.request_id = getattr(_thread_local, 'request_id', '')

        # Add component name if available
        if component_var is not None:
            record.component = component_var.get('')
        else:
            record.component = getattr(_thread_local, 'component', '')

        # Add additional context data
        if context_data_var is not None:
            context = context_data_var.get({})
        else:
            context = getattr(_thread_local, 'context_data', {})

        for key, value in context.items():
            setattr(record, key, value)

        return True


class LogManager:
    """
    Central manager for logging configuration and retrieval.

    This class provides a centralized interface for configuring loggers,
    maintaining context across components, and tracking performance.
    """

    def __init__(self):
        """Initialize the LogManager."""
        self.configured = False
        self.default_config = {
            'level': os.getenv('LOG_LEVEL', DEFAULT_LOG_LEVEL),
            'json_logging': os.getenv('LOG_JSON', 'false').lower() == 'true',
            'log_file': os.getenv('LOG_FILE', None),
            # 10 MB
            'rotation_size': int(os.getenv('LOG_ROTATION_SIZE', '10485760')),
            'rotation_count': int(os.getenv('LOG_ROTATION_COUNT', '5')),
            'daily_rotation': os.getenv('LOG_DAILY_ROTATION', 'false').lower() == 'true',
        }

    def configure(self,
                  level: Optional[Union[str, int]] = None,
                  json_logging: Optional[bool] = None,
                  log_file: Optional[str] = None,
                  rotation_size: Optional[int] = None,
                  rotation_count: Optional[int] = None,
                  daily_rotation: Optional[bool] = None) -> None:
        """
        Configure the logging system.

        Args:
            level: Log level (debug, info, warning, error, critical)
            json_logging: Whether to use JSON-formatted logs
            log_file: Path to log file
            rotation_size: Maximum size of each log file in bytes
            rotation_count: Number of backup log files to keep
            daily_rotation: Whether to rotate logs daily
        """
        # Update config with provided values
        if level is not None:
            self.default_config['level'] = level
        if json_logging is not None:
            self.default_config['json_logging'] = json_logging
        if log_file is not None:
            self.default_config['log_file'] = log_file
        if rotation_size is not None:
            self.default_config['rotation_size'] = rotation_size
        if rotation_count is not None:
            self.default_config['rotation_count'] = rotation_count
        if daily_rotation is not None:
            self.default_config['daily_rotation'] = daily_rotation

        # Configure root logger
        root_logger = logging.getLogger()

        # Convert string level to logging level constant
        if isinstance(self.default_config['level'], str):
            level_value = LOG_LEVELS.get(
                self.default_config['level'].lower(),
                logging.INFO
            )
        else:
            level_value = self.default_config['level']

        root_logger.setLevel(level_value)

        # Remove existing handlers to avoid duplicates
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

        # Create formatter
        if self.default_config['json_logging']:
            formatter = jsonlogger.JsonFormatter(DEFAULT_JSON_FORMAT)
        else:
            formatter = logging.Formatter(DEFAULT_TEXT_FORMAT)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Add filters
        sensitive_filter = SensitiveFilter()
        context_filter = ContextFilter()
        console_handler.addFilter(sensitive_filter)
        console_handler.addFilter(context_filter)

        root_logger.addHandler(console_handler)

        # Create file handler if specified
        if self.default_config['log_file']:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(self.default_config['log_file'])
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Create the appropriate handler based on configuration
            if self.default_config['daily_rotation']:
                file_handler = TimedRotatingFileHandler(
                    self.default_config['log_file'],
                    when='midnight',
                    backupCount=self.default_config['rotation_count']
                )
            else:
                file_handler = RotatingFileHandler(
                    self.default_config['log_file'],
                    maxBytes=self.default_config['rotation_size'],
                    backupCount=self.default_config['rotation_count']
                )

            file_handler.setFormatter(formatter)
            file_handler.addFilter(sensitive_filter)
            file_handler.addFilter(context_filter)
            root_logger.addHandler(file_handler)

        self.configured = True

    def get_logger(self, name: str = "verifact", **kwargs) -> logging.Logger:
        """
        Get a logger for the specified name, creating it if necessary.

        Args:
            name: Logger name
            **kwargs: Additional configuration parameters

        Returns:
            Logger instance
        """
        # Ensure the logging system is configured
        if not self.configured:
            self.configure()

        # Check for cached logger
        if name in _LOGGERS:
            return _LOGGERS[name]

        # Create new logger
        logger = logging.getLogger(name)

        # Store in cache
        _LOGGERS[name] = logger

        return logger

    def get_component_logger(self, component: str) -> logging.Logger:
        """
        Get a logger for a specific component.

        Args:
            component: Component name (e.g., 'claim_detector', 'evidence_hunter')

        Returns:
            Logger configured for the component
        """
        # Set component in context
        self.set_component(component)

        # Get logger with the component name
        return self.get_logger(f"verifact.{component}")

    def set_request_id(self, request_id: Optional[str] = None) -> str:
        """
        Set the current request ID for context tracking.

        Args:
            request_id: Request ID to set, or None to generate a new one

        Returns:
            The request ID
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        if request_id_var is not None:
            request_id_var.set(request_id)
        else:
            _thread_local.request_id = request_id

        return request_id

    def get_request_id(self) -> str:
        """Get the current request ID."""
        if request_id_var is not None:
            return request_id_var.get('')
        else:
            return getattr(_thread_local, 'request_id', '')

    def set_component(self, component: str) -> None:
        """
        Set the current component name for context tracking.

        Args:
            component: Component name
        """
        if component_var is not None:
            component_var.set(component)
        else:
            _thread_local.component = component

    def get_component(self) -> str:
        """Get the current component name."""
        if component_var is not None:
            return component_var.get('')
        else:
            return getattr(_thread_local, 'component', '')

    def add_context(self, **kwargs) -> None:
        """
        Add data to the current logging context.

        Args:
            **kwargs: Key-value pairs to add to context
        """
        if context_data_var is not None:
            context = context_data_var.get({}).copy()
            context.update(kwargs)
            context_data_var.set(context)
        else:
            if not hasattr(_thread_local, 'context_data'):
                _thread_local.context_data = {}
            _thread_local.context_data.update(kwargs)

    def clear_context(self) -> None:
        """Clear the current logging context."""
        if context_data_var is not None:
            context_data_var.set({})
        else:
            _thread_local.context_data = {}

    @contextmanager
    def request_context(self, request_id: Optional[str] = None, **kwargs):
        """
        Context manager for tracking request context.

        Args:
            request_id: Request ID (generated if not provided)
            **kwargs: Additional context data

        Yields:
            The request ID
        """
        # Store current context to restore later
        prev_request_id = self.get_request_id()
        prev_context = {}

        if context_data_var is not None:
            prev_context = context_data_var.get({}).copy()
        else:
            prev_context = getattr(_thread_local, 'context_data', {}).copy()

        try:
            # Set new request ID and context data
            request_id = self.set_request_id(request_id)
            self.add_context(**kwargs)

            yield request_id

        finally:
            # Restore previous context
            if request_id_var is not None:
                request_id_var.set(prev_request_id)
            else:
                _thread_local.request_id = prev_request_id

            if context_data_var is not None:
                context_data_var.set(prev_context)
            else:
                _thread_local.context_data = prev_context

    @contextmanager
    def performance_timer(self,
                          operation: str,
                          logger: Optional[logging.Logger] = None,
                          log_level: str = "debug",
                          **kwargs):
        """
        Context manager for timing and logging operation performance.

        Args:
            operation: Name of the operation being timed
            logger: Logger to use (uses default if not provided)
            log_level: Level to log the timing information
            **kwargs: Additional context data to include in the log

        Yields:
            None
        """
        if logger is None:
            logger = self.get_logger()

        level = LOG_LEVELS.get(log_level.lower(), logging.DEBUG)

        try:
            # Record start time
            start_time = time.time()

            # Add operation to context
            self.add_context(operation=operation, **kwargs)

            yield

        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Log performance data
            logger.log(
                level,
                f"Performance: {operation} completed in {duration:.4f}s",
                extra={
                    "duration": duration,
                    "operation": operation,
                    **kwargs
                }
            )

            # Remove operation from context if it matches
            if context_data_var is not None:
                context = context_data_var.get({}).copy()
                if context.get('operation') == operation:
                    context.pop('operation', None)
                context_data_var.set(context)
            else:
                context = getattr(_thread_local, 'context_data', {})
                if context.get('operation') == operation:
                    context.pop('operation', None)


# Create global LogManager instance
log_manager = LogManager()


def setup_logger(
    name: str = "verifact",
    level: Union[str, int] = "info",
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_TEXT_FORMAT,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    json_logging: bool = False
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
        json_logging: Whether to use JSON-formatted logs

    Returns:
        Configured logger instance
    """
    # Configure the log manager with these settings
    log_manager.configure(
        level=level,
        json_logging=json_logging,
        log_file=log_file,
        rotation_size=max_file_size,
        rotation_count=backup_count
    )

    # Get logger through the manager
    return log_manager.get_logger(name)


def get_logger(name: str = "verifact") -> logging.Logger:
    """
    Get a logger for the specified name, creating it if necessary.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return log_manager.get_logger(name)


def get_component_logger(component: str) -> logging.Logger:
    """
    Get a logger for a specific component.

    Args:
        component: Component name (e.g., 'claim_detector', 'evidence_hunter')

    Returns:
        Logger configured for the component
    """
    return log_manager.get_component_logger(component)


# Function decorators for performance tracking
F = TypeVar('F', bound=Callable[..., Any])


def log_performance(operation: Optional[str] = None,
                    logger: Optional[Union[str, logging.Logger]] = None,
                    level: str = "debug") -> Callable[[F], F]:
    """
    Decorator for timing and logging function execution.

    Args:
        operation: Name of the operation (defaults to function name)
        logger: Logger to use (name or instance)
        level: Log level for the timing information

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the logger
            log = logger
            if isinstance(logger, str):
                log = get_logger(logger)
            elif logger is None:
                log = get_logger()

            # Get the operation name
            op_name = operation or f"{func.__module__}.{func.__name__}"

            # Use performance timer context
            with log_manager.performance_timer(op_name, log, level):
                return func(*args, **kwargs)

        return cast(F, wrapper)
    return decorator


# Context manager shortcuts
def request_context(request_id: Optional[str] = None, **kwargs):
    """Context manager for tracking request context."""
    return log_manager.request_context(request_id, **kwargs)


def performance_timer(operation: str, logger: Optional[logging.Logger] = None,
                      level: str = "debug", **kwargs):
    """Context manager for timing and logging operation performance."""
    return log_manager.performance_timer(operation, logger, level, **kwargs)


# Create default logger
logger = get_logger()
