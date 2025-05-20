"""VeriFact Batch Factchecking API.

This module provides API endpoints for batch factchecking of multiple claims.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any

import requests
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    Request,
    Security,
    status,
)
from fastapi.security.api_key import APIKey, APIKeyHeader

from src.models.factcheck import (
    BatchClaimStatus,
    BatchFactcheckRequest,
    BatchProcessingProgress,
    Claim,
    FactcheckJob,
    JobStatus,
    Verdict,
)
from src.pipeline import PipelineConfig
from src.utils.async_processor import AsyncClaimProcessor, ProcessingProgress
from src.utils.cache import Cache
from src.utils.db import SupabaseClient
from src.utils.exceptions import (
    PipelineError,
    ValidationError,
)
from src.utils.metrics import track_api_call
from src.utils.retry import with_async_retry
from src.utils.validation import (
    validate_model,
)


# Define CancelledError class for job cancellation
class CancelledError(Exception):
    """Exception raised when a batch factcheck job is cancelled by the user."""
    pass

# Setup logging
logger = logging.getLogger(__name__)

# In-memory store for batch job results
_batch_jobs: dict[str, FactcheckJob] = {}

# Setup rate limiting
batch_rate_limit_cache = Cache(max_size=1000, ttl_seconds=3600)

# API Key security (reusing from factcheck.py)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Create database clien
db_client = SupabaseClient()

# Initialize router
router = APIRouter(
    prefix="/batch",
    tags=["Batch Factchecking"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        429: {"description": "Too many requests"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)


async def get_api_key(
    api_key_header: str = Security(api_key_header),
) -> APIKey:
    """Validate API key for protected endpoints.

    Args:
        api_key_header: API key from request header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid
    """
    # In production, these would be stored securely in a database
    # For now, using environment variables
    import os

    valid_api_keys = os.getenv("VERIFACT_API_KEYS", "test-api-key").split(",")

    if api_key_header in valid_api_keys:
        return api_key_header

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
        headers={"WWW-Authenticate": "APIKey"},
    )


def check_rate_limit(api_key: str, limit: int = 5, window: int = 60):
    """Check if the request exceeds rate limits.

    Args:
        api_key: API key from authenticated reques
        limit: Maximum number of requests in time window
        window: Time window in seconds

    Raises:
        HTTPException: If rate limit is exceeded
    """
    current_time = int(time.time())
    window_start = current_time - window

    # Get request history for this API key
    key = f"batch_rate_limit:{api_key}"
    requests_history = batch_rate_limit_cache.get(key, [])

    # Filter out old requests
    recent_requests = [timestamp for timestamp in requests_history if timestamp > window_start]

    # Check if limit exceeded
    if len(recent_requests) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} batch requests per {window} seconds",
        )

    # Add current request timestamp and update cache
    recent_requests.append(current_time)
    batch_rate_limit_cache.set(key, recent_requests)


async def create_pipeline_config(options: dict[str, Any]) -> PipelineConfig:
    """Create a pipeline configuration from options.

    Args:
        options: Configuration options

    Returns:
        PipelineConfig instance
    """
    try:
        # Add configuration options from the reques
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
        # Re-raise with more contex
        raise ValidationError(
            message=f"Invalid pipeline configuration: {e.message}", details=e.details
        ) from e


async def process_single_claim(claim_text: str, options: dict[str, Any]) -> Verdict:
    """Process a single claim through the factchecking pipeline.

    Args:
        claim_text: The claim text to process
        options: Processing options

    Returns:
        Verdict for the claim
    """
    try:
        # Create pipeline configuration
        config = await create_pipeline_config(options)

        # Create pipeline with default agents
        from src.pipeline.factcheck_pipeline import create_default_pipeline

        pipeline = create_default_pipeline(config=config)

        # Process the claim
        # For a single claim, we wrap it in some context to help the claim detector
        wrapper_text = f"The following is a factual claim to verify: {claim_text}"

        # Process through pipeline
        verdicts = await pipeline.process_text(wrapper_text)

        if not verdicts:
            raise PipelineError("No verdict generated for the claim")

        # Return the first (and likely only) verdic
        return verdicts[0]
    except Exception as e:
        logger.error(f"Error processing claim: {str(e)}", exc_info=True)
        raise


def convert_to_batch_claim_status(
    claim_id: str, claim_text: str, status: JobStatus
) -> BatchClaimStatus:
    """Convert claim information to a BatchClaimStatus object.

    Args:
        claim_id: ID of the claim
        claim_text: Text of the claim
        status: Current status

    Returns:
        BatchClaimStatus objec
    """
    return BatchClaimStatus(claim_id=claim_id, status=status, claim_text=claim_text)


def log_job_progress(job_id: str, progress: ProcessingProgress) -> None:
    """Log job progress information.

    Args:
        job_id: ID of the job
        progress: Progress information
    """
    logger.info(
        f"Batch job {job_id} progress: "
        f"{progress.processed_items}/{progress.total_items} processed, "
        f"{progress.pending_items} pending, "
        f"{progress.failed_items} failed, "
        f"success rate: {progress.success_rate:.2f}"
    )


def send_webhook_notification(url: str, data: dict[str, Any]) -> bool:
    """Send webhook notification to the specified URL.

    Args:
        url: URL to send notification to
        data: Data to send in notification

    Returns:
        bool: Whether notification was sent successfully
    """
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.status_code >= 200 and response.status_code < 300
    except Exception:
        logger.exception(f"Failed to send webhook notification to {url}")
        return False


@router.post(
    "/factcheck",
    response_model=dict[str, Any],
    summary="Process multiple claims in a batch",
    description="""
    Start an asynchronous batch processing job for multiple claims.

    This endpoint accepts a list of claims and processes them concurrently
    based on priority and available resources. The response includes a job ID
    that can be used to check the status and retrieve results when complete.

    Options can be used to control concurrency, timeouts, and other aspects
    of the batch processing.
    """,
)
async def batch_factcheck(
    request: BatchFactcheckRequest,
    background_tasks: BackgroundTasks,
    api_request: Request,
    api_key: APIKey = None,
):
    """Start a batch factchecking job for multiple claims.

    Args:
        request: The batch factchecking reques
        background_tasks: FastAPI background tasks manager
        api_request: FastAPI request objec
        api_key: Validated API key

    Returns:
        Dict with job ID for status checking
    """
    # Get API key if not provided
    if api_key is None:
        api_key = await get_api_key()

    # Check rate limits
    check_rate_limit(api_key)

    # Track API call
    track_api_call("batch_factcheck", api_key)

    try:
        # Validate inpu
        if not request.claims:
            raise ValidationError(message="No claims provided")

        # Generate a unique job ID
        job_id = f"batch_{int(time.time())}_{hash(str(request.claims)) % 10000}"
        request_id = getattr(api_request.state, "request_id", str(uuid.uuid4()))

        # Get processing options
        max_concurrent = request.options.get("max_concurrent", 3)
        detect_related = request.options.get("detect_related_claims", True)
        webhook_url = request.options.get("webhook_url")

        # Create job record
        job = FactcheckJob(
            job_id=job_id,
            status=JobStatus.QUEUED,
            metadata={
                "total_claims": len(request.claims),
                "webhook_url": webhook_url,
            },
        )

        # Store job in memory
        _batch_jobs[job_id] = job

        # Start factchecking in background
        background_tasks.add_task(
            _run_batch_factcheck_job,
            job_id,
            request,
            request_id,
            api_key,
            max_concurrent,
            detect_related,
            webhook_url,
        )

        return {
            "job_id": job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "message": f"Batch factchecking job started with {len(request.claims)} claims",
            "request_id": request_id,
        }
    except ValidationError as e:
        logger.warning(f"Validation error in batch request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error in batch request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get(
    "/factcheck/job/{job_id}",
    response_model=dict[str, Any],
    summary="Get status of a batch factchecking job",
    description="""
    Check the status of a batch factchecking job and retrieve results if available.

    This endpoint returns detailed information about the job, including:
    - Overall job status
    - Progress information (claims processed, pending, failed)
    - Status of individual claims in the batch
    - Results for completed claims
    - Estimated time remaining
    """,
)
async def get_batch_job_status(
    job_id: str,
    include_verdicts: bool = Query(
        True, description="Whether to include full verdicts in the response"
    ),
    api_key: APIKey = None,
):
    """Get the status of a batch factchecking job.

    Args:
        job_id: The job ID to check
        include_verdicts: Whether to include full verdicts in response
        api_key: Validated API key

    Returns:
        Dict with job status and results if available
    """
    # Get API key if not provided
    if api_key is None:
        api_key = await get_api_key()

    # Track API call
    track_api_call("get_batch_job_status", api_key)

    if job_id not in _batch_jobs:
        # Try to find in database
        try:
            job_data = db_client.get_factcheck_by_id(job_id)
            if job_data:
                return job_data
        except Exception as e:
            logger.error(f"Error retrieving job from database: {str(e)}")

        # If not found, raise error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch job not found: {job_id}"
        )

    job_data = _batch_jobs[job_id].dict()

    # Convert datetime objects to ISO strings
    if isinstance(job_data.get("created_at"), datetime):
        job_data["created_at"] = job_data["created_at"].isoformat()
    if isinstance(job_data.get("updated_at"), datetime):
        job_data["updated_at"] = job_data["updated_at"].isoformat()
    if isinstance(job_data.get("completed_at"), datetime):
        job_data["completed_at"] = job_data["completed_at"].isoformat()

    # If no verdicts requested, filter them out to reduce response size
    if not include_verdicts and "results" in job_data and job_data["results"]:
        for claim in job_data["results"]:
            if "verdict" in claim:
                # Keep only basic verdict information
                verdict = claim["verdict"]
                claim["verdict"] = {
                    "verdict": verdict.get("verdict"),
                    "confidence": verdict.get("confidence"),
                }

    return job_data


@router.post(
    "/factcheck/job/{job_id}/cancel",
    response_model=dict[str, Any],
    summary="Cancel a batch factchecking job",
    description="Cancel a running batch factchecking job.",
)
async def cancel_batch_job(job_id: str, api_key: APIKey = None):
    """Cancel a batch factchecking job.

    Args:
        job_id: The job ID to cancel
        api_key: Validated API key

    Returns:
        Dict with cancellation resul
    """
    # Get API key if not provided
    if api_key is None:
        api_key = await get_api_key()

    # Track API call
    track_api_call("cancel_batch_job", api_key)

    if job_id not in _batch_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch job not found: {job_id}"
        )

    job = _batch_jobs[job_id]

    # Only cancel if still in progress
    if job.status not in (JobStatus.QUEUED, JobStatus.PROCESSING):
        return {
            "job_id": job_id,
            "status": job.status,
            "message": f"Job is already in {job.status} state, cannot cancel",
            "success": False,
        }

    # Mark job as cancelled
    job.status = JobStatus.CANCELLED
    job.updated_at = datetime.utcnow()
    _batch_jobs[job_id] = job

    return {
        "job_id": job_id,
        "status": job.status,
        "message": "Job cancelled successfully",
        "success": True,
    }


@with_async_retry(max_attempts=3, initial_delay=1.0)
async def _run_batch_factcheck_job(
    job_id: str,
    request: BatchFactcheckRequest,
    request_id: str,
    api_key: str,
    max_concurrent: int = 3,
    detect_related_claims: bool = True,
    webhook_url: str | None = None,
):
    """Run a batch factchecking job in the background.

    Args:
        job_id: Unique job identifier
        request: The batch factchecking reques
        request_id: Original request ID
        api_key: API key for tracking
        max_concurrent: Maximum concurrent claims to process
        detect_related_claims: Whether to detect and merge related claims
        webhook_url: Optional URL to send job completion notification
    """
    try:
        # Get job from store
        if job_id not in _batch_jobs:
            logger.error(f"Job {job_id} not found")
            return

        job = _batch_jobs[job_id]

        # Update job status to processing
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.utcnow()
        _batch_jobs[job_id] = job

        # Prepare the claims for processing
        claims = []
        claim_statuses = {}

        # Extract claim texts from reques
        for i, claim_data in enumerate(request.claims):
            # Generate a unique ID for this claim
            # If the claim already has an ID, use it, otherwise generate one
            if isinstance(claim_data, dict):
                claim_id = claim_data.get("id", f"{job_id}_claim_{i}")
                claim_text = claim_data.get("text", "")
            else:
                claim_id = f"{job_id}_claim_{i}"
                claim_text = claim_data

            # Create a Claim object and add to processing lis
            claim = Claim(id=claim_id, text=claim_text)
            claims.append(claim)

            # Initialize status for this claim
            claim_statuses[claim_id] = convert_to_batch_claim_status(
                claim_id, claim_text, JobStatus.QUEUED
            )

        # Update job with initial claim statuses
        job.claims = list(claim_statuses.values())
        _batch_jobs[job_id] = job

        # Initialize results collector
        results = {}
        options = request.options or {}

        # For each processed claim_id, track the corresponding verdic
        async def process_claim(claim: Claim) -> Verdict:
            return await process_single_claim(claim.text, options)

        # Progress callback to update job status
        def progress_callback(progress: ProcessingProgress) -> None:
            # Log progress
            log_job_progress(job_id, progress)

            # Get the job from store
            if job_id in _batch_jobs:
                batch_job = _batch_jobs[job_id]

                # Check if job was cancelled
                if batch_job.status == JobStatus.CANCELLED:
                    raise CancelledError("Job was cancelled")

                # Update progress information
                batch_progress = BatchProcessingProgress(
                    total_claims=progress.total_items,
                    processed_claims=progress.processed_items,
                    pending_claims=progress.pending_items,
                    failed_claims=progress.failed_items,
                    success_rate=progress.success_rate,
                    estimated_time_remaining=progress.estimated_time_remaining,
                    average_processing_time=progress.average_processing_time,
                )

                batch_job.progress = batch_progress

                # If webhook URL specified and progress reaches certain thresholds,
                # send progress notification
                if webhook_url and progress.progress_percent % 20 == 0:
                    notification_data = {
                        "job_id": job_id,
                        "status": "in_progress",
                        "progress": progress.progress_percent,
                        "processed_claims": progress.processed_items,
                        "total_claims": progress.total_items,
                    }
                    send_webhook_notification(webhook_url, notification_data)

                # Update job in store
                _batch_jobs[job_id] = batch_job

        # Setup claim processor to handle concurrency and status tracking
        processor = AsyncClaimProcessor(
            claims=claims,
            process_func=process_claim,
            progress_callback=progress_callback,
            max_concurrent=max_concurrent,
        )

        # Process all claims
        await processor.process_all()

        # Get all processing results
        for _i, (claim_id, result) in enumerate(processor.results.items()):
            if result.success:
                # Store the verdic
                results[claim_id] = {
                    "verdict": result.result.dict()
                    if hasattr(result.result, "dict")
                    else result.result,
                    "processing_time": result.processing_time,
                }
                # Update claim status
                claim_statuses[claim_id].status = JobStatus.COMPLETED
            else:
                # Store error information
                results[claim_id] = {
                    "error": str(result.error),
                    "processing_time": result.processing_time,
                }
                # Update claim status
                claim_statuses[claim_id].status = JobStatus.FAILED

        # Update job with final status
        if job_id in _batch_jobs:
            job = _batch_jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.claims = list(claim_statuses.values())
            job.results = results
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            _batch_jobs[job_id] = job

            # Send final webhook notification if URL specified
            if webhook_url:
                notification_data = {
                    "job_id": job_id,
                    "status": "completed",
                    "total_claims": len(claims),
                    "processed_claims": len(results),
                    "success_count": sum(1 for r in results.values() if "verdict" in r),
                    "failure_count": sum(1 for r in results.values() if "error" in r),
                }
                send_webhook_notification(webhook_url, notification_data)

    except Exception as e:
        logger.error(f"Error in batch job {job_id}: {str(e)}", exc_info=True)

        # Store error state
        if job_id in _batch_jobs:
            job = _batch_jobs[job_id]
            job.status = JobStatus.FAILED
            job.error = {"message": str(e), "type": e.__class__.__name__}
            job.updated_at = datetime.utcnow()
            _batch_jobs[job_id] = job

            # Send error webhook notification if URL specified
            if webhook_url:
                notification_data = {
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e),
                }
                send_webhook_notification(webhook_url, notification_data)
