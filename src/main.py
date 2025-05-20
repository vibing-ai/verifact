"""
VeriFact API Entry Point

This module serves as the main entry point for the VeriFact API service.
It initializes a FastAPI application with the factcheck router.

To run the API server directly:
    python -m src.main

For the web UI interface, use `app.py` with Chainlit.
For CLI access, use `cli.py`.
"""

import logging
import os
import platform
import time
from typing import Any, Dict, List

import psutil
from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from src.api.admin import router as admin_router
from src.api.factcheck import router as factcheck_router
from src.api.factcheck_batch import router as batch_router
from src.api.feedback import router as feedback_router
from src.api.middleware import (
    LoggingContextMiddleware,
    register_exception_handlers,
    setup_middleware,
)
from src.utils.db.db import SupabaseClient
from src.utils.db.db_init import initialize_database
from src.utils.error_handling import ErrorResponseFactory
from src.utils.health.checkers import check_database, check_openrouter_api, check_redis
from src.utils.logging.structured_logger import configure_logging, get_structured_logger
from src.utils.version import get_version_info

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", "INFO")
log_format = os.getenv("LOG_FORMAT", "json")
log_file = os.getenv("LOG_FILE")

numeric_level = getattr(logging, log_level.upper(), logging.INFO)
configure_logging(
    level=numeric_level, json_output=(log_format.lower() == "json"), log_file=log_file
)

logger = get_structured_logger("verifact")

description = """
# VeriFact API

VeriFact is an open-source AI factchecking application designed to detect claims, 
gather evidence, and generate accurate verdicts.

## Factchecking

You can use this API to verify factual claims in text by:
* **Submitting text** containing potential claims
* Receiving **verdicts** with explanations and source citations

The system employs three specialized AI agents:
* **ClaimDetector**: Identifies factual claims worth checking
* **EvidenceHunter**: Gathers evidence from trusted sources
* **VerdictWriter**: Analyzes evidence and generates verdicts

## Feedback

The API also supports collecting user feedback on factchecking results:
* **Submit feedback** with accuracy and helpfulness ratings
* Access **feedback statistics** to analyze user satisfaction
* View feedback for specific claims to identify improvement areas

## Configuration Options

The API supports several configuration options:
* **min_check_worthiness**: Threshold for claims to check (0.0-1.0)
* **max_claims**: Limit the number of claims to process (1-100)
* **domains**: Filter claims by domain/category
* **explanation_detail**: Level of detail for explanations ("brief", "standard", "detailed")
* **include_evidence**: Whether to include evidence details in responses

## Batch Processing

The API includes batch processing capabilities:
* Process multiple claims concurrently
* Prioritize claims based on importance
* Track progress of batch jobs
* Detect relationships between claims
* Receive webhook notifications when processing completes

## Authentication

All API endpoints are protected with API key authentication. Include your API key in the request header:
```
X-API-Key: your-api-key
```

## Rate Limiting

The API includes rate limiting to ensure fair usage. Each API key has a limit on the number of requests
per time window. Rate limit information is included in the response headers:
* **X-RateLimit-Limit**: Total number of requests allowed
* **X-RateLimit-Remaining**: Remaining requests in the current window
* **X-RateLimit-Reset**: Time when the rate limit window resets

## Note

This is an alpha version of the API. Features and endpoints may change as the project evolves.
"""

tags_metadata = [
    {
        "name": "Factchecking",
        "description": "Operations related to factchecking claims in text.",
    },
    {
        "name": "Batch Factchecking",
        "description": "Operations related to batch processing of multiple claims.",
    },
    {
        "name": "Feedback",
        "description": "Operations related to user feedback on factchecking results.",
    },
    {
        "name": "Health",
        "description": "Operations related to system health and monitoring.",
    },
]

app = FastAPI(
    title="VeriFact API",
    description=description,
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "VeriFact Team",
        "url": "https://github.com/vibing-ai/verifact",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Create health check router
health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=Dict[str, Any])
async def health_check(full: bool = False):
    """
    Health check endpoint that verifies system status.

    Args:
        full: If True, returns detailed health information about all dependencies

    Returns:
        Health status information
    """
    start_time = time.time()

    # Basic health information
    health_info = {
        "status": "ok",
        "version": get_version_info(),
        "timestamp": int(time.time()),
        "uptime": int(time.time() - psutil.boot_time()),
        "request_time_ms": 0,  # Will be updated before return
    }

    # Check dependencies if full check requested
    if full:
        health_info["dependencies"] = await check_dependencies()
        health_info["system"] = get_system_info()

    # Calculate request processing time
    health_info["request_time_ms"] = int((time.time() - start_time) * 1000)

    # Update overall status based on dependency checks
    if full and any(dep["status"] != "ok" for dep in health_info["dependencies"]):
        health_info["status"] = "degraded"

    return health_info


