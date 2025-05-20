"""
VeriFact API Middleware

This module contains middleware components for the VeriFact API,
including error handling, logging, request/response processing, rate limiting, and security.
"""

import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.cache import Cache
from src.utils.exceptions import (
    APIAuthenticationError,
    APIError,
    PipelineError,
    RequestTimeoutError,
    ResourceUnavailableError,
    TooManyRequestsError,
    ValidationError,
    VerifactError,
)
from src.utils.logging.structured_logger import (
    clear_component_context,
    clear_request_context,
    set_component_context,
    set_request_context,
)

logger = logging.getLogger("verifact.api")

# Rate limiting settings
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour in seconds

# API Key settings
API_KEY_SALT = os.getenv("API_KEY_SALT", "verifact_salt")
API_KEY_ENABLED = os.getenv("API_KEY_ENABLED", "true").lower() == "true"
API_KEY_PATTERN = re.compile(r"^vf_[a-zA-Z0-9]{32}$")  # Format: vf_<32 alphanumeric chars>
API_KEY_EXEMPT_PATHS = [
    "/api/docs", 
    "/api/redoc", 
    "/api/openapi.json",
    "/api/v1/health"
]

# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'",
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache"
}

# Define the API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set up logging context for each request."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.logger = logging.getLogger("verifact.api.middleware")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and set logging context."""
        start_time = time.time()
        
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Get correlation ID if provided
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Get session ID if provided
        session_id = request.headers.get("X-Session-ID")
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.id
        
        # Set request context for structured logging
        set_request_context(
            request_id=request_id, 
            user_id=user_id,
            correlation_id=correlation_id,
            session_id=session_id
        )
        
        # Set component context
        set_component_context(component="api", operation=f"{request.method}:{request.url.path}")
        
        # Log the request
        self.logger.info(
            f"Request started: {request.method} {request.url.path}", 
            extra={
                "http_method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
                "client_port": request.client.port if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
                "content_type": request.headers.get("Content-Type"),
                "content_length": request.headers.get("Content-Length"),
            }
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Set request ID in response header
            response.headers["X-Request-ID"] = request_id
            
            # Add processing time header
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            # Log the response
            self.logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": int(process_time * 1000),
                    "response_type": response.headers.get("Content-Type"),
                    "response_length": response.headers.get("Content-Length"),
                }
            )
            
            return response
        except Exception as exc:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log the exception
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "duration_ms": int(process_time * 1000),
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                }
            )
            
            # Re-raise the exception to be handled by the error handlers
            raise
        finally:
            # Clear request context
            clear_request_context()
            clear_component_context()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")
        
        # Process timing
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(f"Response {request_id}: {response.status_code} (took {process_time:.4f}s)")
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            logger.exception(f"Error {request_id}: {str(e)} (took {process_time:.4f}s)")
            
            # Let the exception propagate to be handled by the ErrorHandlerMiddleware
            raise


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling exceptions and returning standardized error responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and handle any exceptions."""
        try:
            return await call_next(request)
        except VerifactError as e:
            # Handle our custom exceptions - status code and format are already defined
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict()
            )
        except Exception as e:
            # Handle unexpected exceptions
            error_id = str(uuid.uuid4())
            logger.exception(f"Unhandled exception {error_id}: {str(e)}")
            
            # Return a generic error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {
                            "error_id": error_id
                        }
                    }
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add security headers to the response."""
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
            
        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.api_key_cache = Cache(max_size=1000, ttl_seconds=3600)  # Cache API key validation for 1 hour
    
    def _is_valid_key_format(self, api_key: str) -> bool:
        """Check if the API key format is valid."""
        # Use a more strict format: prefix.base64urlsafe
        try:
            prefix, rest = api_key.split(".", 1)
            return len(prefix) == 8 and len(rest) > 0
        except ValueError:
            return False
    
    async def _validate_and_get_key_data(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return its metadata.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Optional[Dict[str, Any]]: Metadata for the API key, or None if invalid
        """
        if not self._is_valid_key_format(api_key):
            return None
        
        # Check cache first for performance
        cache_key = f"api_key_data:{api_key}"
        cached_data = self.api_key_cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            # Import here to avoid circular imports
            from src.utils.db.api_keys import validate_api_key

            # Validate the key using our database utility
            key_data = await validate_api_key(api_key)
            
            # If the key is invalid, return None
            if not key_data:
                return None
                
            # Cache the key data
            self.api_key_cache.set(cache_key, key_data)
            
            return key_data
        except Exception as e:
            logger.warning(f"API key validation failed: {str(e)}")
            return None
    
    def _is_path_exempt(self, path: str) -> bool:
        """Check if the path is exempt from API key authentication."""
        return any(path.startswith(exempt_path) for exempt_path in API_KEY_EXEMPT_PATHS)
    
    def _has_required_scope(self, key_data: Dict[str, Any], path: str, method: str) -> bool:
        """
        Check if the API key has the required scope for this endpoint.
        
        Args:
            key_data: Metadata for the API key
            path: Request path
            method: HTTP method
            
        Returns:
            bool: True if the key has the required scope, False otherwise
        """
        # Skip scope check for exempt paths
        if self._is_path_exempt(path):
            return True
            
        # Get scopes for this API key
        scopes = key_data.get("scopes", [])
        
        # Admin scope has access to everything
        if "admin" in scopes:
            return True
            
        # Check for read-only operations
        if method in ("GET", "HEAD", "OPTIONS"):
            return any(scope in scopes for scope in ["read:only", "write"])
            
        # For write operations, need write scope
        return "write" in scopes
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and check for valid API key."""
        # Skip API key check if disabled or path is exempt
        if not API_KEY_ENABLED or self._is_path_exempt(request.url.path):
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        # Check if API key is present
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "API_KEY_MISSING",
                        "message": "API key is required",
                        "details": {
                            "header": "X-API-Key"
                        }
                    }
                }
            )
        
        # Check if API key format is valid
        if not self._is_valid_key_format(api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "INVALID_API_KEY_FORMAT",
                        "message": "API key format is invalid",
                        "details": {
                            "format": "prefix.rest"
                        }
                    }
                }
            )
        
        # Validate API key and get metadata
        key_data = await self._validate_and_get_key_data(api_key)
        if not key_data:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "API key is invalid, revoked, or expired"
                    }
                }
            )
        
        # Check if the key has the required scope for this endpoint
        if not self._has_required_scope(key_data, request.url.path, request.method):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "code": "INSUFFICIENT_SCOPE",
                        "message": "API key does not have sufficient permissions for this operation"
                    }
                }
            )
        
        # Store API key data in request state for later use
        request.state.api_key = api_key
        request.state.api_key_data = key_data
        
        # Process the request
        return await call_next(request)


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for global rate limiting across all requests."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # Import here to avoid circular imports
        from src.utils.rate_limiter import rate_limiter
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and apply rate limiting."""
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)
            
        # Get client IP (use X-Forwarded-For if behind a proxy)
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Get API key and key data if present
        api_key = request.headers.get("X-API-Key")
        api_key_data = getattr(request.state, "api_key_data", None)
        
        # Create identifier
        identifier = api_key or client_ip
        
        # Check rate limit
        result = await self.rate_limiter.check(identifier, api_key_data)
        
        # If rate limited, return error response
        if not result.allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded: {result.limit} requests per hour",
                        "details": {
                            "limit": result.limit,
                            "window": "3600 seconds",
                            "retry_after": result.retry_after
                        }
                    }
                },
                headers={"Retry-After": str(result.retry_after)}
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset)
        
        return response


async def verify_api_key(
    api_key: str = Depends(API_KEY_HEADER),
    required_scopes: Optional[List[ApiKeyScope]] = None
) -> str:
    """
    Verify the API key and check required scopes.
    
    Args:
        api_key: The API key from the header
        required_scopes: Optional list of required scopes
        
    Returns:
        The owner_id associated with the API key
        
    Raises:
        HTTPException: If the API key is invalid or lacks required permissions
    """
    # Validate API key format
    try:
        prefix, rest = api_key.split(".", 1)
        if len(prefix) != 8:
            raise ValueError("Invalid key format")
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid API key format")
    
    # Import here to avoid circular imports
    from src.utils.db.api_keys import validate_api_key

    # Get the API key from database
    key_data = await validate_api_key(api_key)
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check if key has expired
    if key_data.get("expires_at") and datetime.fromisoformat(key_data["expires_at"]) < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key has expired")
    
    # Check scopes if required
    if required_scopes:
        key_scopes = key_data.get("scopes", [])
        has_scope = any(scope.value in key_scopes for scope in required_scopes)
        if not has_scope:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Return the owner ID for potential further operations
    return key_data["owner_id"]


def setup_middleware(app: FastAPI) -> None:
    """
    Set up all middleware for the FastAPI application.
    
    Args:
        app: The FastAPI application
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development - restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add API key authentication middleware
    app.add_middleware(APIKeyAuthMiddleware)
    
    # Add global rate limiting middleware
    app.add_middleware(GlobalRateLimitMiddleware)
    
    # Add error handling middleware
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register exception handlers for specific exception types.
    
    Args:
        app: The FastAPI application
    """
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle validation errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(PipelineError)
    async def pipeline_exception_handler(request: Request, exc: PipelineError):
        """Handle pipeline processing errors."""
        # Log detailed info about pipeline errors
        logger.error(f"Pipeline error in stage {exc.details.get('pipeline_stage')}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(APIError)
    async def api_exception_handler(request: Request, exc: APIError):
        """Handle API-specific errors."""
        logger.error(f"API error: {exc.message}")
        response = JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
        return response
    
    @app.exception_handler(RequestTimeoutError)
    async def timeout_exception_handler(request: Request, exc: RequestTimeoutError):
        """Handle timeout errors."""
        logger.error(f"Request timeout: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(TooManyRequestsError)
    async def rate_limit_exception_handler(request: Request, exc: TooManyRequestsError):
        """Handle rate limit errors."""
        retry_after = exc.details.get("retry_after")
        response = JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        return response
    
    @app.exception_handler(APIAuthenticationError)
    async def api_auth_exception_handler(request: Request, exc: APIAuthenticationError):
        """Handle API authentication errors."""
        logger.warning(f"API authentication error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
            headers={"WWW-Authenticate": "APIKey"}
        )
    
    @app.exception_handler(ResourceUnavailableError)
    async def resource_exception_handler(request: Request, exc: ResourceUnavailableError):
        """Handle resource unavailable errors."""
        # Add Retry-After header for rate limit errors
        response = JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
        if exc.code == "RATE_LIMIT_ERROR" and exc.details.get("retry_after"):
            response.headers["Retry-After"] = str(exc.details["retry_after"])
        return response 