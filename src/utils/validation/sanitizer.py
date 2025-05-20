"""
Input Sanitization Utilities

This module provides functions for sanitizing input data to prevent
security vulnerabilities like XSS, SQL injection, etc.
"""

import html
import re
import unicodedata
from typing import Any, Dict, List


def sanitize_text(text: str) -> str:
    """
    Sanitize text input to prevent XSS attacks.

    Args:
        text: Text to sanitize

    Returns:
        str: Sanitized text
    """
    if not text:
        return ""

    # Escape HTML entities
    sanitized = html.escape(text)

    # Normalize unicode to remove potentially dangerous characters
    sanitized = unicodedata.normalize("NFKC", sanitized)

    return sanitized


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content to remove potentially dangerous tags and attributes.
    For VeriFact, we don't need to allow any HTML, so we just escape everything.

    Args:
        html_content: HTML content to sanitize

    Returns:
        str: Sanitized HTML
    """
    return sanitize_text(html_content)


def sanitize_url(url: str) -> str:
    """
    Sanitize a URL to prevent XSS attacks.

    Args:
        url: URL to sanitize

    Returns:
        str: Sanitized URL
    """
    if not url:
        return ""

    # Only allow http and https schemes
    if not url.startswith("http://") and not url.startswith("https://"):
        # Safer to return empty than an unsafe URL
        return ""

    # Remove control characters and spaces
    sanitized = "".join(c for c in url if unicodedata.category(c)[0] != "C" and c != " ")

    # Escape HTML entities
    sanitized = html.escape(sanitized)

    return sanitized


def sanitize_sql(sql_input: str) -> str:
    """
    Sanitize SQL input to prevent injection attacks.

    This is a basic sanitization only - proper SQL safety should use
    parameterized queries with database drivers, not string concatenation.

    Args:
        sql_input: SQL string to sanitize

    Returns:
        str: Sanitized SQL
    """
    if not sql_input:
        return ""

    # Remove comments
    sanitized = re.sub(r"--.*?(\r\n|\n|$)", "", sql_input)
    sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)

    # Remove SQL control keywords
    dangerous_keywords = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "UNION",
        "SELECT",
        "GRANT",
        "REVOKE",
        "CREATE",
        "SHUTDOWN",
    ]

    pattern = r"\b(" + "|".join(dangerous_keywords) + r")\b"
    sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

    return sanitized


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.

    Args:
        data: Dictionary to sanitize

    Returns:
        Dict[str, Any]: Sanitized dictionary
    """
    if not data:
        return {}

    sanitized = {}

    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_text(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        else:
            # Non-string values don't need sanitization
            sanitized[key] = value

    return sanitized


def sanitize_list(data: List[Any]) -> List[Any]:
    """
    Recursively sanitize all string values in a list.

    Args:
        data: List to sanitize

    Returns:
        List[Any]: Sanitized list
    """
    if not data:
        return []

    sanitized = []

    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_text(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        else:
            # Non-string values don't need sanitization
            sanitized.append(item)

    return sanitized


def validate_text_length(text: str, min_length: int = 1, max_length: int = 10000) -> bool:
    """
    Validate text length within specified bounds.

    Args:
        text: Text to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        bool: True if text length is valid, False otherwise
    """
    if not text:
        return min_length == 0

    text_length = len(text)
    return min_length <= text_length <= max_length


def validate_url_format(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        bool: True if URL format is valid, False otherwise
    """
    if not url:
        return False

    # Simple URL validation pattern
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        # domain
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or ipv4
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    return bool(url_pattern.match(url))


def validate_email_format(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email to validate

    Returns:
        bool: True if email format is valid, False otherwise
    """
    if not email:
        return False

    # Simple email validation pattern
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    return bool(email_pattern.match(email))
