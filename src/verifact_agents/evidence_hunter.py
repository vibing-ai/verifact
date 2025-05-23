import os
from datetime import datetime
from typing import Any, Dict, List

from agents import Agent, WebSearchTool
from pydantic import BaseModel, Field

from verifact_agents.claim_detector import Claim


class Evidence(BaseModel):
    """Evidence related to a claim."""

    content: str
    source: str
    relevance: float = 1.0
    stance: str = "supporting"  # supporting, contradicting, neutral
    credibility: float = 1.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# PROMPT = """
# You are an evidence gathering agent tasked with finding and evaluating evidence related to factual claims.

# For each claim:
# 1. Formulate effective search queries that will find relevant information
#     - Extract key entities and concepts
#     - Create multiple queries to find different perspectives
#     - Consider queries that might find contradicting evidence

# 2. Evaluate search results carefully:
#     - Determine source credibility (news organizations, academic sources, government sites are typically more reliable)
#     - Assess relevance to the specific claim
#     - Identify the stance (supporting, contradicting, or neutral)
#     - Extract specific passages that directly address the claim

# 3. Return a comprehensive set of evidence:
#     - Include both supporting and contradicting evidence when available
#     - Rank evidence by relevance and credibility (0.0-1.0 scale)
#     - Provide full source information for citation
#     - Include stance classification for each piece of evidence

# Your responsibilities:
# 1. Focus on facts and evidence, not opinions
# 2. Find multiple sources when possible to corroborate information
# 3. Identify contradictions or nuances in the evidence
# 4. Evaluate source credibility and provide higher relevance to more credible sources

# For each evidence piece, provide:
# - content: The relevant text passage that addresses the claim
# - source: The full URL of the source
# - relevance: A score from 0.0 to 1.0 indicating how relevant this evidence is to the claim
# - stance: "supporting", "contradicting", or "neutral" based on how the evidence relates to the claim
# """

# PROMPT = """
#         You are an evidence gathering agent tasked with finding and evaluating evidence related to factual claims.

#         For each claim:
#         1. Formulate effective search queries that will find relevant information
#             - Extract key entities and concepts
#             - Create multiple queries to find different perspectives
#             - Consider queries that might find contradicting evidence

#         2. Evaluate search results carefully:
#             - Determine source credibility (news organizations, academic sources, government sites are typically more reliable)
#             - Assess relevance to the specific claim
#             - Identify the stance (supporting, contradicting, or neutral)
#             - Extract specific passages that directly address the claim

#         3. Return a comprehensive set of evidence:
#             - Include both supporting and contradicting evidence when available
#             - Include multiple evidences on different aspects of the claim
#             - Rank evidence by relevance and credibility (0.0-1.0 scale)
#             - Provide full source information for citation
#             - Include stance classification for each piece of evidence

#         Your responsibilities:
#         1. Focus on facts and evidence, not opinions
#         2. Find multiple sources when possible to corroborate information
#         3. Identify contradictions or nuances in the evidence
#         4. Evaluate source credibility and provide higher relevance to more credible sources

#         For each evidence piece, provide:
#         - content: The relevant text passage that addresses the claim
#         - source: The full URL of the source
#         - relevance: A score from 0.0 to 1.0 indicating how relevant this evidence is to the claim
#         - stance: "supporting", "contradicting", or "neutral" based on how the evidence relates to the claim
#         - credibility: A score from 0.0 to 1.0 indicating the credibility of the source
#         - timestamp: The timestamp of the evidence
# """

def get_trust_sources(path: str):
    """Get the trust sources from the file, skipping empty and comment lines.

    Returns:
        list[str]: A list of trust sources.
    """
    with open(path, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

class EvidenceHunter:

    def __init__(self,trust_sources_path: str="trust_sources.txt"):
        """Initialize the evidence hunter with a claim.
        
        Args:
            claims (list[Claim]): The claims to find evidence for.
        """
        self.trust_sources = get_trust_sources(trust_sources_path)

        PROMPT = """
        You are an evidence gathering agent tasked with finding and evaluating evidence related to factual claims.

        For each claim:
        1. Formulate effective search queries that will find relevant information
            - Extract key entities and concepts
            - Create multiple queries to find different perspectives
            - Consider queries that might find contradicting evidence

        2. Evaluate search results carefully:
            - Determine source credibility (news organizations, academic sources, government sites are typically more reliable)
            - Consider the trusted sources in the list: {self.trust_sources}
            - Assess relevance to the specific claim
            - Identify the stance (supporting, contradicting, or neutral)
            - Extract specific passages that directly address the claim

        3. Return a comprehensive set of evidence:
            - Include both supporting and contradicting evidence when available
            - Include multiple evidences on different aspects of the claim
            - Rank evidence by relevance and credibility (0.0-1.0 scale)
            - Provide full source information for citation
            - Include stance classification for each piece of evidence

        Your responsibilities:
        1. Focus on facts and evidence, not opinions
        2. Find multiple sources when possible to corroborate information
        3. Identify contradictions or nuances in the evidence
        4. Evaluate source credibility and provide higher relevance to more credible sources

        For each evidence piece, provide:
        - content: The relevant text passage that addresses the claim
        - source: The full URL of the source
        - relevance:
            - A score from 0.0 to 1.0 indicating how relevant this evidence is to the claim
            - If the evidence is not relevant, set the relevance to 0.0
            - If the evidence is strongly contradicting, set the relevance close to 1.0
            - If the evidence is strongly supporting, set the relevance close to 1.0
        - stance: 
            - "supporting" if the evidence directly supports the claim,
            - "contradicting" if the evidence directly refutes the claim,
            - "neutral" if the evidence is related but does not clearly support or contradict the claim.
        - credibility: 
            - A score from 0.0 to 1.0 indicating the credibility of the source
            - If the source is in the list of trusted sources, set the credibility close to 1.0
            - If the timestamp of the evidence is older than 10 years, set the credibility close to 0.0

        - timestamp: The timestamp of the evidence
        """

        self.evidence_hunter_agent = Agent(
            name="EvidenceHunter",
            instructions=PROMPT,
            output_type=list[Evidence],
            tools=[WebSearchTool()],
            model=os.getenv("EVIDENCE_HUNTER_MODEL"),
        )

    def query_formulation(self, claim: Claim):
        """Formulate a query for a single claim.
        
        Args:
            claim (Claim): The claim to formulate a query for.

        Returns:
            str: The formulated query.
        """

        context = getattr(claim, "context", None)
        claim_context = context if context else "No additional context provided"
        query = f"""Claim to investigate: {claim.text}

        Context of the claim: {claim_context}

        Your task:
        1. Find evidence from credible sources that either supports or contradicts this claim
        2. Consider the trusted sources in the list: {self.trust_sources}
        3. Search for multiple perspectives and authoritative sources
        4. Evaluate the reliability and relevance of each source
        5. Collect both supporting and contradicting evidence when available.

        Return a comprehensive set of evidence pieces in the required format.
        """
        return query

