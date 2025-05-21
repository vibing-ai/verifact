#!/usr/bin/env python3
"""Test script to verify imports are working correctly."""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, ".")

# Import the agent classes
try:
    import agents
    print("✅ Successfully imported agents package")
except ImportError as e:
    print(f"❌ Failed to import agents package: {e}")

# Import from the async module
try:
    import src.utils
    # Get the async module without using the keyword directly
    async_module = getattr(src.utils, "async")
    print(f"✅ Successfully imported async module: {dir(async_module)}")
except ImportError as e:
    print(f"❌ Failed to import async module: {e}")
except AttributeError as e:
    print(f"❌ Failed to get async module: {e}")

# Import ClaimDetector
try:
    from src.verifact_agents.claim_detector import ClaimDetector
    print("✅ Successfully imported ClaimDetector")
except ImportError as e:
    print(f"❌ Failed to import ClaimDetector: {e}")

print("\nImport test completed")

def test_import_standard_modules():
    """Test that standard Python modules can be imported."""
    import os
    import sys
    import json
    import time
    import datetime
    import logging
    
    # Assert that modules are imported successfully
    assert os
    assert sys
    assert json
    assert time
    assert datetime
    assert logging
    
    print("All standard modules imported successfully") 