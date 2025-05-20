"""
Version information utilities for VeriFact.

This module provides functions for getting version information.
"""

import os
import subprocess
from typing import Dict, Any


def get_version_info() -> Dict[str, Any]:
    """
    Get detailed version information including git commit if available.

    Returns:
        Dictionary with version information
    """
    version_info = {
        "version": os.getenv("VERSION", "dev"),
        "build_date": os.getenv("BUILD_DATE", "unknown"),
    }

    # Try to get git information if in a git repository
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()

        git_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()

        version_info["git_hash"] = git_hash
        version_info["git_branch"] = git_branch
    except (subprocess.SubprocessError, FileNotFoundError):
        # Not a git repository or git not available
        pass

    return version_info
