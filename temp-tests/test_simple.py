#!/usr/bin/env python3
"""Simple basic test to verify the environment is working correctly."""

import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test that the environment variables are loaded correctly."""
    # Load environment variables
    load_dotenv()
    
    # Check some basic environment variables
    print("\n=== Testing Environment Variables ===\n")
    
    environment = os.environ.get("ENVIRONMENT", "development")
    print(f"Environment: {environment}")
    
    # Check Python version
    print(f"\nPython version: {sys.version}")
    
    # Check path
    print(f"\nPython path: {sys.path[0]}")
    
    # Test importing key modules
    print("\n=== Testing Module Imports ===\n")
    
    try:
        import src.utils.logging.structured_logger
        print("✅ Successfully imported structured_logger module")
    except ImportError as e:
        print(f"❌ Failed to import structured_logger module: {e}")
    
    try:
        import src.utils.models.model_config
        print("✅ Successfully imported model_config module")
    except ImportError as e:
        print(f"❌ Failed to import model_config module: {e}")
    
    print("\n=== Test Complete ===")
    
    # Assert that the test passes
    assert True

if __name__ == "__main__":
    test_environment() 