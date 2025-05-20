"""
VeriFact Factchecking API

This module provides the API endpoints for the factchecking service.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException, status, Security, Query
from fastapi.security.api_key import APIKeyHeader, APIKey
from datetime import datetime
import time
import asyncio
import uuid
import logging
from typing import Dict, Any, List, Optional, Union

from src.models.factcheck import (
    FactcheckRequest,
    FactcheckResponse,
    Verdict,
    Claim,
    Evidence,
    PipelineConfig,
    FactcheckJob,
    JobStatus
)
from src.agents.claim_detector import ClaimDetector
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.verdict_writer import VerdictWriter
from src.pipeline import FactcheckPipeline
from src.utils.exceptions import (
    VerifactError, ValidationError, ModelError, 
    PipelineError, InputTooLongError
)
from src.utils.validation import (
    validate_text_length, sanitize_text, validate_model,
    convert_verdict_for_response
)
from src.utils.retry import with_async_retry
from src.utils.db import SupabaseClient
from src.utils.cache import Cache
from src.utils.metrics import track_api_call, track_performance
from src.utils.security.credentials import get_credential

# Setup logging
logger = logging.getLogger(__name__)

# In-memory store for job results (would be a database in production)
_job_results: Dict[str, Dict[str, Any]] = {}

# Setup rate limiting
rate_limit_cache = Cache(max_size=1000, ttl_seconds=3600)

# API Key security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Create database client
db_client = SupabaseClient()

# Initialize router
router = APIRouter(
    tags=["Factchecking"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        429: {"description": "Too many requests"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)

async def get_api_key(
    api_key_header: str = Security(api_key_header),
) -> APIKey:
    """
    Validate API key for protected endpoints.
    
    Args:
        api_key_header: API key from request header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    # Get valid API keys from secure credential manager
    valid_api_keys = get_credential("VERIFACT_API_KEYS", "test-api-key").split(",")
    
    if api_key_header in valid_api_keys:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
        headers={"WWW-Authenticate": "APIKey"},
    )

