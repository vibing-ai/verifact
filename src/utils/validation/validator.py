"""Input Validation Utilities

This module provides functions for validating and sanitizing input data.
"""

import logging
from collections.abc import Callable
from typing import Any

from src.utils.exceptions import ValidationError
from src.utils.validation.config import validation_config
from src.utils.validation.sanitizer import (
    sanitize_text,
    sanitize_url,
    validate_text_length,
    validate_url_format,
)

logger = logging.getLogger("verifact.validation")


class Validator:
    """Input validator class that combines validation and sanitization."""

    @staticmethod
    def validate_text(text: str, field_name: str = "text", strict: bool = False) -> str:
        """Validate and sanitize text input.

        Args:
            text: Text to validate
            field_name: Name of the field (for error messages)
            strict: If True, raise an exception for invalid text

        Returns:
            str: Sanitized text

        Raises:
            ValidationError: If text is invalid and strict is True
        """
        if not text:
            if strict:
                raise ValidationError(f"{field_name} is required")
            return ""

        # Get configuration values
        min_length = validation_config.get("text.min_length", 1)
        max_length = validation_config.get("text.max_length", 50000)

        # Check length
        if not validate_text_length(text, min_length, max_length):
            if strict:
                raise ValidationError(
                    f"{field_name} must be between {min_length} and {max_length} characters",
                    details={
                        "field": field_name,
                        "actual_length": len(text),
                        "min_length": min_length,
                        "max_length": max_length,
                    },
                )
            # Truncate text to maximum length if not strict
            text = text[:max_length]

        # Sanitize the text
        sanitized = sanitize_text(text)

        return sanitized

    @staticmethod
    def validate_claim_text(text: str, strict: bool = False) -> str:
        """Validate and sanitize claim text.

        Args:
            text: Claim text to validate
            strict: If True, raise an exception for invalid text

        Returns:
            str: Sanitized claim text

        Raises:
            ValidationError: If text is invalid and strict is True
        """
        if not text:
            if strict:
                raise ValidationError("Claim text is required")
            return ""

        # Get configuration values
        min_length = validation_config.get("claim.min_length", 5)
        max_length = validation_config.get("claim.max_length", 1000)

        # Check length
        if not validate_text_length(text, min_length, max_length):
            if strict:
                raise ValidationError(
                    f"Claim text must be between {min_length} and {max_length} characters",
                    details={
                        "field": "claim_text",
                        "actual_length": len(text),
                        "min_length": min_length,
                        "max_length": max_length,
                    },
                )
            # Truncate claim to maximum length if not strict
            text = text[:max_length]

        # Sanitize the text
        sanitized = sanitize_text(text)

        return sanitized

    @staticmethod
    def validate_url(url: str, strict: bool = False) -> str:
        """Validate and sanitize URL.

        Args:
            url: URL to validate
            strict: If True, raise an exception for invalid URL

        Returns:
            str: Sanitized URL

        Raises:
            ValidationError: If URL is invalid and strict is True
        """
        if not url:
            if strict:
                raise ValidationError("URL is required")
            return ""

        # Get configuration values
        max_length = validation_config.get("url.max_length", 2048)
        allowed_schemes = validation_config.get("url.allowed_schemes", ["http", "https"])

        # Check URL format
        if not validate_url_format(url):
            if strict:
                raise ValidationError(
                    "Invalid URL format", details={"field": "url", "actual_value": url}
                )
            return ""

        # Check if scheme is allowed
        for scheme in allowed_schemes:
            if url.startswith(f"{scheme}://"):
                break
        else:
            if strict:
                raise ValidationError(
                    f"URL scheme must be one of: {', '.join(allowed_schemes)}",
                    details={
                        "field": "url",
                        "actual_value": url,
                        "allowed_schemes": allowed_schemes,
                    },
                )
            return ""

        # Check length
        if len(url) > max_length:
            if strict:
                raise ValidationError(
                    f"URL must not exceed {max_length} characters",
                    details={"field": "url", "actual_length": len(url), "max_length": max_length},
                )
            return ""

        # Sanitize the URL
        sanitized = sanitize_url(url)

        return sanitized

    @staticmethod
    def validate_claims_count(count: int, strict: bool = False) -> int:
        """Validate the number of claims.

        Args:
            count: Number of claims to validate
            strict: If True, raise an exception for invalid count

        Returns:
            int: Validated count

        Raises:
            ValidationError: If count is invalid and strict is True
        """
        if count <= 0:
            if strict:
                raise ValidationError("Number of claims must be positive")
            return 0

        # Get configuration value
        max_claims = validation_config.get("api.max_claims_per_request", 20)

        # Check count
        if count > max_claims:
            if strict:
                raise ValidationError(
                    f"Number of claims cannot exceed {max_claims}",
                    details={
                        "field": "claims_count",
                        "actual_count": count,
                        "max_count": max_claims,
                    },
                )
            return max_claims

        return count

    @staticmethod
    def validate_batch_claims_count(count: int, strict: bool = False) -> int:
        """Validate the number of batch claims.

        Args:
            count: Number of batch claims to validate
            strict: If True, raise an exception for invalid count

        Returns:
            int: Validated count

        Raises:
            ValidationError: If count is invalid and strict is True
        """
        if count <= 0:
            if strict:
                raise ValidationError("Number of batch claims must be positive")
            return 0

        # Get configuration value
        max_batch_claims = validation_config.get("api.max_batch_claims", 100)

        # Check count
        if count > max_batch_claims:
            if strict:
                raise ValidationError(
                    f"Number of batch claims cannot exceed {max_batch_claims}",
                    details={
                        "field": "batch_claims_count",
                        "actual_count": count,
                        "max_count": max_batch_claims,
                    },
                )
            return max_batch_claims

        return count

    @staticmethod
    def validate_check_worthiness(score: float, strict: bool = False) -> float:
        """Validate check-worthiness score.

        Args:
            score: Check-worthiness score to validate
            strict: If True, raise an exception for invalid score

        Returns:
            float: Validated score

        Raises:
            ValidationError: If score is invalid and strict is True
        """
        if not 0 <= score <= 1:
            if strict:
                raise ValidationError(
                    "Check-worthiness score must be between 0 and 1",
                    details={"field": "check_worthiness", "actual_value": score},
                )
            # Clamp score to valid range
            return max(0, min(score, 1))

        return score

    @staticmethod
    def validate_feedback_comment(comment: str, strict: bool = False) -> str:
        """Validate and sanitize feedback comment.

        Args:
            comment: Feedback comment to validate
            strict: If True, raise an exception for invalid comment

        Returns:
            str: Sanitized feedback comment

        Raises:
            ValidationError: If comment is invalid and strict is True
        """
        if not comment:
            return ""

        # Get configuration values
        min_length = validation_config.get("feedback.min_comment_length", 5)
        max_length = validation_config.get("feedback.max_comment_length", 1000)

        # Check length
        if not validate_text_length(comment, min_length, max_length):
            if strict:
                raise ValidationError(
                    f"Feedback comment must be between {min_length} and {max_length} characters",
                    details={
                        "field": "comment",
                        "actual_length": len(comment),
                        "min_length": min_length,
                        "max_length": max_length,
                    },
                )
            # Truncate comment to maximum length if not strict
            comment = comment[:max_length]

        # Sanitize the comment
        sanitized = sanitize_text(comment)

        return sanitized

    @staticmethod
    def validate_input(
        input_data: dict[str, Any], validation_rules: dict[str, Callable], strict: bool = False
    ) -> dict[str, Any]:
        """Validate and sanitize input data using validation rules.

        Args:
            input_data: Input data to validate
            validation_rules: Dictionary mapping field names to validation functions
            strict: If True, raise an exception for invalid input

        Returns:
            Dict[str, Any]: Validated and sanitized input data

        Raises:
            ValidationError: If input is invalid and strict is True
        """
        if not input_data:
            if strict:
                raise ValidationError("Input data is required")
            return {}

        validated_data = {}
        errors = []

        # Apply validation rules to input data
        for field, validator in validation_rules.items():
            try:
                value = input_data.get(field)
                validated_data[field] = validator(value, strict)
            except ValidationError as e:
                if strict:
                    raise
                errors.append(str(e))

        # Log validation errors
        if errors:
            logger.warning(f"Validation errors: {', '.join(errors)}")

        return validated_data


# Create functions that use the Validator class
validate_text = Validator.validate_text
validate_claim_text = Validator.validate_claim_text
validate_url = Validator.validate_url
validate_claims_count = Validator.validate_claims_count
validate_batch_claims_count = Validator.validate_batch_claims_count
validate_check_worthiness = Validator.validate_check_worthiness
validate_feedback_comment = Validator.validate_feedback_comment
validate_input = Validator.validate_input
