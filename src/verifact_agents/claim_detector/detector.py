"""Core claim detection functionality.

This module contains the main ClaimDetector class that coordinates
the claim detection process.
"""

import hashlib
import importlib.util
import sys
import time
from typing import Any, Dict, List, Optional

# Attempt to import OpenAI agents with multiple fallback options
try:
    # First try import from openai-agents package
    from openai.agents import Agent, Runner, WebSearchTool, ModelSettings
    print("Successfully imported openai.agents from openai-agents package")
except ImportError:
    try:
        # Try importing directly if available
        import openai.agents
        from openai.agents import Agent, Runner, WebSearchTool, ModelSettings
        print(f"Successfully imported openai.agents directly")
    except ImportError:
        try:
            # Try to import from standalone agents package if available
            from agents import Agent, Runner, WebSearchTool, ModelSettings
            print(f"Using agents module from: {sys.modules['agents'].__file__}")
        except ImportError as e:
            # Set defaults to None and handle missing dependencies gracefully
            print(f"WARNING: Could not import OpenAI agents - some functionality will be limited: {e}")
            Agent = Runner = WebSearchTool = ModelSettings = None

from src.verifact_agents.claim_detector.domain_classifier import DomainClassifier
from src.verifact_agents.claim_detector.entity_extractor import EntityExtractor
from src.verifact_agents.claim_detector.models import Claim, ClaimDomain, Entity, EntityType
from src.verifact_agents.claim_detector.utils import (
    contains_specificity_indicators,
)
from src.verifact_agents.interfaces import IClaimDetector
from src.utils.cache import claim_cache, entity_cache, model_cache
from src.utils.logging.structured_logger import get_structured_logger
from src.utils.metrics import claim_detector_metrics
from src.utils.model_config import ModelManager


class DetectionError(Exception):
    """Exception raised when claim detection fails."""
    pass


