"""VeriFact Configuration Module.

This module provides centralized configuration management using Pydantic for
validation of environment variables.
"""

import os
from enum import Enum
from typing import Any

from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    PostgresDsn,
    RedisDsn,
    root_validator,
    validator,
    ValidationError,
)
from pydantic_settings import BaseSettings

# Load .env file if it exists
load_dotenv()


class LogLevel(str, Enum):
    """Valid log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Possible environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class ModelConfig(BaseModel):
    """LLM configuration settings."""

    temperature: float = Field(0.1, ge=0.0, le=1.0, description="Model temperature (randomness)")
    max_tokens: int = Field(1000, gt=0, description="Maximum tokens in model response")
    request_timeout: int = Field(120, gt=0, description="Timeout for model requests in seconds")


class DatabaseConfig(BaseModel):
    """Database configuration settings."""

    url: PostgresDsn = Field(..., description="Database connection URL")
    min_pool_size: int = Field(2, ge=1, description="Minimum connections in pool")
    max_pool_size: int = Field(10, ge=1, description="Maximum connections in pool")
    max_idle_time: float = Field(300.0, ge=0, description="Maximum idle time in seconds")
    command_timeout: float = Field(60.0, ge=0, description="Command timeout in seconds")

    @validator("url", pre=True)
    def build_db_url(cls, v: str | None) -> str:
        """Build database URL from environment variables if not directly provided.

        Args:
            v: The URL value from settings or None

        Returns:
            str: Complete PostgreSQL connection URL
        """
        if v:
            return v

        # Construct from components if not provided directly
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "postgres")

        return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class RedisConfig(BaseModel):
    """Redis configuration settings."""

    enabled: bool = Field(True, description="Enable Redis caching")
    url: RedisDsn | None = Field(None, description="Redis connection URL")
    password: str | None = Field("", description="Redis password")
    cache_ttl: int = Field(86400, ge=0, description="Default cache TTL in seconds (24 hours)")
    evidence_cache_ttl: int = Field(86400, ge=0, description="Evidence cache TTL in seconds")

    @validator("url", pre=True)
    def build_redis_url(cls, v: str | None, values: dict[str, Any]) -> str | None:
        """Build Redis URL from environment variables if not directly provided.

        Args:
            v: The URL value from settings or None
            values: Other configuration values

        Returns:
            str or None: Complete Redis connection URL or None if Redis is disabled
        """
        if not values.get("enabled", True):
            return None

        if v:
            return v

        # Construct from components if not provided directly
        password_part = f":{values.get('password', '')}@" if values.get("password") else ""
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        db = os.getenv("REDIS_DB", "0")

        return f"redis://{password_part}{host}:{port}/{db}"


class APIConfig(BaseModel):
    """API configuration settings."""

    host: str = Field("0.0.0.0", description="API host")
    port: int = Field(8000, gt=0, lt=65536, description="API port")
    api_keys: list[str] = Field([], description="List of valid API keys")
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests: int = Field(100, gt=0, description="Maximum requests per window")
    rate_limit_window: int = Field(3600, gt=0, description="Rate limit window in seconds")
    api_key_enabled: bool = Field(True, description="Enable API key authentication")
    api_key_salt: str = Field("verifact_salt", description="Salt for API key hashing")
    api_key_expiry_days: int = Field(30, ge=1, description="API key expiry in days")

    @validator("api_keys", pre=True)
    def parse_api_keys(cls, v: str | list[str]) -> list[str]:
        """Parse API keys from string to list.

        Args:
            v: API keys as comma-separated string or lis

        Returns:
            list[str]: List of API keys
        """
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v


class UIConfig(BaseModel):
    """UI configuration settings."""

    host: str = Field("0.0.0.0", description="UI host")
    port: int = Field(8501, gt=0, lt=65536, description="UI port")
    auth_enabled: bool = Field(False, description="Enable authentication")
    auth_secret: str | None = Field(None, description="Authentication secret")
    admin_user: str = Field("admin", description="Admin username")
    persist: bool = Field(True, description="Persist chats in database")


class OpenRouterConfig(BaseModel):
    """OpenRouter API configuration."""

    api_key: str = Field(..., description="OpenRouter API key")
    site_url: HttpUrl | None = Field(None, description="Site URL for OpenRouter")
    site_name: str = Field("VeriFact", description="Site name for OpenRouter")


class ModelSelectionConfig(BaseModel):
    """Model selection configuration."""

    default_model: str = Field("meta-llama/llama-3.3-8b-instruct:free", description="Default model")
    claim_detector_model: str = Field("qwen/qwen3-8b:free", description="Claim detector model")
    evidence_hunter_model: str = Field(
        "google/gemma-3-27b-it:free", description="Evidence hunter model"
    )
    verdict_writer_model: str = Field(
        "deepseek/deepseek-chat:free", description="Verdict writer model"
    )
    embedding_model: str = Field("text-embedding-3-small", description="Embedding model")
    enable_caching: bool = Field(True, description="Enable model response caching")
    cache_size: int = Field(1000, gt=0, description="Size of model response cache")
    fallback_models: list[str] | None = Field(None, description="Fallback models")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = Field(LogLevel.INFO, description="Log level")
    format: str = Field("json", description="Log format (json or text)")
    file: str | None = Field(None, description="Log file path")
    rotation_size: int = Field(10485760, gt=0, description="Log rotation size in bytes")
    rotation_count: int = Field(5, ge=0, description="Number of rotated logs to keep")
    daily_rotation: bool = Field(False, description="Enable daily log rotation")


class SearchConfig(BaseModel):
    """Search configuration."""

    use_serper: bool = Field(False, description="Use Serper.dev API")
    serper_api_key: str | None = Field(None, description="Serper.dev API key")

    @validator("serper_api_key")
    def validate_serper_api_key(cls, v: str | None, values: dict[str, Any]) -> str | None:
        """Validate that Serper API key is provided when Serper is enabled.

        Args:
            v: The Serper API key or None
            values: Other configuration values

        Returns:
            str or None: The validated API key

        Raises:
            ValueError: If Serper is enabled but no API key is provided
        """
        if values.get("use_serper", False) and not v:
            raise ValueError("Serper API key is required when use_serper is True")
        return v


class Settings(BaseSettings):
    """Main configuration class for VeriFact."""

    # Application metadata
    app_name: str = Field("VeriFact", description="Application name")
    environment: Environment = Field(Environment.DEVELOPMENT, description="Deployment environment")
    app_version: str = Field("0.1.0", description="Application version")

    # Component configurations
    database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig())
    redis: RedisConfig = Field(default_factory=lambda: RedisConfig())
    api: APIConfig = Field(default_factory=lambda: APIConfig())
    ui: UIConfig = Field(default_factory=lambda: UIConfig())
    openrouter: OpenRouterConfig
    models: ModelSelectionConfig = Field(default_factory=lambda: ModelSelectionConfig())
    model_params: ModelConfig = Field(default_factory=lambda: ModelConfig())
    logging: LoggingConfig = Field(default_factory=lambda: LoggingConfig())
    search: SearchConfig = Field(default_factory=lambda: SearchConfig())

    class Config:
        """Pydantic config."""

        env_nested_delimiter = "__"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True
        extra = "ignore"

    @root_validator(pre=True, skip_on_failure=True)
    def build_config(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Pre-process raw values to inject nested configuration.

        Args:
            values: Raw configuration values to process

        Returns:
            dict: Processed configuration with nested values
        """
        result = dict(values)

        # Construct database config from components
        result.setdefault("database", {})
        db_url = os.getenv("SUPABASE_DB_URL")
        if db_url:
            result["database"]["url"] = db_url
        result["database"].setdefault("min_pool_size", os.getenv("DB_POOL_MIN_SIZE", "2"))
        result["database"].setdefault("max_pool_size", os.getenv("DB_POOL_MAX_SIZE", "10"))
        result["database"].setdefault("max_idle_time", os.getenv("DB_POOL_MAX_IDLE_TIME", "300"))
        result["database"].setdefault("command_timeout", os.getenv("DB_COMMAND_TIMEOUT", "60.0"))

        # Construct Redis config
        result.setdefault("redis", {})
        result["redis"].setdefault("enabled", os.getenv("REDIS_ENABLED", "true").lower() == "true")
        result["redis"].setdefault("url", os.getenv("REDIS_URL"))
        result["redis"].setdefault("password", os.getenv("REDIS_PASSWORD", ""))
        result["redis"].setdefault("cache_ttl", os.getenv("REDIS_CACHE_TTL", "86400"))
        result["redis"].setdefault("evidence_cache_ttl", os.getenv("EVIDENCE_CACHE_TTL", "86400"))

        # Construct API config
        result.setdefault("api", {})
        result["api"].setdefault("host", os.getenv("HOST", "0.0.0.0"))
        result["api"].setdefault("port", os.getenv("PORT", "8000"))
        result["api"].setdefault("api_keys", os.getenv("VERIFACT_API_KEYS", ""))
        result["api"].setdefault("rate_limit_enabled", os.getenv("RATE_LIMIT_ENABLED", "true"))
        result["api"].setdefault("rate_limit_requests", os.getenv("RATE_LIMIT_REQUESTS", "100"))
        result["api"].setdefault("rate_limit_window", os.getenv("RATE_LIMIT_WINDOW", "3600"))
        result["api"].setdefault("api_key_enabled", os.getenv("API_KEY_ENABLED", "true"))
        result["api"].setdefault("api_key_salt", os.getenv("API_KEY_SALT", "verifact_salt"))
        result["api"].setdefault("api_key_expiry_days", os.getenv("API_KEY_EXPIRY_DAYS", "30"))

        # Construct UI config
        result.setdefault("ui", {})
        result["ui"].setdefault("host", os.getenv("CHAINLIT_HOST", "0.0.0.0"))
        result["ui"].setdefault("port", os.getenv("CHAINLIT_PORT", "8501"))
        result["ui"].setdefault(
            "auth_enabled", os.getenv("CHAINLIT_AUTH_ENABLED", "false").lower() == "true"
        )
        result["ui"].setdefault("auth_secret", os.getenv("CHAINLIT_AUTH_SECRET"))
        result["ui"].setdefault("admin_user", os.getenv("VERIFACT_ADMIN_USER", "admin"))
        result["ui"].setdefault("persist", os.getenv("CHAINLIT_PERSIST", "true").lower() == "true")

        # Construct OpenRouter config
        result.setdefault("openrouter", {})
        result["openrouter"].setdefault("api_key", os.getenv("OPENROUTER_API_KEY", ""))
        result["openrouter"].setdefault("site_url", os.getenv("OPENROUTER_SITE_URL"))
        result["openrouter"].setdefault("site_name", os.getenv("OPENROUTER_SITE_NAME", "VeriFact"))

        # Construct model selection config
        result.setdefault("models", {})
        result["models"].setdefault(
            "default_model", os.getenv("DEFAULT_MODEL", "meta-llama/llama-3.3-8b-instruct:free")
        )
        result["models"].setdefault(
            "claim_detector_model", os.getenv("CLAIM_DETECTOR_MODEL", "qwen/qwen3-8b:free")
        )
        result["models"].setdefault(
            "evidence_hunter_model",
            os.getenv("EVIDENCE_HUNTER_MODEL", "google/gemma-3-27b-it:free"),
        )
        result["models"].setdefault(
            "verdict_writer_model", os.getenv("VERDICT_WRITER_MODEL", "deepseek/deepseek-chat:free")
        )
        result["models"].setdefault(
            "embedding_model", os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        )
        result["models"].setdefault(
            "enable_caching", os.getenv("ENABLE_MODEL_CACHING", "true").lower() == "true"
        )
        result["models"].setdefault("cache_size", os.getenv("MODEL_CACHE_SIZE", "1000"))
        fallback_models = os.getenv("FALLBACK_MODELS")
        if fallback_models:
            result["models"].setdefault("fallback_models", fallback_models.split(","))

        # Construct model parameters config
        result.setdefault("model_params", {})
        result["model_params"].setdefault("temperature", os.getenv("MODEL_TEMPERATURE", "0.1"))
        result["model_params"].setdefault("max_tokens", os.getenv("MODEL_MAX_TOKENS", "1000"))
        result["model_params"].setdefault(
            "request_timeout", os.getenv("MODEL_REQUEST_TIMEOUT", "120")
        )

        # Construct logging config
        result.setdefault("logging", {})
        result["logging"].setdefault("level", os.getenv("LOG_LEVEL", "INFO"))
        result["logging"].setdefault("format", os.getenv("LOG_FORMAT", "json"))
        result["logging"].setdefault("file", os.getenv("LOG_FILE"))
        result["logging"].setdefault("rotation_size", os.getenv("LOG_ROTATION_SIZE", "10485760"))
        result["logging"].setdefault("rotation_count", os.getenv("LOG_ROTATION_COUNT", "5"))
        result["logging"].setdefault(
            "daily_rotation", os.getenv("LOG_DAILY_ROTATION", "false").lower() == "true"
        )

        # Construct search config
        result.setdefault("search", {})
        result["search"].setdefault(
            "use_serper", os.getenv("USE_SERPER", "false").lower() == "true"
        )
        result["search"].setdefault("serper_api_key", os.getenv("SERPER_API_KEY"))

        # Set application metadata
        result.setdefault("environment", os.getenv("ENVIRONMENT", "development"))
        result.setdefault("app_version", os.getenv("APP_VERSION", "0.1.0"))

        return result


# Create a global instance of settings
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings singleton.

    This function is provided for use with FastAPI Depends.

    Returns:
        Settings: The application settings.
    """
    return settings
