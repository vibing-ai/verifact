"""
API Key Management Utilities

This module provides functions for managing API keys in the database.
It includes functions for creating, validating, and revoking API keys.
"""

import os
import uuid
import hmac
import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import asyncpg
from asyncpg.pool import Pool

from src.utils.exceptions import InvalidAPIKeyError, DatabaseError
from src.models.security import ApiKey, ApiKeyScope
from src.utils.security.hashing import hash_value, secure_compare
from src.utils.db.db import QueryError

logger = logging.getLogger("verifact.api_keys")

# Get salt from environment or use a default for development
API_KEY_SALT = os.getenv("API_KEY_SALT", "verifact_salt")
API_KEY_EXPIRY_DAYS = int(os.getenv("API_KEY_EXPIRY_DAYS", "30"))
API_KEY_PREFIX = "vf_"
API_KEY_LENGTH = 32  # Length of the key not including prefix


# Database connection pool
_pool: Optional[Pool] = None

# In-memory cache for dev/testing
# In production, use Redis or a similar distributed cache
_api_key_cache = {}


async def get_pool() -> Pool:
    """
    Get or create the database connection pool.
    
    Returns:
        Pool: A connection pool for the database
    """
    global _pool
    if _pool is None:
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise DatabaseError(
                "Database connection URL not configured",
                details={"env_var": "SUPABASE_DB_URL"}
            )
        
        try:
            _pool = await asyncpg.create_pool(db_url)
            logger.info("Database connection pool created")
            
            # Ensure the API keys table exists
            await _ensure_api_keys_table()
        except Exception as e:
            logger.exception("Failed to create database connection pool")
            raise DatabaseError(
                "Failed to connect to database",
                details={"error": str(e)}
            )
    
    return _pool


async def _ensure_api_keys_table() -> None:
    """
    Ensure the api_keys table exists in the database.
    This creates the table if it doesn't exist.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create the api_keys table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                key_hash TEXT NOT NULL,
                key_prefix VARCHAR(8) NOT NULL,
                user_id UUID,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                revoked BOOLEAN DEFAULT FALSE,
                permissions JSONB DEFAULT '{}'::JSONB,
                UNIQUE(key_hash)
            );
            
            -- Add index for faster key lookup
            CREATE INDEX IF NOT EXISTS api_keys_key_hash_idx ON api_keys(key_hash);
            CREATE INDEX IF NOT EXISTS api_keys_user_id_idx ON api_keys(user_id);
            
            -- Add comment to the table
            COMMENT ON TABLE api_keys IS 'API keys for accessing the VeriFact API';
        """)
        
        logger.info("API keys table created or verified")


def _hash_api_key(api_key: str) -> str:
    """
    Create a secure hash of the API key.
    
    Args:
        api_key: The API key to hash
        
    Returns:
        str: A hex-encoded hash of the API key
    """
    return hmac.new(
        API_KEY_SALT.encode(), 
        api_key.encode(), 
        hashlib.sha256
    ).hexdigest()


def _generate_api_key() -> str:
    """
    Generate a new random API key.
    
    Returns:
        str: A new API key in the format "vf_<32 alphanumeric chars>"
    """
    # Generate random bytes and encode as base64
    random_bytes = secrets.token_bytes(24)  # 24 bytes will give us about 32 characters in base64
    
    # Convert to base64 and remove non-alphanumeric characters
    key_part = base64.b64encode(random_bytes).decode('utf-8')
    key_part = ''.join(c for c in key_part if c.isalnum())
    
    # Truncate to the desired length
    key_part = key_part[:API_KEY_LENGTH]
    
    # Add prefix
    return f"{API_KEY_PREFIX}{key_part}"


async def create_api_key(
    name: str,
    owner_id: str,
    scopes: List[ApiKeyScope],
    expires_at: Optional[datetime] = None
) -> tuple[ApiKey, str]:
    """
    Create a new API key and store it in the database.
    
    Args:
        name: Name for the API key
        owner_id: ID of the key owner
        scopes: List of permission scopes
        expires_at: Optional expiration date
        
    Returns:
        Tuple of (ApiKey object, plain text key for one-time display)
    """
    # Create the API key
    api_key, plain_key = ApiKey.create(name, owner_id, scopes, expires_at)
    
    try:
        # In a real implementation, store in database
        # For now, just use in-memory cache for demonstration
        _api_key_cache[api_key.id] = api_key
        
        # Also index by prefix for faster lookups
        _api_key_cache[f"prefix:{api_key.key_prefix}"] = api_key
        
        return api_key, plain_key
    except Exception as e:
        raise QueryError(f"Failed to create API key: {str(e)}")


async def get_api_key_by_id(key_id: str) -> Optional[ApiKey]:
    """
    Get an API key by its ID.
    
    Args:
        key_id: The API key ID
        
    Returns:
        The API key if found, None otherwise
    """
    # In a real implementation, fetch from database
    return _api_key_cache.get(key_id)


