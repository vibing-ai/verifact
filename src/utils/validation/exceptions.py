"""VeriFact Exception Classes.

This module defines a hierarchy of custom exceptions for the VeriFact system
to ensure consistent error handling across all interfaces (API, CLI, UI).
"""

from typing import Any


class VerifactError(Exception):
    """Base exception class for all VeriFact errors."""

    def __init__(
        self,
        message: str = "An error occurred in the VeriFact system",
        code: str = "VERIFACT_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the base VeriFact error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            status_code: HTTP status code to use in API responses
            details: Additional error context and metadata
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a standardized dictionary format."""
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


# Input/Validation Errors


class ValidationError(VerifactError):
    """Exception raised for data validation errors."""

    def __init__(
        self,
        message: str = "Invalid data format or values",
        details: dict[str, Any] | None = None,
        field: str | None = None,
    ):
        """Initialize a validation error.

        Args:
            message: Description of the validation error
            details: Additional error details
            field: Name of the specific field that failed validation
        """
        code = "VALIDATION_ERROR"
        if field:
            details = details or {}
            details["field"] = field
            code = f"VALIDATION_ERROR_{field.upper()}"

        super().__init__(message=message, code=code, status_code=400, details=details)


class DataFormatError(ValidationError):
    """Exception raised when data is in an incorrect format."""

    def __init__(
        self,
        message: str = "Data format is incorrect",
        expected_format: str | None = None,
        details: dict[str, Any] | None = None,
        field: str | None = None,
    ):
        """Initialize a data format error.

        Args:
            message: Description of the format error
            expected_format: Description of the expected format
            details: Additional error details
            field: Name of the specific field with incorrect format
        """
        details = details or {}
        if expected_format:
            details["expected_format"] = expected_format

        super().__init__(message=message, details=details, field=field)


class InputTooLongError(ValidationError):
    """Exception raised when input text exceeds maximum allowed length."""

    def __init__(self, max_length: int, actual_length: int):
        """Initialize an input length error.

        Args:
            max_length: Maximum allowed length in characters
            actual_length: Actual length of the provided input
        """
        super().__init__(
            message=f"Input text exceeds maximum allowed length of {max_length} characters",
            details={"max_length": max_length, "actual_length": actual_length},
            field="text",
        )


# Pipeline Errors


class PipelineError(VerifactError):
    """Base exception for errors in the factchecking pipeline."""

    def __init__(
        self,
        message: str = "Error in factchecking pipeline",
        code: str = "PIPELINE_ERROR",
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize a pipeline error.

        Args:
            message: Description of the pipeline error
            code: Error code for the specific pipeline error
            stage: Pipeline stage where the error occurred
            details: Additional error details
        """
        details = details or {}
        if stage:
            details["pipeline_stage"] = stage

        super().__init__(message=message, code=code, status_code=500, details=details)


class ModelError(PipelineError):
    """Exception raised when an AI model fails."""

    def __init__(
        self,
        message: str = "AI model processing failed",
        model_name: str | None = None,
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize a model error.

        Args:
            message: Description of the model error
            model_name: Name of the AI model that failed
            stage: Pipeline stage where the error occurred
            details: Additional error details
        """
        details = details or {}
        if model_name:
            details["model_name"] = model_name

        super().__init__(message=message, code="MODEL_ERROR", stage=stage, details=details)


class EvidenceGatheringError(PipelineError):
    """Exception raised when evidence gathering fails."""

    def __init__(
        self,
        message: str = "Failed to gather evidence",
        source: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize an evidence gathering error.

        Args:
            message: Description of the evidence gathering error
            source: Source where evidence gathering failed
            details: Additional error details
        """
        details = details or {}
        if source:
            details["source"] = source

        super().__init__(
            message=message, code="EVIDENCE_ERROR", stage="evidence_gathering", details=details
        )


class RateLimitError(PipelineError):
    """Exception raised when a rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        service: str | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize a rate limit error.

        Args:
            message: Description of the rate limit error
            service: Service that imposed the rate limit
            retry_after: Seconds to wait before retrying
            details: Additional error details
        """
        details = details or {}
        if service:
            details["service"] = service
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(message=message, code="RATE_LIMIT_ERROR", details=details)


# Resource/Service Errors


class ResourceUnavailableError(VerifactError):
    """Exception raised when a required resource is unavailable."""

    def __init__(
        self,
        message: str = "Required resource is unavailable",
        resource_type: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize a resource unavailable error.

        Args:
            message: Description of the resource error
            resource_type: Type of resource that is unavailable
            details: Additional error details
        """
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type

        super().__init__(
            message=message, code="RESOURCE_UNAVAILABLE", status_code=503, details=details
        )


class DatabaseError(ResourceUnavailableError):
    """Exception raised when database operations fail."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize a database error.

        Args:
            message: Description of the database error
            operation: Database operation that failed
            details: Additional error details
        """
        details = details or {}
        if operation:
            details["operation"] = operation

        super().__init__(message=message, resource_type="database", details=details)


class ExternalServiceError(ResourceUnavailableError):
    """Exception raised when an external service fails or is unavailable."""

    def __init__(
        self,
        message: str = "External service error",
        service_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize an external service error.

        Args:
            message: Description of the external service error
            service_name: Name of the external service
            details: Additional error details
        """
        details = details or {}
        if service_name:
            details["service_name"] = service_name

        super().__init__(message=message, resource_type="external_service", details=details)


# Authentication/Authorization Errors


class AuthError(VerifactError):
    """Base exception for authentication and authorization errors."""

    def __init__(
        self,
        message: str = "Authentication error",
        code: str = "AUTH_ERROR",
        details: dict[str, Any] | None = None,
    ):
        """Initialize an authentication error.

        Args:
            message: Description of the authentication error
            code: Error code for the specific authentication error
            details: Additional error details
        """
        super().__init__(message=message, code=code, status_code=401, details=details)


class UnauthorizedError(AuthError):
    """Exception raised when a user is not authorized to perform an action."""

    def __init__(
        self,
        message: str = "Not authorized to perform this action",
        details: dict[str, Any] | None = None,
    ):
        """Initialize an unauthorized error.

        Args:
            message: Description of the authorization error
            details: Additional error details
        """
        super().__init__(message=message, code="UNAUTHORIZED", details=details)


# API Specific Errors


class APIError(VerifactError):
    """Base exception for API-related errors."""

    def __init__(
        self,
        message: str = "API operation failed",
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize an API error.

        Args:
            message: Description of the API error
            endpoint: API endpoint where the error occurred
            details: Additional error details
        """
        details = details or {}
        if endpoint:
            details["endpoint"] = endpoint

        super().__init__(message=message, code="API_ERROR", status_code=500, details=details)


# Add an alias for backward compatibility with old code that uses ApiError
ApiError = APIError


class RequestTimeoutError(APIError):
    """Exception raised when an API request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        endpoint: str | None = None,
        timeout: float | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize a request timeout error.

        Args:
            message: Description of the timeout error
            endpoint: API endpoint that timed out
            timeout: Timeout duration in seconds
            details: Additional error details
        """
        details = details or {}
        if timeout:
            details["timeout_seconds"] = timeout

        super().__init__(message=message, endpoint=endpoint, details=details)
        self.status_code = 408


class TooManyRequestsError(APIError):
    """Exception raised when API rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Too many requests",
        endpoint: str | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize a rate limiting error.

        Args:
            message: Description of the rate limit error
            endpoint: API endpoint that imposed the rate limit
            retry_after: Seconds to wait before retrying
            details: Additional error details
        """
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(message=message, endpoint=endpoint, details=details)
        self.status_code = 429


class APIAuthenticationError(AuthError):
    """Exception raised when API authentication fails."""

    def __init__(
        self, message: str = "API authentication failed", details: dict[str, Any] | None = None
    ):
        """Initialize an API authentication error.

        Args:
            message: Description of the authentication error
            details: Additional error details
        """
        super().__init__(message=message, code="API_AUTH_ERROR", details=details)


class InvalidAPIKeyError(APIAuthenticationError):
    """Exception raised when an invalid API key is provided."""

    def __init__(self, message: str = "Invalid API key", details: dict[str, Any] | None = None):
        """Initialize an invalid API key error.

        Args:
            message: Description of the API key error
            details: Additional error details
        """
        super().__init__(message=message, details=details)


class ExpiredAPIKeyError(APIAuthenticationError):
    """Exception raised when an expired API key is provided."""

    def __init__(
        self,
        message: str = "API key has expired",
        expiry_date: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize an expired API key error.

        Args:
            message: Description of the API key expiration
            expiry_date: When the API key expired
            details: Additional error details
        """
        details = details or {}
        if expiry_date:
            details["expiry_date"] = expiry_date

        super().__init__(message=message, details=details)


class InsufficientQuotaError(APIError):
    """Exception raised when a user exceeds their quota."""

    def __init__(
        self,
        message: str = "Insufficient API quota",
        current_usage: int | None = None,
        quota_limit: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize an insufficient quota error.

        Args:
            message: Description of the quota error
            current_usage: Current usage amount
            quota_limit: Maximum allowed quota
            details: Additional error details
        """
        details = details or {}
        if current_usage is not None:
            details["current_usage"] = current_usage
        if quota_limit is not None:
            details["quota_limit"] = quota_limit

        super().__init__(message=message, details=details)
        self.status_code = 429
