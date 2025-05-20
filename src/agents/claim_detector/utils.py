"""
Utility functions for the ClaimDetector agent.

This module contains utility functions used by the ClaimDetector.
"""

import hashlib
import re
from typing import List

from src.agents.claim_detector.models import Claim


def generate_claim_id(claim_text: str) -> str:
    """
    Generate a unique ID for a claim based on its text.
    
    Args:
        claim_text: The text of the claim
        
    Returns:
        A unique ID string
    """
    # Create a SHA-256 hash of the claim text
    return hashlib.sha256(claim_text.encode('utf-8')).hexdigest()[:16]


def contains_opinion_indicators(text: str) -> bool:
    """
    Check if text contains indicators of subjective opinions.
    
    Args:
        text: The text to check
        
    Returns:
        True if opinion indicators are found, False otherwise
    """
    opinion_phrases = [
        r'\bI think\b', r'\bI believe\b', r'\bI feel\b', r'\bin my opinion\b',
        r'\bI suspect\b', r'\bI guess\b', r'\bI assume\b', r'\bprobably\b',
        r'\bpersonally\b', r'\bmy view\b', r'\bmight be\b', r'\bcould be\b',
        r'\bseems to\b', r'\bappears to\b', r'\bI reckon\b', r'\bI suppose\b'
    ]
    
    for phrase in opinion_phrases:
        if re.search(phrase, text, re.IGNORECASE):
            return True
    return False


def contains_question_indicators(text: str) -> bool:
    """
    Check if text is a question rather than a claim.
    
    Args:
        text: The text to check
        
    Returns:
        True if text is likely a question, False otherwise
    """
    # Check for question marks
    if '?' in text:
        return True
    
    # Check for question words at the beginning
    question_starters = [
        r'^what\b', r'^who\b', r'^where\b', r'^when\b', r'^why\b',
        r'^how\b', r'^is\b', r'^are\b', r'^do\b', r'^does\b', r'^did\b',
        r'^has\b', r'^have\b', r'^can\b', r'^could\b', r'^should\b',
        r'^would\b', r'^will\b'
    ]
    
    for starter in question_starters:
        if re.search(starter, text, re.IGNORECASE):
            return True
    
    return False


def contains_future_prediction(text: str) -> bool:
    """
    Check if text contains predictions about the future that can't be verified now.
    
    Args:
        text: The text to check
        
    Returns:
        True if future prediction indicators are found, False otherwise
    """
    future_phrases = [
        r'\bwill be\b', r'\bgoing to\b', r'\bin the future\b', r'\bin \d+ years\b',
        r'\bnext year\b', r'\bnext month\b', r'\btomorrow\b', r'\bupcoming\b',
        r'\beventually\b', r'\bsoon\b', r'\bforthcoming\b'
    ]
    
    for phrase in future_phrases:
        if re.search(phrase, text, re.IGNORECASE):
            return True
    return False


def contains_specificity_indicators(text: str) -> List[str]:
    """
    Identify specific, verifiable elements in the text.
    
    Args:
        text: The text to analyze
        
    Returns:
        List of specificity indicators found
    """
    indicators = []
    
    # Check for numbers and statistics
    if re.search(r'\d+(?:\.\d+)?%', text):
        indicators.append('percentage')
    
    if re.search(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', text):
        indicators.append('money_amount')
    
    if re.search(r'\b\d{4}\b', text):
        indicators.append('year')
    
    if re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4}\b', text, re.IGNORECASE):
        indicators.append('specific_date')
    
    # Check for named entities (simplified)
    if re.search(r'"[^"]+"', text) or re.search(r"'[^']+'", text):
        indicators.append('quotation')
    
    if re.search(r'\b(?:[A-Z][a-z]+\s+)+(?:University|Institute|College|School|Corporation|Company|Inc|Ltd)\b', text):
        indicators.append('organization')
    
    if re.search(r'\b(?:[A-Z][a-z]*\.?\s?)+(?:Act|Bill|Law|Treaty|Agreement|Regulation)\b', text):
        indicators.append('law_or_policy')
    
    if re.search(r'\b(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?', text):
        indicators.append('url')
    
    return indicators


