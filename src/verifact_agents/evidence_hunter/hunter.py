"""Evidence Hunter agent for gathering evidence for claims.

This module is responsible for searching and evaluating evidence
related to factual claims.
"""

import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

# Check if we're trying to import the local agents module
try:
    # Try to import agents
    import agents
    # Check if it's the local module or the OpenAI one
    if hasattr(agents, 'IS_LOCAL_AGENTS_MODULE'):
        print("WARNING: Detected local agents module instead of OpenAI Agents SDK!")
        # Remove current directory from path to force using site-packages
        current_dir = sys.path[0]
        sys.path.remove(current_dir)
        # Clear the module from sys.modules to force reload
        if 'agents' in sys.modules:
            del sys.modules['agents']
        # Try importing again
        import agents
    print(f"Using agents module from: {agents.__file__}")
    from agents import Agent, Runner
except ImportError as e:
    print(f"Error importing agents: {e}")
    print(f"Python path: {sys.path}")
    raise

from pydantic import BaseModel

from src.verifact_agents.claim_detector.models import Claim
from src.verifact_agents.interfaces import IEvidenceHunter
from src.utils.cache.cache import evidence_cache
from src.utils.logger import get_component_logger
from src.utils.model_config import ModelManager
from src.utils.search.search_tools import get_search_tool

# Create a logger for this module
logger = get_component_logger("evidence_hunter")

# Constants for caching
DEFAULT_CACHE_TTL = int(os.environ.get("EVIDENCE_CACHE_TTL", 86400))  # 24 hours in seconds


class Evidence(BaseModel):
    """Evidence related to a claim."""

    content: str
    source: str
    relevance: float = 1.0
    stance: str = "supporting"  # supporting, contradicting, neutral


