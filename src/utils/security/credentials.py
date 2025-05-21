"""Credential management for VeriFact.

This module provides utilities for securely retrieving credentials
from various sources like environment variables, configuration files,
or secure credential stores.
"""

import os
from pathlib import Path
from typing import Optional

import dotenv

# Load .env file if it exists
dotenv.load_dotenv()


class CredentialError(Exception):
    """Exception raised for credential-related errors."""

    pass


def get_credential(
    name: str,
    default: Optional[str] = None,
    required: bool = False,
    credential_file: Optional[str] = None,
) -> Optional[str]:
    """Get a credential from environment variables or config files.

    This function attempts to retrieve credentials in the following order:
    1. Environment variable
    2. Specified credential file
    3. Default value if provided
    4. Raise an error if required=True and no credential found

    Args:
        name: The name of the credential to retrieve
        default: Optional default value if credential is not found
        required: Whether the credential is required
        credential_file: Optional path to a credential file

    Returns:
        The credential value or None if not found and not required

    Raises:
        CredentialError: If the credential is required but not found
    """
    # Try environment variable first (preferred method)
    value = os.getenv(name)
    if value is not None:
        return value

    # Try credential file if specified
    if credential_file:
        cred_path = Path(credential_file)
        if cred_path.exists():
            try:
                # Load the credential file (.env format)
                config = dotenv.dotenv_values(credential_file)
                if name in config:
                    return config[name]
            except Exception as e:
                if required:
                    raise CredentialError(f"Error reading credential file: {e}") from e

    # Return default if provided
    if default is not None:
        return default

    # Raise error if required
    if required:
        raise CredentialError(
            f"Required credential '{name}' not found in environment variables or credential file"
        )

    # Return None if not required and not found
    return None 