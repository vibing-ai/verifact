"""
Pydantic models for the VeriFact factchecking system.

This module contains the data models used throughout the application for:
- Claims: Factual statements identified for verification
- Evidence: Supporting or contradicting information for claims
- Verdicts: Final assessment of claim truthfulness
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    AnyUrl,
    BaseModel,
    Field,
    constr,
    root_validator,
    validator,
)


class SourceType(str, Enum):
    """Enumeration of evidence source types."""
    WEBPAGE = "webpage"
    NEWS_ARTICLE = "news_article"
    ACADEMIC_PAPER = "academic_paper"
    GOVERNMENT_DOCUMENT = "government_document"
    SOCIAL_MEDIA = "social_media"
    DATASET = "dataset"
    EXPERT_TESTIMONY = "expert_testimony"
    UNKNOWN = "unknown"


class StanceType(str, Enum):
    """Enumeration of stance types for evidence."""
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NEUTRAL = "neutral"


class VerdictType(str, Enum):
    """Enumeration of verdict types."""
    TRUE = "true"
    FALSE = "false"
    PARTIALLY_TRUE = "partially_true"
    UNVERIFIABLE = "unverifiable"
    MISLEADING = "misleading"
    OUTDATED = "outdated"


class Claim(BaseModel):
    """A factual claim identified from text."""
    text: constr(min_length=3, max_length=1000) = Field(..., description="The exact text of the claim")
    context: constr(max_length=5000) = Field("", description="Surrounding context of the claim")
    checkworthy: bool = Field(True, description="Whether the claim is worth checking")
    domain: Optional[str] = Field(None, description="Domain/category of the claim (politics, health, etc.)")
    entities: List[str] = Field(default_factory=list, description="Named entities mentioned in the claim")
    extracted_at: Optional[datetime] = Field(default_factory=datetime.now, description="When the claim was extracted")
    source_text: Optional[str] = Field(None, description="Original text the claim was extracted from")
    source_url: Optional[AnyUrl] = Field(None, description="URL where the claim was found")
    
    @validator('text')
    def text_not_empty(cls, v):
        """Validate that claim text is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Claim text cannot be empty")
        return v
    
    @validator('entities', each_item=True)
    def entity_not_empty(cls, v):
        """Validate that entity names are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Entity name cannot be empty")
        return v


class Evidence(BaseModel):
    """Evidence related to a factual claim."""
    text: constr(min_length=5, max_length=10000) = Field(..., description="The evidence text")
    source: str = Field(..., description="Source of the evidence (URL, document, etc.)")
    source_name: Optional[str] = Field(None, description="Name of the source")
    source_type: SourceType = Field(SourceType.UNKNOWN, description="Type of source")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    stance: StanceType = Field(..., description="Whether evidence supports or contradicts the claim")
    timestamp: Optional[datetime] = Field(None, description="Publication date/time of the evidence")
    credibility: Optional[float] = Field(None, ge=0.0, le=1.0, description="Source credibility score (0-1)")
    excerpt_context: Optional[str] = Field(None, description="Context around the evidence excerpt")
    retrieval_date: Optional[datetime] = Field(default_factory=datetime.now, description="When the evidence was retrieved")
    
    @validator('text')
    def text_not_empty(cls, v):
        """Validate that evidence text is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Evidence text cannot be empty")
        return v
    
    @validator('source')
    def source_not_empty(cls, v):
        """Validate that source is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Source cannot be empty")
        return v
    
    @root_validator(skip_on_failure=True)
    def check_source_name(cls, values):
        """Set source_name if not provided."""
        if not values.get('source_name') and values.get('source'):
            source = values.get('source')
            # Attempt to extract a name from source (e.g., domain from URL)
            if source.startswith(('http://', 'https://')):
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(source).netloc
                    values['source_name'] = domain
                except:
                    pass
        return values


class Verdict(BaseModel):
    """Verdict on a factual claim."""
    claim: str = Field(..., description="The claim being verified")
    claim_id: Optional[str] = Field(None, description="ID of the claim if available")
    verdict: VerdictType = Field(..., description="Final assessment of claim truthfulness")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict (0-1)")
    explanation: constr(min_length=10) = Field(..., description="Detailed explanation of the verdict")
    sources: List[str] = Field(..., description="Sources used for verification")
    evidence_summary: Optional[str] = Field(None, description="Summary of key evidence")
    key_evidence: List[Evidence] = Field(default_factory=list, description="Key evidence supporting the verdict")
    generated_at: datetime = Field(default_factory=datetime.now, description="When the verdict was generated")
    
    @validator('sources')
    def sources_not_empty(cls, v):
        """Validate that sources list is not empty."""
        if not v:
            raise ValueError("Sources list cannot be empty")
        return v
    
    @validator('explanation')
    def explanation_not_empty(cls, v):
        """Validate that explanation is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Explanation cannot be empty")
        return v


