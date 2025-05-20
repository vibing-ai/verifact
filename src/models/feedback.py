"""Pydantic models for the VeriFact user feedback system.

This module contains the data models used for collecting and managing user feedback
on factchecking results.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, constr, root_validator


class FeedbackType(str, Enum):
    """Types of feedback that can be provided."""

    ACCURACY = "accuracy"
    HELPFULNESS = "helpfulness"
    GENERAL = "general"


class Rating(int, Enum):
    """Rating scale from 1 to 5."""

    VERY_POOR = 1
    POOR = 2
    AVERAGE = 3
    GOOD = 4
    EXCELLENT = 5


class Feedback(BaseModel):
    """User feedback on a factcheck result."""

    feedback_id: str | None = Field(None, description="Unique identifier for the feedback")
    claim_id: str = Field(..., description="ID of the factcheck claim this feedback relates to")
    user_id: str | None = Field(None, description="ID of the authenticated user providing feedback")
    session_id: str | None = Field(None, description="Session ID for anonymous users")
    accuracy_rating: Rating | None = Field(None, description="Rating for factcheck accuracy (1-5)")
    helpfulness_rating: Rating | None = Field(
        None, description="Rating for factcheck helpfulness (1-5)"
    )
    comment: constr(max_length=1000) | None = Field(None, description="Optional user comment")
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the feedback was submitted"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (browser, device, etc.)"
    )

    @root_validator(skip_on_failure=True)
    def check_identifiers(cls, values):
        """Validate that either user_id or session_id is provided."""
        user_id = values.get("user_id")
        session_id = values.get("session_id")

        if not user_id and not session_id:
            raise ValueError("Either user_id or session_id must be provided")

        return values

    @root_validator(skip_on_failure=True)
    def check_ratings(cls, values):
        """Validate that at least one rating is provided."""
        accuracy_rating = values.get("accuracy_rating")
        helpfulness_rating = values.get("helpfulness_rating")
        comment = values.get("comment")

        if not accuracy_rating and not helpfulness_rating and not comment:
            raise ValueError("At least one rating or comment must be provided")

        return values


class FeedbackRequest(BaseModel):
    """API request model for submitting feedback."""

    claim_id: str = Field(..., description="ID of the factcheck claim")
    accuracy_rating: int | None = Field(
        None, ge=1, le=5, description="Rating for factcheck accuracy (1-5)"
    )
    helpfulness_rating: int | None = Field(
        None, ge=1, le=5, description="Rating for factcheck helpfulness (1-5)"
    )
    comment: constr(max_length=1000) | None = Field(None, description="Optional user comment")

    @root_validator(skip_on_failure=True)
    def check_at_least_one_field(cls, values):
        """Validate that at least one feedback field is provided."""
        if not any(
            values.get(field) for field in ["accuracy_rating", "helpfulness_rating", "comment"]
        ):
            raise ValueError("At least one feedback field (rating or comment) must be provided")
        return values


class FeedbackResponse(BaseModel):
    """API response model for feedback submission."""

    success: bool = Field(..., description="Whether the feedback was successfully stored")
    feedback_id: str | None = Field(None, description="ID of the stored feedback")
    message: str = Field(..., description="Status message")


class FeedbackStats(BaseModel):
    """Statistics about feedback for a claim or overall."""

    total_feedback: int = Field(..., description="Total number of feedback submissions")
    average_accuracy: float | None = Field(None, description="Average accuracy rating")
    average_helpfulness: float | None = Field(None, description="Average helpfulness rating")
    feedback_count_by_rating: dict[str, dict[int, int]] = Field(
        default_factory=dict, description="Count of feedback by rating type and value"
    )
    recent_comments: list[dict[str, Any]] | None = Field(
        None, description="Recent comments (limited to 5)"
    )
