"""Claim detection rules and patterns for VeriFact.

This module defines the rules, patterns, and scoring configurations
used for identifying and evaluating factual claims.
"""

from dataclasses import dataclass
from typing import Dict, List
import re

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
        (re.compile(r"specific numbers", re.IGNORECASE), 0.8),
        (re.compile(r"dates", re.IGNORECASE), 0.7),
        (re.compile(r"percentages", re.IGNORECASE), 0.8),
        (re.compile(r"study references", re.IGNORECASE), 0.7),
        (re.compile(r"named entities", re.IGNORECASE), 0.6),
        (re.compile(r"is|are|was|were", re.IGNORECASE), 0.6),
        (re.compile(r"has|have|had", re.IGNORECASE), 0.6),
        (re.compile(r"contains|includes", re.IGNORECASE), 0.6),
    ],
    "opinion_indicators": [
        (re.compile(r"i think", re.IGNORECASE), -0.5),
        (re.compile(r"in my opinion", re.IGNORECASE), -0.5),
        (re.compile(r"should", re.IGNORECASE), -0.3),
        (re.compile(r"would", re.IGNORECASE), -0.3),
        (re.compile(r"might", re.IGNORECASE), -0.4),
        (re.compile(r"i believe", re.IGNORECASE), -0.5),
        (re.compile(r"i feel", re.IGNORECASE), -0.5),
        (re.compile(r"possibly", re.IGNORECASE), -0.4),
    ],
    "exclusion_patterns": [
        re.compile(r"^i think", re.IGNORECASE),
        re.compile(r"^in my opinion", re.IGNORECASE),
        re.compile(r"\?$"),
        re.compile(r"^should", re.IGNORECASE),
        re.compile(r"^would", re.IGNORECASE),
    ]
}
    
    @classmethod
    def get_default_rules(cls) -> List[ClaimRule]:
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
    
def calculate_scores(text: str, domain: str) -> tuple[float, float, float, float]:
    """Calculate various scores for a claim using ClaimRules."""
    # Initialize base scores
    specificity = 0.5
    public_interest = 0.5
    impact = 0.5
    
    # Apply factual indicators
    for indicator, score in ClaimRules.SCORING_RULES["factual_indicators"]:
        if re.search(indicator, text.lower()):
            specificity = max(specificity, score)
    
    # Apply opinion indicators
    for indicator, score in ClaimRules.SCORING_RULES["opinion_indicators"]:
        if re.search(indicator, text.lower()):
            specificity = max(0.0, specificity + score)  # Ensure non-negative
    
    # Apply domain-specific rules
    for rule in ClaimRules.get_default_rules():
        if rule.domain == domain and re.search(rule.pattern, text.lower()):
            specificity = max(specificity, rule.min_specificity)
            public_interest = max(public_interest, rule.min_public_interest)
            impact = max(impact, rule.min_impact)

    # Check exclusion patterns
    for pattern in ClaimRules.SCORING_RULES["exclusion_patterns"]:
        if re.search(pattern, text.lower()):
            specificity = 0.0
            break
    
    # Calculate check-worthiness as weighted average
    check_worthiness = (specificity * 0.4 + public_interest * 0.3 + impact * 0.3)
    
    return specificity, public_interest, impact, check_worthiness