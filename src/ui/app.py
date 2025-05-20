"""VeriFact Chainlit UI Entry Point

This module serves as the main entry point for the VeriFact Chainlit web interface.
It initializes a Chainlit chat application with the three main agents:
- ClaimDetector: Identifies factual claims from user input
- EvidenceHunter: Gathers evidence for those claims
- VerdictWriter: Generates verdicts based on the evidence

To run the web interface:
    chainlit run app.py

For API access, use `src/main.py`.
For CLI access, use `cli.py`.
"""

import datetime
import json
import os
import sys

import chainlit as cl

from src.ui.agent_manager import handle_selected_claims, process_claims

# Import UI components
from src.ui.utils import export_results_to_json, get_feedback_stats, save_feedback
from src.utils.db import SupabaseClient

# Check that authentication secret is set
if not os.environ.get("CHAINLIT_AUTH_SECRET"):
    print("\n⚠️  WARNING: CHAINLIT_AUTH_SECRET environment variable is not set!")
    print("Authentication will not work properly without a secret key.")
    print("Run './create_secret.py' to generate a secure secret key")
    print("and add it to your .env file.\n")

    # Ask if they want to continue anyway or exit
    if input("Continue without authentication? (y/n): ").lower() != "y":
        print("Exiting. Please set up authentication and try again.")
        sys.exit(1)


@cl.on_message
async def main(message: cl.Message):
    """Process user messages and run the VeriFact pipeline."""
    # Get the agents from the user session
    claim_detector = cl.user_session.get("claim_detector")

    # Get user settings
    settings = cl.user_session.get("settings")
    max_claims = int(settings.get("max_claims", 5))
    show_detailed_evidence = settings.get("detailed_evidence", True)
    show_confidence = settings.get("show_confidence_scores", True)
    show_feedback_form = settings.get("show_feedback_form", True)
    detect_related_claims = settings.get("detect_related_claims", True)
    concurrent_processing = settings.get("concurrent_processing", True)
    max_concurrent = int(settings.get("max_concurrent", 3))

    # Create main response message with progress indicators
    main_msg = cl.Message(content="", author="VeriFact")
    await main_msg.send()

    try:
        # Step 1: Detect claims with progress updates
        with cl.Step(name="Detecting Claims", show_input=True) as step:
            await main_msg.update(content="🔎 Analyzing your input to identify factual claims...")

            # Update progress in the step
            await step.stream_token("Scanning text for check-worthy claims...")
            claims = await claim_detector.detect_claims(message.content, max_claims=max_claims)

            if not claims:
                await main_msg.update(
                    content="❗ No check-worthy claims were detected in your input. Please try again with a statement containing factual claims."
                )
                await step.stream_token("\n\nNo check-worthy claims found.")
                return

            # Filter to check-worthy claims
            check_worthy_claims = [
                claim
                for claim in claims
                if claim.check_worthiness >= claim_detector.min_check_worthiness
            ]
            if len(check_worthy_claims) > max_claims:
                check_worthy_claims = check_worthy_claims[:max_claims]

            # Format claims in a visually clear way
            claims_content = "## Detected Claims\n\n"
            for i, claim in enumerate(claims):
                # Check if this claim was selected for processing
                is_check_worthy = claim in check_worthy_claims
                check_icon = "✅" if is_check_worthy else "⏩"

                # Show claim with ranking information
                claims_content += f"{check_icon} **Claim {i + 1}:** {claim.text}\n"

                # Add claim details if check-worthy
                if is_check_worthy:
                    claims_content += f"   *Check-worthiness: {claim.check_worthiness:.2f}*\n"
                    if hasattr(claim, "rank") and claim.rank is not None:
                        claims_content += f"   *Rank: {claim.rank}*\n"
                    claims_content += "   *This claim will be fact-checked*\n\n"
                else:
                    claims_content += f"   *Check-worthiness: {claim.check_worthiness:.2f}*\n"
                    claims_content += (
                        "   *This claim is not specific enough to be fact-checked*\n\n"
                    )

            await step.stream_token(
                f"\n\nFound {len(claims)} claims, {len(check_worthy_claims)} are check-worthy."
            )
            await cl.Message(content=claims_content).send()

            # Create claim selection UI if there are multiple claims
            if len(check_worthy_claims) > 1:
                claim_selection_msg = "## Claim Selection\n\nMultiple claims were detected. You can choose which ones to fact-check:"

                # Create a checkbox for each claim
                claim_checkboxes = []
                for i, claim in enumerate(check_worthy_claims):
                    claim_checkboxes.append(
                        cl.Checkbox(
                            id=f"claim_{i}",
                            label=(
                                f"Claim {i + 1}: {claim.text[:60]}..."
                                if len(claim.text) > 60
                                else claim.text
                            ),
                            initial=True,
                        )
                    )

                # Add process button
                process_button = cl.Button(
                    id="process_claims_button", label="Process Selected Claims"
                )

                # Send the selection UI
                await cl.Message(content=claim_selection_msg, elements=claim_checkboxes).send()

                # Send the process button
                await cl.Message(content="", elements=[process_button]).send()

                # Store claims for later processing when button is clicked
                cl.user_session.set("pending_claims", check_worthy_claims)
                await main_msg.update(
                    content="Select which claims to fact-check and click 'Process Selected Claims'"
                )
                return

            # If only one claim or user doesn't want to select, continue with all check-worthy claims
            await main_msg.update(
                content=f"Found {len(check_worthy_claims)} check-worthy claims. Gathering evidence..."
            )

        # Process the claims
        await process_claims(
            check_worthy_claims,
            main_msg,
            show_detailed_evidence,
            show_confidence,
            show_feedback_form,
            detect_related_claims,
            concurrent_processing,
            max_concurrent,
        )

    except Exception as e:
        # Handle errors with user-friendly messages
        await main_msg.update(content=f"❌ An error occurred: {str(e)}")
        cl.logger.error(f"Error in VeriFact pipeline: {str(e)}")


