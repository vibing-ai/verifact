"""
Utility functions for the VeriFact UI.

This module contains utility functions used by the Chainlit UI components.
"""

import datetime
import json
import os
import uuid
from typing import Any, Dict, List

import chainlit as cl

from src.models.feedback import Feedback, FeedbackStats


async def export_results_to_json(results: List[Dict[str, Any]]) -> str:
    """
    Export fact-check results to a JSON string.

    Args:
        results: List of fact-check results

    Returns:
        JSON string of the results
    """
    # Create a serializable version of the results
    serializable_results = []

    for result in results:
        # Create a copy without non-serializable objects
        serializable_result = {
            "claim": result["claim"],
            "evidence": result.get("evidence", []),
            "verdict": result.get("verdict", {}),
            "timestamp": result.get("timestamp"),
        }

        # Remove any non-serializable objects from evidence
        for evidence in serializable_result["evidence"]:
            for key in list(evidence.keys()):
                if isinstance(evidence[key], (datetime.datetime, datetime.date)):
                    evidence[key] = evidence[key].isoformat()
                elif not isinstance(evidence[key], (str, int, float, bool, list, dict, type(None))):
                    evidence[key] = str(evidence[key])

        serializable_results.append(serializable_result)

    # Convert to JSON
    results_json = json.dumps(serializable_results, indent=2)
    return results_json


async def save_feedback(fact_check_id: str, feedback_data: Dict[str, Any]) -> None:
    """
    Save user feedback to the database.

    Args:
        fact_check_id: ID of the fact-check
        feedback_data: Feedback data to save
    """
    # Get the database client
    from src.utils.db import SupabaseClient

    db_client = SupabaseClient()

    # Get the user session ID
    session_id = cl.user_session.get("session_id", str(uuid.uuid4()))

    # Get the authenticated user if available
    user = cl.user_session.get("user")
    user_id = getattr(user, "identifier", None) if user else None

    # Create the feedback object
    feedback = Feedback(
        id=str(uuid.uuid4()),
        fact_check_id=fact_check_id,
        session_id=session_id,
        user_id=user_id,
        accuracy_rating=feedback_data.get("accuracy", "neutral"),
        helpfulness_rating=feedback_data.get("helpfulness", "neutral"),
        comments=feedback_data.get("comments", ""),
        timestamp=datetime.datetime.now().isoformat(),
    )

    # Save to database
    if db_client.is_connected():
        try:
            await db_client.save_feedback(feedback)
            return True
        except Exception as e:
            cl.logger.error(f"Error saving feedback: {str(e)}")
            return False
    else:
        # Save to local file if database is not connected
        feedback_file = os.path.join(os.getcwd(), "data", "feedback.json")
        os.makedirs(os.path.dirname(feedback_file), exist_ok=True)

        # Read existing feedback
        existing_feedback = []
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, "r") as f:
                    existing_feedback = json.load(f)
            except Exception:
                existing_feedback = []

        # Add new feedback
        existing_feedback.append(feedback.dict())

        # Write back to file
        with open(feedback_file, "w") as f:
            json.dump(existing_feedback, f, indent=2)

        return True


async def get_feedback_stats() -> FeedbackStats:
    """
    Get statistics about collected feedback.

    Returns:
        FeedbackStats object with feedback statistics
    """
    # Get the database client
    from src.utils.db import SupabaseClient

    db_client = SupabaseClient()

    # Try to get stats from database
    if db_client.is_connected():
        try:
            return await db_client.get_feedback_stats()
        except Exception as e:
            cl.logger.error(f"Error getting feedback stats: {str(e)}")

    # Fall back to local file if database is not connected
    feedback_file = os.path.join(os.getcwd(), "data", "feedback.json")
    if not os.path.exists(feedback_file):
        return FeedbackStats(
            total_feedback=0, accuracy_ratings={}, helpfulness_ratings={}, recent_feedback=[]
        )

    # Read feedback from file
    with open(feedback_file, "r") as f:
        feedback_list = json.load(f)

    # Compile statistics
    total_feedback = len(feedback_list)
    accuracy_ratings = {}
    helpfulness_ratings = {}

    for feedback in feedback_list:
        # Count accuracy ratings
        accuracy = feedback.get("accuracy_rating", "neutral")
        accuracy_ratings[accuracy] = accuracy_ratings.get(accuracy, 0) + 1

        # Count helpfulness ratings
        helpfulness = feedback.get("helpfulness_rating", "neutral")
        helpfulness_ratings[helpfulness] = helpfulness_ratings.get(helpfulness, 0) + 1

    # Get recent feedback (last 10)
    recent_feedback = feedback_list[-10:] if feedback_list else []

    # Create stats object
    stats = FeedbackStats(
        total_feedback=total_feedback,
        accuracy_ratings=accuracy_ratings,
        helpfulness_ratings=helpfulness_ratings,
        recent_feedback=recent_feedback,
    )

    return stats
