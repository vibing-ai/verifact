import hashlib
import hmac
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_hash_key() -> bytes:
    """Get the key used for hashing, cached for performance."""
    # Use a secure, application-specific key for HMAC
    key = os.environ.get("HASH_KEY")
    if not key:
        # In production, this should be set and consistent
        # For development, we can generate one
        key = os.urandom(32).hex()
        print(f"WARNING: HASH_KEY not set, generated temporary key: {key}")
    return key.encode()


def hash_value(value: str) -> str:
    """Create a secure hash of a value using HMAC-SHA256.

    Args:
        value: The value to hash

    Returns:
        The secure hash as a hex string
    """
    key = get_hash_key()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def secure_compare(val1: str, val2: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks.

    Args:
        val1: First value
        val2: Second value

    Returns:
        True if the values are equal, False otherwise
    """
    return hmac.compare_digest(val1, val2)
