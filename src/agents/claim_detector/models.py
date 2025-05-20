"""
Data models for the ClaimDetector agent.

This module contains the data models and types used by the ClaimDetector.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class ClaimDomain(str, Enum):
    """Enumeration of claim domains/categories."""
    POLITICS = "politics"
    ECONOMICS = "economics"
    HEALTH = "health"
    SCIENCE = "science"
    TECHNOLOGY = "technology"
    ENVIRONMENT = "environment"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    OTHER = "other"


class EntityType(str, Enum):
    """Enumeration of entity types that can be extracted from claims."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    MONEY = "money"
    PERCENT = "percent"
    NUMBER = "number"
    PRODUCT = "product"
    EVENT = "event"
    WORK_OF_ART = "work_of_art"
    LAW = "law"
    LANGUAGE = "language"
    SCIENTIFIC_TERM = "scientific_term"
    MEDICAL_TERM = "medical_term"
    OTHER = "other"


class Entity(BaseModel):
    """Named entity extracted from a claim."""
    text: str = Field(..., description="The entity text as it appears in the claim")
    type: EntityType = Field(..., description="Type of entity")
    normalized_text: Optional[str] = Field(None, description="Normalized/canonical form of the entity")
    relevance: float = Field(1.0, ge=0.0, le=1.0, description="Relevance of entity to the claim (0-1)")
    
    @validator("text")
    def text_not_empty(cls, v):
        """Validate that entity text is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Entity text cannot be empty")
        return v


class Claim(BaseModel):
    """A factual claim identified from text."""
    text: str = Field(..., description="The identified claim text")
    original_text: str = Field(..., description="The original, unmodified claim text")
    context: str = Field("", description="Surrounding context for the claim")
    check_worthiness: float = Field(..., ge=0.0, le=1.0, description="How check-worthy the claim is (0-1)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in claim detection (0-1)")
    domain: ClaimDomain = Field(ClaimDomain.OTHER, description="Primary domain/category of the claim")
    sub_domains: List[str] = Field(default_factory=list, description="Additional domains/categories")
    entities: List[Entity] = Field(default_factory=list, description="Named entities extracted from the claim")
    source_location: Optional[Dict[str, Any]] = Field(None, description="Location of claim in source text")
    normalized_text: Optional[str] = Field(None, description="Standardized form of the claim")
    compound_parts: List[str] = Field(default_factory=list, description="Parts of a compound claim")
    extracted_at: datetime = Field(default_factory=datetime.now, description="When the claim was extracted")
    rank: Optional[int] = Field(None, description="Ranking of claim relative to other claims")
    specificity_score: float = Field(0.0, ge=0.0, le=1.0, description="How specific the claim is (0-1)")
    public_interest_score: float = Field(0.0, ge=0.0, le=1.0, description="Public interest value of the claim (0-1)")
    impact_score: float = Field(0.0, ge=0.0, le=1.0, description="Potential impact of the claim (0-1)")
    
    @validator("text")
    def text_not_empty(cls, v):
        """Validate that claim text is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Claim text cannot be empty")
        return v
    
    @validator("check_worthiness")
    def valid_check_worthiness(cls, v):
        """Validate check-worthiness score."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Check-worthiness must be between the range of 0.0 and 1.0")
        return v 