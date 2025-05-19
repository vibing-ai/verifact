"""
VeriFact Chainlit UI Entry Point

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

import os
import chainlit as cl
from chainlit.playground.providers import ChatOpenAI
from src.agents.claim_detector import ClaimDetector
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.verdict_writer import VerdictWriter

@cl.on_chat_start
async def start():
    """
    Initialize the VeriFact system when a new chat session starts.
    """
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
        author="VeriFact"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    """
    Process user messages and run the VeriFact pipeline.
    """
    # Get the agents from the user session
    claim_detector = cl.user_session.get("claim_detector")
    evidence_hunter = cl.user_session.get("evidence_hunter")
    verdict_writer = cl.user_session.get("verdict_writer")
    
    # Send a processing message
    processing_msg = cl.Message(content="Processing your input...", author="VeriFact")
    await processing_msg.send()
    
    try:
        # Step 1: Detect claims
        with cl.Step(name="Detecting Claims", show_input=True):
            claims = await claim_detector.detect_claims(message.content)
            if not claims:
                await processing_msg.update(content="No check-worthy claims were detected in your input. Please try again with a statement containing factual claims.")
                return
            
            claims_text = "\n\n".join([f"Claim: {claim.text}\nCheck-worthiness: {claim.checkworthy}" for claim in claims])
            await cl.Message(content=f"I found the following claims:\n\n{claims_text}").send()
        
        # Step 2: Gather evidence for each claim
        all_evidence = []
        for i, claim in enumerate(claims):
            if claim.checkworthy:
                with cl.Step(name=f"Gathering Evidence for Claim {i+1}", show_input=True):
                    evidence = await evidence_hunter.gather_evidence(claim)
                    all_evidence.append(evidence)
                    
                    evidence_text = "\n\n".join([f"Source: {e.source}\nRelevance: {e.relevance}" for e in evidence])
                    await cl.Message(content=f"Evidence for claim '{claim.text}':\n\n{evidence_text}").send()
        
        # Step 3: Generate verdicts
        for i, (claim, evidence) in enumerate(zip(claims, all_evidence)):
            if claim.checkworthy:
                with cl.Step(name=f"Writing Verdict for Claim {i+1}", show_input=True):
                    verdict = await verdict_writer.generate_verdict(claim, evidence)
                    
                    verdict_text = f"**Claim:** {claim.text}\n\n**Verdict:** {verdict.verdict}\n\n**Confidence:** {verdict.confidence}\n\n**Explanation:** {verdict.explanation}\n\n**Sources:**\n"
                    for source in verdict.sources:
                        verdict_text += f"- {source}\n"
                    
                    await cl.Message(content=verdict_text).send()
        
        # Update the processing message
        await processing_msg.update(content="Factchecking complete!")
        
    except Exception as e:
        # Handle errors
        await processing_msg.update(content=f"An error occurred: {str(e)}")
        cl.logger.error(f"Error in VeriFact pipeline: {str(e)}") 