def normalize_claim_text(text: str) -> str:
    """
    Normalize claim text by standardizing formats and expansions.
    
    Args:
        text: The claim text to normalize
        
    Returns:
        Normalized version of the text
    """
    # Trim whitespace
    normalized = text.strip()
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Expand common abbreviations
    abbreviations = {
        r'\bU\.?S\.?A?\b': 'United States',
        r'\bU\.?K\.?\b': 'United Kingdom',
        r'\bE\.?U\.?\b': 'European Union',
        r'\bW\.?H\.?O\.?\b': 'World Health Organization',
        r'\bU\.?N\.?\b': 'United Nations',
        r'\bNASA\b': 'National Aeronautics and Space Administration',
        r'\bCDC\b': 'Centers for Disease Control and Prevention',
        r'\bFBI\b': 'Federal Bureau of Investigation',
        r'\bCIA\b': 'Central Intelligence Agency',
        r'\bDOJ\b': 'Department of Justice',
        r'\bDOD\b': 'Department of Defense',
        r'\bIMF\b': 'International Monetary Fund',
        r'\bWB\b': 'World Bank'
    }
    
    for abbr, expanded in abbreviations.items():
        normalized = re.sub(abbr, expanded, normalized, flags=re.IGNORECASE)
    
    # Normalize numeric representations
    def format_number(match):
        """Format numbers consistently"""
        num_str = match.group(0).replace(',', '')
        try:
            num = float(num_str)
            if num.is_integer():
                return f"{int(num)}"
            return f"{num:.2f}"
        except:
            return match.group(0)
    
    normalized = re.sub(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', format_number, normalized)
    
    return normalized


def split_compound_claim(claim_text: str) -> List[str]:
    """
    Split a compound claim into individual claims.
    
    Args:
        claim_text: The compound claim text
        
    Returns:
        List of individual claim texts
    """
    # Common separators for compound claims
    separators = [
        r'(?<=[.!?])\s+(?=[A-Z])',  # Sentence boundaries
        r'\band\b(?!\s+[^A-Z])',    # 'and' between separate thoughts
        r'\bmoreover\b',
        r'\bfurthermore\b',
        r'\badditionally\b',
        r'\balso\b',
        r'\bhowever\b',
        r'\bnevertheless\b',
        r'\bbut\b',
        r'\byet\b',
        r'\bwhile\b',
        r'\bwhereas\b',
        r';'                       # Semicolons
    ]
    
    # If we have any of these patterns, the claim might be compound
    compound_pattern = '|'.join(separators)
    
    # If it doesn't match any compound patterns, return the original claim
    if not re.search(compound_pattern, claim_text):
        return [claim_text]
    
    # Try to split by sentence boundaries first
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', claim_text)
    
    # If we got multiple sentences, return them
    if len(sentences) > 1:
        return [s.strip() for s in sentences]
    
    # Otherwise try other separators
    for separator in separators[1:]:  # Skip sentence boundaries as we already tried
        parts = re.split(separator, claim_text, flags=re.IGNORECASE)
        if len(parts) > 1:
            # Clean up each part
            clean_parts = []
            for part in parts:
                part = part.strip()
                # Make sure it's a complete sentence that can stand alone
                if part and not contains_question_indicators(part) and len(part.split()) > 3:
                    clean_parts.append(part)
            
            # If we have multiple valid parts, return them
            if len(clean_parts) > 1:
                return clean_parts
    
    # If no good split found, return the original claim
    return [claim_text]


def calculate_similarity(claim1: Claim, claim2: Claim) -> float:
    """
    Calculate the semantic similarity between two claims.
    
    Args:
        claim1: First claim
        claim2: Second claim
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # This is a simple implementation using text overlap
    # A more sophisticated implementation would use embeddings or other NLP techniques
    
    # Get the set of words in each claim
    words1 = set(claim1.text.lower().split())
    words2 = set(claim2.text.lower().split())
    
    # Calculate Jaccard similarity: intersection over union
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    # Avoid division by zero
    if union == 0:
        return 0.0
    
    return intersection / union 