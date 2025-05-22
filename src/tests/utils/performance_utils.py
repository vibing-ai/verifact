"""Utilities for measuring and analyzing performance of the VeriFact pipeline."""

import time
import asyncio
from typing import Dict, List, Any, Callable, Awaitable, Optional, Tuple
import statistics
from dataclasses import dataclass, field

from src.verifact_manager import VerifactManager


@dataclass
class TimingResult:
    """Result of a timing measurement."""
    
    operation: str
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Performance report for a pipeline run."""
    
    total_duration_ms: float
    claim_detection_ms: float
    evidence_gathering_ms: float
    verdict_generation_ms: float
    claim_count: int
    evidence_count: int
    verdict_count: int
    evidence_per_claim: float
    ms_per_claim: float
    ms_per_evidence: float
    ms_per_verdict: float
    parallelism_efficiency: float  # 1.0 means perfect parallelism
    timings: List[TimingResult] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Return a string representation of the performance report."""
        return f"""
Performance Report:
------------------
Total Duration: {self.total_duration_ms:.2f}ms ({self.total_duration_ms / 1000:.2f}s)

Claim Detection: {self.claim_detection_ms:.2f}ms ({self.claim_detection_ms / self.total_duration_ms * 100:.1f}%)
Evidence Gathering: {self.evidence_gathering_ms:.2f}ms ({self.evidence_gathering_ms / self.total_duration_ms * 100:.1f}%)
Verdict Generation: {self.verdict_generation_ms:.2f}ms ({self.verdict_generation_ms / self.total_duration_ms * 100:.1f}%)

Counts:
- Claims: {self.claim_count}
- Evidence: {self.evidence_count}
- Verdicts: {self.verdict_count}
- Evidence per claim: {self.evidence_per_claim:.1f}

Performance Metrics:
- Ms per claim: {self.ms_per_claim:.2f}
- Ms per evidence: {self.ms_per_evidence:.2f}
- Ms per verdict: {self.ms_per_verdict:.2f}
- Parallelism efficiency: {self.parallelism_efficiency:.2f} (1.0 is perfect)
"""


