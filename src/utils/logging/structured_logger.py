import json
import logging
import os
import socket
import time
import traceback
import uuid
from contextvars import ContextVar, Token

# Context variables for tracking request and execution context
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
component_var: ContextVar[str] = ContextVar("component", default="")
operation_var: ContextVar[str] = ContextVar("operation", default="")

# Global application metadata
HOSTNAME = socket.gethostname()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")


class StructuredLogRecord(logging.LogRecord):
    """Extended LogRecord class that includes structured context data."""

    def __init__(self, *args, **kwargs):
        """Initialize a structured log record with context data.

        Args:
            *args: Arguments passed to the parent LogRecord constructor
            **kwargs: Keyword arguments passed to the parent LogRecord constructor
        """
        super().__init__(*args, **kwargs)
        # Add context data to log record
        self.request_id = request_id_var.get()
        self.user_id = user_id_var.get()
        self.correlation_id = correlation_id_var.get()
        self.session_id = session_id_var.get()
        self.component = component_var.get()
        self.operation = operation_var.get()

        # Add environment metadata
        self.hostname = HOSTNAME
        self.environment = ENVIRONMENT
        self.app_version = APP_VERSION

        # Add timestamps for precise timing
        self.timestamp_ms = int(time.time() * 1000)


class StructuredLogger(logging.Logger):
    """Logger subclass that creates StructuredLogRecord instances."""

    def makeRecord(self, *args, **kwargs):
        """Create a StructuredLogRecord instance.

        Args:
            *args: Arguments passed to the LogRecord constructor
            **kwargs: Keyword arguments passed to the LogRecord constructor

        Returns:
            StructuredLogRecord: A log record with added context data
        """
        return StructuredLogRecord(*args, **kwargs)

    def process_success(self, message: str, duration_ms: float | None = None, **kwargs):
        """Log a successful operation with timing information."""
        extra = kwargs.pop("extra", {})
        extra.update({"event_type": "process_success", "duration_ms": duration_ms, **kwargs})
        self.info(message, extra=extra)

    def process_failure(
        self,
        message: str,
        error: Exception | None = None,
        duration_ms: float | None = None,
        **kwargs,
    ):
        """Log a failed operation with error details and timing information."""
        extra = kwargs.pop("extra", {})
        extra.update({"event_type": "process_failure", "duration_ms": duration_ms, **kwargs})

        if error:
            extra["error_type"] = error.__class__.__name__
            extra["error_message"] = str(error)
            extra["traceback"] = traceback.format_exc()

        self.error(message, extra=extra)

    def api_request(
        self,
        method: str,
        url: str,
        status_code: int | None = None,
        duration_ms: float | None = None,
        **kwargs,
    ):
        """Log API request information."""
        extra = kwargs.pop("extra", {})
        extra.update(
            {
                "event_type": "api_request",
                "http_method": method,
                "url": url,
                "status_code": status_code,
                "duration_ms": duration_ms,
                **kwargs,
            }
        )

        if status_code and status_code >= 400:
            self.warning("API request failed", extra=extra)
        else:
            self.info("API request completed", extra=extra)

    def with_context(self, **context):
        """Create a context manager for adding temporary context to logs."""
        return LoggingContext(self, **context)


class LoggingContext:
    """Context manager for adding temporary context to logs."""

    def __init__(self, logger: StructuredLogger, **context):
        """Initialize the logging context manager.

        Args:
            logger: The logger to use within the context
            **context: Key-value pairs to add to the logging context
        """
        self.logger = logger
        self.context = context
        self.tokens: list[tuple[ContextVar, Token]] = []

    def __enter__(self):
        """Set up the logging context when entering the context manager.

        Returns:
            StructuredLogger: The logger with added context
        """
        # Set context variables and store tokens for later reset
        for key, value in self.context.items():
            if key == "request_id" and value:
                self.tokens.append((request_id_var, request_id_var.set(value)))
            elif key == "user_id" and value:
                self.tokens.append((user_id_var, user_id_var.set(value)))
            elif key == "correlation_id" and value:
                self.tokens.append((correlation_id_var, correlation_id_var.set(value)))
            elif key == "session_id" and value:
                self.tokens.append((session_id_var, session_id_var.set(value)))
            elif key == "component" and value:
                self.tokens.append((component_var, component_var.set(value)))
            elif key == "operation" and value:
                self.tokens.append((operation_var, operation_var.set(value)))
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the logging context when exiting the context manager.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        # Reset context variables to their previous values
        for var, token in reversed(self.tokens):
            var.reset(token)