class ProcessingStats(BaseModel):
    """Statistics about the factchecking process."""
    processing_time: float = Field(..., description="Total processing time in seconds")
    claims_detected: int = Field(..., ge=0, description="Number of claims detected")
    evidence_gathered: int = Field(..., ge=0, description="Total pieces of evidence gathered")
    verdicts_generated: int = Field(..., ge=0, description="Number of verdicts generated")
    sources_consulted: Optional[int] = Field(None, ge=0, description="Number of distinct sources consulted")
    tokens_processed: Optional[int] = Field(None, ge=0, description="Total tokens processed")
    model_calls: Optional[Dict[str, int]] = Field(default_factory=dict, description="Number of calls to each model")


class PipelineConfig(BaseModel):
    """Configuration options for the factchecking pipeline."""
    claim_detection_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Threshold for claim detection confidence")
    max_claims: int = Field(10, ge=1, le=100, description="Maximum number of claims to process")
    max_evidence_per_claim: int = Field(5, ge=1, le=50, description="Maximum pieces of evidence per claim")
    relevance_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum relevance score for evidence")
    allowed_domains: Optional[List[str]] = Field(None, description="List of allowed domains for evidence sources")
    blocked_domains: List[str] = Field(default_factory=list, description="List of blocked domains for evidence sources")
    claim_categories: Optional[List[str]] = Field(None, description="Categories of claims to focus on")
    min_credibility_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum credibility score for sources")
    # Enhanced configuration options
    min_check_worthiness: float = Field(0.5, ge=0.0, le=1.0, description="Minimum threshold for claim check-worthiness")
    explanation_detail: Literal["brief", "standard", "detailed"] = Field("standard", description="Level of detail for verdict explanations")
    include_evidence: bool = Field(True, description="Whether to include evidence details in responses")
    domains: Optional[List[str]] = Field(None, description="Filter claims by domain/category")
    
    @validator('max_claims')
    def validate_max_claims(cls, v):
        """Validate maximum claims."""
        if v > 100:
            raise ValueError("Maximum number of claims cannot exceed 100")
        return v
    
    @validator('explanation_detail')
    def validate_explanation_detail(cls, v):
        """Validate explanation detail level."""
        valid_levels = ["brief", "standard", "detailed"]
        if v not in valid_levels:
            raise ValueError(f"Explanation detail must be one of: {', '.join(valid_levels)}")
        return v


class FactcheckRequest(BaseModel):
    """Request model for factchecking API."""
    text: constr(min_length=10, max_length=50000) = Field(..., description="Text containing claims to verify")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="""
        Optional configuration parameters:
        - min_check_worthiness: Threshold for claims to check (float, 0.0-1.0)
        - max_claims: Limit number of claims to process (int, 1-100)
        - domains: Filter claims by domain/category (list of strings)
        - explanation_detail: Level of detail for explanations ("brief", "standard", "detailed")
        - include_evidence: Whether to include evidence details (boolean)
        - relevance_threshold: Minimum relevance score for evidence (float, 0.0-1.0)
        - blocked_domains: List of domains to exclude from evidence (list of strings)
        - claim_categories: Categories of claims to focus on (list of strings)
    """)
    url: Optional[AnyUrl] = Field(None, description="URL to fetch content from instead of text")
    callback_url: Optional[AnyUrl] = Field(None, description="URL to call with results when processing is complete")
    
    @root_validator(skip_on_failure=True)
    def check_text_or_url(cls, values):
        """Validate that either text or URL is provided."""
        if not values.get('text') and not values.get('url'):
            raise ValueError("Either text or URL must be provided")
        return values
    
    @validator('options')
    def validate_options(cls, v):
        """Validate configuration options."""
        if not v:
            return v
            
        # Validate numeric ranges
        for numeric_field in ['min_check_worthiness', 'relevance_threshold', 'min_credibility_score']:
            if numeric_field in v:
                value = v[numeric_field]
                if not isinstance(value, (int, float)) or value < 0 or value > 1:
                    raise ValueError(f"{numeric_field} must be a number between 0 and 1")
        
        # Validate integer ranges
        if 'max_claims' in v:
            value = v['max_claims']
            if not isinstance(value, int) or value < 1 or value > 100:
                raise ValueError("max_claims must be an integer between 1 and 100")
                
        if 'max_evidence_per_claim' in v:
            value = v['max_evidence_per_claim']
            if not isinstance(value, int) or value < 1 or value > 50:
                raise ValueError("max_evidence_per_claim must be an integer between 1 and 50")
        
        # Validate explanation detail
        if 'explanation_detail' in v:
            value = v['explanation_detail']
            if value not in ['brief', 'standard', 'detailed']:
                raise ValueError("explanation_detail must be one of: brief, standard, detailed")
        
        # Validate boolean fields
        for bool_field in ['include_evidence']:
            if bool_field in v and not isinstance(v[bool_field], bool):
                raise ValueError(f"{bool_field} must be a boolean value")
        
        # Validate list fields
        for list_field in ['domains', 'blocked_domains', 'claim_categories']:
            if list_field in v and v[list_field] is not None and not isinstance(v[list_field], list):
                raise ValueError(f"{list_field} must be a list")
        
        return v