@cl.on_button_click
async def on_button_click(button):
    """Handle button clicks for claim processing."""
    if button.id == "process_claims_button":
        # Get settings
        settings = cl.user_session.get("settings")
        if not settings:
            await cl.Message(content="Error: Settings not found").send()
            return

        # Process the selected claims
        await handle_selected_claims(settings)


@cl.action_callback("export_results")
async def on_export(action):
    """Handle export button click to download results as JSON."""
    # Get the fact-check history
    factcheck_history = cl.user_session.get("factcheck_history", [])

    if not factcheck_history:
        await cl.Message(content="No fact-check results to export").send()
        return

    # Export to JSON
    results_json = await export_results_to_json(factcheck_history)

    # Generate a filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"verifact_results_{timestamp}.json"

    # Create a downloadable file
    await cl.Message(
        content="Your fact-check results are ready for download.",
        attachments=[
            cl.Attachment(name=filename, content=results_json.encode(), mime="application/json")
        ],
    ).send()


@cl.action_callback("view_history")
async def on_view_history(action):
    """Display the user's fact-check history."""
    # Get the fact-check history
    factcheck_history = cl.user_session.get("factcheck_history", [])

    if not factcheck_history:
        await cl.Message(content="You haven't fact-checked any claims yet").send()
        return

    # Create a summary of the history
    history_content = "# Your Fact-Check History\n\n"

    for i, result in enumerate(factcheck_history):
        claim_text = result["claim"]
        verdict = result.get("verdict", {})
        rating = verdict.get("rating", "Unknown")

        # Add verdict emoji
        rating_emoji = (
            "✅"
            if rating == "True"
            else "❌"
            if rating == "False"
            else "⚠️"
            if rating == "Partially True"
            else "❓"
        )

        # Format timestamp
        timestamp = result.get("timestamp", "")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    dt = timestamp
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                timestamp_str = str(timestamp)
        else:
            timestamp_str = "Unknown time"

        history_content += f"## {i + 1}. {rating_emoji} {rating} - {timestamp_str}\n\n"
        history_content += f"**Claim:** {claim_text}\n\n"

        if "explanation" in verdict:
            history_content += f"**Verdict:** {verdict['explanation']}\n\n"

        history_content += "---\n\n"

    # Send the history message
    await cl.Message(content=history_content).send()


@cl.action_callback("feedback_*")
async def on_feedback(action):
    """Handle feedback submission."""
    # Extract fact-check ID from action ID
    fact_check_id = action.id.replace("feedback_", "")

    # Get values from UI elements
    accuracy_value = cl.user_session.get(f"accuracy_{fact_check_id}")
    helpfulness_value = cl.user_session.get(f"helpfulness_{fact_check_id}")
    comments_value = cl.user_session.get(f"comments_{fact_check_id}", "")

    # Prepare feedback data
    feedback_data = {
        "accuracy": accuracy_value,
        "helpfulness": helpfulness_value,
        "comments": comments_value,
    }

    # Save feedback
    success = await save_feedback(fact_check_id, feedback_data)

    if success:
        await cl.Message(
            content="Thank you for your feedback! It helps us improve VeriFact."
        ).send()
    else:
        await cl.Message(
            content="There was an error saving your feedback. Please try again later."
        ).send()


