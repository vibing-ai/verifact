"""Test package for VeriFact.

This package contains all tests for the VeriFact system:
- Unit tests
- Integration tests
- API tests
- Agent tests
- System tests
- Performance tests
"""

import os
import sys

# Debug: Print the Python path before any imports
print("Python path at test initialization:")
for p in sys.path:
    print(f"  - {p}")

# Prioritize site-packages over local modules
site_packages = [p for p in sys.path if 'site-packages' in p]
if site_packages:
    # Remove the local directory from path
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if current_dir in sys.path:
        sys.path.remove(current_dir)
    
    # Ensure site-packages comes first in the path
    for sp in site_packages:
        if sp in sys.path:
            sys.path.remove(sp)
            sys.path.insert(0, sp)
    
    # Add the local directory back at the end
    sys.path.append(current_dir)

print("Modified Python path:")
for p in sys.path:
    print(f"  - {p}")

# Add the src directory to the path so that imports work correctly
# for both running tests and for the modules being tested
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try loading the agents module to see which one is being used
try:
    import agents
    print(f"TEST: Using agents module from: {agents.__file__}")
except ImportError as e:
    print(f"TEST: Error importing agents: {e}")

# Import all test packages for pytest discovery
# Temporarily comment out problematic imports for testing
from . import agents, api, integration, models, system, utils

# Skip performance tests for now as they cause import issues with matplotlib
# from . import performance

# Export test packages
__all__ = ["agents", "api", "integration", "models", "system", "utils"]
# __all__ = ["agents", "api", "integration", "models", "performance", "system", "utils"]
