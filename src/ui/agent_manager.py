"""
Agent initialization and management for the VeriFact UI.

This module contains functions for initializing, configuring, and managing
the VeriFact agents within the Chainlit UI.
"""

import asyncio
import datetime
from typing import Any, Dict, List

import chainlit as cl

from src.agents.claim_detector import ClaimDetector
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.verdict_writer import VerdictWriter
from src.ui.components import create_evidence_display, create_verdict_display


async def initialize_agents():
    """
    Initialize all VeriFact agents and store them in the user session.

    Returns:
        Tuple of (claim_detector, evidence_hunter, verdict_writer)
    """
    # Initialize the agents
    claim_detector = ClaimDetector()
    evidence_hunter = EvidenceHunter()
    verdict_writer = VerdictWriter()

    # Store the agents in the user session
    cl.user_session.set("claim_detector", claim_detector)
    cl.user_session.set("evidence_hunter", evidence_hunter)
    cl.user_session.set("verdict_writer", verdict_writer)

    return claim_detector, evidence_hunter, verdict_writer


async def process_claims(
    claims: List[Any],
    main_msg: cl.Message,
    show_detailed_evidence: bool = True,
    show_confidence: bool = True,
    show_feedback_form: bool = True,
    detect_related_claims: bool = True,
    concurrent_processing: bool = True,
    max_concurrent: int = 3,
):
    """
    Process a list of claims through the VeriFact pipeline.

    Args:
        claims: List of claims to process
        main_msg: The main message to update with status
        show_detailed_evidence: Whether to show detailed evidence
        show_confidence: Whether to show confidence scores
        show_feedback_form: Whether to show feedback form
        detect_related_claims: Whether to detect related claims
        concurrent_processing: Whether to process claims concurrently
        max_concurrent: Maximum number of concurrent claims to process
    """
    # Get the agents from the user session
    evidence_hunter = cl.user_session.get("evidence_hunter")
    verdict_writer = cl.user_session.get("verdict_writer")

    # Get the session history
    factcheck_history = cl.user_session.get("factcheck_history", [])

    # Record start time for performance tracking
    start_time = datetime.datetime.now()

    # Keep track of progress
    total_claims = len(claims)
    completed_claims = 0
    results = []

    # Function to update progress display
    async def update_progress():
        percent = int(completed_claims / total_claims * 100)
        await main_msg.update(
            content=f"Processing {completed_claims}/{total_claims} claims... {percent}%"
        )

    # Function to process a single claim
    async def process_claim(claim):
        nonlocal completed_claims

        # Update status UI
        claim_number = claims.index(claim) + 1
        current_step = f"Claim {claim_number}/{total_claims}"

        with cl.Step(name=f"Fact-checking: {current_step}", show_input=True) as step:
            # Step 1: Display the claim being checked
            await step.stream_token(f"Fact-checking claim: {claim.text}\n\n")

            # Step 2: Gather evidence
            await step.stream_token("Gathering evidence...\n")
            try:
                evidence = await evidence_hunter.find_evidence(claim.text)
                if not evidence:
                    await step.stream_token("\nNo evidence found for this claim.")
                    evidence_content = "*No evidence found*"
                else:
                    await step.stream_token(f"\nFound {len(evidence)} pieces of evidence.\n")
                    evidence_content = await create_evidence_display(
                        evidence, detailed=show_detailed_evidence, show_confidence=show_confidence
                    )
            except Exception as e:
                await step.stream_token(f"\nError gathering evidence: {str(e)}")
                evidence = []
                evidence_content = f"*Error gathering evidence: {str(e)}*"

            # Step 3: Generate verdict
            await step.stream_token("\nGenerating verdict...\n")
            try:
                verdict = await verdict_writer.write_verdict(claim.text, evidence)
                if not verdict:
                    await step.stream_token("\nUnable to generate verdict.")
                    verdict_content = "*Unable to generate verdict*"
                else:
                    verdict_content = await create_verdict_display(
                        verdict, show_confidence=show_confidence
                    )
                    await step.stream_token(f"\nVerdict: {verdict.get('rating', 'Unknown')}")
            except Exception as e:
                await step.stream_token(f"\nError generating verdict: {str(e)}")
                verdict = {}
                verdict_content = f"*Error generating verdict: {str(e)}*"

            # Save the result
            result = {
                "claim": claim.text,
                "claim_object": claim,
                "evidence": evidence,
                "verdict": verdict,
                "timestamp": datetime.datetime.now().isoformat(),
                "evidence_content": evidence_content,
                "verdict_content": verdict_content,
            }
            results.append(result)

            # Update the completion count and progress
            completed_claims += 1
            await update_progress()

            # Return the completed result
            return result

    # Process claims either concurrently or sequentially
    if concurrent_processing and total_claims > 1:
        # Process claims concurrently in batches
        all_tasks = []
        for i in range(0, len(claims), max_concurrent):
            batch = claims[i:i + max_concurrent]
            tasks = [process_claim(claim) for claim in batch]
            await asyncio.gather(*tasks)
            all_tasks.extend(tasks)
    else:
        # Process claims sequentially
        for claim in claims:
            await process_claim(claim)

    # Record end time and calculate duration
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Update the history with the new results
    factcheck_history.extend(results)
    cl.user_session.set("factcheck_history", factcheck_history)

    # Update main message with completion status
    await main_msg.update(
        content=f"✅ Fact-checking complete! Processed {total_claims} claims in {duration:.1f} seconds."
    )

    # Create a summary message with final results
    summary = "# Fact-Check Results\n\n"
    summary += f"Processed {total_claims} claims in {duration:.1f} seconds.\n\n"

    for i, result in enumerate(results):
        claim_text = result["claim"]
        verdict = result.get("verdict", {})
        rating = verdict.get("rating", "Unknown")

        # Add verdict emoji
        rating_emoji = (
            "✅"
            if rating == "True"
            else "❌" if rating == "False" else "⚠️" if rating == "Partially True" else "❓"
        )

        summary += f"## Claim {i+1}: {rating_emoji} {rating}\n\n"
        summary += f"{claim_text}\n\n"

        # Add a brief explanation if available
        if "explanation" in verdict:
            explanation = verdict["explanation"]
            # Truncate if too long
            if len(explanation) > 150:
                explanation = explanation[:150] + "..."
            summary += f"*{explanation}*\n\n"

    # Add export button
    export_button = cl.Action(name="Export Results", value="export", id="export_results")

    # Send the summary message with export button
    await cl.Message(content=summary, actions=[export_button]).send()


