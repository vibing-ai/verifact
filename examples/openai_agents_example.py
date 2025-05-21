"""Example showing how to use the OpenAI Agents SDK alongside VeriFact agents.

This demonstrates the correct import patterns to avoid namespace conflicts
now that we've renamed our local 'agents' module to 'verifact_agents'.
"""

import os
from typing import Dict, List

# Import OpenAI Agents SDK
from agents import Agent as OpenAIAgent
from agents import Runner

# Import VeriFact agents
from src.verifact_agents import ClaimDetector
from src.verifact_agents.claim_detector.models import Claim
from src.verifact_agents.evidence_hunter import EvidenceHunter
from src.verifact_agents.verdict_writer import VerdictWriter


async def run_factcheck_with_openai_agent() -> Dict:
    """Demonstrates using both OpenAI Agents SDK and VeriFact agents together."""
    # First, use VeriFact agents to extract claims
    claim_detector = ClaimDetector()
    claims = await claim_detector.process("The Earth is flat and vaccines cause autism.")
    
    # Use OpenAI Agent to evaluate the claims
    # Make sure OPENAI_API_KEY is set in environment
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY must be set in environment")
    
    fact_checker_agent = OpenAIAgent(
        name="Fact Checker",
        instructions=(
            "You are a fact-checking assistant. Your job is to verify claims "
            "and provide evidence for your verdicts. Use reliable sources and "
            "explain your reasoning clearly."
        ),
    )
    
    # Format claims for the OpenAI agent
    claim_texts = [f"- {claim.text}" for claim in claims]
    message = "Please verify these claims:\n" + "\n".join(claim_texts)
    
    # Run the agent
    result = await Runner.run(fact_checker_agent, message)
    
    # Return the results
    return {
        "claims": [claim.dict() for claim in claims],
        "openai_agent_response": result.final_output
    }


if __name__ == "__main__":
    import asyncio
    
    async def main():
        result = await run_factcheck_with_openai_agent()
        print("\nClaims detected by VeriFact:")
        for i, claim in enumerate(result["claims"]):
            print(f"{i+1}. {claim['text']}")
        
        print("\nOpenAI Agent response:")
        print(result["openai_agent_response"])
    
    asyncio.run(main()) 