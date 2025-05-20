"""
VeriFact Batch Factchecking API

This module provides API endpoints for batch factchecking of multiple claims.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

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
    BatchFactcheckResponse,
    BatchProcessingProgress,
    Claim,
    FactcheckJob,
    JobStatus,
    Verdict,
)
from src.pipeline import FactcheckPipeline, PipelineConfig
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

# Setup logging
logger = logging.getLogger(__name__)

# In-memory store for batch job results
_batch_jobs: Dict[str, FactcheckJob] = {}

# Setup rate limiting
batch_rate_limit_cache = Cache(max_size=1000, ttl_seconds=3600)

# API Key security (reusing from factcheck.py)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Create database client
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
    key = f"batch_rate_limit:{api_key}"
    requests_history = batch_rate_limit_cache.get(key, [])
    
    # Filter out old requests
    recent_requests = [timestamp for timestamp in requests_history if timestamp > window_start]
    
    # Check if limit exceeded
    if len(recent_requests) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} batch requests per {window} seconds"
        )
    
    # Add current request timestamp and update cache
    recent_requests.append(current_time)
    batch_rate_limit_cache.set(key, recent_requests)

async def create_pipeline_config(options: Dict[str, Any]) -> PipelineConfig:
    """
    Create a pipeline configuration from options.
    
    Args:
        options: Configuration options
        
    Returns:
        PipelineConfig instance
    """
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

async def process_single_claim(claim_text: str, options: Dict[str, Any]) -> Verdict:
    """
    Process a single claim through the factchecking pipeline.
    
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
            
        # Return the first (and likely only) verdict
        return verdicts[0]
    except Exception as e:
        logger.error(f"Error processing claim: {str(e)}", exc_info=True)
        raise

def convert_to_batch_claim_status(claim_id: str, claim_text: str, status: JobStatus) -> BatchClaimStatus:
    """
    Convert claim information to a BatchClaimStatus object.
    
    Args:
        claim_id: ID of the claim
        claim_text: Text of the claim
        status: Current status
        
    Returns:
        BatchClaimStatus object
    """
    return BatchClaimStatus(
        claim_id=claim_id,
        status=status,
        claim_text=claim_text
    )

def log_job_progress(job_id: str, progress: ProcessingProgress) -> None:
    """
    Log job progress information.
    
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

def send_webhook_notification(url: str, data: Dict[str, Any]) -> bool:
    """
    Send webhook notification to the specified URL.
    
    Args:
        url: URL to send notification to
        data: Data to send
        
    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VeriFact-Batch-Processor/1.0"
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.ok:
            logger.info(f"Webhook notification sent successfully to {url}")
            return True
        else:
            logger.warning(f"Webhook notification failed: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending webhook notification: {str(e)}")
        return False

@router.post(
    "/factcheck",
    response_model=Dict[str, Any],
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
    api_key: APIKey = Security(get_api_key)
):
    """
    Process multiple claims in a batch.
    
    Args:
        request: Batch factchecking request with claims and options
        background_tasks: FastAPI background tasks
        api_request: FastAPI request object
        api_key: Validated API key
        
    Returns:
        Job information including job ID
    """
    # Check rate limits
    check_rate_limit(api_key)
    
    # Track API call
    track_api_call("batch_factcheck", api_key)
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    request_id = getattr(api_request.state, 'request_id', str(uuid.uuid4()))
    
    # Extract options
    options = request.options or {}
    max_concurrent = options.get("max_concurrent", 3)
    detect_related = options.get("detect_related_claims", True)
    webhook_notification = options.get("webhook_notification", False)
    
    # Initialize job status tracker
    claim_statuses = {}
    for i, claim in enumerate(request.claims):
        # Generate claim ID if not provided
        claim_id = claim.id or f"{job_id}-claim-{i+1}"
        
        # Create status entry
        claim_statuses[claim_id] = convert_to_batch_claim_status(
            claim_id=claim_id,
            claim_text=claim.text,
            status=JobStatus.QUEUED
        )
    
    # Create job object
    job = FactcheckJob(
        job_id=job_id,
        status=JobStatus.QUEUED,
        is_batch=True,
        progress=BatchProcessingProgress(
            total_claims=len(request.claims),
            processed_claims=0,
            pending_claims=len(request.claims),
            failed_claims=0,
            success_rate=1.0
        ),
        claim_statuses=claim_statuses
    )
    
    # Store job
    _batch_jobs[job_id] = job
    
    # Start processing in background
    background_tasks.add_task(
        _run_batch_factcheck_job,
        job_id=job_id,
        request=request,
        request_id=request_id,
        api_key=api_key,
        max_concurrent=max_concurrent,
        detect_related_claims=detect_related,
        webhook_url=request.callback_url if webhook_notification else None
    )
    
    # Return job information
    return {
        "job_id": job_id,
        "status": job.status,
        "total_claims": len(request.claims),
        "created_at": job.created_at.isoformat(),
        "message": "Batch factchecking job started"
    }

