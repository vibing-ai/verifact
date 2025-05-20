"""Chainlit event handlers for the VeriFact UI.

This module contains the event handlers for Chainlit events such as
on_chat_start, on_message, etc.
"""

import os
import uuid

import chainlit as cl

from src.agents.claim_detector import ClaimDetector
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.verdict_writer import VerdictWriter
from src.utils.db import SupabaseClient

# Initialize database client
db_client = SupabaseClient()


# Configuration for authentication
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Handle password-based authentication.
    This is a simple implementation for demonstration.
    In production, you should use secure password storage and verification.
    """
    # Get predefined credentials from environment variables or use defaults for demo
    valid_credentials = {
        os.environ.get("VERIFACT_ADMIN_USER", "admin"): os.environ.get(
            "VERIFACT_ADMIN_PASSWORD", "admin"
        ),
        os.environ.get("VERIFACT_DEMO_USER", "demo"): os.environ.get(
            "VERIFACT_DEMO_PASSWORD", "demo"
        ),
    }

    if username in valid_credentials and password == valid_credentials[username]:
        return cl.User(identifier=username, metadata={"role": "user", "provider": "credentials"})
    return None


@cl.on_chat_start
async def on_chat_start():
    """Initialize the VeriFact system when a new chat session starts."""
    # Get the authenticated user
    user = cl.user_session.get("user")

    # Initialize the agents
    claim_detector = ClaimDetector()
    evidence_hunter = EvidenceHunter()
    verdict_writer = VerdictWriter()

    # Store the agents in the user session
    cl.user_session.set("claim_detector", claim_detector)
    cl.user_session.set("evidence_hunter", evidence_hunter)
    cl.user_session.set("verdict_writer", verdict_writer)

    # Store empty history in the user session
    cl.user_session.set("factcheck_history", [])

    # Generate a session ID for anonymous feedback
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)

    # Create settings to let users configure aspects of the factchecking
    await cl.ChatSettings(
        [
            cl.Switch(id="detailed_evidence", label="Show detailed evidence", initial=True),
            cl.Switch(id="show_confidence_scores", label="Show confidence scores", initial=True),
            cl.Switch(id="show_feedback_form", label="Show feedback form", initial=True),
            cl.Switch(id="detect_related_claims", label="Detect related claims", initial=True),
            cl.Switch(
                id="concurrent_processing", label="Process claims concurrently", initial=True
            ),
            cl.Slider(
                id="max_claims", label="Maximum claims to process", initial=5, min=1, max=10, step=1
            ),
            cl.Slider(
                id="max_concurrent",
                label="Maximum concurrent tasks",
                initial=3,
                min=1,
                max=5,
                step=1,
            ),
        ]
    ).send()

    # Send welcome message
    await cl.Message(
        content=f"Welcome to VeriFact, {user.identifier}! I can help you fact-check claims. Simply enter a statement or piece of text containing claims you want to verify.",
        author="VeriFact",
    ).send()


@cl.on_chat_resume
async def on_chat_resume():
    """Handle restoration of a previous chat session."""
    # Get the user information
    user = cl.user_session.get("user")

    # Reset the agents to ensure we have fresh instances
    claim_detector = ClaimDetector()
    evidence_hunter = EvidenceHunter()
    verdict_writer = VerdictWriter()

    # Store the agents in the user session
    cl.user_session.set("claim_detector", claim_detector)
    cl.user_session.set("evidence_hunter", evidence_hunter)
    cl.user_session.set("verdict_writer", verdict_writer)

    # Retrieve the session ID, or generate a new one
    session_id = cl.user_session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        cl.user_session.set("session_id", session_id)

    # Send welcome back message
    await cl.Message(
        content=f"Welcome back to VeriFact, {user.identifier}! Your previous chat session has been restored.",
        author="VeriFact",
    ).send()


@cl.on_element_change
async def on_element_change(element, input_value):
    """Handle changes to UI elements like sliders and switches."""
    settings = cl.user_session.get("settings")
    if settings:
        settings[element.id] = input_value
        cl.user_session.set("settings", settings)
