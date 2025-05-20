"""
Security models for VeriFact.

This module defines models for:
- API keys
- Permission scopes
- Authentication tokens
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import secrets
import uuid

from src.utils.security.hashing import hash_value

class ApiKeyScope(str, Enum):
    """API key permission scopes."""
    READ_ONLY = "read:only"
    WRITE = "write"
    ADMIN = "admin"
    # Add other scopes as needed

class ApiKey(BaseModel):
    """Secure API key model with scopes and expiration."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key_prefix: str = Field(min_length=8, max_length=8)
    key_hash: str
    name: str
    owner_id: str
    scopes: List[ApiKeyScope] = [ApiKeyScope.READ_ONLY]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    
    @classmethod
    def create(cls, name: str, owner_id: str, scopes: List[ApiKeyScope], expires_at: Optional[datetime] = None) -> tuple["ApiKey", str]:
        """
        Create a new API key with a secure random value.
        
        Returns:
            Tuple of (ApiKey object, plain text key for one-time display)
        """
        # Generate random string for key
        key_value = secrets.token_urlsafe(32)
        key_prefix = key_value[:8]
        
        # Never store the full key, only a secure hash
        key_hash = hash_value(key_value)
        
        api_key = cls(
            key_prefix=key_prefix,
            key_hash=key_hash,
            name=name,
            owner_id=owner_id,
            scopes=scopes,
            expires_at=expires_at
        )
        
        # Return both the model (for storage) and the full key (for one-time display)
        return api_key, f"{key_prefix}.{key_value[8:]}"

class TokenType(str, Enum):
    """Types of authentication tokens."""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"

class AuthToken(BaseModel):
    """Secure token model for authentication."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    token_hash: str
    user_id: str
    token_type: TokenType
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(cls, user_id: str, token_type: TokenType, expires_at: datetime) -> tuple["AuthToken", str]:
        """
        Create a new authentication token.
        
        Returns:
            Tuple of (AuthToken object, plain text token for one-time use)
        """
        # Generate random token
        token_value = secrets.token_urlsafe(32)
        
        # Hash the token for storage
        token_hash = hash_value(token_value)
        
        token = cls(
            token_hash=token_hash,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at
        )
        
        # Return both the model (for storage) and the plain token (for one-time use)
        return token, token_value 