@router.get(
    "/factcheck/job/{job_id}",
    response_model=Dict[str, Any],
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
    include_verdicts: bool = Query(True, description="Whether to include full verdicts in the response"),
    api_key: APIKey = Security(get_api_key)
):
    """
    Get status and results of a batch factchecking job.
    
    Args:
        job_id: ID of the batch job
        include_verdicts: Whether to include verdict details in the response
        api_key: Validated API key
        
    Returns:
        Job status and results if available
    """
    # Check if job exists
    if job_id not in _batch_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job with ID {job_id} not found"
        )
    
    # Get job
    job = _batch_jobs[job_id]
    
    # Prepare response
    response = {
        "job_id": job.job_id,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "is_batch": job.is_batch,
    }
    
    # Add progress information
    if job.progress:
        response["progress"] = job.progress.dict()
    
    # Add claim statuses
    if job.claim_statuses:
        if include_verdicts:
            response["claim_statuses"] = {
                claim_id: status.dict() 
                for claim_id, status in job.claim_statuses.items()
            }
        else:
            # Exclude verdict details to reduce response size
            response["claim_statuses"] = {
                claim_id: {
                    k: v for k, v in status.dict().items() 
                    if k != "verdict"
                } 
                for claim_id, status in job.claim_statuses.items()
            }
    
    # Add result if job is completed
    if job.status in [JobStatus.COMPLETED, JobStatus.PARTIALLY_COMPLETED] and job.result:
        if include_verdicts:
            response["result"] = job.result.dict()
        else:
            # Just include summary information
            response["result_summary"] = {
                "total_claims": job.result.total_claims,
                "successful_claims": job.result.successful_claims,
                "processing_time": job.result.processing_time,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
    
    # Add error if job failed
    if job.status == JobStatus.FAILED and job.error:
        response["error"] = job.error
    
    return response

@router.post(
    "/factcheck/job/{job_id}/cancel",
    response_model=Dict[str, Any],
    summary="Cancel a batch factchecking job",
    description="Cancel a running batch factchecking job.",
)
async def cancel_batch_job(
    job_id: str,
    api_key: APIKey = Security(get_api_key)
):
    """
    Cancel a batch factchecking job.
    
    Args:
        job_id: ID of the job to cancel
        api_key: Validated API key
        
    Returns:
        Status of the cancelation request
    """
    # Check if job exists
    if job_id not in _batch_jobs:
        from fastapi import status as status_codes
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail=f"Batch job with ID {job_id} not found"
        )
    
    # Get job
    job = _batch_jobs[job_id]
    
    # Check if job can be canceled
    if job.status not in [JobStatus.QUEUED, JobStatus.PROCESSING]:
        return {
            "job_id": job_id,
            "status": job.status,
            "message": f"Cannot cancel job with status {job.status}"
        }
    
    # Update job status
    job.status = JobStatus.CANCELED
    job.updated_at = datetime.now()
    job.completed_at = datetime.now()
    
    # Update claim statuses for queued claims
    if job.claim_statuses:
        for claim_id, status in job.claim_statuses.items():
            if status.status == JobStatus.QUEUED:
                status.status = JobStatus.CANCELED
    
    # Store updated job
    _batch_jobs[job_id] = job
    
    return {
        "job_id": job_id,
        "status": job.status,
        "message": "Job canceled successfully"
    }