class EvidenceHunter(IEvidenceHunter):
    """Agent for gathering evidence for claims."""

    def __init__(self, model_name: str | None = None):
        """Initialize the EvidenceHunter agent.

        Args:
            model_name: Optional name of the model to use
        """
        # Create a ModelManager instance for this agent
        self.model_manager = ModelManager(agent_type="evidence_hunter")

        # Override the model name if explicitly provided
        if model_name:
            self.model_manager.model_name = model_name
            # Rebuild fallback chain with new primary model
            self.model_manager.fallback_models = [model_name] + self.model_manager.fallback_models[
                1:
            ]

        # Configure OpenAI for Agent SDK
        self.model_manager.configure_openai_for_agent()

        # Log model being used - default is google/gemma-3-27b-it:free which has 128k context
        logger.info(f"Using model: {self.model_manager.model_name} for evidence gathering")
        logger.info(
            "Gemma 3-27b-it provides 128k context window for processing large amounts of evidence"
        )

        # Get the search tool (WebSearchTool or SerperSearchTool based on configuration)
        search_tool = get_search_tool()

        # Create the agent with enhanced instructions for better evidence gathering
        self.agent = Agent(
            name="EvidenceHunter",
            instructions="""
            You are an evidence gathering agent tasked with finding and evaluating evidence related to factual claims.

            For each claim:
            1. Formulate effective search queries that will find relevant information
               - Extract key entities and concepts
                             - Create multiple queries to find different perspectives
              - Consider queries that might find contradicting evidence

            2. Evaluate search results carefully:
               - Determine source credibility (news organizations, academic sources, government sites are typically more reliable)
               - Assess relevance to the specific claim
               - Identify the stance (supporting, contradicting, or neutral)
               - Extract specific passages that directly address the claim

            3. Return a comprehensive set of evidence:
               - Include both supporting and contradicting evidence when available
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
            - relevance: A score from 0.0 to 1.0 indicating how relevant this evidence is to the claim
            - stance: "supporting", "contradicting", or "neutral" based on how the evidence relates to the claim
            """,
            output_type=list[Evidence],
            tools=[search_tool],
            model=self.model_manager.model_name,
            **self.model_manager.parameters,
        )

    async def gather_evidence(self, claim: Claim) -> list[Evidence]:
        """Gather evidence for the provided claim.

        Args:
            claim: The claim to gather evidence for

        Returns:
            List[Evidence]: A list of evidence pieces
        """
        # Check cache first
        cache_key = self._generate_cache_key(claim)
        cached_evidence = self._get_from_cache(cache_key)

        # If we have cached evidence, return it
        if cached_evidence:
            logger.info(f"Cache hit for claim: {claim.text[:50]}...")
            return cached_evidence

        logger.info(f"Cache miss for claim: {claim.text[:50]}...")

        # Create a rich query with context and guidance for better search results
        query = f"""
        Claim to investigate: {claim.text}

        Context of the claim: {claim.context if hasattr(claim, "context") and claim.context else "No additional context provided"}

        Your task:
        1. Find evidence from credible sources that either supports or contradicts this claim
        2. Search for multiple perspectives and authoritative sources
        3. Evaluate the reliability and relevance of each source
        4. Collect both supporting and contradicting evidence when available

        Return a comprehensive set of evidence pieces in the required format.
        """

        logger.info(f"Gathering evidence for claim: {claim.text[:50]}...")

        start_time = time.time()

        # Run the agent with the enhanced query
        result = await Runner.run(self.agent, query)

        # Update token usage tracking
        if hasattr(result, "usage") and result.usage:
            self.model_manager._update_token_usage({"usage": result.usage})

        # Log evidence gathering results
        evidence_count = len(result.output) if result.output else 0
        logger.info(f"Found {evidence_count} evidence pieces for claim")

        # Calculate and log execution time
        execution_time = time.time() - start_time
        logger.info(f"Evidence gathering completed in {execution_time:.2f} seconds")

        # Cache the results
        if result.output:
            self._store_in_cache(cache_key, result.output)

        return result.output

    def _generate_cache_key(self, claim: Claim) -> str:
        """Generate a deterministic cache key from a claim.

        Normalize text by lowercasing, removing punctuation, and stemming.

        Args:
            claim: The claim to generate a cache key for

        Returns:
            str: A normalized cache key
        """
        # Normalize the claim text
        # - Convert to lowercase
        # - Remove punctuation
        # - Remove extra whitespace
        normalized_text = claim.text.lower()
        normalized_text = re.sub(r"[^\w\s]", "", normalized_text)
        normalized_text = re.sub(r"\s+", " ", normalized_text).strip()

        # Create a hash of the normalized text
        return f"evidence:{hashlib.md5(normalized_text.encode('utf-8')).hexdigest()}"

    def _get_from_cache(self, key: str) -> list[Evidence] | None:
        """Retrieve evidence from Redis cache if available.

        Returns None if cache miss.

        Args:
            key: The cache key to retrieve

        Returns:
            Optional[List[Evidence]]: List of evidence or None if not found
        """
        start_time = time.time()

        try:
            cached_data = evidence_cache.get(key)

            if cached_data:
                evidence_list = json.loads(cached_data)
                result = [Evidence(**item) for item in evidence_list]
                logger.debug(f"Cache hit for {key}")

                # Update cache metrics
                execution_time = time.time() - start_time
                logger.debug(f"Cache retrieval completed in {execution_time:.4f} seconds")

                return result

        except Exception as e:
            logger.warning(f"Error retrieving from cache: {str(e)}")

        return None

    def _store_in_cache(
        self, key: str, evidence: list[Evidence], ttl: int = DEFAULT_CACHE_TTL
    ) -> None:
        """Store evidence in Redis cache with the given TTL.

        Args:
            key: The cache key
            evidence: The evidence to store
            ttl: Time-to-live in seconds
        """
        try:
            # Convert to serializable format
            serializable_evidence = [e.dict() for e in evidence]

            # Store in cache
            evidence_cache.set(key, json.dumps(serializable_evidence), ex=ttl)
            logger.debug(f"Stored evidence in cache with key {key}, TTL={ttl}s")

        except Exception as e:
            logger.warning(f"Error storing in cache: {str(e)}")