async def get_api_key_by_prefix(prefix: str) -> Optional[ApiKey]:
    """
    Get an API key by its prefix.
    
    Args:
        prefix: The API key prefix
        
    Returns:
        The API key if found, None otherwise
    """
    # In a real implementation, fetch from database
    return _api_key_cache.get(f"prefix:{prefix}")


async def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Validate an API key and return its metadata.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        Dict with API key metadata if valid, None otherwise
    """
    try:
        # Parse the key
        prefix, rest = api_key.split(".", 1)
        
        # Get the API key from the database
        db_key = await get_api_key_by_prefix(prefix)
        if not db_key:
            return None
        
        # Check if key has expired
        if db_key.expires_at and db_key.expires_at < datetime.utcnow():
            return None
        
        # Verify the key using secure comparison
        full_key = f"{prefix}.{rest}"
        if not secure_compare(hash_value(full_key), db_key.key_hash):
            return None
        
        # Update last used timestamp
        db_key.last_used_at = datetime.utcnow()
        _api_key_cache[db_key.id] = db_key
        _api_key_cache[f"prefix:{db_key.key_prefix}"] = db_key
        
        # Return key metadata
        return {
            "id": db_key.id,
            "owner_id": db_key.owner_id,
            "scopes": [scope.value for scope in db_key.scopes],
            "name": db_key.name,
            "created_at": db_key.created_at.isoformat(),
            "expires_at": db_key.expires_at.isoformat() if db_key.expires_at else None
        }
    except Exception:
        return None


async def list_api_keys(owner_id: str) -> List[ApiKey]:
    """
    List all API keys for an owner.
    
    Args:
        owner_id: The owner ID
        
    Returns:
        List of API keys
    """
    # In a real implementation, fetch from database
    # For now, just filter the in-memory cache
    return [
        key for key in _api_key_cache.values()
        if isinstance(key, ApiKey) and key.owner_id == owner_id
    ]


async def revoke_api_key(key_id: str, owner_id: str) -> bool:
    """
    Revoke an API key.
    
    Args:
        key_id: The API key ID
        owner_id: The owner ID (for authorization)
        
    Returns:
        True if the key was revoked, False otherwise
    """
    # In a real implementation, update database
    api_key = _api_key_cache.get(key_id)
    
    if not api_key or not isinstance(api_key, ApiKey) or api_key.owner_id != owner_id:
        return False
    
    # Remove from cache
    prefix = api_key.key_prefix
    _api_key_cache.pop(key_id, None)
    _api_key_cache.pop(f"prefix:{prefix}", None)
    
    return True


async def update_api_key_last_used(key_id: str) -> None:
    """
    Update the last used timestamp for an API key.
    
    Args:
        key_id: The API key ID
    """
    # In a real implementation, update database
    api_key = _api_key_cache.get(key_id)
    
    if api_key and isinstance(api_key, ApiKey):
        api_key.last_used_at = datetime.utcnow()
        _api_key_cache[key_id] = api_key
        _api_key_cache[f"prefix:{api_key.key_prefix}"] = api_key


async def rotate_api_key(api_key: str) -> Tuple[str, Dict[str, Any]]:
    """
    Rotate an API key by revoking the old key and creating a new one.
    
    Args:
        api_key: The API key to rotate
        
    Returns:
        Tuple[str, Dict[str, Any]]: The new API key and its metadata
        
    Raises:
        InvalidAPIKeyError: If the API key is invalid, revoked, or expired
    """
    # Validate the existing key
    key_data = await validate_api_key(api_key)
    
    # Create a new key with the same permissions and user
    new_key, new_key_data = await create_api_key(
        name=key_data["name"],
        owner_id=key_data["owner_id"],
        scopes=key_data["scopes"],
    )
    
    # Revoke the old key
    await revoke_api_key(key_data["id"], key_data["owner_id"])
    
    logger.info(f"Rotated API key for user {key_data['owner_id']}")
    
    return new_key, new_key_data


async def list_user_api_keys(user_id: str) -> List[Dict[str, Any]]:
    """
    List all active API keys for a user.
    
    Args:
        user_id: The user ID to list keys for
        
    Returns:
        List[Dict[str, Any]]: A list of API key metadata
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get all active keys for the user
            rows = await conn.fetch("""
                SELECT 
                    id, key_prefix, user_id, created_at, expires_at,
                    permissions
                FROM api_keys
                WHERE user_id = $1
                  AND NOT revoked
                  AND expires_at > NOW()
                ORDER BY created_at DESC
            """, user_id)
            
            # Convert rows to dictionaries
            keys = [
                {
                    "id": str(row["id"]),
                    "prefix": row["key_prefix"],
                    "created_at": row["created_at"].isoformat(),
                    "expires_at": row["expires_at"].isoformat(),
                    "permissions": row["permissions"]
                }
                for row in rows
            ]
            
            return keys
    except Exception as e:
        logger.exception("Failed to list user API keys")
        raise DatabaseError(
            "Failed to list user API keys",
            details={"error": str(e)}
        ) 