class FactcheckResponse(BaseModel):
    """Response model for factchecking API."""
    claims: List[Verdict] = Field(..., description="Verified claims with verdicts")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata and statistics")
    request_id: Optional[str] = Field(None, description="ID of the original request")
    original_text: Optional[str] = Field(None, description="First 200 chars of the original text that was analyzed")
    
    @validator('claims')
    def validate_claims(cls, v):
        """Validate that claims list is not too large."""
        if len(v) > 100:
            raise ValueError("Too many claims in response (max 100)")
        return v
    
    @root_validator(skip_on_failure=True)
    def set_original_text_preview(cls, values):
        """Set a preview of the original text."""
        if 'metadata' in values and 'original_text' in values['metadata']:
            orig_text = values['metadata']['original_text']
            if isinstance(orig_text, str) and len(orig_text) > 200:
                values['original_text'] = orig_text[:200] + "..."
            else:
                values['original_text'] = orig_text
        return values


class JobStatus(str, Enum):
    """Enumeration of job status types."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELED = "canceled"
    PAUSED = "paused"


class FactcheckJob(BaseModel):
    """Model for tracking asynchronous factchecking jobs."""
    job_id: str = Field(..., description="Unique identifier for the job")
    status: JobStatus = Field(JobStatus.QUEUED, description="Current status of the job")
    created_at: datetime = Field(default_factory=datetime.now, description="When the job was created")
    updated_at: Optional[datetime] = Field(None, description="When the job was last updated")
    completed_at: Optional[datetime] = Field(None, description="When the job was completed")
    result: Optional[FactcheckResponse] = Field(None, description="Results when job is completed")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if job failed")
    
    @root_validator(skip_on_failure=True)
    def update_timestamps(cls, values):
        """Update timestamps based on status."""
        now = datetime.now()
        if values.get('status') in [JobStatus.COMPLETED, JobStatus.FAILED]:
            values['completed_at'] = now
        values['updated_at'] = now
        return values


class BatchClaim(BaseModel):
    """Individual claim for batch processing."""
    text: constr(min_length=3, max_length=1000) = Field(..., description="The exact text of the claim")
    id: Optional[str] = Field(None, description="Optional client-provided identifier for the claim")
    context: Optional[constr(max_length=5000)] = Field(None, description="Optional context surrounding the claim")
    priority: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional priority for processing (higher = higher priority)")
    domain: Optional[str] = Field(None, description="Optional domain/category of the claim")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata associated with the claim")
    
    @validator('text')
    def text_not_empty(cls, v):
        """Validate that claim text is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Claim text cannot be empty")
        return v


class BatchFactcheckRequest(BaseModel):
    """Request model for batch factchecking API."""
    claims: List[BatchClaim] = Field(..., min_items=1, max_items=100, description="List of claims to verify")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="""
        Optional configuration parameters:
        - max_concurrent: Maximum number of claims to process concurrently (int, 1-10)
        - min_check_worthiness: Threshold for claims to check (float, 0.0-1.0)
        - timeout_per_claim: Maximum processing time per claim in seconds (int, 10-300)
        - explanation_detail: Level of detail for explanations ("brief", "standard", "detailed")
        - include_evidence: Whether to include evidence details (boolean)
        - relevance_threshold: Minimum relevance score for evidence (float, 0.0-1.0)
        - blocked_domains: List of domains to exclude from evidence (list of strings)
        - detect_related_claims: Whether to detect and group related claims (boolean)
        - webhook_notification: Whether to send webhook notification on completion (boolean)
    """)
    callback_url: Optional[AnyUrl] = Field(None, description="URL to call with results when processing is complete")
    
    @validator('claims')
    def validate_claims(cls, v):
        """Validate claims list."""
        if not v:
            raise ValueError("At least one claim must be provided")
        if len(v) > 100:
            raise ValueError("Maximum of 100 claims can be processed in a single request")
        return v
    
    @validator('options')
    def validate_options(cls, v):
        """Validate options."""
        if v is None:
            return {}
            
        # Validate max_concurrent
        if "max_concurrent" in v:
            max_concurrent = v["max_concurrent"]
            if not isinstance(max_concurrent, int) or max_concurrent < 1 or max_concurrent > 10:
                raise ValueError("max_concurrent must be an integer between 1 and 10")
                
        # Validate timeout_per_claim
        if "timeout_per_claim" in v:
            timeout = v["timeout_per_claim"]
            if not isinstance(timeout, (int, float)) or timeout < 10 or timeout > 300:
                raise ValueError("timeout_per_claim must be between 10 and 300 seconds")
                
        # Validate min_check_worthiness
        if "min_check_worthiness" in v:
            threshold = v["min_check_worthiness"]
            if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
                raise ValueError("min_check_worthiness must be between 0.0 and 1.0")
                
        # Validate detect_related_claims
        if "detect_related_claims" in v and not isinstance(v["detect_related_claims"], bool):
            raise ValueError("detect_related_claims must be a boolean")
            
        # Validate webhook_notification
        if "webhook_notification" in v and not isinstance(v["webhook_notification"], bool):
            raise ValueError("webhook_notification must be a boolean")
            
        return v


