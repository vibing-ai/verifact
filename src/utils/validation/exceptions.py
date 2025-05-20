"""
VeriFact Exception Classes

This module defines a hierarchy of custom exceptions for the VeriFact system
to ensure consistent error handling across all interfaces (API, CLI, UI).
"""

from typing import Optional, Any, Dict


class VerifactError(Exception):
    """Base exception class for all VeriFact errors."""
    
    def __init__(
        self, 
        message: str = "An error occurred in the VeriFact system",
        code: str = "VERIFACT_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a standardized dictionary format."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


# Input/Validation Errors

class ValidationError(VerifactError):
    """Exception raised for data validation errors."""
    
    def __init__(
        self, 
        message: str = "Invalid data format or values",
        details: Optional[Dict[str, Any]] = None,
        field: Optional[str] = None
    ):
        code = "VALIDATION_ERROR"
        if field:
            details = details or {}
            details["field"] = field
            code = f"VALIDATION_ERROR_{field.upper()}"
            
        super().__init__(
            message=message,
            code=code,
            status_code=400,
            details=details
        )


class InputTooLongError(ValidationError):
    """Exception raised when input text exceeds maximum allowed length."""
    
    def __init__(self, max_length: int, actual_length: int):
        super().__init__(
            message=f"Input text exceeds maximum allowed length of {max_length} characters",
            details={
                "max_length": max_length,
                "actual_length": actual_length
            },
            field="text"
        )


# Pipeline Errors

class PipelineError(VerifactError):
    """Base exception for errors in the factchecking pipeline."""
    
    def __init__(
        self,
        message: str = "Error in factchecking pipeline",
        code: str = "PIPELINE_ERROR",
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if stage:
            details["pipeline_stage"] = stage
            
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            details=details
        )


class ModelError(PipelineError):
    """Exception raised when an AI model fails."""
    
    def __init__(
        self,
        message: str = "AI model processing failed",
        model_name: Optional[str] = None,
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if model_name:
            details["model_name"] = model_name
            
        super().__init__(
            message=message,
            code="MODEL_ERROR",
            stage=stage,
            details=details
        )


class EvidenceGatheringError(PipelineError):
    """Exception raised when evidence gathering fails."""
    
    def __init__(
        self,
        message: str = "Failed to gather evidence",
        source: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if source:
            details["source"] = source
            
        super().__init__(
            message=message,
            code="EVIDENCE_ERROR",
            stage="evidence_gathering",
            details=details
        )


class RateLimitError(PipelineError):
    """Exception raised when a rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        service: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if service:
            details["service"] = service
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details=details
        )


# Resource/Service Errors

class ResourceUnavailableError(VerifactError):
    """Exception raised when a required resource is unavailable."""
    
    def __init__(
        self,
        message: str = "Required resource is unavailable",
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
            
        super().__init__(
            message=message,
            code="RESOURCE_UNAVAILABLE",
            status_code=503,
            details=details
        )


class DatabaseError(ResourceUnavailableError):
    """Exception raised when database operations fail."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            resource_type="database",
            details=details
        )


class ExternalServiceError(ResourceUnavailableError):
    """Exception raised when an external service fails or is unavailable."""
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if service_name:
            details["service_name"] = service_name
            
        super().__init__(
            message=message,
            resource_type="external_service",
            details=details
        )


# Authentication/Authorization Errors

class AuthError(VerifactError):
    """Base exception for authentication and authorization errors."""
    
    def __init__(
        self,
        message: str = "Authentication error",
        code: str = "AUTH_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=401,
            details=details
        )


class UnauthorizedError(AuthError):
    """Exception raised when a user is not authorized to perform an action."""
    
    def __init__(
        self,
        message: str = "Not authorized to perform this action",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            details=details
        )


# API Specific Errors

class APIError(VerifactError):
    """Base exception for API related errors."""
    
    def __init__(
        self,
        message: str = "API operation failed",
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if endpoint:
            details["endpoint"] = endpoint
            
        super().__init__(
            message=message,
            code="API_ERROR",
            status_code=500,
            details=details
        )


class RequestTimeoutError(APIError):
    """Exception raised when an API request times out."""
    
    def __init__(
        self,
        message: str = "Request timed out",
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if timeout:
            details["timeout_seconds"] = timeout
            
        super().__init__(
            message=message,
            endpoint=endpoint,
            details=details
        )
        self.status_code = 408


class TooManyRequestsError(APIError):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Too many requests",
        endpoint: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            endpoint=endpoint,
            details=details
        )
        self.status_code = 429


class APIAuthenticationError(AuthError):
    """Exception raised when API authentication fails."""
    
    def __init__(
        self,
        message: str = "API authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="API_AUTH_ERROR",
            details=details
        )
        self.status_code = 401


class InvalidAPIKeyError(APIAuthenticationError):
    """Exception raised when an invalid API key is provided."""
    
    def __init__(
        self,
        message: str = "Invalid API key",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )


class ExpiredAPIKeyError(APIAuthenticationError):
    """Exception raised when an expired API key is provided."""
    
    def __init__(
        self,
        message: str = "API key has expired",
        expiry_date: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if expiry_date:
            details["expiry_date"] = expiry_date
            
        super().__init__(
            message=message,
            details=details
        )


class InsufficientQuotaError(APIError):
    """Exception raised when the user has insufficient quota."""
    
    def __init__(
        self,
        message: str = "Insufficient API quota",
        current_usage: Optional[int] = None,
        quota_limit: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if current_usage is not None:
            details["current_usage"] = current_usage
        if quota_limit is not None:
            details["quota_limit"] = quota_limit
            
        super().__init__(
            message=message,
            details=details
        )
        self.status_code = 403 