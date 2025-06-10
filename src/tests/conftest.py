import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)
