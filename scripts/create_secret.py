#!/usr/bin/env python3
"""
Script to generate a secure secret key for Chainlit authentication.
This key should be used as the CHAINLIT_AUTH_SECRET environment variable.

Usage:
    python create_secret.py
    
Output:
    A randomly generated 32-byte key that can be used for CHAINLIT_AUTH_SECRET
"""

import os
import secrets
import base64

def generate_secret_key():
    """Generate a random 32-byte key encoded as base64."""
    # Generate 32 random bytes
    random_bytes = secrets.token_bytes(32)
    # Encode in base64 for easy copy-pasting
    encoded = base64.urlsafe_b64encode(random_bytes).decode()
    return encoded

if __name__ == "__main__":
    print("\n=== VeriFact Authentication Secret Generator ===\n")
    secret_key = generate_secret_key()
    print(f"Generated secret key: {secret_key}")
    print("\nAdd this to your .env file as:")
    print(f"CHAINLIT_AUTH_SECRET=\"{secret_key}\"")
    print("\nKeep this key secure and don't share it publicly!") 