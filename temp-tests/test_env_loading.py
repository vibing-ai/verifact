#!/usr/bin/env python3
"""Test environment variable loading."""

import os
import sys
import pytest
from dotenv import load_dotenv


def test_env_loading():
    """Test that environment variables can be loaded from .env file."""
    load_dotenv()
    
    # Check for some environment variables
    # We're just checking if they exist, not their actual values
    assert "PYTHONPATH" in os.environ
    
    # Print some info for debugging
    print("Environment variables loaded successfully")
    print(f"Python version: {os.sys.version}")
    print(f"Current directory: {os.getcwd()}")
    for var in ["PYTHONPATH", "PATH"]:
        if var in os.environ:
            print(f"{var} is set")
        else:
            print(f"{var} is not set")


if __name__ == "__main__":
    test_env_loading() 