def check_rate_limit(api_key: str, limit: int = 10, window: int = 60):
    """
    Check if the request exceeds rate limits.
    
    Args:
        api_key: API key from authenticated request
        limit: Maximum number of requests in time window
        window: Time window in seconds
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    current_time = int(time.time())
    window_start = current_time - window
    
    # Get request history for this API key
    key = f"rate_limit:{api_key}"
    requests_history = rate_limit_cache.get(key, [])
    
    # Filter out old requests
    recent_requests = [timestamp for timestamp in requests_history if timestamp > window_start]
    
    # Check if limit exceeded
    if len(recent_requests) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} requests per {window} seconds"
        )
    
    # Add current request timestamp and update cache
    recent_requests.append(current_time)
    rate_limit_cache.set(key, recent_requests)

async def get_pipeline_config(request: FactcheckRequest) -> PipelineConfig:
    """
    Create a pipeline configuration from request options.
    
    Args:
        request: Factchecking request
        
    Returns:
        PipelineConfig instance
    """
    # Extract options from request
    options = request.options or {}
    
    try:
        # Add configuration options from the request
        config_dict = {
            # Default PipelineConfig fields
            "claim_detection_threshold": options.get("min_check_worthiness", 0.5),
            "max_claims": options.get("max_claims", 10),
            "max_evidence_per_claim": options.get("max_evidence_per_claim", 5),
            "relevance_threshold": options.get("relevance_threshold", 0.7),
            "allowed_domains": options.get("domains", None),
            "blocked_domains": options.get("blocked_domains", []),
            "claim_categories": options.get("claim_categories", None),
            "min_credibility_score": options.get("min_credibility_score", None),
            
            # Additional fields for pipeline
            "include_evidence": options.get("include_evidence", True),
            "explanation_detail": options.get("explanation_detail", "standard"),
        }
        
        # Validate options against PipelineConfig model
        return validate_model(config_dict, PipelineConfig)
    except ValidationError as e:
        # Re-raise with more context
        raise ValidationError(
            message=f"Invalid pipeline configuration: {e.message}",
            details=e.details
        )

@router.post(
    "/factcheck", 
    response_model=FactcheckResponse,
    summary="Factcheck claims in text",
    description="""
    Process a piece of text, extract claims, gather evidence, and generate verdicts.
    
    This endpoint accepts text input containing potential factual claims and
    returns an assessment of the truthfulness of those claims with supporting evidence
    and explanations.
    
    The factchecking process includes:
    1. Claim detection and extraction
    2. Evidence gathering from trusted sources
    3. Verdict generation based on the evidence
    
    Request options can be used to customize the factchecking process, such as
    setting minimum check-worthiness thresholds or limiting the domains of interest.
    """,
    response_description="Factchecking results with verdicts for identified claims"
)
async def factcheck(
    request: FactcheckRequest, 
    api_request: Request,
    api_key: APIKey = Security(get_api_key)
):
    """
    Factcheck claims in the provided text.
    
    Args:
        request: The factchecking request containing text and options
        api_request: FastAPI request object
        api_key: Validated API key
        
    Returns:
        A FactcheckResponse with verdicts for identified claims
        
    Raises:
        ValidationError: If input validation fails
        PipelineError: If processing fails
    """
    # Check rate limits
    check_rate_limit(api_key)
    
    # Track API call
    track_api_call("factcheck", api_key)
    
    # Start tracking performance
    with track_performance("factcheck_api") as perf:
        start_time = time.time()
        request_id = getattr(api_request.state, 'request_id', str(uuid.uuid4()))
        
        try:
            # Sanitize and validate input text
            text = sanitize_text(request.text)
            validate_text_length(text)
            
            # Get pipeline configuration
            config = await get_pipeline_config(request)
            
            # Create pipeline
            pipeline = FactcheckPipeline(config=config)
            
            # Process the text through the pipeline
            verdicts = await pipeline.process_text(text)
            
            # Convert verdicts to standard format
            processed_verdicts = [convert_verdict_for_response(v.dict() if hasattr(v, 'dict') else v) for v in verdicts]
            
            # Build response
            processing_time = time.time() - start_time
            response = FactcheckResponse(
                claims=processed_verdicts,
                request_id=request_id,
                metadata={
                    "processing_time": f"{processing_time:.1f}s",
                    "processing_time_seconds": processing_time,
                    "claims_detected": pipeline.stats["claims_detected"],
                    "evidence_gathered": pipeline.stats["evidence_gathered"],
                    "verdicts_generated": pipeline.stats["verdicts_generated"],
                    "original_text": text[:200] + "..." if len(text) > 200 else text,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Store result in database for future reference
            try:
                factcheck_data = {
                    "request_id": request_id,
                    "text": text,
                    "verdicts": [v.dict() if hasattr(v, 'dict') else v for v in verdicts],
                    "metadata": response.metadata,
                    "created_at": datetime.now().isoformat()
                }
                db_client.store_factcheck_result(factcheck_data)
            except Exception as db_error:
                # Log error but don't fail the request
                logger.error(f"Failed to store factcheck result: {str(db_error)}")
            
            return response
        except InputTooLongError as e:
            # Re-raise input validation errors
            perf.add_error("input_too_long")
            logger.warning(f"Input too long: {str(e)}")
            raise e
        except ValidationError as e:
            # Re-raise validation errors
            perf.add_error("validation_error")
            logger.warning(f"Validation error: {str(e)}")
            raise e
        except ModelError as e:
            # Handle model errors
            perf.add_error("model_error")
            logger.error(f"Model error during factchecking: {str(e)}")
            raise PipelineError(
                message=f"Model error during factchecking: {str(e)}",
                stage=getattr(e, "stage", "unknown")
            ) from e
        except Exception as e:
            # Convert other exceptions to PipelineError
            perf.add_error("pipeline_error")
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            if not isinstance(e, VerifactError):
                raise PipelineError(
                    message=f"Factchecking pipeline failed: {str(e)}",
                    stage="factcheck_processing"
                ) from e
            raise


@router.post(
    "/factcheck/async",
    response_model=Dict[str, Any],
    summary="Asynchronously factcheck claims in text",
    description="""
    Start an asynchronous factchecking process. This endpoint returns immediately with a job ID
    that can be used to check the status of the factchecking process and retrieve results when complete.
    
    This is useful for factchecking large documents or when the client doesn't want to keep a connection open.
    """,
)
async def factcheck_async(
    request: FactcheckRequest, 
    background_tasks: BackgroundTasks, 
    api_request: Request,
    api_key: APIKey = Security(get_api_key)
):
    """
    Start an asynchronous factchecking job.
    
    Args:
        request: The factchecking request containing text and options
        background_tasks: FastAPI background tasks manager
        api_request: FastAPI request object
        api_key: Validated API key
        
    Returns:
        Dict with job_id for status checking
        
    Raises:
        ValidationError: If input validation fails
    """
    # Check rate limits
    check_rate_limit(api_key)
    
    # Track API call
    track_api_call("factcheck_async", api_key)
    
    try:
        # Sanitize and validate input text
        text = sanitize_text(request.text)
        validate_text_length(text)
        
        # Generate a unique job ID
        job_id = f"job_{int(time.time())}_{hash(text) % 10000}"
        request_id = getattr(api_request.state, 'request_id', str(uuid.uuid4()))
        
        # Create job record
        job = FactcheckJob(
            job_id=job_id,
            status=JobStatus.QUEUED
        )
        
        # Store job in memory (would be in a database in production)
        _job_results[job_id] = job.dict()
        
        # Start factchecking in background
        background_tasks.add_task(_run_factcheck_job, job_id, request, request_id, api_key)
        
        return {
            "job_id": job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "message": "Factchecking job started",
            "request_id": request_id
        }
    except ValidationError as e:
        # Re-raise validation errors
        logger.warning(f"Validation error in async request: {str(e)}")
        raise e
    except Exception as e:
        # Convert other exceptions to ValidationError
        logger.error(f"Error in async request: {str(e)}", exc_info=True)
        if not isinstance(e, VerifactError):
            raise ValidationError(
                message=f"Failed to start factchecking job: {str(e)}"
            ) from e
        raise


@router.get(
    "/factcheck/job/{job_id}",
    response_model=Dict[str, Any],
    summary="Get status of an asynchronous factchecking job",
    description="""
    Check the status of an asynchronous factchecking job and retrieve results if available.
    """,
)
async def get_job_status(
    job_id: str,
    api_key: APIKey = Security(get_api_key)
):
    """
    Get the status of a factchecking job.
    
    Args:
        job_id: The job ID to check
        api_key: Validated API key
        
    Returns:
        Job status and results if complete
        
    Raises:
        HTTPException: If job not found
    """
    # Track API call
    track_api_call("get_job_status", api_key)
    
    if job_id not in _job_results:
        # Try to find in database
        try:
            job_data = db_client.get_factcheck_by_id(job_id)
            if job_data:
                return job_data
        except Exception as e:
            logger.error(f"Error retrieving job from database: {str(e)}")
        
        # If not found, raise error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    job_data = _job_results[job_id]
    
    # Convert datetime objects to ISO strings for JSON response
    if isinstance(job_data.get("created_at"), datetime):
        job_data["created_at"] = job_data["created_at"].isoformat()
    if isinstance(job_data.get("updated_at"), datetime):
        job_data["updated_at"] = job_data["updated_at"].isoformat()
    if isinstance(job_data.get("completed_at"), datetime):
        job_data["completed_at"] = job_data["completed_at"].isoformat()
    
    return job_data


@router.get(
    "/factchecks",
    summary="Get recent factchecks",
    description="Retrieve a list of recent factchecks with pagination and filtering options.",
    response_model=Dict[str, Any]
)
async def get_factchecks(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    domain: Optional[str] = None,
    verdict_type: Optional[str] = None,
    api_key: APIKey = Security(get_api_key)
):
    """
    Get recent factchecks with pagination and filtering.
    
    Args:
        limit: Maximum number of results to return
        offset: Number of results to skip for pagination
        domain: Filter by domain/category
        verdict_type: Filter by verdict type
        api_key: Validated API key
        
    Returns:
        List of factchecks with metadata
    """
    # Check rate limits
    check_rate_limit(api_key)
    
    # Track API call
    track_api_call("get_factchecks", api_key)
    
    try:
        results = db_client.get_recent_factchecks(
            limit=limit,
            offset=offset,
            domain=domain,
            verdict_type=verdict_type
        )
        return results
    except Exception as e:
        logger.error(f"Error retrieving factchecks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve factchecks: {str(e)}"
        )


@router.get(
    "/factchecks/{factcheck_id}",
    summary="Get factcheck by ID",
    description="Retrieve a specific factcheck by its ID.",
    response_model=Dict[str, Any]
)
async def get_factcheck(
    factcheck_id: str,
    api_key: APIKey = Security(get_api_key)
):
    """
    Get a specific factcheck by ID.
    
    Args:
        factcheck_id: The ID of the factcheck to retrieve
        api_key: Validated API key
        
    Returns:
        Factcheck details
        
    Raises:
        HTTPException: If factcheck not found
    """
    # Check rate limits
    check_rate_limit(api_key)
    
    # Track API call
    track_api_call("get_factcheck", api_key)
    
    try:
        result = db_client.get_factcheck_by_id(factcheck_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Factcheck not found: {factcheck_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving factcheck: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve factcheck: {str(e)}"
        )


@with_async_retry(max_attempts=3, initial_delay=1.0)
async def _run_factcheck_job(job_id: str, request: FactcheckRequest, request_id: str, api_key: str):
    """
    Run a factchecking job in the background.
    
    Args:
        job_id: Unique job identifier
        request: The factchecking request
        request_id: Original request ID
        api_key: API key for tracking
    """
    with track_performance(f"async_factcheck_job_{job_id}") as perf:
        try:
            # Update job status to processing
            job = FactcheckJob(
                job_id=job_id,
                status=JobStatus.PROCESSING,
                created_at=_job_results[job_id]["created_at"] if isinstance(_job_results[job_id]["created_at"], datetime) else 
                        datetime.fromisoformat(_job_results[job_id]["created_at"]) 
            )
            _job_results[job_id] = job.dict()
            
            # Get pipeline configuration
            config = await get_pipeline_config(request)
            
            # Create pipeline
            pipeline = FactcheckPipeline(config=config)
            
            # Process the text through the pipeline
            start_time = time.time()
            text = sanitize_text(request.text)
            verdicts = await pipeline.process_text(text)
            processing_time = time.time() - start_time
            
            # Convert verdicts to standard format
            processed_verdicts = [convert_verdict_for_response(v.dict() if hasattr(v, 'dict') else v) for v in verdicts]
            
            # Build response
            response = FactcheckResponse(
                claims=processed_verdicts,
                request_id=request_id,
                metadata={
                    "processing_time": f"{processing_time:.1f}s",
                    "processing_time_seconds": processing_time,
                    "claims_detected": pipeline.stats["claims_detected"],
                    "evidence_gathered": pipeline.stats["evidence_gathered"],
                    "verdicts_generated": pipeline.stats["verdicts_generated"],
                    "original_text": text[:200] + "..." if len(text) > 200 else text,
                    "timestamp": datetime.now().isoformat(),
                    "job_id": job_id
                }
            )
            
            # Store result in database
            try:
                factcheck_data = {
                    "request_id": request_id,
                    "job_id": job_id,
                    "text": text,
                    "verdicts": [v.dict() if hasattr(v, 'dict') else v for v in verdicts],
                    "metadata": response.metadata,
                    "created_at": datetime.now().isoformat(),
                    "api_key": api_key
                }
                db_client.store_factcheck_result(factcheck_data)
            except Exception as db_error:
                logger.error(f"Failed to store factcheck result: {str(db_error)}")
            
            # Update job with results
            job = FactcheckJob(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                created_at=_job_results[job_id]["created_at"] if isinstance(_job_results[job_id]["created_at"], datetime) else 
                        datetime.fromisoformat(_job_results[job_id]["created_at"]),
                result=response
            )
            _job_results[job_id] = job.dict()
            
        except Exception as e:
            perf.add_error(str(e))
            # Store error state
            error_details = {
                "message": str(e),
                "type": e.__class__.__name__
            }
            
            if isinstance(e, VerifactError):
                error_details = e.to_dict()["error"]
            
            logger.error(f"Error in async factcheck job {job_id}: {str(e)}", exc_info=True)
            
            job = FactcheckJob(
                job_id=job_id,
                status=JobStatus.FAILED,
                created_at=_job_results[job_id]["created_at"] if isinstance(_job_results[job_id]["created_at"], datetime) else 
                        datetime.fromisoformat(_job_results[job_id]["created_at"]),
                error=error_details
            )
            _job_results[job_id] = job.dict() 