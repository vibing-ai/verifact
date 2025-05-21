"""Exceptions module for backward compatibility.

This module re-exports all exceptions from the validation.exceptions module
for backward compatibility with code that imports from src.utils.exceptions.
"""

from src.utils.validation.exceptions import (
    APIAuthenticationError,
    APIError,
    AuthError,
    DataFormatError,
    DatabaseError,
    EvidenceGatheringError,
    ExpiredAPIKeyError,
    ExternalServiceError,
    InputTooLongError,
    InsufficientQuotaError,
    InvalidAPIKeyError,
    ModelError,
    PipelineError,
    RateLimitError,
    RequestTimeoutError,
    ResourceUnavailableError,
    TooManyRequestsError,
    UnauthorizedError,
    ValidationError,
    VerifactError,
)

__all__ = [
    "APIAuthenticationError",
    "APIError",
    "AuthError",
    "DataFormatError",
    "DatabaseError",
    "EvidenceGatheringError",
    "ExpiredAPIKeyError",
    "ExternalServiceError",
    "InputTooLongError",
    "InsufficientQuotaError",
    "InvalidAPIKeyError",
    "ModelError",
    "PipelineError",
    "RateLimitError",
    "RequestTimeoutError",
    "ResourceUnavailableError",
    "TooManyRequestsError",
    "UnauthorizedError",
    "ValidationError",
    "VerifactError",
] 