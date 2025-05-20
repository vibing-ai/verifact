"""
Validation utilities for VeriFact.

This module provides functions for validating inputs before processing.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar, cast

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from src.models.factcheck import Claim, Evidence, Verdict
from src.utils.validation.exceptions import InputTooLongError, ValidationError

T = TypeVar('T', bound=BaseModel)


def validate_model(data: Dict[str, Any], model_class: Type[T]) -> T:
    """
    Validate data against a Pydantic model and return the validated model instance.

    Args:
        data: The data to validate
        model_class: The Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return model_class(**data)
    except PydanticValidationError as e:
        # Convert Pydantic validation error to our custom error format
        field_errors = {}
        for error in e.errors():
            field = ".".join(error["loc"])
            field_errors[field] = error["msg"]

        message = "Data validation failed"
        if len(field_errors) == 1:
            field = next(iter(field_errors.keys()))
            message = f"Validation error for field '{field}': {field_errors[field]}"

        raise ValidationError(
            message=message,
            details={"field_errors": field_errors}
        )


def sanitize_text(text: str) -> str:
    """
    Sanitize input text by removing control characters and excess whitespace.

    Args:
        text: The text to sanitize

    Returns:
        Sanitized text
    """
    # Replace control characters except common whitespace
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Normalize whitespace (replace multiple spaces with single space)
    text = re.sub(r'\s+', ' ', text)

    # Trim
    return text.strip()


def validate_text_length(text: str, max_length: int = 50000) -> str:
    """
    Validate text length and raise an exception if it exceeds the maximum.

    Args:
        text: The text to validate
        max_length: Maximum allowed length

    Returns:
        The original text if valid

    Raises:
        InputTooLongError: If text exceeds maximum length
    """
    if len(text) > max_length:
        raise InputTooLongError(max_length=max_length, actual_length=len(text))
    return text


def parse_datetime(timestamp: Optional[str]) -> Optional[datetime]:
    """
    Parse a string timestamp into a datetime object.

    Args:
        timestamp: String timestamp in various formats

    Returns:
        Datetime object or None if parsing fails
    """
    if not timestamp:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format with microseconds
        "%Y-%m-%dT%H:%M:%SZ",     # ISO format without microseconds
        "%Y-%m-%d %H:%M:%S",      # Standard datetime format
        "%Y-%m-%d",               # Just date
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue

    return None


def convert_claim_for_response(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a claim dictionary to a standardized format for API responses.

    Args:
        claim: Claim data dictionary

    Returns:
        Standardized claim dictionary
    """
    # Validate and convert using our model
    validated = validate_model(claim, Claim)

    # Return the model as a dict, removing None values
    return {k: v for k, v in validated.dict().items() if v is not None}


def convert_evidence_for_response(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert evidence dictionary to a standardized format for API responses.

    Args:
        evidence: Evidence data dictionary

    Returns:
        Standardized evidence dictionary
    """
    # Validate and convert using our model
    validated = validate_model(evidence, Evidence)

    # Format datetime fields for consistent output
    result = validated.dict()

    if result.get("timestamp"):
        if isinstance(result["timestamp"], datetime):
            result["timestamp"] = result["timestamp"].isoformat()

    if result.get("retrieval_date"):
        if isinstance(result["retrieval_date"], datetime):
            result["retrieval_date"] = result["retrieval_date"].isoformat()

    # Remove None values
    return {k: v for k, v in result.items() if v is not None}


def convert_verdict_for_response(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert verdict dictionary to a standardized format for API responses.

    Args:
        verdict: Verdict data dictionary

    Returns:
        Standardized verdict dictionary
    """
    # If key_evidence is present, process each evidence item
    if "key_evidence" in verdict and verdict["key_evidence"]:
        evidence_list = []
        for ev in verdict["key_evidence"]:
            if isinstance(ev, dict):
                evidence_list.append(convert_evidence_for_response(ev))
            elif isinstance(ev, Evidence):
                evidence_list.append(convert_evidence_for_response(ev.dict()))
        verdict["key_evidence"] = evidence_list

    # Validate and convert using our model
    validated = validate_model(verdict, Verdict)

    # Format datetime fields for consistent output
    result = validated.dict()

    if result.get("generated_at"):
        if isinstance(result["generated_at"], datetime):
            result["generated_at"] = result["generated_at"].isoformat()

    # Remove None values
    return {k: v for k, v in result.items() if v is not None}


def get_json_serializable_error(exception: Exception) -> Dict[str, Any]:
    """
    Convert an exception to a JSON-serializable error dictionary.

    Args:
        exception: The exception to convert

    Returns:
        Error dictionary
    """
    if hasattr(
        exception,
        'to_dict') and callable(
            exception.to_dict):
        return cast(Any, exception).to_dict()

    return {
        "error": {
            "code": exception.__class__.__name__.upper(),
            "message": str(exception),
            "details": {}
        }
    }


def try_parse_json(json_str: str) -> Dict[str, Any]:
    """
    Try to parse a JSON string into a dictionary.

    Args:
        json_str: JSON string to parse

    Returns:
        Parsed dictionary

    Raises:
        ValidationError: If parsing fails
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValidationError(
            message=f"Invalid JSON: {str(e)}",
            details={"json_error": str(e)}
        )
