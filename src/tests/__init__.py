"""Test suite for the VeriFact project.

This package contains all tests for the VeriFact project, organized by module.
The test structure follows the same structure as the source code:

- agents/: Tests for the agent implementations
- api/: Tests for the API endpoints
- models/: Tests for data models and schemas
- utils/: Tests for utility functions
- integration/: End-to-end and integration tests
- performance/: Performance and benchmark tests
- system/: System-level tests
"""

import os
import sys

# Add the src directory to the path so that imports work correctly
# for both running tests and for the modules being tested
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import test modules from subdirectories
from .agents import *
from .api import *
from .utils import *
from .models import *
from .integration import *
from .performance import *
from .system import * 