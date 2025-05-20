"""
Core claim detection functionality.

This module contains the main ClaimDetector class that coordinates
the claim detection process.
"""

import os
import hashlib
import time
from typing import List, Optional, Dict, Any, Tuple, Set
from openai.agents import Agent, Runner
from openai.agents.tools import WebSearchTool

from src.utils.model_config import ModelManager
from src.utils.logging.structured_logger import get_structured_logger
from src.utils.cache import claim_cache, entity_cache, model_cache
from src.utils.metrics import claim_detector_metrics

from src.agents.claim_detector.models import Claim, Entity, ClaimDomain
from src.agents.claim_detector.entity_extractor import EntityExtractor
from src.agents.claim_detector.domain_classifier import DomainClassifier
from src.agents.claim_detector.utils import (
    normalize_claim_text,
    split_compound_claim,
    calculate_similarity,
    contains_specificity_indicators
)
from src.agents.interfaces import IClaimDetector


class ClaimDetector(IClaimDetector):
    """Agent for detecting factual claims in text."""
    
    def __init__(self, model_name: Optional[str] = None, min_check_worthiness: float = 0.7, max_claims: int = 10):
        """
        Initialize the ClaimDetector agent.
        
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
        
        self.logger.info("Initializing ClaimDetector agent", extra={
            "model_name": model_name,
            "min_check_worthiness": min_check_worthiness,
            "max_claims": max_claims,
            "component": "claim_detector"
        })
        
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
            self.model_manager.fallback_models = [model_name] + self.model_manager.fallback_models[1:]
            self.logger.info(f"Using custom model", extra={"model_name": model_name})
            # Default model is qwen/qwen3-8b:free, which excels at structured output
            if "qwen" in self.model_manager.model_name.lower():
                self.logger.info("Using Qwen model with optimized parameters", extra={
                    "model": "qwen3-8b",
                    "optimization": "structured output",
                    "temperature": 0.1
                })
                # Use lower temperature for more consistent structured output
                self.model_manager.set_parameter("temperature", 0.1)
        else:
            self.logger.info("Using default model", extra={"model_name": self.model_manager.model_name})
        
        # Configure OpenAI for Agent SDK
        self.model_manager.configure_openai_for_agent()
        
        # Create the claim detection agent
        agent_start_time = time.time()
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
            - Can be verified with evidence
            - Make specific, measurable assertions
            - Examples: statistical claims, historical facts, scientific statements
            
            NOT FACTUAL CLAIMS:
            - Personal opinions ("I think pizza is delicious")
            - Subjective judgments ("This is the best movie")
            - Hypotheticals ("If it rains tomorrow...")
            - Pure predictions about future events ("Next year's winner will be...")
            - Questions ("Is climate change real?")
            
            DISTINCTNESS:
            Ensure each claim is distinct and doesn't substantially overlap with other claims. 
            If a statement contains multiple related but distinct claims, separate them.
            
            CHECK-WORTHINESS SCORING:
            Rate claims from 0.0-1.0 based on:
            - Specificity (specificity_score): How specific and measurable the claim is (0.0-1.0)
            - Public interest (public_interest_score): Relevance to public figures/institutions (0.0-1.0)
            - Potential impact (impact_score): Significance of consequences if true/false (0.0-1.0)
            - Overall check_worthiness should be a weighted combination of these factors
            
            RANKING CRITERIA:
            Rank claims in order of importance for fact-checking, considering:
            1. Check-worthiness score (primary factor)
            2. Specificity of the claim (easier to verify)
            3. Domain importance (health/safety claims prioritized)
            4. Public interest value
            5. Potential impact if the claim is true/false
            
            ENTITY EXTRACTION:
            Identify entities such as:
            - People, organizations, locations
            - Dates, times, numbers, statistics, percentages
            - Products, technologies, scientific terms
            
            DOMAIN CLASSIFICATION:
            Assign claims to the most relevant domain:
            - Politics, Economics, Health, Science, Technology
            - Environment, Education, Entertainment, Sports, Other
            
            CLAIM NORMALIZATION:
            - Standardize formatting and phrasing
            - Resolve pronouns to their antecedents
            - Expand abbreviations and acronyms
            - Standardize numerical expressions
            
            COMPOUND CLAIMS:
            If a statement contains multiple verifiable claims, break it down into separate checkable statements.
            
            For each claim, return:
            1. The original claim text
            2. A normalized version of the claim
            3. Check-worthiness score (0.0-1.0)
            4. Specificity score (0.0-1.0)
            5. Public interest score (0.0-1.0)
            6. Impact score (0.0-1.0)
            7. Confidence in detection (0.0-1.0)
            8. Domain classification
            9. Extracted entities with types
            10. Parts of compound claims (if applicable)
            11. Rank (relative to other claims)
            """,
            output_type=List[Claim],
            tools=[WebSearchTool()],
            model=self.model_manager.model_name,
            **self.model_manager.parameters
        )
        
        # Log agent creation time
        agent_creation_time = time.time() - agent_start_time
        self.logger.debug("Created claim detection agent", extra={
            "agent_name": "ClaimDetector",
            "creation_time_seconds": agent_creation_time,
            "model": self.model_manager.model_name
        })
            
        # Create the entity extraction agent for detailed entity analysis
        entity_agent_start_time = time.time()
        self.entity_agent = Agent(
            name="EntityExtractor",
            instructions="""
            You are an entity extraction agent specialized in identifying named entities from factual claims.
            
            For each entity, identify:
            1. The entity text exactly as it appears
            2. The entity type (person, organization, location, date, number, etc.)
            3. A normalized/canonical form of the entity when applicable
            4. Relevance to the claim (0.0-1.0)
            
            Example entity types:
            - PERSON: Names of individual people
            - ORGANIZATION: Companies, agencies, institutions
            - LOCATION: Countries, cities, regions, geographical features
            - DATE: Calendar dates, periods of time
            - TIME: Times of day
            - MONEY: Monetary values, currencies
            - PERCENT: Percentage values
            - NUMBER: Numeric values not falling into another category
            - PRODUCT: Commercial products, objects
            - EVENT: Named events (conferences, wars, sports events)
            - WORK_OF_ART: Titles of books, songs, etc.
            - LAW: Named laws, bills, regulations
            - LANGUAGE: Named languages
            - SCIENTIFIC_TERM: Scientific terms, theories, disciplines
            - MEDICAL_TERM: Medical conditions, treatments, procedures
            
            When extracting entities, look for:
            - Proper nouns with capital letters
            """,
            output_type=List[Entity],
            model=self.model_manager.model_name,
            **self.model_manager.parameters
        )
        
        # Log entity agent creation time
        entity_agent_creation_time = time.time() - entity_agent_start_time
        self.logger.debug("Created entity extraction agent", extra={
            "agent_name": "EntityExtractor",
            "creation_time_seconds": entity_agent_creation_time,
            "model": self.model_manager.model_name
        })
        
    async def detect_claims(self, text: str, min_check_worthiness: Optional[float] = None, 
                           expected_claims: Optional[List[Dict[str, Any]]] = None,
                           max_claims: Optional[int] = None) -> List[Claim]:
        """
        Detect claims in the given text.
        
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
        self.logger.info("Starting claim detection", extra={
            "text_length": len(text),
            "operation_id": operation_id,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "text_snippet": text[:100] + "..." if len(text) > 100 else text
        })
        
        # Use instance defaults if not overridden
        min_worthiness = min_check_worthiness if min_check_worthiness is not None else self.min_check_worthiness
        max_claim_count = max_claims if max_claims is not None else self.max_claims
        
        # Check if this exact text has been processed before
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cached_claims = self.claim_cache.get(text_hash)
        
        if cached_claims:
            self.logger.info("Retrieved claims from cache", extra={
                "cache_hit": True,
                "text_hash": text_hash,
                "claim_count": len(cached_claims)
            })
            return cached_claims
            
        try:
            # Create a runner for the agent
            runner = Runner(agent=self.agent)
            
            # Run the agent with the text
            agent_start_time = time.time()
            response = await runner.run(text)
            agent_processing_time = time.time() - agent_start_time
            
            # Extract claims from the response
            if response and isinstance(response, list):
                claims = response
                self.logger.info("Claims detected successfully", extra={
                    "claim_count": len(claims),
                    "agent_processing_time_ms": int(agent_processing_time * 1000)
                })
            else:
                self.logger.warning("Unexpected response format from agent", extra={
                    "response_type": type(response).__name__
                })
                claims = []
                
            # Filter claims by check-worthiness
            if min_worthiness > 0:
                original_count = len(claims)
                claims = [c for c in claims if c.check_worthiness >= min_worthiness]
                self.logger.debug("Filtered claims by check-worthiness", extra={
                    "original_count": original_count,
                    "filtered_count": len(claims),
                    "min_check_worthiness": min_worthiness
                })
                
            # Enhance claims with additional entity information
            for claim in claims:
                claim = await self._enhance_claim_entities(claim)
                
            # Rank and limit claims
            claims = self.rank_claims(claims)
            
            # Limit to max_claims
            if max_claim_count > 0 and len(claims) > max_claim_count:
                claims = claims[:max_claim_count]
                self.logger.debug("Limited claims to maximum count", extra={
                    "max_claims": max_claim_count,
                    "returned_claims": len(claims)
                })
                
            # Cache the results
            self.claim_cache.set(text_hash, claims)
            
            total_processing_time = time.time() - start_time
            self.logger.info("Claim detection completed", extra={
                "processing_time_ms": int(total_processing_time * 1000),
                "claims_found": len(claims),
                "text_length": len(text)
            })
            
            return claims
                
        except Exception as e:
            self.logger.exception("Error in claim detection", extra={
                "error_type": type(e).__name__,
                "text_length": len(text)
            })
            raise
            
    async def _enhance_claim_entities(self, claim: Claim) -> Claim:
        """Enhance a claim with detailed entity information."""
        start_time = time.time()
        
        # Skip if claim already has detailed entities
        if claim.entities and len(claim.entities) > 0 and hasattr(claim.entities[0], 'relevance'):
            return claim
            
        try:
            # Create a runner for the entity agent
            runner = Runner(agent=self.entity_agent)
            
            # Check cache first
            cache_key = hashlib.md5(claim.text.encode()).hexdigest()
            cached_entities = self.entity_cache.get(cache_key)
            
            if cached_entities:
                self.logger.debug("Retrieved entities from cache", extra={
                    "claim_text": claim.text[:50] + "..." if len(claim.text) > 50 else claim.text,
                    "entity_count": len(cached_entities)
                })
                claim.entities = cached_entities
                return claim
                
            # Run entity extraction
            response = await runner.run(claim.text)
            
            if response and isinstance(response, list):
                claim.entities = response
                
                # Cache the entities
                self.entity_cache.set(cache_key, claim.entities)
                
                processing_time = time.time() - start_time
                self.logger.debug("Enhanced claim with entities", extra={
                    "claim_text": claim.text[:50] + "..." if len(claim.text) > 50 else claim.text,
                    "entity_count": len(claim.entities),
                    "processing_time_ms": int(processing_time * 1000)
                })
            else:
                self.logger.warning("Unexpected entity extraction response", extra={
                    "response_type": type(response).__name__,
                    "claim_text": claim.text[:50] + "..." if len(claim.text) > 50 else claim.text
                })
                
            return claim
                
        except Exception as e:
            self.logger.exception("Error enhancing claim entities", extra={
                "error_type": type(e).__name__,
                "claim_text": claim.text[:50] + "..." if len(claim.text) > 50 else claim.text
            })
            # Return original claim if enhancement fails
            return claim

    def rank_claims(self, claims: List[Claim]) -> List[Claim]:
        """
        Rank claims by importance for fact-checking.
        
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
            if hasattr(claim, 'specificity_score') and claim.specificity_score is not None:
                score += claim.specificity_score * 0.2
            elif contains_specificity_indicators(claim.text):
                score += 0.15
                
            # Add domain importance component
            if claim.domain in [ClaimDomain.HEALTH, ClaimDomain.SCIENCE]:
                score += 0.1
            elif claim.domain in [ClaimDomain.POLITICS, ClaimDomain.ECONOMICS]:
                score += 0.08
                
            # Add impact component
            if hasattr(claim, 'impact_score') and claim.impact_score is not None:
                score += claim.impact_score * 0.1
                
            return score
            
        # Sort claims by importance score
        ranked_claims = sorted(claims, key=claim_importance_score, reverse=True)
        
        # Set rank property based on sorted position
        for i, claim in enumerate(ranked_claims):
            claim.rank = i + 1
            
        self.logger.debug("Claims ranked by importance", extra={
            "claim_count": len(ranked_claims)
        })
            
        return ranked_claims
        
    def get_performance_metrics(self, 
                          metric_name: Optional[str] = None, 
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for the claim detector.
        
        Args:
            metric_name: Optional name of specific metric to retrieve
            start_time: Optional start time for time-bounded metrics
            end_time: Optional end time for time-bounded metrics
            
        Returns:
            Dict[str, Any]: Performance metrics
        """
        return self.metrics.get_metrics(metric_name, start_time, end_time) 