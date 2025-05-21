"""VeriFact Chainlit UI Entry Point.

This is a simplified version that focuses on core functionality.
"""

import chainlit as cl
from chainlit.element import Text
from src.verifact_agents.claim_detector import ClaimDetector
from src.verifact_agents.evidence_hunter import EvidenceHunter
from src.verifact_agents.verdict_writer import VerdictWriter

@cl.on_chat_start
async def on_chat_start():
    """Initialize the VeriFact system when a new chat session starts."""
    # Initialize the agents
    claim_detector = ClaimDetector()
    evidence_hunter = EvidenceHunter()
    verdict_writer = VerdictWriter()

    # Store the agents in the user session
    cl.user_session.set("claim_detector", claim_detector)
    cl.user_session.set("evidence_hunter", evidence_hunter)
    cl.user_session.set("verdict_writer", verdict_writer)

    # Send welcome message
    await cl.Message(
        content="Welcome to VeriFact! I can help you fact-check claims. Simply enter a statement or piece of text containing claims you want to verify.",
        author="VeriFact",
    ).send()

@cl.on_message
async def main(message: cl.Message):
    """Process user messages and run the VeriFact pipeline."""
    # Get the agents from the user session
    claim_detector = cl.user_session.get("claim_detector")
    evidence_hunter = cl.user_session.get("evidence_hunter")
    verdict_writer = cl.user_session.get("verdict_writer")

    # Create main response message with progress indicators
    main_msg = cl.Message(content="🔎 Analyzing your input to identify factual claims...", author="VeriFact")
    await main_msg.send()

    try:
        # Step 1: Detect claims
        with cl.Step(name="Detecting Claims", show_input=True) as step:
            await step.stream_token("Scanning text for check-worthy claims...")
            claims = await claim_detector.detect_claims(message.content, max_claims=3)

            if not claims:
                await main_msg.update(content="❗ No check-worthy claims were detected in your input. Please try again with a statement containing factual claims.")
                await step.stream_token("\n\nNo check-worthy claims found.")
                return

            # Format claims
            claims_content = "## Detected Claims\n\n"
            for i, claim in enumerate(claims):
                claims_content += f"**Claim {i + 1}:** {claim.text}\n"
                if hasattr(claim, "check_worthiness"):
                    claims_content += f"   *Check-worthiness: {claim.check_worthiness:.2f}*\n\n"

            await step.stream_token(f"\n\nFound {len(claims)} claims.")
            await cl.Message(content=claims_content).send()

        # Step 2: Process the first claim as a demonstration
        if claims:
            claim = claims[0]
            await main_msg.update(content=f"Processing claim: {claim.text}")

            # Step 2a: Gather evidence
            with cl.Step(name="Gathering Evidence", show_input=True) as step:
                await step.stream_token(f"Searching for evidence related to: {claim.text}\n")
                evidence = await evidence_hunter.gather_evidence(claim.text)
                
                evidence_content = "## Evidence Found\n\n"
                if evidence:
                    await step.stream_token(f"\nFound {len(evidence)} pieces of evidence.")
                    for i, e in enumerate(evidence):
                        evidence_content += f"**Source {i+1}:** {e.get('source', 'Unknown')}\n"
                        evidence_content += f"{e.get('text', 'No text available')[:200]}...\n\n"
                else:
                    evidence_content += "No evidence found for this claim."
                
                await cl.Message(content=evidence_content).send()

            # Step 2b: Generate verdict
            with cl.Step(name="Generating Verdict", show_input=True) as step:
                await step.stream_token("Analyzing evidence and generating verdict...\n")
                verdict = await verdict_writer.generate_verdict(claim, evidence)
                
                if verdict:
                    verdict_content = "## Verdict\n\n"
                    verdict_content += f"**Rating:** {verdict.get('rating', 'Unknown')}\n\n"
                    verdict_content += f"**Explanation:** {verdict.get('explanation', 'No explanation available')}\n\n"
                    
                    await step.stream_token(f"\nVerdict: {verdict.get('rating', 'Unknown')}")
                    await cl.Message(content=verdict_content).send()
                else:
                    await step.stream_token("\nUnable to generate verdict.")
                    await cl.Message(content="Unable to generate a verdict for this claim.").send()
                
            await main_msg.update(content="✅ Fact-checking complete!")
            
    except Exception as e:
        # Handle errors
        await main_msg.update(content=f"❌ An error occurred: {str(e)}")
