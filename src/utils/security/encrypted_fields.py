from typing import Any, ClassVar, Dict, List

from src.utils.security.encryption import decrypt_value, encrypt_value


class EncryptedStr(str):
    """
    A string type that is automatically encrypted when stored and decrypted when retrieved.

    Usage:
        class User(BaseModel):
            username: str
            password: EncryptedStr
    """
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if v is None:
            return v
        if not isinstance(v, str):
            raise TypeError('string required')
        return v

    def __repr__(self):
        return "EncryptedStr('***')"


class EncryptedModel:
    """Mixin for models with encrypted fields."""
    # This will be populated by each model with fields that need encryption
    encrypted_fields: ClassVar[List[str]] = []

    def dict(self, *args, **kwargs):
        """Override dict to encrypt sensitive fields."""
        exclude = kwargs.pop('exclude', set())
        exclude_encrypted = kwargs.pop('exclude_encrypted', False)

        if exclude_encrypted:
            exclude = exclude.union(set(self.encrypted_fields))

        # Get the regular dict representation
        data = super().dict(*args, exclude=exclude, **kwargs)

        # Encrypt fields marked for encryption
        for field in self.encrypted_fields:
            if field in data and data[field] is not None:
                data[field] = encrypt_value(data[field])

        return data

    @classmethod
    def from_encrypted(cls, data: Dict[str, Any]) -> "EncryptedModel":
        """Create a model instance from encrypted data."""
        # Copy the data so we don't modify the original
        data_copy = data.copy()

        # Decrypt encrypted fields
        for field in cls.encrypted_fields:
            if field in data_copy and data_copy[field] is not None:
                data_copy[field] = decrypt_value(data_copy[field])

        return cls(**data_copy)