class ClaimDetector(IClaimDetector):
    """Agent for detecting factual claims in text."""

    def __init__(
        self,
        model_name: str | None = None,
        min_check_worthiness: float = 0.7,
        max_claims: int = 10,
    ):
        """Initialize the ClaimDetector agent.

        Args:
            model_name: Optional name of the model to use
            min_check_worthiness: Minimum threshold for considering a claim check-worthy (0-1)
            max_claims: Maximum number of claims to return, ranked by check-worthiness
        """
        # Get component-specific logger
        self.logger = get_structured_logger("verifact.claim_detector")

        # Set component context for logging
        from src.utils.logging.structured_logger import set_component_context

        set_component_context(component="claim_detector", operation="initialize")

        self.logger.info(
            "Initializing ClaimDetector agent",
            extra={
                "model_name": model_name,
                "min_check_worthiness": min_check_worthiness,
                "max_claims": max_claims,
                "component": "claim_detector",
            },
        )
        # Set minimum check-worthiness threshold and max claims
        self.min_check_worthiness = min_check_worthiness
        self.max_claims = max_claims

        # Create a ModelManager instance for this agent
        self.model_manager = ModelManager(agent_type="claim_detector")

        # Cache instances
        self.claim_cache = claim_cache
        self.entity_cache = entity_cache
        self.model_cache = model_cache

        # Metrics tracker
        self.metrics = claim_detector_metrics

        # Initialize helper components
        self.entity_extractor = EntityExtractor(model_name=model_name)
        self.domain_classifier = DomainClassifier()
        # Override the model name if explicitly provided
        if model_name:
            self.model_manager.model_name = model_name
            # Rebuild fallback chain with new primary model
            self.model_manager.fallback_models = [model_name] + self.model_manager.fallback_models[
                1:
            ]
            self.logger.info("Using custom model", extra={"model_name": model_name})
        else:
            self.logger.info(
                "Using default model", extra={"model_name": self.model_manager.model_name}
            )
        # Configure OpenAI for Agent SDK
        self.model_manager.configure_openai_for_agent()

        # Create the claim detection agent
        agent_start_time = time.time()
        
        # Only use supported parameters for Agent creation
        # Filter out model parameters that should be in ModelSettings
        
        # Create ModelSettings with appropriate parameters
        model_settings = ModelSettings(
            temperature=self.model_manager.parameters.get("temperature"),
            top_p=self.model_manager.parameters.get("top_p"),
            frequency_penalty=self.model_manager.parameters.get("frequency_penalty"),
            presence_penalty=self.model_manager.parameters.get("presence_penalty"),
            max_tokens=self.model_manager.parameters.get("max_tokens")
        )
        
        self.agent = Agent(
            name="ClaimDetector",
            instructions="""
            You are a claim detection agent designed to identify factual claims from text that require verification.
            Your task is to:
            1. Identify explicit and implicit factual claims
            2. Score each claim's check-worthiness, specificity, public interest, and impact
            3. Extract and categorize entities mentioned in claims
            4. Classify claims by domain (politics, science, health, etc.)
            5. Normalize claims to a standard format
            6. Split compound claims into separate checkable statements
            7. Rank claims by overall importance for fact-checking

            FACTUAL CLAIMS:
            - Are statements presented as facts
            - Can be verified or falsified with evidence
            - Usually contain specific details, numbers, dates, or causal relationships
            - May be explicit or implicit in the text

            Focus on statements that:
            - Make factual assertions about the world
            - Could influence public opinion or decision-making
            - Contain verifiable information
            - Address matters of public interest
            
            DO NOT identify as claims:
            - Pure opinions without factual components
            - Subjective judgments or preferences
            - Hypothetical scenarios or questions
            - Widely accepted truths that don't need verification
            - Vague statements without specific, checkable content

            OUTPUT FORMAT:
            Return a list of claim objects with these properties:
            - claim_text: The exact text of the claim
            - normalized_text: The claim rewritten as a clear factual statement
            - check_worthiness_score: 1-10 rating of importance to verify (10 is highest)
            - specificity_score: 1-10 rating of how specific the claim is
            - public_interest_score: 1-10 rating of public importance
            - impact_score: 1-10 rating of potential impact if false
            - domain: The primary domain/topic of the claim
            - entities: Array of named entities referenced in the claim
            - evidence_candidates: Array of possible sources or search queries to verify
            """,
            model=self.model_manager.model_name,
            model_settings=ModelSettings(
                temperature=self.model_manager.parameters.get("temperature", 0.0),
                top_p=self.model_manager.parameters.get("top_p", 1.0),
                frequency_penalty=self.model_manager.parameters.get("frequency_penalty", 0.0),
                presence_penalty=self.model_manager.parameters.get("presence_penalty", 0.0),
                max_tokens=self.model_manager.parameters.get("max_tokens", 4000),
            ),
        )

        # Log agent creation time
        agent_creation_time = time.time() - agent_start_time
        self.logger.debug(
            "Created claim detection agent",
            extra={
                "agent_name": "ClaimDetector",
                "creation_time_seconds": agent_creation_time,
                "model": self.model_manager.model_name,
            },
        )

        # Create the entity extraction agent for detailed entity analysis
        entity_agent_start_time = time.time()
        self.entity_agent = Agent(
            name="EntityExtractor",
            instructions="""
            You are an entity extraction agent that analyzes claims to identify and categorize entities.
            Your task is to extract all named entities from a claim and categorize them by type.
            
            ENTITY TYPES:
            - PERSON: Real individuals (e.g., politicians, celebrities, historical figures)
            - ORGANIZATION: Companies, agencies, institutions, and other formal groups
            - LOCATION: Geographic locations, countries, cities, landmarks, regions
            - DATE: Specific dates, time periods, or years
            - NUMBER: Quantities, statistics, percentages, monetary values
            - EVENT: Named events (e.g., elections, wars, conferences, disasters)
            - LAW: Laws, regulations, treaties, agreements, legal doctrines
            - PRODUCT: Commercial products, brands, technologies
            - MEDIA: Books, movies, articles, studies, platforms, publications
            - SCIENTIFIC: Scientific concepts, theories, disciplines, diseases
            - OTHER: Any entity that doesn't fit the above categories
            
            OUTPUT FORMAT:
            For each entity you identify, provide:
            - name: The exact name of the entity as it appears in the text
            - type: The entity type from the list above
            - description: A brief 1-2 sentence description of the entity
            - relevance: 1-10 score of how central the entity is to the claim (10 being highest)
            - disambiguation: Any clarification needed if the entity name is ambiguous
            """,
            model=self.model_manager.model_name,
            model_settings=ModelSettings(
                temperature=self.model_manager.parameters.get("temperature", 0.0),
                top_p=self.model_manager.parameters.get("top_p", 1.0),
                frequency_penalty=self.model_manager.parameters.get("frequency_penalty", 0.0),
                presence_penalty=self.model_manager.parameters.get("presence_penalty", 0.0),
                max_tokens=self.model_manager.parameters.get("max_tokens", 2000),
            ),
        )

        # Log entity agent creation time
        entity_agent_creation_time = time.time() - entity_agent_start_time
        self.logger.debug(
            "Created entity extraction agent",
            extra={
                "agent_name": "EntityExtractor",
                "creation_time_seconds": entity_agent_creation_time,
                "model": self.model_manager.model_name,
            },
        )

    async def detect_claims(
        self,
        text: str,
        min_check_worthiness: float | None = None,
        expected_claims: list[dict[str, Any]] | None = None,
        max_claims: int | None = None,
    ) -> list[Claim]:
        """Detect claims in the given text.

        Args:
            text: The text to analyze for claims
            min_check_worthiness: Optional override for min check-worthiness threshold
            expected_claims: Expected claims for testing/evaluation
            max_claims: Optional override for maximum number of claims to return

        Returns:
            List[Claim]: Detected claims, sorted by importance
        """
        # Set component context for this operation
        from src.utils.logging.structured_logger import set_component_context

        set_component_context(component="claim_detector", operation="detect_claims")

        # Generate operation ID for tracing this specific claim detection
        operation_id = hashlib.md5(f"{text[:100]}-{time.time()}".encode()).hexdigest()[:10]

        start_time = time.time()
        self.logger.info(
            "Starting claim detection",
            extra={
                "text_length": len(text),
                "operation_id": operation_id,
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
                "text_snippet": text[:100] + "..." if len(text) > 100 else text,
            },
        )

        # Use instance defaults if not overridden
        min_worthiness = (
            min_check_worthiness if min_check_worthiness is not None else self.min_check_worthiness
        )
        max_claim_count = max_claims if max_claims is not None else self.max_claims

        # Check if this exact text has been processed before
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cached_claims = self.claim_cache.get(text_hash)

        if cached_claims:
            self.logger.info(
                "Retrieved claims from cache",
                extra={
                    "cache_hit": True,
                    "text_hash": text_hash,
                    "claim_count": len(cached_claims),
                },
            )
            return cached_claims

        try:
            # Create a runner for the agent and run it with the text
            agent_start_time = time.time()
            response = await Runner.run(self.agent, text)
            agent_processing_time = time.time() - agent_start_time

            # Extract claims from the response
            if response and hasattr(response, 'final_output') and response.final_output is not None:
                claims = response.final_output 
                self.logger.info(
                    "Claims detected successfully",
                    extra={
                        "claim_count": len(claims),
                        "agent_processing_time_ms": int(agent_processing_time * 1000),
                    },
                )
            else:
                self.logger.warning(
                    "No claims detected in text", extra={"text_length": len(text)}
                )
                return []

            # Filter claims by check-worthiness
            if min_worthiness > 0:
                original_count = len(claims)
                claims = [c for c in claims if c.check_worthiness >= min_worthiness]
                self.logger.debug(
                    "Filtered claims by check-worthiness",
                    extra={
                        "original_count": original_count,
                        "filtered_count": len(claims),
                        "min_check_worthiness": min_worthiness,
                    },
                )

            # Enhance claims with additional entity information
            for claim in claims:
                claim = await self._enhance_claim_entities(claim)

            # Rank and limit claims
            claims = self.rank_claims(claims)

            # Limit to max_claims
            if max_claim_count > 0 and len(claims) > max_claim_count:
                claims = claims[:max_claim_count]
                self.logger.debug(
                    "Limited claims to maximum count",
                    extra={"max_claims": max_claim_count, "returned_claims": len(claims)},
                )

            # Cache the results
            self.claim_cache.set(text_hash, claims)

            total_processing_time = time.time() - start_time
            self.logger.info(
                "Claim detection completed",
                extra={
                    "processing_time_ms": int(total_processing_time * 1000),
                    "claims_found": len(claims),
                    "text_length": len(text),
                },
            )

            return claims

        except Exception as e:
            self.logger.error("Error in claim detection", exc_info=True)
            raise DetectionError(f"Error detecting claims: {str(e)}") from e

    async def _enhance_claim_entities(self, claim: Claim) -> Claim:
        """Extract and enhance entities in a claim using a specialized entity extraction agent.

        Args:
            claim: The claim to enhance with entity information

        Returns:
            The enhanced claim with detailed entity information
        """
        self.logger.debug(f"Enhancing entities for claim: {claim.claim_text[:50]}...")

        try:
            # Run the entity extraction agent on the claim text
            response = await Runner.run(
                self.entity_agent, 
                f"Extract entities from this claim: {claim.claim_text}"
            )

            # Process the response and update the claim's entities
            if response and hasattr(response, 'final_output') and response.final_output is not None:
                # Update the claim's entities with the enhanced entity information
                claim.entities = response.final_output
                self.logger.info(
                    f"Enhanced claim with {len(claim.entities)} entities",
                    extra={"claim_id": claim.id},
                )
            else:
                self.logger.warning(
                    "Entity extraction returned no results",
                    extra={"claim_id": claim.id},
                )

            return claim

        except Exception as e:
            self.logger.error(
                "Error in entity extraction", 
                extra={"claim_id": claim.id, "error": str(e)},
                exc_info=True
            )
            # Return the original claim if entity extraction fails
            return claim

    def rank_claims(self, claims: list[Claim]) -> list[Claim]:
        """Rank claims by importance for fact-checking.

        Args:
            claims: List of claims to rank

        Returns:
            List[Claim]: Ranked claims
        """
        if not claims:
            return []

        # Define scoring function for ranking
        def claim_importance_score(claim: Claim) -> float:
            # Base score is the check_worthiness
            score = claim.check_worthiness * 0.6

            # Add specificity component
            if hasattr(claim, "specificity_score") and claim.specificity_score is not None:
                score += claim.specificity_score * 0.2
            elif contains_specificity_indicators(claim.text):
                score += 0.15

            # Add domain importance component
            if claim.domain in [ClaimDomain.HEALTH, ClaimDomain.SCIENCE]:
                score += 0.1
            elif claim.domain in [ClaimDomain.POLITICS, ClaimDomain.ECONOMICS]:
                score += 0.08

            # Add impact component
            if hasattr(claim, "impact_score") and claim.impact_score is not None:
                score += claim.impact_score * 0.1

            return score

        # Sort claims by importance score
        ranked_claims = sorted(claims, key=claim_importance_score, reverse=True)

        # Set rank property based on sorted position
        for i, claim in enumerate(ranked_claims):
            claim.rank = i + 1

        self.logger.debug("Claims ranked by importance", extra={"claim_count": len(ranked_claims)})

        return ranked_claims

    def get_performance_metrics(
        self,
        metric_name: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Get performance metrics for the claim detector.

        Args:
            metric_name: Optional name of specific metric to retrieve
            start_time: Optional start time for time-bounded metrics
            end_time: Optional end time for time-bounded metrics

        Returns:
            Dict[str, Any]: Performance metrics
        """
        return self.metrics.get_metrics(metric_name, start_time, end_time)
