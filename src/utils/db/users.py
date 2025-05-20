"""Database utilities for user management.

This module provides functions for:
- Creating users
- Retrieving users
- Updating users
- Deleting users
"""

from datetime import datetime

from src.models.user import User
from src.utils.db.db import QueryError


async def create_user(user: User) -> str:
    """Create a new user with encrypted sensitive fields.

    Args:
        user: The user to create

    Returns:
        The ID of the created user
    """
    try:
        # Convert to dict with encryption applied
        user_data = user.dict()

        # In a real implementation, store in database
        # For now, we'll demonstrate the approach

        # Example SQL that would be used
        query = """
        INSERT INTO users (
            id, email, name, phone, api_key, access_token, refresh_token,
            created_at, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        # Note: user_data["api_key"], user_data["access_token"], etc. are
        # already encrypted

        # In a real implementation, execute the query and return the ID
        return user.id
    except Exception as e:
        raise QueryError(f"Failed to create user: {str(e)}")


async def get_user_by_id(user_id: str) -> User | None:
    """Get a user by ID, automatically decrypting sensitive fields.

    Args:
        user_id: The user ID

    Returns:
        The user if found, None otherwise
    """
    try:
        # In a real implementation, fetch from database

        # Example SQL that would be used
        query = """
        SELECT id, email, name, phone, api_key, access_token, refresh_token,
               created_at, updated_at, last_login_at, metadata
        FROM users
        WHERE id = %s
        """

        # For demonstration, we'll return a mock user
        # In a real implementation, this would be fetched from the database

        # Mock data with encrypted fields
        mock_user_data = {
            "id": user_id,
            "email": "user@example.com",
            "name": "Example User",
            "phone": "123-456-7890",
            # These would be encrypted in the database
            "api_key": "encrypted_api_key_value",
            "access_token": "encrypted_access_token_value",
            "refresh_token": "encrypted_refresh_token_value",
            "created_at": datetime.utcnow(),
            "metadata": {"last_ip": "127.0.0.1"},
        }

        # Create user from encrypted data
        # This will automatically decrypt the sensitive fields
        return User.from_encrypted(mock_user_data)
    except Exception as e:
        raise QueryError(f"Failed to get user: {str(e)}")


async def update_user(user: User) -> bool:
    """Update a user, encrypting sensitive fields.

    Args:
        user: The user to update

    Returns:
        True if the user was updated, False otherwise
    """
    try:
        # Convert to dict with encryption applied
        user_data = user.dict()

        # Update the updated_at timestamp
        user_data["updated_at"] = datetime.utcnow()

        # In a real implementation, update in database
        # Note: user_data["api_key"], user_data["access_token"], etc. are
        # already encrypted

        # Example SQL that would be used
        query = """
        UPDATE users
        SET email = %s, name = %s, phone = %s, api_key = %s,
            access_token = %s, refresh_token = %s, updated_at = %s,
            metadata = %s
        WHERE id = %s
        """

        # In a real implementation, execute the query and return success
        return True
    except Exception as e:
        raise QueryError(f"Failed to update user: {str(e)}")


async def delete_user(user_id: str) -> bool:
    """Delete a user.

    Args:
        user_id: The user ID

    Returns:
        True if the user was deleted, False otherwise
    """
    try:
        # In a real implementation, delete from database

        # Example SQL that would be used
        query = """
        DELETE FROM users
        WHERE id = %s
        """

        # In a real implementation, execute the query and return success
        return True
    except Exception as e:
        raise QueryError(f"Failed to delete user: {str(e)}")


async def get_users(limit: int = 100, offset: int = 0) -> list[User]:
    """Get a list of users.

    Args:
        limit: Maximum number of users to return
        offset: Offset to start from

    Returns:
        List of users
    """
    try:
        # In a real implementation, fetch from database

        # Example SQL that would be used
        query = """
        SELECT id, email, name, phone, api_key, access_token, refresh_token,
               created_at, updated_at, last_login_at, metadata
        FROM users
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """

        # For demonstration, we'll return an empty list
        # In a real implementation, this would be fetched from the database
        return []
    except Exception as e:
        raise QueryError(f"Failed to get users: {str(e)}")


async def find_user_by_email(email: str) -> User | None:
    """Find a user by email.

    Args:
        email: The email to search for

    Returns:
        The user if found, None otherwise
    """
    try:
        # In a real implementation, fetch from database

        # Example SQL that would be used
        query = """
        SELECT id, email, name, phone, api_key, access_token, refresh_token,
               created_at, updated_at, last_login_at, metadata
        FROM users
        WHERE email = %s
        """

        # For demonstration, we'll return None
        # In a real implementation, this would be fetched from the database
        return None
    except Exception as e:
        raise QueryError(f"Failed to find user by email: {str(e)}")
