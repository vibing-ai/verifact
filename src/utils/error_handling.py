"""Error handling utilities for VeriFact.

This module provides standardized error handling through the ErrorResponseFactory class.
"""

import logging
import os
from typing import Any

from fastapi import HTTPException, status

# Configure logger
logger = logging.getLogger(__name__)


class ErrorDetail:
    """Structured error detail."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int = 400,
    ):
        """Initialize an ErrorDetail object.

        Args:
            code: Error code identifier
            message: Human-readable error message
            details: Additional context about the error
            status_code: HTTP status code associated with this error
        """
        self.code = code
        self.message = message
        self.details = details
        self.log_level = logging.ERROR


class ErrorResponseFactory:
    """Factory for creating consistent error responses."""

    # Define standard error types
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"

    # Map error types to HTTP status codes
    STATUS_CODES = {
        VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AUTHENTICATION_ERROR: status.HTTP_401_UNAUTHORIZED,
        AUTHORIZATION_ERROR: status.HTTP_403_FORBIDDEN,
        NOT_FOUND_ERROR: status.HTTP_404_NOT_FOUND,
        RATE_LIMIT_ERROR: status.HTTP_429_TOO_MANY_REQUESTS,
        SERVER_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    @classmethod
    def create_error_response(
        cls,
        error_type: str,
        message: str,
        details: str | dict[str, Any] | None = None,
        status_code: int | None = None,
        log_exception: bool = True,
        exc_info: Exception | None = None,
    ) -> dict[str, Any]:
        """Create a standardized error response.

        Args:
            error_type: Type of error (use class constants)
            message: User-friendly error message
            details: Additional error details (omitted in production)
            status_code: HTTP status code (defaults based on error_type)
            log_exception: Whether to log the exception
            exc_info: Exception information to log

        Returns:
            Standardized error response dictionary
        """
        if status_code is None:
            status_code = cls.STATUS_CODES.get(error_type, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Log the error
        if log_exception:
            log_level = logging.ERROR if status_code >= 500 else logging.WARNING
            logger.log(log_level, f"Error {error_type}: {message}", exc_info=exc_info)

        # In production, don't include detailed error information
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        response_details = None if is_production else details

        return {
            "error": {
                "code": error_type,
                "message": message,
                "details": response_details,
            }
        }

    @classmethod
    def raise_http_exception(
        cls,
        error_type: str,
        message: str,
        details: str | dict[str, Any] | None = None,
        status_code: int | None = None,
        log_exception: bool = True,
        exc_info: Exception | None = None,
    ) -> None:
        """Create and raise an HTTPException with standardized format.

        This is a convenience method for API handlers.
        """
        if status_code is None:
            status_code = cls.STATUS_CODES.get(error_type, status.HTTP_500_INTERNAL_SERVER_ERROR)

        error_response = cls.create_error_response(
            error_type=error_type,
            message=message,
            details=details,
            status_code=status_code,
            log_exception=log_exception,
            exc_info=exc_info,
        )

        raise HTTPException(status_code=status_code, detail=error_response["error"])
