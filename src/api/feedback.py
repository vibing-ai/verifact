"""VeriFact Feedback API

This module provides API endpoints for handling user feedback on factchecking results.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Security, status
from fastapi.security.api_key import APIKey, APIKeyHeader

from src.models.feedback import (
    Feedback,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackStats,
)
from src.utils.cache import Cache
from src.utils.db import SupabaseClient
from src.utils.exceptions import QueryError, ValidationError
from src.utils.security.credentials import get_credential

# Setup logging
logger = logging.getLogger(__name__)

# Setup rate limiting for feedback submissions
feedback_rate_limit_cache = Cache(max_size=1000, ttl_seconds=3600)

# API Key security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Create database client
db_client = SupabaseClient()

# Initialize router
router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        429: {"description": "Too many requests"},
        500: {"description": "Internal server error"},
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
    # Get valid API keys from secure credential manager
    valid_api_keys = get_credential("VERIFACT_API_KEYS", "test-api-key").split(",")

    if api_key_header in valid_api_keys:
        return api_key_header

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
        headers={"WWW-Authenticate": "APIKey"},
    )


def check_feedback_rate_limit(request: Request, limit: int = 5, window: int = 3600):
    """Check if the request exceeds rate limits for feedback submission.

    Args:
        request: FastAPI request object
        limit: Maximum number of feedback submissions allowed in time window
        window: Time window in seconds (default: 1 hour)

    Raises:
        HTTPException: If rate limit is exceeded
    """
    client_ip = request.client.host
    current_time = int(time.time())
    window_start = current_time - window

    # Get request history for this IP address
    key = f"feedback_rate_limit:{client_ip}"
    requests_history = feedback_rate_limit_cache.get(key, [])

    # Filter out old requests
    recent_requests = [timestamp for timestamp in requests_history if timestamp > window_start]

    # Check if limit exceeded
    if len(recent_requests) >= limit:
        logger.warning(
            f"Rate limit exceeded for IP {client_ip}: {len(recent_requests)} feedback submissions in the last hour"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} feedback submissions per hour",
        )

    # Add current request timestamp and update cache
    recent_requests.append(current_time)
    feedback_rate_limit_cache.set(key, recent_requests)


@router.post(
    "",
    response_model=FeedbackResponse,
    summary="Submit feedback on a factcheck",
    description="""
    Submit user feedback for a specific factcheck.
    
    This endpoint allows users to provide ratings and comments on factchecking results.
    It includes rate limiting to prevent abuse (5 submissions per hour per IP address).
    
    Feedback can include:
    - Accuracy rating (1-5 scale)
    - Helpfulness rating (1-5 scale)
    - Optional text comment
    
    At least one of these fields must be provided.
    """,
)
async def submit_feedback(
    feedback_request: FeedbackRequest, request: Request, api_key: APIKey | None = None
):
    """Handle submission of user feedback."""
    # Check rate limit (only for non-API submissions)
    if not api_key:
        check_feedback_rate_limit(request)

    try:
        # Extract client info for metadata
        metadata = {
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "timestamp": datetime.now().isoformat(),
        }

        # Create feedback object
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            claim_id=feedback_request.claim_id,
            user_id=None,  # Anonymous by default
            session_id=request.cookies.get("session_id", str(uuid.uuid4())),
            accuracy_rating=feedback_request.accuracy_rating,
            helpfulness_rating=feedback_request.helpfulness_rating,
            comment=feedback_request.comment,
            created_at=datetime.now(),
            metadata=metadata,
        )

        # If user is authenticated (via Chainlit), add user_id
        user_info = request.session.get("user") if hasattr(request, "session") else None
        if user_info:
            feedback.user_id = user_info.get("identifier")

        # Store feedback in database
        result = db_client.store_feedback(feedback)

        # Return success response
        return FeedbackResponse(
            success=True,
            feedback_id=result.get("feedback_id"),
            message="Thank you for your feedback!",
        )

    except ValidationError as e:
        logger.error(f"Validation error in feedback submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid feedback data: {str(e)}"
        )
    except QueryError as e:
        logger.error(f"Database error in feedback submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store feedback. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in feedback submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred"
        )


@router.get(
    "/stats",
    response_model=FeedbackStats,
    summary="Get feedback statistics",
    description="""
    Get aggregated statistics for feedback across all factchecks.
    
    This endpoint provides summary statistics including:
    - Total number of feedback submissions
    - Average ratings for accuracy and helpfulness
    - Distribution of ratings
    - Recent comments
    """,
)
async def get_feedback_stats(api_key: APIKey = Security(get_api_key)):
    """Get aggregated feedback statistics."""
    try:
        # Get statistics from database
        stats = db_client.get_feedback_statistics()

        # Convert to FeedbackStats model
        feedback_stats = FeedbackStats(
            total_feedback=stats.get("total_feedback", 0),
            average_accuracy=stats.get("average_accuracy"),
            average_helpfulness=stats.get("average_helpfulness"),
            feedback_count_by_rating=stats.get("feedback_count_by_rating", {}),
            recent_comments=stats.get("recent_comments", []),
        )

        return feedback_stats

    except Exception as e:
        logger.error(f"Error getting feedback statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback statistics",
        )


@router.get(
    "/{claim_id}",
    response_model=list[dict[str, Any]],
    summary="Get feedback for a specific claim",
    description="""
    Get all feedback for a specific factcheck claim.
    
    This endpoint retrieves all feedback submissions for a given claim ID,
    with pagination support.
    """,
)
async def get_claim_feedback(
    claim_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: APIKey = Security(get_api_key),
):
    """Get feedback for a specific claim."""
    try:
        # Get feedback from database
        feedback_list = db_client.get_feedback_for_claim(claim_id, limit, offset)
        return feedback_list

    except Exception as e:
        logger.error(f"Error getting feedback for claim {claim_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback for claim {claim_id}",
        )


@router.get(
    "/stats/{claim_id}",
    response_model=FeedbackStats,
    summary="Get feedback statistics for a specific claim",
    description="""
    Get aggregated statistics for feedback on a specific factcheck claim.
    
    This endpoint provides claim-specific summary statistics including:
    - Total number of feedback submissions for this claim
    - Average ratings for accuracy and helpfulness
    - Distribution of ratings
    - Recent comments
    """,
)
async def get_claim_feedback_stats(claim_id: str, api_key: APIKey = Security(get_api_key)):
    """Get aggregated feedback statistics for a specific claim."""
    try:
        # Get statistics from database
        stats = db_client.get_feedback_statistics(claim_id)

        # Convert to FeedbackStats model
        feedback_stats = FeedbackStats(
            total_feedback=stats.get("total_feedback", 0),
            average_accuracy=stats.get("average_accuracy"),
            average_helpfulness=stats.get("average_helpfulness"),
            feedback_count_by_rating=stats.get("feedback_count_by_rating", {}),
            recent_comments=stats.get("recent_comments", []),
        )

        return feedback_stats

    except Exception as e:
        logger.error(f"Error getting feedback statistics for claim {claim_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback statistics for claim {claim_id}",
        )
