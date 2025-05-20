"""Security utilities for VeriFact.

This package contains modules for:
- Secure credential management
- Encryption of sensitive data
- Secure hashing and comparison
- API key security management
"""

from src.utils.security.credentials import CredentialError, get_credential
from src.utils.security.encryption import EncryptionError, decrypt_value, encrypt_value
from src.utils.security.hashing import hash_value, secure_compare

__all__ = [
    "get_credential",
    "CredentialError",
    "encrypt_value",
    "decrypt_value",
    "EncryptionError",
    "hash_value",
    "secure_compare",
]