async def check_dependencies() -> List[Dict[str, Any]]:
    """Check the health of all system dependencies."""
    dependencies = []

    # Check database connection
    db_status = await check_database()
    dependencies.append(
        {
            "name": "database",
            "type": "supabase",
            "status": db_status["status"],
            "latency_ms": db_status["latency_ms"],
            "details": db_status.get("details"),
        }
    )

    # Check Redis if used
    redis_status = await check_redis()
    if redis_status:
        dependencies.append(
            {
                "name": "redis",
                "type": "redis",
                "status": redis_status["status"],
                "latency_ms": redis_status["latency_ms"],
                "details": redis_status.get("details"),
            }
        )

    # Check OpenRouter API
    api_status = await check_openrouter_api()
    dependencies.append(
        {
            "name": "openrouter",
            "type": "api",
            "status": api_status["status"],
            "latency_ms": api_status["latency_ms"],
            "details": api_status.get("details"),
        }
    )

    return dependencies


def get_system_info() -> Dict[str, Any]:
    """Get system information for health check."""
    return {
        "os": platform.system(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_mb": round(psutil.virtual_memory().total / (1024 * 1024)),
        "memory_available_mb": round(psutil.virtual_memory().available / (1024 * 1024)),
        "disk_free_mb": round(psutil.disk_usage("/").free / (1024 * 1024)),
    }


# Add LoggingContextMiddleware first
app.add_middleware(LoggingContextMiddleware)

# Add routers
app.include_router(factcheck_router, prefix="/api/v1")
app.include_router(batch_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1/feedback")
app.include_router(admin_router, prefix="/api/v1")
# Include the health router
app.include_router(health_router, prefix="/api/v1")


# Initialize database on startup and close on shutdown
@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    logger.info("Initializing application resources")

    # Initialize Supabase database schema
    try:
        db_init_result = await initialize_database()
        if db_init_result["status"] == "success":
            logger.info("Supabase database schema initialized successfully")

            # Check pgvector extension
            if "pgvector_status" in db_init_result:
                pgvector_status = db_init_result["pgvector_status"]
                if not pgvector_status.get("available", False):
                    logger.warning(
                        "PGVector extension not available in Supabase! Vector similarity search and embeddings "
                        "functionality will not work. Please enable the pgvector extension in your Supabase project."
                    )
                else:
                    logger.info(
                        f"PGVector extension is available (version: {pgvector_status.get('version', 'unknown')})"
                    )
        else:
            logger.error(
                f"Failed to initialize Supabase database schema: {db_init_result['message']}"
            )
    except Exception as e:
        logger.exception(f"Error during database initialization: {str(e)}")

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Shutting down application and cleaning up resources")

    # Close any connections
    try:
        # Close Supabase client if needed
        client = SupabaseClient()
        client.close()
    except Exception as e:
        logger.exception(f"Error during shutdown: {str(e)}")

    logger.info("Application shutdown complete")


# Set up middleware
setup_middleware(app)

# Register exception handlers
register_exception_handlers(app)


# Additional global exception handlers
@app.exception_handler(PydanticValidationError)
async def validation_exception_handler(request: Request, exc: PydanticValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            ErrorResponseFactory.create_error_response(
                error_type=ErrorResponseFactory.VALIDATION_ERROR,
                message="Invalid request parameters",
                details=exc.errors(),
                exc_info=exc,
            )
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ErrorResponseFactory.create_error_response(
                error_type=getattr(exc, "error_type", "http_error"),
                message=str(exc.detail) if isinstance(exc.detail, str) else "HTTP error occurred",
                details=exc.detail if not isinstance(exc.detail, str) else None,
                status_code=exc.status_code,
                exc_info=exc,
            )
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions."""
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            ErrorResponseFactory.create_error_response(
                error_type=ErrorResponseFactory.SERVER_ERROR,
                message="An internal server error occurred",
                details=str(exc) if not is_production else None,
                exc_info=exc,
            )
        ),
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting VeriFact API server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
