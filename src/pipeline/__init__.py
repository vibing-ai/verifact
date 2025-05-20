"""VeriFact pipeline module.

This module provides the FactcheckPipeline class which orchestrates the three main agents
(ClaimDetector, EvidenceHunter, and VerdictWriter) to process factual claims in text.

Exported Classes:
    FactcheckPipeline: The main pipeline class that processes text through all three agents
    PipelineConfig: Configuration class for customizing pipeline behavior
    PipelineEvent: Enum for events emitted by the pipeline
    PipelineStage: Enum for tracking the current stage of the pipeline
    
Example:
    ```python
    from src.pipeline import FactcheckPipeline
    
    # Create a pipeline with default configuration
    pipeline = FactcheckPipeline()
    
    # Process text synchronously
    verdicts = pipeline.process_text_sync("Earth is the third planet from the sun.")
    
    # Or asynchronously
    import asyncio
    verdicts = asyncio.run(pipeline.process_text("Earth is the third planet from the sun."))
    ```
"""

from .factcheck_pipeline import (
    FactcheckPipeline,
    PipelineConfig,
    PipelineEvent,
    PipelineProgress,
    PipelineStage,
)

__all__ = [
    "FactcheckPipeline",
    "PipelineConfig", 
    "PipelineEvent",
    "PipelineStage",
    "PipelineProgress"
] 