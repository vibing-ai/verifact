"""
VerdictWriter agent for generating verdicts based on evidence.
"""

import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from agents import Agent, Runner
from src.utils.model_config import get_model_name, get_model_settings
from src.agents.claim_detector.detector import Claim
from src.agents.evidence_hunter.hunter import Evidence


class Verdict(BaseModel):
    """A verdict on a claim based on evidence."""
    claim: str
    verdict: Literal["true", "false", "partially true", "unverifiable"] = Field(
        description="The verdict on the claim: true, false, partially true, or unverifiable"
    )
    confidence: float = Field(
        description="Confidence in the verdict (0-1)",
        ge=0.0,
        le=1.0
    )
    explanation: str = Field(
        description="Detailed explanation of the verdict with reasoning"
    )
    sources: List[str] = Field(
        description="List of sources used to reach the verdict",
        min_items=1
    )


class VerdictWriter:
    """Agent for generating verdicts based on evidence."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the VerdictWriter agent.
        
        Args:
            model_name: Optional name of the model to use
        """
        self.model_name = get_model_name(model_name)
        self.model_settings = get_model_settings()
        
        # Create the agent for analyzing evidence and generating verdicts
        self.agent = Agent(
            name="VerdictWriter",
            instructions="""
            You are a verdict writing agent. Your job is to analyze evidence and determine
            the accuracy of a claim, providing a detailed explanation and citing sources.
            
            Your verdict should:
            1. Classify the claim as true, false, partially true, or unverifiable
            2. Assign a confidence score (0-1)
            3. Provide a detailed explanation of your reasoning
            4. Cite all sources used
            
            Guidelines:
            - Base your verdict solely on the provided evidence
            - Weigh contradicting evidence fairly
            - Consider the reliability of sources
            - Be transparent about limitations in the evidence
            - When evidence is insufficient, label as "unverifiable" with low confidence
            - For partially true claims, explain which parts are true and which are false
            
            Your explanation must be clear, factual, and balanced, avoiding political bias.
            """,
            output_type=Verdict,
            model=self.model_name,
            **self.model_settings
        )
    
    async def generate_verdict(self, claim: Claim, evidence: List[Evidence]) -> Verdict:
        """
        Generate a verdict for the claim based on evidence.
        
        Args:
            claim: The claim to evaluate
            evidence: The evidence to consider
            
        Returns:
            Verdict: The verdict on the claim
        """
        # Format the evidence for the agent
        evidence_text = "\n\n".join([
            f"Source: {e.source}\nStance: {e.stance}\nRelevance: {e.relevance}\nContent: {e.content}"
            for e in evidence
        ])
        
        query = f"Claim: {claim.text}\n\nEvidence:\n{evidence_text}"
        result = await Runner.run(self.agent, query)
        return result.output 