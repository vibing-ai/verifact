"""Claim detection rules and patterns for VeriFact.

This module defines the rules, patterns, and scoring configurations
used for identifying and evaluating factual claims.
"""


import re
from dataclasses import dataclass

@dataclass
class ClaimRule:
    """Represents a rule for claim detection."""
    pattern: str
    domain: str
    min_specificity: float
    min_public_interest: float
    min_impact: float
    # weight: float = 1.0

class ClaimRules:
    """Collection of rules and patterns for claim detection."""

    SCORING_RULES = {
    "factual_indicators": [
        # Match actual numbers and percentages
        (re.compile(r'\d+(?:\.\d+)?%?'), 0.8),  # Matches numbers and percentages
        # Match date formats
        (re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}'), 0.7),  # Matches dates
        # Match study references
        (re.compile(r'(?:according to|based on|study|research|paper|journal|published|found|shows|indicates|demonstrates|concludes)', re.IGNORECASE), 0.7),
        # Match named entities (basic pattern)
        (re.compile(r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'), 0.6),  # Matches capitalized phrases
        # Common factual verbs
        (re.compile(r'\b(?:is|are|was|were|has|have|had|contains|includes)\b', re.IGNORECASE), 0.6),
    ],
    "opinion_indicators": [
        # Personal opinion markers
        (re.compile(r'\b(?:i think|in my opinion|i believe|i feel|in my view|from my perspective)\b', re.IGNORECASE), -0.5),
        # Speculative markers
        (re.compile(r'\b(?:should|would|could|might|possibly|perhaps|maybe)\b', re.IGNORECASE), -0.4),
        # Subjective markers
        (re.compile(r'\b(?:seems|appears|looks like|feels like|sounds like)\b', re.IGNORECASE), -0.3),
    ],
    "exclusion_patterns": [
        re.compile(r'^\s*(?:i think|in my opinion|i believe|i feel)\b', re.IGNORECASE),
        re.compile(r'\?$'),
        re.compile(r'^\s*(?:should|would|could)\b', re.IGNORECASE),
    ]
}

    @classmethod
    def get_default_rules(cls) -> list[ClaimRule]:
        """Get the default set of claim detection rules."""
        return [
            ClaimRule(
                pattern=re.compile(r"\d+%"),
                domain="statistics",
                min_specificity=0.8,
                min_public_interest=0.5,
                min_impact=0.6
            ),
            ClaimRule(
                pattern=re.compile(r"according to (?:the|a) study"),
                domain="science",
                min_specificity=0.7,
                min_public_interest=0.6,
                min_impact=0.5
            ),
            ClaimRule(
                pattern=re.compile(r"research shows"),
                domain="science",
                min_specificity=0.7,
                min_public_interest=0.6,
                min_impact=0.5
            ),
            ClaimRule(
                pattern=re.compile(r"has been proven"),
                domain="science",
                min_specificity=0.8,
                min_public_interest=0.7,
                min_impact=0.6
            ),

            # Domain-specific rules
            ClaimRule(
                pattern=re.compile(r"sky|weather|climate|atmosphere", re.IGNORECASE),
                domain="nature",
                min_specificity=0.7,
                min_public_interest=0.6,
                min_impact=0.5
            ),
            ClaimRule(
                pattern=re.compile(r"earth|planet|world", re.IGNORECASE),
                domain="nature",
                min_specificity=0.7,
                min_public_interest=0.6,
                min_impact=0.5
            ),
            ClaimRule(
                pattern=re.compile(r"health|medical|disease", re.IGNORECASE),
                domain="health",
                min_specificity=0.8,
                min_public_interest=0.7,
                min_impact=0.6
            ),
            ClaimRule(
                pattern=re.compile(r"technology|software|hardware", re.IGNORECASE),
                domain="technology",
                min_specificity=0.7,
                min_public_interest=0.6,
                min_impact=0.5
            ),
            ClaimRule(
                pattern=re.compile(r"is|are|was|were", re.IGNORECASE),
                domain="general",
                min_specificity=0.6,
                min_public_interest=0.5,
                min_impact=0.5
            ),
            ClaimRule(
                pattern=re.compile(r"has|have|had"),
                domain="general",
                min_specificity=0.6,
                min_public_interest=0.5,
                min_impact=0.5
            ),
        ]
def _calculate_specificity_from_indicators(text: str) -> float:
    """Calculate specificity score based on factual and opinion indicators."""
    specificity = 0.5
    
    # Apply factual indicators
    for indicator, score in ClaimRules.SCORING_RULES["factual_indicators"]:
        if re.search(indicator, text.lower()):
            specificity = max(specificity, score)
    
    # Apply opinion indicators
    for indicator, score in ClaimRules.SCORING_RULES["opinion_indicators"]:
        if re.search(indicator, text.lower()):
            specificity = max(0.0, specificity + score)
    
    return specificity

def _calculate_domain_scores(text: str, domain: str) -> tuple[float, float, float]:
    """Calculate domain-specific scores."""
    specificity = 0.5
    public_interest = 0.5
    impact = 0.5
    
    for rule in ClaimRules.get_default_rules():
        if rule.domain == domain and re.search(rule.pattern, text.lower()):
            specificity = max(specificity, rule.min_specificity)
            public_interest = max(public_interest, rule.min_public_interest)
            impact = max(impact, rule.min_impact)
    
    return specificity, public_interest, impact

def _check_exclusion_patterns(text: str) -> bool:
    """Check if text matches any exclusion patterns."""
    return any(re.search(pattern, text.lower()) for pattern in ClaimRules.SCORING_RULES["exclusion_patterns"])

def calculate_scores(text: str, domain: str) -> tuple[float, float, float, float]:
    """Calculate various scores for a claim using ClaimRules."""
    # Calculate base scores
    specificity = _calculate_specificity_from_indicators(text)
    
    # Apply domain-specific rules
    domain_specificity, public_interest, impact = _calculate_domain_scores(text, domain)
    specificity = max(specificity, domain_specificity)
    
    # Check exclusion patterns
    if _check_exclusion_patterns(text):
        specificity = 0.0
    
    # Calculate check-worthiness as weighted average
    check_worthiness = specificity * 0.4 + public_interest * 0.3 + impact * 0.3
    
    return specificity, public_interest, impact, check_worthiness
