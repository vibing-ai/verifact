"""Evidence hunter agent that searches for evidence to support or refute claims."""

import logging
import os
from datetime import datetime
from pathlib import Path

from agents import Agent, WebSearchTool
from pydantic import BaseModel, Field

from utils.search.search_tools import get_search_tools
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

def deduplicate_evidence(evidence_list: list[Evidence]) -> list[Evidence]:
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
    """Evidence hunter agent that searches for evidence to support or refute claims."""

    def __init__(self, trust_sources_path: str = "data/trust_sources.txt", search_tools: list[str] = None):
        """Initialize the evidence hunter.
        
        Args:
            trust_sources_path (str): Path to the trusted sources file.
            search_tools (list[str]): List of search tools to use.
        """
        self.trust_sources = get_trust_sources(trust_sources_path)
        self.use_serper = os.getenv("USE_SERPER", "false").lower() == "true"

        PROMPT = self.get_prompt(self.trust_sources)

        tools = get_search_tools(search_tools)
        if not tools:
            logger.warning("No search tools available, using default WebSearchTool")
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
        if self.use_serper:
            return f"""
                For each claim:
                1. Formulate ONE effective search query
                    - Extract the most important key entities and concepts
                    - Create a focused query targeting fact-checking sources
                    - Aim for authoritative and direct evidence

                2. Evaluate search results carefully:
                    - Determine source credibility (prioritize fact-checking sites, news organizations, academic sources)
                    - Consider the trusted sources in the list: {", ".join(trust_sources)}
                    - Assess relevance to the specific claim
                    - Identify the stance (supporting, contradicting, or neutral)
                    - Extract specific passages that directly address the claim
                    - Process ALL results from a SINGLE search
            """
        else:
            return f"""
                For each claim:
                1. Formulate effective search queries that will find relevant information
                    - Extract key entities and concepts
                    - Create multiple queries to find different perspectives
                    - Consider queries that might find contradicting evidence

                2. Evaluate search results carefully:
                    - Determine source credibility (news organizations, academic sources, government sites are typically more reliable)
                    - Consider the trusted sources in the list: {", ".join(trust_sources)}
                    - Assess relevance to the specific claim
                    - Identify the stance (supporting, contradicting, or neutral)
                    - Extract specific passages that directly address the claim
            """

    def get_tool_requirements(self):
        """Get the requirements for using different search tools and formatting their results.
        
        Returns:
            str: The requirements for tool usage and result formatting.
        """

        if self.use_serper:
            return self._get_serper_tool_requirements()
        
        return self._get_diversity_tool_requirements()
    
    def _get_diversity_tool_requirements(self):
        return """
            - Search tool usage requirements (Diversity Mode):
                - Make comprehensive search queries to gather diverse perspectives
                - Aim for 3-4 results from different viewpoints
                - Include both supporting and contradicting evidence when available
                - Consider multiple aspects of the claim
                - Balance between authoritative and diverse sources

                Evidence output format example:
                [
                {
                    "content": "...",        // Use the 'snippet' field from the search result
                    "source": "...",         // Use the 'url' field from the search result
                    "relevance": 1.0,        // How directly it addresses the claim
                    "stance": "supporting",  // supporting, contradicting, or neutral
                    "credibility": 1.0,      // Based on source reputation
                    "timestamp": "..."       // Current time or date from result
                }
                ]

            - IMPORTANT:
                - Gather diverse perspectives
                - Include different types of sources
                - Balance between supporting and contradicting evidence
            """

    def _get_serper_tool_requirements(self):
        return """
            You have a maximum of 5 search attempts.
            - Search tool usage requirements (Efficiency Mode):
                - Make ONE precise search query
                - Aim for 2-3 high-quality, highly relevant results
                - Focus on fact-checking and authoritative sources
                - Do not make multiple searches
                - Focus on precision over coverage

                Evidence output format example:
                [
                {
                    "content": "...",        // Use the 'snippet' field from the search result
                    "source": "...",         // Use the 'url' field from the search result
                    "relevance": 1.0,        // How directly it addresses the claim
                    "stance": "supporting",  // supporting, contradicting, or neutral
                    "credibility": 1.0,      // Based on source reputation
                    "timestamp": "..."       // Current time or date from result
                }
                ]

            - IMPORTANT: 
                - Make only ONE search call
                - Return only the most relevant results
                - Prefer quality over quantity
            """

    def get_evidence_requirements(self):
        """Get the requirements for evidence collection and diversity.
        
        Returns:
            str: The requirements for evidence collection.
        """
        return """
            3. Return a comprehensive set of evidence:
                - For each evidence object:
                    - Only include evidence that directly and explicitly addresses the claim
                    - Only return one piece of evidence per source
                    - Do not combine or summarize information from multiple sources
                    - The content must be a direct quote or close paraphrase
                - Include supporting, neutral, and contradicting evidence when available
                - Rank evidence by relevance and credibility (0.0-1.0 scale)
                - Provide full source information for citation
                - Include stance classification for each piece of evidence

            4. Search efficiency requirements (IMPORTANT):
                - Make the FIRST search query count - formulate it to get the most relevant results
                - If you get good results from the first search, do not perform additional searches
                - Only perform a second search if the first results are completely irrelevant or insufficient
                - Never perform more than two searches total per claim
                - If you can't find good evidence after two searches, return whatever evidence you have
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
                    - If there's important information mismatch like numbers, dates, names, etc., classify as "contradicting".

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
        tool_reqs = self.get_tool_requirements()
        evidence_reqs = self.get_evidence_requirements()
        output_reqs = self.get_output_requirements()

        PROMPT = f"""
            You are an evidence gathering agent tasked with finding and evaluating evidence related to factual claims.

            {claim_reqs}

            {tool_reqs}

            {evidence_reqs}

            {output_reqs}

            After you receive search results from any tool, IMMEDIATELY process all results and output a list of Evidence objects. 
            DO NOT call the search tool again unless the results are completely empty or obviously irrelevant.
            DO NOT reflect, summarize, or ask for more information.
            ALWAYS output a list of Evidence objects in the required format, one for each relevant search result.
            If you receive multiple search results, process ALL of them in one step and output the full Evidence list at once.
            Do not split the output or call the tool again unless you received no results.
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
        claim_context = str(context) if context != 0.0 else "No additional context provided"
        
        if self.use_serper:
            
            query = f"""Claim to investigate: "{claim.text}" 
            Context of the claim: {claim_context}

            Instructions:
            - Make ONE precise search to find direct evidence
            - Focus on fact-checking sources and authoritative content
            - Look for explicit statements addressing the claim
            - Return only the most relevant results
            - Do not make additional searches
            """
        else:
            query = f"""Claim to investigate: {claim.text}

            Context of the claim: {claim_context}

            Instructions:
            - Search for diverse perspectives on this claim
            - Look for both supporting and contradicting evidence
            - Consider different aspects and interpretations
            - Include various types of reliable sources
            - Balance between different viewpoints
            """
        
        return query

