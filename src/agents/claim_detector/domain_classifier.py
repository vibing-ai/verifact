"""
Domain classification for the ClaimDetector agent.

This module handles the domain/topic classification of claims.
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set
from openai.agents import Agent

from src.utils.logger import get_component_logger, log_performance
from src.utils.cache import model_cache
from src.agents.claim_detector.models import ClaimDomain


class DomainClassifier:
    """Domain classification functionality for the ClaimDetector."""
    
    def __init__(self):
        """Initialize the DomainClassifier."""
        # Get component-specific logger
        self.logger = get_component_logger("domain_classifier")
        self.logger.debug("Initializing DomainClassifier")
        
        # Model cache
        self.model_cache = model_cache
        
        # Domain keyword dictionaries
        self._domain_keywords = self._initialize_domain_keywords()
    
    def _initialize_domain_keywords(self) -> Dict[ClaimDomain, Set[str]]:
        """
        Initialize keyword sets for each domain.
        
        Returns:
            Dictionary mapping domains to sets of keywords
        """
        return {
            ClaimDomain.POLITICS: {
                "president", "government", "election", "vote", "democrat", "republican", 
                "congress", "senate", "law", "bill", "policy", "politician", "campaign",
                "ballot", "parliament", "legislation", "representative", "mayor", "governor",
                "administration", "constitution", "supreme court", "federal", "state", "local"
            },
            ClaimDomain.ECONOMICS: {
                "economy", "market", "stock", "trade", "finance", "money", "investment",
                "dollar", "euro", "business", "inflation", "recession", "growth", "gdp",
                "debt", "deficit", "budget", "interest rate", "tax", "subsidy", "tariff",
                "economic", "financial", "fiscal", "monetary", "banking", "employment", "unemployment"
            },
            ClaimDomain.HEALTH: {
                "health", "disease", "medicine", "doctor", "hospital", "patient", "vaccine",
                "virus", "pandemic", "epidemic", "treatment", "cure", "symptom", "illness",
                "medical", "diet", "nutrition", "fitness", "mental health", "drug", "pharmaceutical",
                "healthcare", "surgery", "diagnosis", "therapy", "cancer", "diabetes", "heart"
            },
            ClaimDomain.SCIENCE: {
                "science", "scientist", "research", "study", "experiment", "theory", "discovery",
                "physics", "chemistry", "biology", "mathematics", "astronomy", "geology", "data",
                "evidence", "hypothesis", "scientific", "laboratory", "academic", "peer-reviewed",
                "innovation", "technology", "engineering", "space", "quantum", "atom", "molecule"
            },
            ClaimDomain.TECHNOLOGY: {
                "technology", "computer", "software", "hardware", "internet", "web", "app",
                "digital", "artificial intelligence", "ai", "machine learning", "data", "algorithm",
                "programming", "code", "cyber", "security", "hack", "device", "gadget", "smartphone",
                "mobile", "online", "virtual", "automation", "robot", "electronic"
            },
            ClaimDomain.ENVIRONMENT: {
                "environment", "climate", "weather", "global warming", "carbon", "emission",
                "pollution", "renewable", "sustainable", "green", "conservation", "ecosystem",
                "biodiversity", "species", "animal", "plant", "forest", "ocean", "water", "air",
                "energy", "solar", "wind", "fossil fuel", "recycle", "waste", "organic"
            },
            ClaimDomain.EDUCATION: {
                "education", "school", "university", "college", "student", "teacher", "professor",
                "academic", "study", "learn", "teach", "curriculum", "degree", "grade", "class",
                "classroom", "course", "lecture", "exam", "test", "homework", "diploma", "graduation",
                "scholarship", "tuition", "literacy", "knowledge", "educational"
            },
            ClaimDomain.ENTERTAINMENT: {
                "entertainment", "movie", "film", "television", "tv", "show", "series", "music",
                "song", "album", "artist", "actor", "actress", "celebrity", "star", "famous",
                "hollywood", "box office", "concert", "performance", "theater", "stage", "award",
                "oscar", "grammy", "book", "novel", "author", "game", "gaming"
            },
            ClaimDomain.SPORTS: {
                "sport", "game", "team", "player", "coach", "athlete", "competition", "tournament",
                "championship", "league", "soccer", "football", "basketball", "baseball", "tennis",
                "golf", "hockey", "cricket", "rugby", "racing", "swimming", "track", "field",
                "olympic", "medal", "win", "lose", "score", "record", "stadium", "fan"
            }
        }
    
    @log_performance(operation="classify_domain", level="debug")
    def classify_domain(self, claim_text: str) -> Tuple[ClaimDomain, List[str]]:
        """
        Classify a claim into one or more domains.
        
        Args:
            claim_text: The text of the claim to classify
            
        Returns:
            Tuple of (primary domain, list of secondary domains)
        """
        # Check cache first
        cache_key = f"domain:{hash(claim_text)}"
        cached_result = self.model_cache.get(cache_key)
        if cached_result:
            self.logger.debug(f"Cache hit for domain classification: {claim_text[:30]}...")
            return cached_result
        
        # Convert to lowercase for matching
        text = claim_text.lower()
        
        # Count keyword matches for each domain
        domain_scores = {}
        for domain, keywords in self._domain_keywords.items():
            domain_scores[domain] = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    # If the keyword is found, increment the score
                    domain_scores[domain] += 1
        
        # Sort domains by score in descending order
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        
        # The primary domain is the one with the highest score
        primary_domain = sorted_domains[0][0] if sorted_domains[0][1] > 0 else ClaimDomain.OTHER
        
        # Secondary domains are those with a score > 0, excluding the primary
        secondary_domains = [str(domain) for domain, score in sorted_domains[1:] if score > 0]
        
        # Store in cache
        result = (primary_domain, secondary_domains)
        self.model_cache.set(cache_key, result)
        
        return result
    
    def get_domain_keywords(self, domain: ClaimDomain) -> Set[str]:
        """
        Get the keywords associated with a specific domain.
        
        Args:
            domain: The domain to get keywords for
            
        Returns:
            Set of keywords for the domain
        """
        return self._domain_keywords.get(domain, set())
    
    def add_domain_keyword(self, domain: ClaimDomain, keyword: str) -> None:
        """
        Add a new keyword to a domain.
        
        Args:
            domain: The domain to add the keyword to
            keyword: The keyword to add
        """
        if domain in self._domain_keywords:
            self._domain_keywords[domain].add(keyword.lower())
        else:
            self._domain_keywords[domain] = {keyword.lower()} 