async def handle_selected_claims(settings: Dict[str, Any]) -> None:
    """
    Process claims that were selected by the user through the UI.

    Args:
        settings: User settings dictionary
    """
    # Get the pending claims from the session
    pending_claims = cl.user_session.get("pending_claims", [])
    if not pending_claims:
        await cl.Message(content="No claims found to process").send()
        return

    # Get the settings values
    show_detailed_evidence = settings.get("detailed_evidence", True)
    show_confidence = settings.get("show_confidence_scores", True)
    show_feedback_form = settings.get("show_feedback_form", True)
    detect_related_claims = settings.get("detect_related_claims", True)
    concurrent_processing = settings.get("concurrent_processing", True)
    max_concurrent = int(settings.get("max_concurrent", 3))

    # Filter claims based on checkboxes
    selected_claims = []
    for i, claim in enumerate(pending_claims):
        checkbox_id = f"claim_{i}"
        if cl.user_session.get(checkbox_id, True):  # Default to True if not found
            selected_claims.append(claim)

    if not selected_claims:
        await cl.Message(content="No claims were selected for processing").send()
        return

    # Create main response message with progress indicators
    main_msg = cl.Message(content="", author="VeriFact")
    await main_msg.send()

    # Process the selected claims
    await process_claims(
        selected_claims,
        main_msg,
        show_detailed_evidence,
        show_confidence,
        show_feedback_form,
        detect_related_claims,
        concurrent_processing,
        max_concurrent,
    )