@cl.action_callback("view_feedback_admin")
async def on_view_feedback_admin(action):
    """Display feedback statistics for admin users."""
    # Check if user is admin
    user = cl.user_session.get("user")
    if not user or getattr(user, "identifier", "") != os.environ.get(
        "VERIFACT_ADMIN_USER", "admin"
    ):
        await cl.Message(content="You don't have permission to view feedback statistics").send()
        return

    # Get feedback statistics
    stats = await get_feedback_stats()

    # Create feedback statistics message
    feedback_content = "# Feedback Statistics\n\n"

    # Total feedback
    feedback_content += f"**Total feedback submissions:** {stats.total_feedback}\n\n"

    # Accuracy ratings
    feedback_content += "## Accuracy Ratings\n\n"
    for rating, count in stats.accuracy_ratings.items():
        percent = (count / stats.total_feedback * 100) if stats.total_feedback > 0 else 0
        feedback_content += f"- **{rating}:** {count} ({percent:.1f}%)\n"

    feedback_content += "\n"

    # Helpfulness ratings
    feedback_content += "## Helpfulness Ratings\n\n"
    for rating, count in stats.helpfulness_ratings.items():
        percent = (count / stats.total_feedback * 100) if stats.total_feedback > 0 else 0
        feedback_content += f"- **{rating}:** {count} ({percent:.1f}%)\n"

    feedback_content += "\n"

    # Recent feedback
    feedback_content += "## Recent Feedback\n\n"
    for i, feedback in enumerate(stats.recent_feedback):
        feedback_content += f"### Feedback {i + 1}\n\n"
        feedback_content += f"**Accuracy:** {feedback.get('accuracy_rating', 'N/A')}\n"
        feedback_content += f"**Helpfulness:** {feedback.get('helpfulness_rating', 'N/A')}\n"

        if feedback.get("comments"):
            feedback_content += f"**Comments:** {feedback.get('comments')}\n"

        # Format timestamp
        timestamp = feedback.get("timestamp", "")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    dt = timestamp
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                timestamp_str = str(timestamp)

            feedback_content += f"**Time:** {timestamp_str}\n"

        feedback_content += "\n---\n\n"

    # Add export button
    export_button = cl.Action(name="Export Feedback", value="export_feedback", id="export_feedback")

    # Send the feedback statistics message
    await cl.Message(content=feedback_content, actions=[export_button]).send()


@cl.action_callback("export_feedback")
async def on_export_feedback(action):
    """Export feedback data as JSON for admin users."""
    # Check if user is admin
    user = cl.user_session.get("user")
    if not user or getattr(user, "identifier", "") != os.environ.get(
        "VERIFACT_ADMIN_USER", "admin"
    ):
        await cl.Message(content="You don't have permission to export feedback data").send()
        return

    # Get feedback statistics
    stats = await get_feedback_stats()

    if stats.total_feedback == 0:
        await cl.Message(content="No feedback data to export").send()
        return

    # Get all feedback data
    db_client = SupabaseClient()

    if db_client.is_connected():
        try:
            all_feedback = await db_client.get_all_feedback()
        except Exception as e:
            cl.logger.error(f"Error getting feedback data: {str(e)}")
            await cl.Message(content=f"Error retrieving feedback data: {str(e)}").send()
            return
    else:
        # Fall back to local file
        feedback_file = os.path.join(os.getcwd(), "data", "feedback.json")
        if not os.path.exists(feedback_file):
            await cl.Message(content="No feedback data found").send()
            return

        with open(feedback_file) as f:
            all_feedback = json.load(f)

    # Convert to JSON
    feedback_json = json.dumps(all_feedback, indent=2)

    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"verifact_feedback_{timestamp}.json"

    # Create a downloadable file
    await cl.Message(
        content="Feedback data export is ready for download.",
        attachments=[
            cl.Attachment(name=filename, content=feedback_json.encode(), mime="application/json")
        ],
    ).send()
