"""VeriFact: AI-powered factchecking system."""

import os
import sys

# Ensure we use the installed 'agents' package, not our local 'src/verifact_agents'
# by removing the project directory from sys.path temporarily
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir in sys.path:
    sys.path.remove(current_dir)
    # Re-add it at the end to ensure it's checked after site-packages
    sys.path.append(current_dir)

__version__ = "0.1.0"
