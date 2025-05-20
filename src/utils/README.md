# VeriFact Utilities

This directory contains utility modules used throughout the VeriFact application, organized into logical subdirectories by functionality.

## Directory Structure

- `db/`: Database utilities for Supabase and PGVector integration
- `logging/`: Logging and metrics tracking
- `async/`: Asynchronous processing, task queues, and retry mechanisms
- `cache/`: Caching utilities for storing frequently accessed data
- `models/`: Model configuration and management
- `search/`: Search tools for retrieving information
- `validation/`: Input validation and exception handling

## Import Guidelines

All key utilities are re-exported from the main `utils` package for convenience:

```python
# Import directly from utils package
from src.utils import Cache, MetricsTracker, db, search_web

# Or import from specific submodules for less common components
from src.utils.logging import LogManager
from src.utils.validation import DataFormatError
```

## Utility Modules

### Database Utilities (`db/`)

```python
from src.utils import db

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

### Logging (`logging/`)

```python
from src.utils.logging import get_logger, get_component_logger

# Get the default logger
logger = get_logger()
logger.info("This is a simple log message")

# Get a component-specific logger
claim_logger = get_component_logger("claim_detector")
claim_logger.info("Processing claim", extra={"claim_id": "123", "text": "Earth is round"})
```

### Metrics Tracking (`logging/`)

```python
from src.utils import MetricsTracker, claim_detector_metrics

# Track claim detection metrics
claim_detector_metrics.increment("claims_processed")
claim_detector_metrics.record_value("detection_time", 0.35)

# Create a custom metrics tracker
custom_metrics = MetricsTracker("custom_component")
custom_metrics.increment("requests")
```

### Caching (`cache/`)

```python
from src.utils import Cache, claim_cache

# Use an existing cache
cached_result = claim_cache.get("Earth is round")

# Create a new cache
my_cache = Cache("my_component", ttl=3600)
my_cache.set("key", "value")
```

### Async Processing (`async/`)

```python
from src.utils import AsyncProcessor, PriorityQueue, retry

# Process tasks asynchronously
processor = AsyncProcessor(max_workers=4)
processor.submit(process_document, doc_id="doc123")

# Use priority queue
queue = PriorityQueue()
queue.put(item, priority=1)

# Retry with exponential backoff
@retry(max_attempts=3)
def api_call():
    # API call that might fail
    pass
```

### Model Configuration (`models/`)

```python
from src.utils.models import configure_model, get_model_config

# Configure model
configure_model("gpt-4", temperature=0.2, max_tokens=500)

# Get model configuration
config = get_model_config("gpt-4")
```

### Search Tools (`search/`)

```python
from src.utils import search_web, extract_sources

# Search for information
results = search_web("climate change effects")

# Extract sources from search results
sources = extract_sources(results)
```

### Validation (`validation/`)

```python
from src.utils import validate_input, ValidationError
from src.utils.validation import DataFormatError

# Validate user input
try:
    validated_data = validate_input(user_data, required_fields=["claim", "sources"])
except ValidationError as e:
    handle_error(e)
```

## Adding New Utilities

When adding new utility modules:

1. Place the module in the appropriate subdirectory
2. Include detailed docstrings explaining the purpose and usage
3. Use type hints for all functions and methods
4. Include appropriate error handling
5. Write tests for all utility functions
6. Update the `__init__.py` file in the subdirectory to export key functions
7. Consider whether to re-export important functions in the main `utils/__init__.py`
8. Update this README with information about the new module
