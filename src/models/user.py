"""
User model for VeriFact.

This module defines the user model with encrypted sensitive fields.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

from src.utils.security.encrypted_fields import EncryptedStr, EncryptedModel

class User(BaseModel, EncryptedModel):
    """User model with encrypted sensitive fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    phone: Optional[str] = None
    api_key: Optional[EncryptedStr] = None
    access_token: Optional[EncryptedStr] = None
    refresh_token: Optional[EncryptedStr] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Specify which fields should be encrypted when stored
    encrypted_fields = ["api_key", "access_token", "refresh_token"] 