@with_async_retry(max_attempts=3, initial_delay=1.0)
async def _run_batch_factcheck_job(
    job_id: str,
    request: BatchFactcheckRequest,
    request_id: str,
    api_key: str,
    max_concurrent: int = 3,
    detect_related_claims: bool = True,
    webhook_url: Optional[str] = None
):
    """
    Run a batch factchecking job.
    
    Args:
        job_id: ID of the job
        request: Batch factchecking request
        request_id: Request ID for tracking
        api_key: API key for authentication
        max_concurrent: Maximum number of concurrent claim processing tasks
        detect_related_claims: Whether to detect related claims
        webhook_url: URL to send notification when processing completes
    """
    try:
        # Start timer
        start_time = time.time()
        
        # Get job
        job = _batch_jobs[job_id]
        
        # Update job status
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.now()
        _batch_jobs[job_id] = job
        
        logger.info(f"Starting batch factchecking job {job_id} with {len(request.claims)} claims")
        
        # Prepare list of claims with metadata
        claims_to_process = []
        claim_map = {}  # Map claim IDs to position in the list
        
        for i, batch_claim in enumerate(request.claims):
            # Generate claim ID if not provided
            claim_id = batch_claim.id or f"{job_id}-claim-{i+1}"
            
            # Create claim object
            claim_obj = Claim(
                text=batch_claim.text,
                context=batch_claim.context or "",
                checkworthy=True,  # Assume all batch claims are check-worthy
                domain=batch_claim.domain,
                entities=[],  # Will be populated during processing
            )
            
            # Add to list
            claims_to_process.append(claim_obj)
            
            # Update map
            claim_map[i] = claim_id
            
            # Update status to show position in queue
            if job.claim_statuses and claim_id in job.claim_statuses:
                job.claim_statuses[claim_id].position = i + 1
        
        # Extract options
        options = request.options or {}
        
        # Define processing function
        async def process_claim(claim: Claim) -> Verdict:
            return await process_single_claim(claim.text, options)
        
        # Define progress callback
        def progress_callback(progress: ProcessingProgress) -> None:
            # Log progress
            log_job_progress(job_id, progress)
            
            # Update job progress
            if job.progress:
                job.progress.processed_claims = progress.processed_items
                job.progress.pending_claims = progress.pending_items
                job.progress.failed_claims = progress.failed_items
                job.progress.success_rate = progress.success_rate
                job.progress.estimated_time_remaining = progress.estimated_time_remaining
                job.progress.avg_processing_time = progress.avg_processing_time
                job.progress.last_update_time = datetime.now()
                
                if not job.progress.start_time and progress.start_time:
                    job.progress.start_time = datetime.fromtimestamp(progress.start_time)
            
            # Update job in store
            _batch_jobs[job_id] = job
        
        # Create async processor
        processor = AsyncClaimProcessor(
            process_func=process_claim,
            max_concurrency=max_concurrent,
            timeout_seconds=options.get("timeout_per_claim", 120),
            retry_attempts=1,
            min_check_worthiness=options.get("min_check_worthiness", 0.5),
            max_batch_size=max_concurrent,
            allow_duplicate_claims=False
        )
        
        # Process claims
        results = await processor.process_items(
            items=claims_to_process,
            progress_callback=progress_callback,
            wait_for_completion=True
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Process results
        verdicts = {}
        failed_claims = {}
        
        for i, result in enumerate(results):
            # Get claim ID
            claim_id = claim_map[i]
            
            # Update claim status
            if job.claim_statuses and claim_id in job.claim_statuses:
                status = job.claim_statuses[claim_id]
                
                if result.success:
                    # Successful processing
                    status.status = JobStatus.COMPLETED
                    status.verdict = result.result
                    status.processing_time = result.processing_time
                    status.completed_at = datetime.now()
                    
                    # Add to verdicts
                    verdicts[claim_id] = result.result
                else:
                    # Failed processing
                    status.status = JobStatus.FAILED
                    status.error = result.error
                    status.completed_at = datetime.now()
                    
                    # Add to failed claims
                    failed_claims[claim_id] = {
                        "error": result.error,
                        "claim_text": status.claim_text
                    }
        
        # Detect related claims if requested
        related_claims = None
        if detect_related_claims and len(verdicts) > 1:
            processor.set_result_relationships()
            
            # Convert relationship data to a map of claim IDs
            related_claims = {}
            
            for claim_id in verdicts.keys():
                claim_obj = claims_to_process[list(claim_map.keys())[list(claim_map.values()).index(claim_id)]]
                related = processor.get_related_claims(claim_obj)
                
                if related:
                    related_ids = []
                    for _, related_item, _ in related:
                        # Find the claim ID for this item
                        for idx, item in enumerate(claims_to_process):
                            if item == related_item:
                                related_ids.append(claim_map[idx])
                                break
                    
                    if related_ids:
                        related_claims[claim_id] = related_ids
                        
                        # Also update claim statuses
                        if job.claim_statuses and claim_id in job.claim_statuses:
                            job.claim_statuses[claim_id].related_claims = related_ids
        
        # Create batch response
        response = BatchFactcheckResponse(
            verdicts=verdicts,
            failed_claims=failed_claims,
            metadata={
                "processing_time": f"{processing_time:.1f}s",
                "request_id": request_id,
                "job_id": job_id,
                "max_concurrent": max_concurrent,
                "detect_related_claims": detect_related_claims
            },
            request_id=request_id,
            total_claims=len(request.claims),
            successful_claims=len(verdicts),
            processing_time=processing_time,
            related_claims=related_claims
        )
        
        # Update job status
        if len(failed_claims) == 0:
            job.status = JobStatus.COMPLETED
        elif len(verdicts) > 0:
            job.status = JobStatus.PARTIALLY_COMPLETED
        else:
            job.status = JobStatus.FAILED
            job.error = {"message": "All claims failed processing"}
        
        job.result = response
        job.updated_at = datetime.now()
        job.completed_at = datetime.now()
        
        # Update job in store
        _batch_jobs[job_id] = job
        
        logger.info(
            f"Completed batch factchecking job {job_id}: "
            f"{len(verdicts)}/{len(request.claims)} successful, "
            f"{len(failed_claims)} failed, "
            f"processing time: {processing_time:.1f}s"
        )
        
        # Send webhook notification if requested
        if webhook_url:
            notification_data = {
                "job_id": job_id,
                "status": job.status,
                "total_claims": len(request.claims),
                "successful_claims": len(verdicts),
                "failed_claims": len(failed_claims),
                "processing_time": processing_time,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            
            send_webhook_notification(webhook_url, notification_data)
    
    except Exception as e:
        # Update job status on error
        if job_id in _batch_jobs:
            job = _batch_jobs[job_id]
            job.status = JobStatus.FAILED
            job.error = {
                "message": f"Batch processing failed: {str(e)}",
                "error_type": type(e).__name__
            }
            job.updated_at = datetime.now()
            job.completed_at = datetime.now()
            _batch_jobs[job_id] = job
        
        logger.error(f"Error in batch processing job {job_id}: {str(e)}", exc_info=True)
        
        # Send webhook notification if requested
        if webhook_url:
            notification_data = {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "completed_at": datetime.now().isoformat()
            }
            
            send_webhook_notification(webhook_url, notification_data) 