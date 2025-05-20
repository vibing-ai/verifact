import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from functools import lru_cache
from src.utils.security.credentials import get_credential

class EncryptionError(Exception):
    """Exception raised for encryption/decryption errors."""
    pass

@lru_cache(maxsize=1)
def get_encryption_key() -> bytes:
    """
    Get or generate the encryption key.
    
    Returns:
        The encryption key as bytes
    """
    # Try to get the key from environment
    encryption_key = get_credential("ENCRYPTION_KEY", None)
    
    if encryption_key:
        try:
            # Validate that it's a valid Fernet key
            key_bytes = base64.urlsafe_b64decode(encryption_key)
            if len(key_bytes) != 32:
                raise ValueError("Invalid key length")
            return encryption_key.encode()
        except Exception as e:
            raise EncryptionError(f"Invalid encryption key: {str(e)}")
    
    # For development only - in production, always set ENCRYPTION_KEY
    salt = get_credential("ENCRYPTION_SALT", "verifact-encryption-salt").encode()
    password = get_credential("ENCRYPTION_PASSWORD", "dev-only-password").encode()
    
    # Derive a key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    
    print("WARNING: Using derived encryption key. Set ENCRYPTION_KEY in production.")
    return key

def get_fernet() -> Fernet:
    """Get a Fernet instance using the encryption key."""
    key = get_encryption_key()
    return Fernet(key)

def encrypt_value(value: str) -> str:
    """
    Encrypt a string value.
    
    Args:
        value: The value to encrypt
        
    Returns:
        The encrypted value as a base64 string
    """
    if not value:
        return value
        
    try:
        f = get_fernet()
        encrypted = f.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {str(e)}")

def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted value.
    
    Args:
        encrypted_value: The encrypted value as a base64 string
        
    Returns:
        The decrypted value
    """
    if not encrypted_value:
        return encrypted_value
        
    try:
        f = get_fernet()
        decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted_value))
        return decrypted.decode()
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {str(e)}") 