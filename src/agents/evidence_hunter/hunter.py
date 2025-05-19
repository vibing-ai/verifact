"""
EvidenceHunter agent for gathering evidence for claims.
"""

import os
from typing import List, Optional
from pydantic import BaseModel
from agents import Agent, Runner
from agents.tools import WebSearchTool
from src.utils.model_config import get_model_name, get_model_settings
from src.agents.claim_detector.detector import Claim


class Evidence(BaseModel):
    """Evidence related to a claim."""
    content: str
    source: str
    relevance: float = 1.0
    stance: str = "supporting"  # supporting, contradicting, neutral


class EvidenceHunter:
    """Agent for gathering evidence for claims."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the EvidenceHunter agent.
        
        Args:
            model_name: Optional name of the model to use
        """
        self.model_name = get_model_name(model_name)
        self.model_settings = get_model_settings()
        
        # Create the agent with WebSearchTool for finding evidence
        self.agent = Agent(
            name="EvidenceHunter",
            instructions="""
            You are an evidence gathering agent. Your job is to find and evaluate evidence
            related to the provided claim.
            
            For each piece of evidence:
            1. Retrieve relevant information from trusted sources
            2. Provide the source URL
            3. Evaluate its relevance to the claim (0-1)
            4. Determine if it supports, contradicts, or is neutral to the claim
            
            Focus on:
            - Reputable sources
            - Recent information (if applicable)
            - Direct evidence that addresses the claim
            - Multiple perspectives when available
            
            Always include:
            - Direct quotes or paraphrases from sources
            - Complete source URLs
            - A mix of supporting and contradicting evidence when available
            """,
            output_type=List[Evidence],
            tools=[WebSearchTool()],
            model=self.model_name,
            **self.model_settings
        )
    
    async def gather_evidence(self, claim: Claim) -> List[Evidence]:
        """
        Gather evidence for the provided claim.
        
        Args:
            claim: The claim to gather evidence for
            
        Returns:
            List[Evidence]: A list of evidence pieces
        """
        query = f"Claim: {claim.text}\nContext: {claim.context}"
        result = await Runner.run(self.agent, query)
        return result.output 