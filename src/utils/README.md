# Utilities

This directory contains utility functions and classes used throughout the VeriFact application.

## Contents

- `db.py`: Database utilities for Supabase and PGVector integration
- `logger.py`: Logging setup and configuration
- Add other utility modules as needed

## Purpose

The utilities in this directory provide common functionality that can be reused across the application:

1. **Database Access**: Connection and query utilities for Supabase and PGVector
2. **Logging**: Standardized logging configuration
3. **Error Handling**: Common error handling utilities
4. **Configuration**: Loading and managing configuration values
5. **Helper Functions**: Reusable code that doesn't fit into a specific component

## Usage

### Database Utilities

```python
from src.utils.db import db

# Store a factcheck result
result = db.store_factcheck_result(
    claim="The Earth is flat",
    verdict="false",
    confidence=0.98,
    explanation="Multiple lines of evidence confirm Earth is approximately spherical",
    sources=["https://nasa.gov/earth-images"]
)

# Retrieve recent factchecks
recent_checks = db.get_recent_factchecks(limit=5)
```

### Logging

```python
from src.utils.logger import get_logger

# Get a logger for your module
logger = get_logger("my_module")

# Log messages
logger.info("Processing claim...")
logger.warning("Evidence retrieval slow")
logger.error("Failed to generate verdict", exc_info=True)
```

## Adding New Utilities

When adding new utility modules:

1. Create a new file with a descriptive name
2. Include detailed docstrings explaining the purpose and usage
3. Use type hints for all functions and methods
4. Include appropriate error handling
5. Write tests for all utility functions
6. Update this README with information about the new module
