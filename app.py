import chainlit as cl
from src.verifact_manager import VerifactManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pipeline = VerifactManager()


@cl.on_message
async def handle_message(message: cl.Message):
    # This dictionary will hold ALL our step objects for the duration of the run
    steps = {}

    # This will act like a stack to keep track of the current active step
    active_step_id_stack = []

    async def progress_callback(type: str, data: dict):
        nonlocal steps, active_step_id_stack

        if type == "step_start":
            parent_id = active_step_id_stack[-1] if active_step_id_stack else None
            logger.info(f"Starting step: {data['title']}")
            step = cl.Step(name=data["title"], parent_id=parent_id, id=data["title"])
            steps[data["title"]] = step
            active_step_id_stack.append(step.id)  # Push new step to stack
            logger.info(f"Step stack after push: {active_step_id_stack}")
            await step.send()

        elif type == "step_end":
            step_id = active_step_id_stack.pop()  # Pop current step from stack
            step = steps[step_id]
            step.output = data["output"]
            await step.update()

        elif type == "step_error":
            step_id = active_step_id_stack.pop()  # Pop current step from stack
            step = steps[step_id]
            step.is_error = True
            step.output = data["output"]
            await step.update()

        elif type == "claims_detected":
            # This logic is special and doesn't use the stack
            # It just adds claim-specific steps for later nesting
            main_pipeline_id = steps["Fact-Checking Pipeline"].id
            for i, claim in enumerate(data["claims"]):
                claim_id = f"claim_{i+1}"
                claim_step = cl.Step(
                    name=f'Claim {i+1}: "{claim.text[:60]}..."',
                    parent_id=main_pipeline_id,
                    id=claim_id,
                )
                steps[claim_id] = claim_step
                await claim_step.send()

    # The main logic starts here
    await progress_callback(type="step_start", data={"title": "Fact-Checking Pipeline"})

    try:
        verdicts = await pipeline.run(
            message.content, progress_callback=progress_callback
        )

        # Debug logging to see what we got back
        logger.info(f"DEBUG: Received {len(verdicts) if verdicts else 0} verdicts")
        logger.info(f"DEBUG: Verdicts content: {verdicts}")

        if not verdicts:
            await progress_callback(
                type="step_end",
                data={"output": "No factual claims were detected in your message."},
            )
            return

        # Format the final message and send it
        response = "## Fact-Checking Complete\nHere are the results:\n"

        for idx, verdict_tuple in enumerate(verdicts):
            logger.info(f"DEBUG: Processing verdict {idx}: {verdict_tuple}")

            # Handle different possible tuple structures
            if len(verdict_tuple) == 3:
                claim, evidence, verdict = verdict_tuple
            else:
                logger.error(f"Unexpected verdict tuple structure: {verdict_tuple}")
                continue

            # Safely extract attributes with fallbacks
            claim_text = (
                getattr(claim, "text", str(claim)) if claim else "Unknown claim"
            )
            verdict_text = (
                getattr(verdict, "verdict", str(verdict)) if verdict else "No verdict"
            )
            confidence = getattr(verdict, "confidence", "N/A") if verdict else "N/A"
            explanation = (
                getattr(verdict, "explanation", "No explanation provided")
                if verdict
                else "N/A"
            )
            sources = getattr(verdict, "sources", []) if verdict else []
            sources_str = "\n".join(sources) if sources else "No sources provided."

            if evidence:
                evidence_str = "\n".join(
                    [
                        f"- {getattr(ev, 'content', str(ev))} (Source: {getattr(ev, 'source', 'N/A')}, Stance: {getattr(ev, 'stance', 'N/A')}, Relevance: {getattr(ev, 'relevance', 'N/A')})"
                        for ev in evidence
                    ]
                )
            else:
                evidence_str = "No evidence found."

            response += (
                f"\n---\n**Claim {idx+1}:** {claim_text}\n"
                f"**Evidence:**\n{evidence_str}\n"
                f"\n**Verdict:** {verdict_text}\n"
                f"**Confidence:** {confidence}\n"
                f"**Explanation:** {explanation}\n"
                f"**Sources:**\n{sources_str}\n"
            )

        # Close the main pipeline step and set its final output
        steps["Fact-Checking Pipeline"].output = response
        await steps["Fact-Checking Pipeline"].update()
        active_step_id_stack.pop()  # Final pop for the main step

        # Send a final, separate message for easy viewing
        await cl.Message(content=response).send()

    except Exception as e:
        logger.error(f"An error occurred in the main pipeline: {e}", exc_info=True)
        # Check if there's an active step to mark as error
        if active_step_id_stack:
            await progress_callback(
                type="step_error", data={"output": f"An error occurred: {str(e)}"}
            )


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="👋 Welcome to VeriFact! The system is up and running. Type your claim or question to get started."
    ).send()
