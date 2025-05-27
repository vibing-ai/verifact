import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from agents import Agent, WebSearchTool
from pydantic import BaseModel, Field

from verifact_agents.claim_detector import Claim

logger = logging.getLogger(__name__)

class Evidence(BaseModel):
    """Evidence related to a claim."""

    content: str
    source: str
    relevance: float = 1.0
    stance: str = "supporting"  # supporting, contradicting, neutral
    credibility: float = 1.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

def deduplicate_evidence(evidence_list):
    """Deduplicate evidence list by source and content.
    Args:
        evidence_list (list[Evidence]): The list of evidence to deduplicate.
    Returns:
        list[Evidence]: The deduplicated list of evidence.
    """
    seen = set()
    unique_evidence = []
    for ev in evidence_list:
        key = (ev.source.strip().lower(), ev.content.strip())
        if key not in seen:
            seen.add(key)
            unique_evidence.append(ev)
    return unique_evidence

def get_trust_sources(path: str):
    """Get the trust sources from the file, skipping empty and comment lines.

    Args:
        path (str): The path to the trust sources file.

    Returns:
        list[str]: A list of trust sources.
    """
    p = Path(path)
    if not p.exists():
        logger.warning("Trust sources file not found: %s – returning empty list.", p)
        return []

    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        return [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
    except OSError as e:
        logger.error("Error reading trust sources file %s: %s – returning empty list.", p, e)
        return []
    
class EvidenceHunter:
    """Agent for gathering and evaluating evidence related to factual claims.
    
    This class encapsulates the logic for formulating search queries,
    evaluating source credibility, and collecting diverse evidence
    from trusted and untrusted sources.
    """
    def __init__(
        self,
        trust_sources_path: str = os.path.join(os.path.dirname(__file__), "..", "..", "data", "trust_sources.txt"),
    ):
        """Initialize the evidence hunter with a claim.
        
        Args:
            trust_sources_path (str): The path to the trust sources file.
        """
        self.trust_sources = get_trust_sources(trust_sources_path)

        PROMPT = self.get_prompt(self.trust_sources)

        # Use provided search tools, create multiple search tools, or use default WebSearchTool

        tools = [WebSearchTool()]

        self.evidence_hunter_agent = Agent(
            name="EvidenceHunter",
            instructions=PROMPT,
            output_type=list[Evidence],
            tools=tools,
            model=os.getenv("EVIDENCE_HUNTER_MODEL"),
        )

    def get_claim_requirements(self, trust_sources: list[str]):
        """Get the requirements for processing each claim.
        
        Args:
            trust_sources (list[str]): The list of trusted sources.

        Returns:
            str: The requirements for claim processing.
        """
        return f"""
            For each claim:
            1. Formulate effective search queries that will find relevant information
                - Extract key entities and concepts
                - Create multiple queries to find different perspectives
                - Consider queries that might find contradicting evidence

            2. Evaluate search results carefully:
                - Use different search tools if needed. Especially when:
                    - The search engine is not working
                    - The search engine is not returning relevant results
                    - The search engine is not returning any results
                    - The search engine is returning a lot of spam or low-quality results
                - Determine source credibility (news organizations, academic sources, government sites are typically more reliable)
                - Consider the trusted sources in the list: {", ".join(trust_sources)}
                - Assess relevance to the specific claim
                - Identify the stance (supporting, contradicting, or neutral)
                - Extract specific passages that directly address the claim
        """

    def get_evidence_requirements(self):
        """Get the requirements for evidence collection and diversity.
        
        Returns:
            str: The requirements for evidence collection.
        """
        return """
            3. Return a comprehensive set of evidence:
                - For each evidence object:
                    - Only include evidence that directly and explicitly addresses the claim. Do not include evidence that is only tangentially related or discusses broader or different topics.
                    - Only return one piece of evidence per source
                    - Do not combine, summarize, or further process information from multiple sources.
                    - The content must be a direct quote or close paraphrase taken from the website, without any additional explanation or synthesis.
                - Include supporting, neutral, and contradicting evidence when available
                - Include multiple evidences on different aspects of the claim
                - Rank evidence by relevance and credibility (0.0-1.0 scale)
                - Provide full source information for citation
                - Include stance classification for each piece of evidence

            4. If possible, ensure the DIVERSITY of the evidence:
                - Include evidence from different types of sources (e.g., news, academic, government, reputable websites)
                - Include evidence from different perspectives, not just supporting but also contradicting, neutral, or exception cases
                - If no contradicting evidence is found, look for alternative explanations, exceptions, or cases where the claim does not hold
                - If possible, include evidence from different time periods or under different conditions

            Your responsibilities:
            1. Focus on facts and evidence, not opinions
            2. Find evidence from credible sources that:
                - supports the claim
                - contradicts the claim
                - is neutral to the claim
                - Exceptions to the claim
                - Alternative explanations for the claim
                - Alternative explanations against the claim
                - Cases where the claim does not hold
                You don't need to find all of these, but try to find as many as possible.
            3. Find multiple sources when possible to corroborate information
            4. If no contradicting evidence is found, look for alternative explanations, exceptions, or cases where the claim does not hold
            5. Identify contradictions or nuances in the evidence
            6. Evaluate source credibility and provide higher relevance to more credible sources
        """

    def get_output_requirements(self):
        """Get the requirements for evidence output format.
        
        Returns:
            str: The requirements for evidence output format.
        """
        return """
            For each evidence piece, provide:
            - content: A direct quote or close paraphrase from a single source that addresses the claim. Do not combine content from multiple sources or add your own explanation.
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
                - When evaluating the stance of a piece of evidence with respect to a claim, you must strictly check every factual aspect of the claim against the evidence. Do not only look for partial matches or keywords—carefully verify if the evidence fully supports, contradicts, or is neutral to the claim.

                    - If the evidence clearly states the opposite of the claim, or provides information that directly conflicts with any key part of the claim, classify the stance as "contradicting".
                    - If the evidence fully supports all factual aspects of the claim, classify as "supporting".
                    - If the evidence is related but does not clearly support or contradict the claim, classify as "neutral".

            - credibility: 
                - A score from 0.0 to 1.0 indicating the credibility of the source
                - If the source is in the list of trusted sources, set the credibility close to 1.0
                - If the timestamp of the evidence is older than 10 years, set the credibility close to 0.0

            - timestamp: The timestamp of the evidence

            Do not return multiple pieces of evidence that are essentially the same in content or from the same source.
        """

    def get_prompt(self, trust_sources: list[str]):
        """Get the prompt for the evidence hunter.
        
        Args:
            trust_sources (list[str]): The list of trusted sources.
        """
        claim_reqs = self.get_claim_requirements(trust_sources)
        evidence_reqs = self.get_evidence_requirements()
        output_reqs = self.get_output_requirements()

        PROMPT = f"""
            You are an evidence gathering agent tasked with finding and evaluating evidence related to factual claims.

            {claim_reqs}

            {evidence_reqs}

            {output_reqs}
        """
        return PROMPT

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

        Search for the evidence that supports, contradicts, or is neutral to the claim from multiple perspectives.
        """
        return query

