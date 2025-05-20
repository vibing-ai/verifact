# VeriFact Configuration System

This document explains the centralized configuration system for VeriFact.

## Overview

VeriFact uses a Pydantic-based configuration system that provides:

1. **Centralized configuration**: All settings in one place
2. **Type validation**: Ensure configuration values have the correct types
3. **Default values**: Sensible defaults for most settings
4. **Hierarchical structure**: Logically grouped settings
5. **Environment variable binding**: Automatic loading from env vars

## Configuration Hierarchy

The configuration is organized into logical sections:

```
Settings
├── app_name
├── environment
├── app_version
├── database
│   ├── url
│   ├── min_pool_size
│   ├── max_pool_size
│   ├── max_idle_time
│   └── command_timeout
├── redis
│   ├── enabled
│   ├── url
│   ├── password
│   ├── cache_ttl
│   └── evidence_cache_ttl
├── api
│   ├── host
│   ├── port
│   ├── api_keys
│   ├── rate_limit_enabled
│   ├── rate_limit_requests
│   ├── rate_limit_window
│   ├── api_key_enabled
│   ├── api_key_salt
│   └── api_key_expiry_days
├── ui
│   ├── host
│   ├── port
│   ├── auth_enabled
│   ├── auth_secret
│   ├── admin_user
│   └── persist
├── openrouter
│   ├── api_key
│   ├── site_url
│   └── site_name
├── models
│   ├── default_model
│   ├── claim_detector_model
│   ├── evidence_hunter_model
│   ├── verdict_writer_model
│   ├── embedding_model
│   ├── enable_caching
│   ├── cache_size
│   └── fallback_models
├── model_params
│   ├── temperature
│   ├── max_tokens
│   └── request_timeout
├── logging
│   ├── level
│   ├── format
│   ├── file
│   ├── rotation_size
│   ├── rotation_count
│   └── daily_rotation
└── search
    ├── use_serper
    └── serper_api_key
```

## Environment Variables

All configuration can be set via environment variables. The system supports both flat and nested environment variables:

### Flat Variables (Legacy Style)

These are directly mapped from the traditional environment variables:

```
OPENROUTER_API_KEY=your_key_here
REDIS_ENABLED=true
DB_POOL_MAX_SIZE=10
```

### Nested Variables (New Style)

These use the nested delimiter `__` to specify the configuration path:

```
MODELS__DEFAULT_MODEL=meta-llama/llama-3.3-8b-instruct:free
DATABASE__MIN_POOL_SIZE=5
LOGGING__LEVEL=DEBUG
```

## Using the Configuration

Import the settings from the configuration module:

```python
from src.config import settings

# Access top-level settings
env = settings.environment
version = settings.app_version

# Access nested settings
db_url = settings.database.url
redis_enabled = settings.redis.enabled
api_port = settings.api.port

# Access deeply nested settings
model_temp = settings.model_params.temperature
```

## Dependency Injection

For FastAPI endpoints, you can use dependency injection:

```python
from fastapi import Depends
from src.config import get_settings, Settings

@app.get("/api/info")
async def get_api_info(settings: Settings = Depends(get_settings)):
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }
```

## Validation

The configuration system validates all settings at startup:

- **Type checking**: Ensures values have the correct type
- **Range validation**: Numerical values within valid ranges
- **Format validation**: URLs, database connections, etc.
- **Dependency validation**: Related settings are compatible

If validation fails, the application will raise an error at startup with a clear message about the invalid configuration.

## Extending the Configuration

To add new configuration sections or values:

1. Define a new Pydantic model for your section
2. Add it to the main `Settings` class
3. Update the `build_config` method to handle your new section
4. Add appropriate environment variable handling

Example:

```python
class NewFeatureConfig(BaseModel):
    """Configuration for the new feature."""
    enabled: bool = Field(True, description="Enable the new feature")
    max_items: int = Field(100, gt=0, description="Maximum items allowed")

# Then in Settings class:
new_feature: NewFeatureConfig = Field(default_factory=NewFeatureConfig)

# And in build_config:
result.setdefault("new_feature", {})
result["new_feature"].setdefault("enabled",
    os.getenv("NEW_FEATURE_ENABLED", "true").lower() == "true")
result["new_feature"].setdefault("max_items",
    os.getenv("NEW_FEATURE_MAX_ITEMS", "100"))
```

## Best Practices

1. **Always use the settings object**: Don't call `os.getenv()` directly
2. **Add validation**: Use Pydantic's validation features for new settings
3. **Document defaults**: Make clear what happens when a setting is not provided
4. **Maintain backward compatibility**: Support legacy environment variable names
5. **Use semantic grouping**: Group related settings into logical sections