class JSONFormatter(logging.Formatter):
    """Formatter that converts log records to JSON."""

    def __init__(self, include_traceback: bool = True):
        """Initialize the JSON formatter.

        Args:
            include_traceback: Whether to include exception tracebacks in the logs
        """
        super().__init__()
        self.include_traceback = include_traceback

    def format(self, record):
        """Format the log record as JSON."""
        # Build basic log data
        log_data = {
            "timestamp": record.timestamp_ms,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
            "environment": record.environment,
            "hostname": record.hostname,
            "app_version": record.app_version,
        }

        # Add context data if available
        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id") and record.user_id:
            log_data["user_id"] = record.user_id

        if hasattr(record, "correlation_id") and record.correlation_id:
            log_data["correlation_id"] = record.correlation_id

        if hasattr(record, "session_id") and record.session_id:
            log_data["session_id"] = record.session_id

        if hasattr(record, "component") and record.component:
            log_data["component"] = record.component

        if hasattr(record, "operation") and record.operation:
            log_data["operation"] = record.operation

        # Add exception info if available
        if record.exc_info and self.include_traceback:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add custom fields from extra
        for key, value in record.__dict__.items():
            if key not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "timestamp_ms",
                "request_id",
                "user_id",
                "correlation_id",
                "session_id",
                "component",
                "operation",
                "hostname",
                "environment",
                "app_version",
            ) and not key.startswith("_"):
                log_data[key] = value

        # Convert to JSON
        return json.dumps(log_data)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance with the given name."""
    logging.setLoggerClass(StructuredLogger)
    logger = logging.getLogger(name)
    return logger


def set_request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    correlation_id: str | None = None,
    session_id: str | None = None,
):
    """Set request context for the current async context."""
    if request_id:
        request_id_var.set(request_id)
    else:
        request_id_var.set(str(uuid.uuid4()))

    if user_id:
        user_id_var.set(user_id)

    if correlation_id:
        correlation_id_var.set(correlation_id)

    if session_id:
        session_id_var.set(session_id)


def set_component_context(component: str, operation: str | None = None):
    """Set component and operation context for the current async context."""
    component_var.set(component)

    if operation:
        operation_var.set(operation)


def clear_request_context():
    """Clear request context for the current async context."""
    request_id_var.set("")
    user_id_var.set(None)
    correlation_id_var.set("")
    session_id_var.set(None)


def clear_component_context():
    """Clear component context for the current async context."""
    component_var.set("")
    operation_var.set("")


def configure_logging(
    level: int = logging.INFO,
    json_output: bool = True,
    log_file: str | None = None,
    include_traceback: bool = True,
    log_handlers: list[logging.Handler] | None = None,
):
    """Configure structured logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Use provided handlers or create default ones
    if log_handlers:
        for handler in log_handlers:
            root_logger.addHandler(handler)
    else:
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        if json_output:
            console_handler.setFormatter(JSONFormatter(include_traceback=include_traceback))
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(levelname)s - [%(request_id)s] - %(name)s - %(message)s"
                )
            )

        root_logger.addHandler(console_handler)

        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)

            if json_output:
                file_handler.setFormatter(JSONFormatter(include_traceback=include_traceback))
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s - %(levelname)s - [%(request_id)s] - %(name)s - %(message)s"
                    )
                )

            root_logger.addHandler(file_handler)

    # Set logger class for all new loggers
    logging.setLoggerClass(StructuredLogger)