class PerformanceTracker:
    """Tracks performance metrics for the VeriFact pipeline."""
    
    def __init__(self):
        self.timings: List[TimingResult] = []
        self.start_time: float = 0
        self.end_time: float = 0
        
    def reset(self):
        """Reset the tracker."""
        self.timings = []
        self.start_time = 0
        self.end_time = 0
        
    def start(self):
        """Start tracking performance."""
        self.reset()
        self.start_time = time.time()
        
    def stop(self):
        """Stop tracking performance."""
        self.end_time = time.time()
        
    def add_timing(self, operation: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None):
        """Add a timing measurement."""
        self.timings.append(TimingResult(
            operation=operation,
            duration_ms=duration_ms,
            metadata=metadata or {},
        ))
        
    async def timed_operation(
        self,
        operation: str,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Any:
        """Time an asynchronous operation and record the result."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        self.add_timing(operation, duration_ms, {
            "args": str(args),
            "kwargs": str(kwargs),
        })
        
        return result
        
    def generate_report(self) -> PerformanceReport:
        """Generate a performance report."""
        if self.start_time == 0 or self.end_time == 0:
            raise ValueError("Performance tracking not started or stopped")
            
        total_duration_ms = (self.end_time - self.start_time) * 1000
        
        # Group timings by operation
        operation_timings: Dict[str, List[float]] = {}
        for timing in self.timings:
            if timing.operation not in operation_timings:
                operation_timings[timing.operation] = []
            operation_timings[timing.operation].append(timing.duration_ms)
            
        # Calculate metrics
        claim_detection_ms = sum(operation_timings.get("claim_detection", [0]))
        evidence_gathering_ms = sum(operation_timings.get("evidence_gathering", [0]))
        verdict_generation_ms = sum(operation_timings.get("verdict_generation", [0]))
        
        claim_count = len(operation_timings.get("claim_detection", []))
        evidence_count = len(operation_timings.get("evidence_gathering", []))
        verdict_count = len(operation_timings.get("verdict_generation", []))
        
        evidence_per_claim = evidence_count / claim_count if claim_count > 0 else 0
        
        ms_per_claim = claim_detection_ms / claim_count if claim_count > 0 else 0
        ms_per_evidence = evidence_gathering_ms / evidence_count if evidence_count > 0 else 0
        ms_per_verdict = verdict_generation_ms / verdict_count if verdict_count > 0 else 0
        
        # Calculate parallelism efficiency
        sequential_time = claim_detection_ms + evidence_gathering_ms + verdict_generation_ms
        parallelism_efficiency = sequential_time / total_duration_ms if total_duration_ms > 0 else 0
        
        return PerformanceReport(
            total_duration_ms=total_duration_ms,
            claim_detection_ms=claim_detection_ms,
            evidence_gathering_ms=evidence_gathering_ms,
            verdict_generation_ms=verdict_generation_ms,
            claim_count=claim_count,
            evidence_count=evidence_count,
            verdict_count=verdict_count,
            evidence_per_claim=evidence_per_claim,
            ms_per_claim=ms_per_claim,
            ms_per_evidence=ms_per_evidence,
            ms_per_verdict=ms_per_verdict,
            parallelism_efficiency=parallelism_efficiency,
            timings=self.timings,
        )


async def benchmark_pipeline(
    manager: VerifactManager,
    input_texts: List[str],
    iterations: int = 1,
) -> List[PerformanceReport]:
    """Benchmark the pipeline with multiple input texts and iterations.
    
    Args:
        manager: The VerifactManager instance to benchmark.
        input_texts: List of input texts to process.
        iterations: Number of iterations to run for each input text.
        
    Returns:
        List of PerformanceReport objects, one for each iteration of each input text.
    """
    reports = []
    
    for input_text in input_texts:
        for _ in range(iterations):
            tracker = PerformanceTracker()
            tracker.start()
            
            # Monkey patch the manager's methods to track performance
            original_detect_claims = manager._detect_claims
            original_gather_evidence_for_claim = manager._gather_evidence_for_claim
            original_generate_verdict_for_claim = manager._generate_verdict_for_claim
            
            async def timed_detect_claims(text):
                return await tracker.timed_operation(
                    "claim_detection",
                    original_detect_claims,
                    text,
                )
                
            async def timed_gather_evidence_for_claim(claim):
                return await tracker.timed_operation(
                    "evidence_gathering",
                    original_gather_evidence_for_claim,
                    claim,
                )
                
            async def timed_generate_verdict_for_claim(claim, evidence):
                return await tracker.timed_operation(
                    "verdict_generation",
                    original_generate_verdict_for_claim,
                    claim,
                    evidence,
                )
                
            # Apply the monkey patches
            manager._detect_claims = timed_detect_claims
            manager._gather_evidence_for_claim = timed_gather_evidence_for_claim
            manager._generate_verdict_for_claim = timed_generate_verdict_for_claim
            
            try:
                # Run the pipeline
                await manager.run(input_text)
            finally:
                # Restore the original methods
                manager._detect_claims = original_detect_claims
                manager._gather_evidence_for_claim = original_gather_evidence_for_claim
                manager._generate_verdict_for_claim = original_generate_verdict_for_claim
                
            tracker.stop()
            reports.append(tracker.generate_report())
            
    return reports


def analyze_benchmark_results(reports: List[PerformanceReport]) -> Dict[str, Any]:
    """Analyze benchmark results and return statistics.
    
    Args:
        reports: List of PerformanceReport objects.
        
    Returns:
        Dictionary with statistics.
    """
    if not reports:
        return {}
        
    # Extract metrics
    total_durations = [report.total_duration_ms for report in reports]
    claim_detection_durations = [report.claim_detection_ms for report in reports]
    evidence_gathering_durations = [report.evidence_gathering_ms for report in reports]
    verdict_generation_durations = [report.verdict_generation_ms for report in reports]
    parallelism_efficiencies = [report.parallelism_efficiency for report in reports]
    
    # Calculate statistics
    stats = {
        "total_duration": {
            "mean": statistics.mean(total_durations),
            "median": statistics.median(total_durations),
            "min": min(total_durations),
            "max": max(total_durations),
            "stdev": statistics.stdev(total_durations) if len(total_durations) > 1 else 0,
        },
        "claim_detection": {
            "mean": statistics.mean(claim_detection_durations),
            "median": statistics.median(claim_detection_durations),
            "min": min(claim_detection_durations),
            "max": max(claim_detection_durations),
            "stdev": statistics.stdev(claim_detection_durations) if len(claim_detection_durations) > 1 else 0,
        },
        "evidence_gathering": {
            "mean": statistics.mean(evidence_gathering_durations),
            "median": statistics.median(evidence_gathering_durations),
            "min": min(evidence_gathering_durations),
            "max": max(evidence_gathering_durations),
            "stdev": statistics.stdev(evidence_gathering_durations) if len(evidence_gathering_durations) > 1 else 0,
        },
        "verdict_generation": {
            "mean": statistics.mean(verdict_generation_durations),
            "median": statistics.median(verdict_generation_durations),
            "min": min(verdict_generation_durations),
            "max": max(verdict_generation_durations),
            "stdev": statistics.stdev(verdict_generation_durations) if len(verdict_generation_durations) > 1 else 0,
        },
        "parallelism_efficiency": {
            "mean": statistics.mean(parallelism_efficiencies),
            "median": statistics.median(parallelism_efficiencies),
            "min": min(parallelism_efficiencies),
            "max": max(parallelism_efficiencies),
            "stdev": statistics.stdev(parallelism_efficiencies) if len(parallelism_efficiencies) > 1 else 0,
        },
    }
    
    return stats
