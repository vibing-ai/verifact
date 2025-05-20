"""User model for VeriFact.

This module defines the user model with encrypted sensitive fields.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from src.utils.security.encrypted_fields import EncryptedModel, EncryptedStr


class User(BaseModel, EncryptedModel):
    """User model with encrypted sensitive fields."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    phone: str | None = None
    api_key: EncryptedStr | None = None
    access_token: EncryptedStr | None = None
    refresh_token: EncryptedStr | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    # Specify which fields should be encrypted when stored
    encrypted_fields = ["api_key", "access_token", "refresh_token"]