class BatchProcessingProgress(BaseModel):
    """Progress information for batch processing."""
    total_claims: int = Field(..., description="Total number of claims in the batch")
    processed_claims: int = Field(..., description="Number of claims processed so far")
    pending_claims: int = Field(..., description="Number of claims pending processing")
    failed_claims: int = Field(..., description="Number of claims that failed processing")
    success_rate: float = Field(..., description="Rate of successful processing (0-1)")
    estimated_time_remaining: Optional[float] = Field(None, description="Estimated time remaining in seconds")
    avg_processing_time: Optional[float] = Field(None, description="Average time to process a claim in seconds")
    start_time: Optional[datetime] = Field(None, description="When processing started")
    last_update_time: datetime = Field(default_factory=datetime.now, description="When progress was last updated")


class BatchClaimStatus(BaseModel):
    """Status of an individual claim in a batch."""
    claim_id: str = Field(..., description="Identifier for the claim")
    status: JobStatus = Field(..., description="Current status of the claim")
    position: Optional[int] = Field(None, description="Position in processing queue")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds if completed")
    verdict: Optional[Verdict] = Field(None, description="Verdict if completed successfully")
    claim_text: str = Field(..., description="The text of the claim")
    related_claims: List[str] = Field(default_factory=list, description="IDs of related claims in the batch")


class FactcheckJob(BaseModel):
    """Model for tracking asynchronous factchecking jobs."""
    job_id: str = Field(..., description="Unique identifier for the job")
    status: JobStatus = Field(JobStatus.QUEUED, description="Current status of the job")
    created_at: datetime = Field(default_factory=datetime.now, description="When the job was created")
    updated_at: Optional[datetime] = Field(None, description="When the job was last updated")
    completed_at: Optional[datetime] = Field(None, description="When the job was completed")
    result: Optional[Union[FactcheckResponse, "BatchFactcheckResponse"]] = Field(None, description="Results when job is completed")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if job failed")
    progress: Optional[BatchProcessingProgress] = Field(None, description="Progress information for batch jobs")
    claim_statuses: Optional[Dict[str, BatchClaimStatus]] = Field(None, description="Status of individual claims for batch jobs")
    is_batch: bool = Field(False, description="Whether this is a batch job")
    
    @root_validator(skip_on_failure=True)
    def update_timestamps(cls, values):
        """Update timestamps based on status changes."""
        status = values.get('status')
        now = datetime.now()
        
        # Always update the updated_at timestamp
        values['updated_at'] = now
        
        # Set completed_at if status is terminal
        if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIALLY_COMPLETED, JobStatus.CANCELED]:
            if not values.get('completed_at'):
                values['completed_at'] = now
                
        return values


class BatchFactcheckResponse(BaseModel):
    """Response model for batch factchecking API."""
    verdicts: Dict[str, Verdict] = Field(..., description="Map of claim IDs to verdicts")
    failed_claims: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Map of claim IDs to failure details")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata and statistics")
    request_id: Optional[str] = Field(None, description="ID of the original request")
    total_claims: int = Field(..., description="Total number of claims processed")
    successful_claims: int = Field(..., description="Number of claims processed successfully")
    processing_time: float = Field(..., description="Total processing time in seconds")
    related_claims: Optional[Dict[str, List[str]]] = Field(None, description="Mapping of related claims")
    
    @validator('verdicts')
    def validate_verdicts(cls, v):
        """Validate verdicts map."""
        if not v:
            raise ValueError("At least one verdict must be provided")
        return v
        
    @root_validator(skip_on_failure=True)
    def calculate_statistics(cls, values):
        """Calculate statistics based on verdicts and failed claims."""
        verdicts = values.get('verdicts', {})
        failed_claims = values.get('failed_claims', {})
        
        values['total_claims'] = len(verdicts) + len(failed_claims)
        values['successful_claims'] = len(verdicts)
        
        return values 