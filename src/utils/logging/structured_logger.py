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
_component_context: ContextVar[str] = ContextVar("component", default="")
_operation_context: ContextVar[str] = ContextVar("operation", default="")

# Global application metadata
HOSTNAME = socket.gethostname()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")


class StructuredLogRecord(logging.LogRecord):
    """Custom LogRecord class that handles structured extra data."""

    def __init__(
        self,
        name,
        level,
        pathname,
        lineno,
        msg,
        args,
        exc_info,
        func=None,
        sinfo=None,
        **kwargs
    ):
        """Initialize the structured log record.

        Args:
            name: The logger name.
            level: The logging level.
            pathname: The pathname of the source file.
            lineno: The line number in the source file.
            msg: The log message.
            args: The log message arguments.
            exc_info: Exception information.
            func: The function name.
            sinfo: Stack info.
            kwargs: Additional keyword arguments.
        """
        # Fix for Python 3.13 compatibility
        if len(args) > 0 and isinstance(args[0], dict) and "extra" in args[0]:
            # Extract extra from args if present in a dict
            extra_data = args[0].pop("extra", {})
            kwargs.update(extra_data)
            
        # Python 3.13 can pass an additional argument - extract only the ones we need
        parent_args = [name, level, pathname, lineno, msg, args, exc_info]
        if func is not None:
            parent_args.append(func)
        if sinfo is not None:
            parent_args.append(sinfo)
            
        # Call parent class with the correct number of arguments
        super().__init__(*parent_args)

        # Add context data to log record
        self.request_id = request_id_var.get()
        self.user_id = user_id_var.get()
        self.correlation_id = correlation_id_var.get()
        self.session_id = session_id_var.get()
        self.component = _component_context.get()
        self.operation = _operation_context.get()

        # Add environment metadata
        self.hostname = HOSTNAME
        self.environment = ENVIRONMENT
        self.app_version = APP_VERSION

        # Add timestamps for precise timing
        self.timestamp_ms = int(time.time() * 1000)


class StructuredLogger(logging.Logger):
    """Logger subclass that creates StructuredLogRecord instances."""

    def makeRecord(
        self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None, **kwargs
    ):
        """Create a structured log record.

        Args:
            name: The logger name.
            level: The logging level.
            fn: The filename.
            lno: The line number.
            msg: The log message.
            args: The log message arguments.
            exc_info: Exception information.
            func: The function name.
            extra: Extra information to be added to the record.
            sinfo: Stack information.
            kwargs: Additional keyword arguments.

        Returns:
            StructuredLogRecord: A structured log record.
        """
        # Combine extra with kwargs
        if extra is not None:
            kwargs.update(extra)

        # Add component context if available
        if _component_context.get():
            if "component" not in kwargs:
                kwargs["component"] = _component_context.get()
        if _operation_context.get():
            if "operation" not in kwargs:
                kwargs["operation"] = _operation_context.get()

        # Create the structured log record
        record_args = [name, level, fn, lno, msg, args, exc_info]
        if func is not None:
            record_args.append(func)
        if sinfo is not None:
            record_args.append(sinfo)
        
        return StructuredLogRecord(*record_args, **kwargs)

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
                self.tokens.append((_component_context, _component_context.set(value)))
            elif key == "operation" and value:
                self.tokens.append((_operation_context, _operation_context.set(value)))
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
    """Format log records as JSON."""

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

        if hasattr(record, "component") and record.component:
            log_data["component"] = record.component

        if hasattr(record, "operation") and record.operation:
            log_data["operation"] = record.operation

        # Add any extra data from the record
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)

        # Exception handling
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Handle Python 3.13 stack_info change - it's now potentially a dict instead of a string
        if hasattr(record, "stack_info"):
            if isinstance(record.stack_info, dict):
                # Convert stack_info dict to string format
                log_data["stack_info"] = str(record.stack_info)
            elif record.stack_info:
                # Handle traditional string stack_info
                log_data["stack_info"] = record.stack_info

        # Return formatted JSON
        return json.dumps(log_data, ensure_ascii=False)


class CustomStreamHandler(logging.StreamHandler):
    """A custom stream handler that handles the Python 3.13 stack_info change"""
    
    def __init__(self, stream=None):
        super().__init__(stream)
    
    def format(self, record):
        """Format the record handling Python 3.13 compatibility issues"""
        # Check if we're using a standard formatter or our custom JSON formatter
        if isinstance(self.formatter, JSONFormatter):
            return self.formatter.format(record)
        
        # For standard formatters, handle special cases for Python 3.13
        if hasattr(record, 'stack_info') and isinstance(record.stack_info, dict):
            # Create a copy of the record to avoid modifying the original
            record_copy = logging.LogRecord(
                record.name, record.levelno, record.pathname, record.lineno,
                record.msg, record.args, record.exc_info, record.funcName
            )
            # Convert the stack_info dict to a string representation
            record_copy.stack_info = str(record.stack_info)
            return self.formatter.format(record_copy)
        
        return self.formatter.format(record)


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
    _component_context.set(component)

    if operation:
        _operation_context.set(operation)


def clear_request_context():
    """Clear request context for the current async context."""
    request_id_var.set("")
    user_id_var.set(None)
    correlation_id_var.set("")
    session_id_var.set(None)


def clear_component_context():
    """Clear component context for the current async context."""
    _component_context.set("")
    _operation_context.set("")


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
        # Create custom console handler
        console_handler = CustomStreamHandler()
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
            file_handler = CustomStreamHandler(open(log_file, 'a'))
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
