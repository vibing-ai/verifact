"""
ClaimDetector agent for identifying factual claims in text.
"""

import os
from typing import List, Optional
from pydantic import BaseModel
from openai.agents import Agent, Runner
from openai.agents.tools import WebSearchTool
from src.utils.model_config import get_model_name, get_model_settings


class Claim(BaseModel):
    """A factual claim identified from text."""
    text: str
    context: str = ""
    checkworthy: bool = True


class ClaimDetector:
    """Agent for detecting factual claims in text."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the ClaimDetector agent.
        
        Args:
            model_name: Optional name of the model to use
        """
        self.model_name = get_model_name(model_name, agent_type="claim_detector")
        self.model_settings = get_model_settings()
        
        # Create the agent with WebSearchTool for context
        self.agent = Agent(
            name="ClaimDetector",
            instructions="""
            You are a claim detection agent. Your job is to identify check-worthy factual claims from input text.
            
            For each claim:
            1. Extract the exact claim text
            2. Determine if it's check-worthy (statements presented as facts, not opinions)
            3. Include relevant context
            
            Focus on:
            - Statements that can be verified with evidence
            - Specific, measurable claims
            - Claims about events, statistics, or historical facts
            
            Ignore:
            - Personal opinions
            - Subjective statements
            - Value judgments
            - Predictions about the future
            """,
            output_type=List[Claim],
            tools=[WebSearchTool()],
            model=self.model_name,
            **self.model_settings
        )
    
    async def detect_claims(self, text: str) -> List[Claim]:
        """
        Detect factual claims in the provided text.
        
        Args:
            text: The text to analyze for claims
            
        Returns:
            List[Claim]: A list of detected claims
        """
        result = await Runner.run(self.agent, text)
        return result.output 