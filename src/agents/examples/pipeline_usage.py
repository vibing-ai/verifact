"""
Example usage of the factchecking pipeline with the new agent architecture.

This script demonstrates how to set up and use the new agent architecture with
proper separation of concerns and dependency injection.
"""

import asyncio
from typing import Dict, Any, List

from src.agents.factory import AgentFactory
from src.agents.orchestrator import FactcheckPipeline, FactcheckPipelineFactory
from src.agents.interfaces import ClaimDetector, EvidenceHunter, VerdictWriter
from src.agents.dto import Claim, Evidence, Verdict


async def process_with_full_pipeline() -> None:
    """
    Example showing how to use the factory to create a complete pipeline.
    
    This approach is recommended for most use cases where you want to run
    the full factchecking process on a text.
    """
    print("=== Using Factory-Created Pipeline ===")
    
    # Define configuration for the pipeline and its agents
    config: Dict[str, Any] = {
        "parallelism": 3,
        "min_check_worthiness": 0.6,
        "max_claims": 5,
        "claim_detector": {
            "model_name": "google/gemma-2-27b-it"
        },
        "evidence_hunter": {
            "model_name": "google/gemma-3-27b-it:free"
        },
        "verdict_writer": {
            "model_name": "deepseek/deepseek-chat:free",
            "explanation_detail": "detailed",
            "citation_style": "academic",
            "include_alternative_perspectives": True
        }
    }
    
    # Create the pipeline using the factory
    pipeline = FactcheckPipelineFactory.create_pipeline(config)
    
    # Sample text to factcheck
    text = """
    The Earth is flat and this has been proven by multiple scientific experiments.
    The COVID-19 vaccine contains microchips that allow the government to track people.
    The climate has always been changing throughout Earth's history.
    """
    
    # Process the text through the pipeline
    verdicts = await pipeline.process_text(text)
    
    # Print the results
    print(f"Generated {len(verdicts)} verdicts:")
    for i, verdict in enumerate(verdicts, 1):
        print(f"\n--- Verdict {i} ---")
        print(f"Claim: {verdict.claim}")
        print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
        print(f"Explanation: {verdict.explanation[:150]}...")


async def process_with_explicit_agents() -> None:
    """
    Example showing how to use the agents individually with explicit control.
    
    This approach gives you more control over the workflow and allows you to
    customize the processing of each step.
    """
    print("\n=== Using Individual Agents ===")
    
    # Create individual agents using the factory
    claim_detector = AgentFactory.create_claim_detector({"model_name": "google/gemma-2-27b-it"})
    evidence_hunter = AgentFactory.create_evidence_hunter({"model_name": "google/gemma-3-27b-it:free"})
    verdict_writer = AgentFactory.create_verdict_writer({
        "model_name": "deepseek/deepseek-chat:free",
        "explanation_detail": "detailed"
    })
    
    # Sample text to factcheck
    text = "Vaccines cause autism according to several studies."
    
    # Step 1: Detect claims
    claims = await claim_detector.detect_claims(text, min_check_worthiness=0.5)
    print(f"Detected {len(claims)} claims.")
    
    # Process each claim individually
    for i, claim in enumerate(claims, 1):
        print(f"\n--- Processing Claim {i}: {claim.text} ---")
        print(f"Check-worthiness: {claim.check_worthiness:.2f}")
        
        # Step 2: Gather evidence
        evidence = await evidence_hunter.gather_evidence(claim)
        print(f"Found {len(evidence)} pieces of evidence.")
        
        # Step 3: Generate verdict
        verdict = await verdict_writer.generate_verdict(
            claim, 
            evidence,
            explanation_detail="standard"
        )
        
        # Print the result
        print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
        print(f"Explanation: {verdict.explanation[:150]}...")


async def process_with_base_protocol() -> None:
    """
    Example showing how to use the base Agent protocol for processing.
    
    This approach demonstrates the use of the generic process() method
    defined in the base Agent protocol, which allows for more flexible
    agent composition.
    """
    print("\n=== Using Base Agent Protocol ===")
    
    # Create individual agents using the factory
    claim_detector = AgentFactory.create_claim_detector()
    evidence_hunter = AgentFactory.create_evidence_hunter()
    verdict_writer = AgentFactory.create_verdict_writer()
    
    # Sample text to factcheck
    text = "The moon landing was faked in a Hollywood studio."
    
    # Use the generic process() method of each agent
    print(f"Processing text: {text}")
    
    # Step 1: Process text to get claims
    claims = await claim_detector.process(text)
    if not claims:
        print("No claims detected.")
        return
    
    claim = claims[0]  # Take the first claim
    print(f"Detected claim: {claim.text}")
    
    # Step 2: Process claim to get evidence
    evidence = await evidence_hunter.process(claim)
    print(f"Found {len(evidence)} pieces of evidence.")
    
    # Step 3: Process claim and evidence to get verdict
    verdict = await verdict_writer.process((claim, evidence))
    
    # Print the result
    print(f"Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
    print(f"Explanation: {verdict.explanation[:150]}...")


async def main() -> None:
    """Run all examples."""
    # Example 1: Using the complete pipeline
    await process_with_full_pipeline()
    
    # Example 2: Using individual agents with explicit control
    await process_with_explicit_agents()
    
    # Example 3: Using the base Agent protocol
    await process_with_base_protocol()


if __name__ == "__main__":
    asyncio.run(main()) 