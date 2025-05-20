"""Validation Configuration Loader.

This module loads and provides access to validation configuration settings.
"""

import os
from pathlib import Path
from typing import Any

import yaml


class ValidationConfig:
    """Validation configuration manager class.

    This class loads and provides access to validation configuration settings
    defined in configs/validation.yml.
    """

    def __init__(self):
        """Initialize the validation configuration manager."""
        self._config = {}
        self._load_config()

    def _load_config(self):
        """Load validation configuration from file."""
        # Determine the config file path
        config_path = self._find_config_path()

        if not config_path:
            # Use default values if config file not found
            self._config = self._get_default_config()
            return

        try:
            with open(config_path) as f:
                self._config = yaml.safe_load(f) or {}
        except Exception as e:
            # Log error and use default values
            print(f"Error loading validation config: {str(e)}")
            self._config = self._get_default_config()

    def _find_config_path(self) -> str | None:
        """Find the validation configuration file path.

        Returns:
            Optional[str]: Path to the configuration file, or None if not found
        """
        # List of possible locations to check
        possible_paths = [
            # Current directory
            Path("configs/validation.yml"),
            # Project root
            Path(__file__).parents[3] / "configs" / "validation.yml",
            # Explicit environment variable
            os.environ.get("VERIFACT_VALIDATION_CONFIG"),
        ]

        # Return the first path that exists
        for path in possible_paths:
            if path and Path(path).is_file():
                return str(path)

        return None

    def _get_default_config(self) -> dict[str, Any]:
        """Get default validation configuration.

        Returns:
            Dict[str, Any]: Default configuration
        """
        return {
            "text": {"min_length": 10, "max_length": 50000, "min_factcheck_length": 50},
            "claim": {"min_length": 5, "max_length": 1000, "min_check_worthiness": 0.5},
            "api": {
                "max_claims_per_request": 20,
                "max_batch_claims": 100,
                "rate_limit": 100,
                "authenticated_rate_limit": 1000,
            },
            "url": {"max_length": 2048, "allowed_schemes": ["http", "https"]},
            "feedback": {"min_comment_length": 5, "max_comment_length": 1000},
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: Configuration key (e.g., "text.max_length")
            default: Default value if key not found

        Returns:
            Any: Configuration value
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value


# Create a singleton instance
validation_config = ValidationConfig()
