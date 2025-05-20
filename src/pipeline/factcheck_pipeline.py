"""
VeriFact Factcheck Pipeline

This module provides a unified pipeline that orchestrates the three agents:
1. ClaimDetector: Identifies factual claims in text
2. EvidenceHunter: Gathers evidence for claims
3. VerdictWriter: Analyzes evidence and generates verdicts

The pipeline handles data transformation between agents, error recovery,
and provides both synchronous and asynchronous operation modes.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, TypeVar

from pydantic import BaseModel, Field

from src.agents.claim_detector.models import Claim
from src.agents.evidence_hunter.hunter import Evidence
from src.agents.interfaces import IClaimDetector, IEvidenceHunter, IVerdictWriter
from src.agents.verdict_writer.writer import Verdict
from src.utils.logger import (
    get_component_logger,
    performance_timer,
)

# Type definitions for progress callbacks
T = TypeVar("T")
ProgressCallback = Callable[[str, float, Optional[T]], None]


class PipelineStage(str, Enum):
    """Enum for tracking pipeline stages."""

    CLAIM_DETECTION = "claim_detection"
    EVIDENCE_GATHERING = "evidence_gathering"
    VERDICT_GENERATION = "verdict_generation"
    COMPLETE = "complete"


class PipelineEvent(str, Enum):
    """Events emitted by the pipeline."""

    STARTED = "started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    CLAIM_DETECTED = "claim_detected"
    EVIDENCE_GATHERED = "evidence_gathered"
    VERDICT_GENERATED = "verdict_generated"
    COMPLETED = "completed"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class PipelineProgress:
    """Tracks progress through the pipeline."""

    stage: PipelineStage
    progress: float  # 0.0 to 1.0
    message: str
    data: Optional[Any] = None


class PipelineConfig(BaseModel):
    """Configuration options for the factcheck pipeline."""

    claim_detector_model: Optional[str] = None
    evidence_hunter_model: Optional[str] = None
    verdict_writer_model: Optional[str] = None
    min_checkworthiness: float = Field(0.5, ge=0.0, le=1.0)
    max_claims: Optional[int] = None
    evidence_per_claim: int = Field(5, ge=1)
    timeout_seconds: float = 120.0
    enable_fallbacks: bool = True
    retry_attempts: int = 2
    raise_exceptions: bool = False
    include_debug_info: bool = False


class FactcheckPipeline:
    """
    Unified pipeline for factchecking that orchestrates all three agents.

    This pipeline:
    1. Accepts input text and processes it through all agents sequentially
    2. Handles data transformation between agent outputs and inputs
    3. Implements proper error handling and recovery
    4. Supports both synchronous and asynchronous operation
    5. Includes progress tracking and event emission
    6. Provides detailed logging throughout the process
    7. Supports configuration options for customizing pipeline behavior
    """

    def __init__(
        self,
        claim_detector: IClaimDetector,
        evidence_hunter: IEvidenceHunter,
        verdict_writer: IVerdictWriter,
        config: Optional[PipelineConfig] = None,
    ):
        """
        Initialize the factcheck pipeline with specific agent implementations.

        Args:
            claim_detector: Agent for detecting claims
            evidence_hunter: Agent for gathering evidence
            verdict_writer: Agent for generating verdicts
            config: Optional configuration for the pipeline
        """
        self.config = config or PipelineConfig()
        self.logger = get_component_logger("factcheck_pipeline")
        self.logger.info("Initializing FactcheckPipeline")

        # Initialize event handlers
        self._event_handlers: Dict[PipelineEvent, List[Callable]] = {
            event: [] for event in PipelineEvent
        }

        # Store injected agent implementations
        self.claim_detector = claim_detector
        self.evidence_hunter = evidence_hunter
        self.verdict_writer = verdict_writer

        # Stats/metrics tracking
        self.stats: Dict[str, Any] = {
            "started_at": None,
            "completed_at": None,
            "total_processing_time": None,
            "claim_detection_time": None,
            "evidence_gathering_time": None,
            "verdict_generation_time": None,
            "claims_detected": 0,
            "evidence_gathered": 0,
            "verdicts_generated": 0,
            "errors": 0,
            "warnings": 0,
        }

    def register_event_handler(self, event: PipelineEvent, handler: Callable):
        """
        Register a handler for a pipeline event.

        Args:
            event: The event to handle
            handler: Callback function for the event
        """
        self._event_handlers[event].append(handler)

    def unregister_event_handler(self, event: PipelineEvent, handler: Callable) -> bool:
        """
        Unregister a handler for a pipeline event.

        Args:
            event: The event to unregister from
            handler: The handler to remove

        Returns:
            bool: True if handler was removed, False if not found
        """
        if handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)
            return True
        return False

    def _emit_event(self, event: PipelineEvent, data: Any = None):
        """
        Emit an event to all registered handlers.

        Args:
            event: The event to emit
            data: Data to pass to handlers
        """
        if event == PipelineEvent.ERROR:
            self.stats["errors"] += 1
        elif event == PipelineEvent.WARNING:
            self.stats["warnings"] += 1

        # Call all registered handlers
        for handler in self._event_handlers[event]:
            try:
                handler(event, data)
            except Exception as e:
                self.logger.error(f"Error in event handler: {str(e)}", exc_info=True)

    def _emit_progress(self, stage: PipelineStage, progress: float, message: str, data: Any = None):
        """
        Emit progress updates for the pipeline.

        Args:
            stage: Current pipeline stage
            progress: Progress value from 0.0 to 1.0
            message: Progress description
            data: Optional data to include
        """
        progress_data = PipelineProgress(stage=stage, progress=progress, message=message, data=data)
        self._emit_event(PipelineEvent.STAGE_STARTED, progress_data)

    async def _detect_claims(self, text: str) -> List[Claim]:
        """
        Detect claims in text with error handling and retries.

        Args:
            text: Input text to analyze

        Returns:
            List of detected claims
        """
        self._emit_progress(PipelineStage.CLAIM_DETECTION, 0.0, "Starting claim detection")

        retry_count = 0
        while True:
            try:
                with performance_timer("claim_detection", logger=self.logger) as timer:
                    claims = await self.claim_detector.detect_claims(text)

                self.stats["claim_detection_time"] = timer.elapsed
                self.stats["claims_detected"] = len(claims)

                # Filter claims by checkworthiness if configured
                if self.config.min_checkworthiness > 0:
                    original_count = len(claims)
                    claims = [c for c in claims if c.checkworthy]
                    if len(claims) < original_count:
                        self.logger.info(
                            f"Filtered out {original_count - len(claims)} claims below checkworthiness threshold"
                        )

                # Limit max claims if configured
                if self.config.max_claims and len(claims) > self.config.max_claims:
                    self.logger.info(
                        f"Limiting claims from {len(claims)} to {self.config.max_claims}"
                    )
                    claims = claims[: self.config.max_claims]

                self._emit_progress(
                    PipelineStage.CLAIM_DETECTION, 1.0, f"Detected {len(claims)} claims", claims
                )

                self._emit_event(
                    PipelineEvent.STAGE_COMPLETED,
                    {"stage": PipelineStage.CLAIM_DETECTION, "claims": claims},
                )

                return claims

            except Exception as e:
                retry_count += 1
                self.logger.error(
                    f"Error detecting claims (attempt {retry_count}): {str(e)}", exc_info=True
                )

                self._emit_event(
                    PipelineEvent.ERROR,
                    {
                        "stage": PipelineStage.CLAIM_DETECTION,
                        "error": str(e),
                        "attempt": retry_count,
                    },
                )

                if retry_count >= self.config.retry_attempts:
                    if self.config.raise_exceptions:
                        raise
                    return []

                # Wait before retrying
                await asyncio.sleep(1.0)

    async def _gather_evidence(self, claim: Claim) -> List[Evidence]:
        """
        Gather evidence for a claim with error handling and retries.

        Args:
            claim: Claim to gather evidence for

        Returns:
            List of evidence items
        """
        retry_count = 0
        while True:
            try:
                with performance_timer("evidence_gathering", logger=self.logger) as timer:
                    evidence = await self.evidence_hunter.gather_evidence(claim)

                self._emit_event(
                    PipelineEvent.EVIDENCE_GATHERED, {"claim": claim, "evidence": evidence}
                )

                return evidence

            except Exception as e:
                retry_count += 1
                self.logger.error(
                    f"Error gathering evidence (attempt {retry_count}): {str(e)}", exc_info=True
                )

                self._emit_event(
                    PipelineEvent.ERROR,
                    {
                        "stage": PipelineStage.EVIDENCE_GATHERING,
                        "claim": claim.text,
                        "error": str(e),
                        "attempt": retry_count,
                    },
                )

                if retry_count >= self.config.retry_attempts:
                    if self.config.raise_exceptions:
                        raise
                    return []

                # Wait before retrying
                await asyncio.sleep(1.0)

    async def _generate_verdict(self, claim: Claim, evidence: List[Evidence]) -> Optional[Verdict]:
        """
        Generate a verdict for a claim with error handling and retries.

        Args:
            claim: The claim to evaluate
            evidence: Evidence to consider

        Returns:
            Verdict or None if generation failed
        """
        retry_count = 0
        while True:
            try:
                with performance_timer("verdict_generation", logger=self.logger) as timer:
                    verdict = await self.verdict_writer.generate_verdict(claim, evidence)

                self._emit_event(
                    PipelineEvent.VERDICT_GENERATED,
                    {"claim": claim, "evidence": evidence, "verdict": verdict},
                )

                return verdict

            except Exception as e:
                retry_count += 1
                self.logger.error(
                    f"Error generating verdict (attempt {retry_count}): {str(e)}", exc_info=True
                )

                self._emit_event(
                    PipelineEvent.ERROR,
                    {
                        "stage": PipelineStage.VERDICT_GENERATION,
                        "claim": claim.text,
                        "error": str(e),
                        "attempt": retry_count,
                    },
                )

                if retry_count >= self.config.retry_attempts:
                    if self.config.raise_exceptions:
                        raise
                    return None

                # Wait before retrying
                await asyncio.sleep(1.0)

    async def process_text(self, text: str) -> List[Verdict]:
        """
        Process text through the complete pipeline.

        Args:
            text: Input text to factcheck

        Returns:
            List of verdicts for claims in the text
        """
        self.stats["started_at"] = time.time()
        self._emit_event(PipelineEvent.STARTED, {"text": text})

        self.logger.info(f"Starting factcheck pipeline for text ({len(text)} chars)")

        try:
            # Stage 1: Detect claims
            claims = await self._detect_claims(text)
            if not claims:
                self.logger.info("No claims detected, pipeline complete")
                self._emit_event(PipelineEvent.COMPLETED, {"verdicts": []})
                return []

            self.logger.info(f"Detected {len(claims)} claims, gathering evidence")

            # Stage 2: Gather evidence for each claim
            verdicts = []
            total_claims = len(claims)

            for i, claim in enumerate(claims):
                # Update progress
                self._emit_progress(
                    PipelineStage.EVIDENCE_GATHERING,
                    i / total_claims,
                    f"Gathering evidence for claim {i+1}/{total_claims}",
                )

                # Get evidence for this claim
                evidence = await self._gather_evidence(claim)
                self.stats["evidence_gathered"] += len(evidence)

                if not evidence:
                    self.logger.warning(f"No evidence found for claim: {claim.text}")
                    self._emit_event(
                        PipelineEvent.WARNING,
                        {
                            "stage": PipelineStage.EVIDENCE_GATHERING,
                            "message": f"No evidence found for claim: {claim.text}",
                        },
                    )
                    continue

                # Stage 3: Generate verdict for this claim
                self._emit_progress(
                    PipelineStage.VERDICT_GENERATION,
                    i / total_claims,
                    f"Generating verdict for claim {i+1}/{total_claims}",
                )

                verdict = await self._generate_verdict(claim, evidence)
                if verdict:
                    verdicts.append(verdict)
                    self.stats["verdicts_generated"] += 1

            # Complete
            self._emit_progress(
                PipelineStage.COMPLETE,
                1.0,
                f"Pipeline complete, generated {len(verdicts)} verdicts",
            )

            self.stats["completed_at"] = time.time()
            self.stats["total_processing_time"] = (
                self.stats["completed_at"] - self.stats["started_at"]
            )

            self._emit_event(PipelineEvent.COMPLETED, {"verdicts": verdicts})

            self.logger.info(
                f"Pipeline complete in {self.stats['total_processing_time']:.2f}s, "
                f"generated {len(verdicts)} verdicts"
            )

            return verdicts

        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            self._emit_event(PipelineEvent.ERROR, {"error": str(e)})

            if self.config.raise_exceptions:
                raise

            return []

    def process_text_sync(self, text: str) -> List[Verdict]:
        """
        Synchronous version of the pipeline for non-async code.

        Args:
            text: Input text to factcheck

        Returns:
            List of verdicts for claims in the text
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.process_text(text))
        finally:
            loop.close()

    async def process_text_streaming(self, text: str) -> AsyncIterator[Verdict]:
        """
        Streaming version of the pipeline that yields verdicts as they're generated.

        Args:
            text: Input text to factcheck

        Yields:
            Verdicts as they are generated
        """
        self.stats["started_at"] = time.time()
        self._emit_event(PipelineEvent.STARTED, {"text": text})

        self.logger.info(f"Starting streaming factcheck pipeline for text ({len(text)} chars)")

        try:
            # Stage 1: Detect claims
            claims = await self._detect_claims(text)
            if not claims:
                self.logger.info("No claims detected, pipeline complete")
                self._emit_event(PipelineEvent.COMPLETED, {"verdicts": []})
                return

            self.logger.info(f"Detected {len(claims)} claims, gathering evidence")

            # Process each claim independently
            total_claims = len(claims)
            for i, claim in enumerate(claims):
                # Update progress
                self._emit_progress(
                    PipelineStage.EVIDENCE_GATHERING,
                    i / total_claims,
                    f"Gathering evidence for claim {i+1}/{total_claims}",
                )

                # Get evidence for this claim
                evidence = await self._gather_evidence(claim)
                self.stats["evidence_gathered"] += len(evidence)

                if not evidence:
                    self.logger.warning(f"No evidence found for claim: {claim.text}")
                    self._emit_event(
                        PipelineEvent.WARNING,
                        {
                            "stage": PipelineStage.EVIDENCE_GATHERING,
                            "message": f"No evidence found for claim: {claim.text}",
                        },
                    )
                    continue

                # Generate verdict for this claim
                self._emit_progress(
                    PipelineStage.VERDICT_GENERATION,
                    i / total_claims,
                    f"Generating verdict for claim {i+1}/{total_claims}",
                )

                verdict = await self._generate_verdict(claim, evidence)
                if verdict:
                    self.stats["verdicts_generated"] += 1
                    yield verdict

            # Complete
            self.stats["completed_at"] = time.time()
            self.stats["total_processing_time"] = (
                self.stats["completed_at"] - self.stats["started_at"]
            )

            self._emit_event(
                PipelineEvent.COMPLETED, {"verdict_count": self.stats["verdicts_generated"]}
            )

            self.logger.info(
                f"Pipeline complete in {self.stats['total_processing_time']:.2f}s, "
                f"generated {self.stats['verdicts_generated']} verdicts"
            )

        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            self._emit_event(PipelineEvent.ERROR, {"error": str(e)})

            if self.config.raise_exceptions:
                raise


def create_default_pipeline(config: Optional[PipelineConfig] = None) -> FactcheckPipeline:
    """
    Create a pipeline with default agent implementations.

    Args:
        config: Optional configuration for the pipeline

    Returns:
        FactcheckPipeline: A pipeline with default agent implementations
    """
    from src.agents.claim_detector.detector import ClaimDetector
    from src.agents.evidence_hunter.hunter import EvidenceHunter
    from src.agents.verdict_writer.writer import VerdictWriter

    # Create configuration with defaults if not provided
    config = config or PipelineConfig()

    # Create the agents with any model overrides from config
    claim_detector = ClaimDetector(
        model_name=config.claim_detector_model,
        min_check_worthiness=config.min_checkworthiness,
        max_claims=config.max_claims,
    )

    evidence_hunter = EvidenceHunter(model_name=config.evidence_hunter_model)

    verdict_writer = VerdictWriter(model_name=config.verdict_writer_model)

    # Create and return the pipeline with injected dependencies
    return FactcheckPipeline(
        claim_detector=claim_detector,
        evidence_hunter=evidence_hunter,
        verdict_writer=verdict_writer,
        config=config,
    )
