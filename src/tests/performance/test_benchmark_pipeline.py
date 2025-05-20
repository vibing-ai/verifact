"""
Performance benchmarking for VeriFact.

This script runs performance benchmarks for the VeriFact factchecking components
and pipeline, measuring processing times and token usage.

Usage:
    python -m src.tests.test_benchmark_pipeline

Example:
    python -m src.tests.test_benchmark_pipeline --claims 5 --iterations 3

For integration with CI/CD, the script can output results in various formats:
    python -m src.tests.test_benchmark_pipeline --format json --output benchmark_results.json
"""

import os
import sys
import time
import json
import asyncio
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

from src.agents.claim_detector import ClaimDetector
from src.agents.evidence_hunter import EvidenceHunter
from src.agents.verdict_writer import VerdictWriter
from src.pipeline.factcheck_pipeline import FactcheckPipeline, PipelineConfig


class BenchmarkResults:
    """Container for benchmark results."""
    
    def __init__(self):
        """Initialize benchmark results container."""
        self.claim_detection_times = []
        self.evidence_gathering_times = []
        self.verdict_generation_times = []
        self.pipeline_times = []
        self.token_usage = []
        self.claim_counts = []
        self.evidence_counts = []
        self.verdict_counts = []
        self.metadata = {
            "timestamp": datetime.now().isoformat(),
            "environment": {},
            "configuration": {}
        }
        
    def add_claim_detection(self, detection_time: float, claim_count: int, tokens: Dict[str, int]):
        """Add claim detection benchmark result."""
        self.claim_detection_times.append(detection_time)
        self.claim_counts.append(claim_count)
        self.token_usage.append(tokens)
    
    def add_evidence_gathering(self, gathering_time: float, evidence_count: int, tokens: Dict[str, int]):
        """Add evidence gathering benchmark result."""
        self.evidence_gathering_times.append(gathering_time)
        self.evidence_counts.append(evidence_count)
        self.token_usage.append(tokens)
    
    def add_verdict_generation(self, generation_time: float, tokens: Dict[str, int]):
        """Add verdict generation benchmark result."""
        self.verdict_generation_times.append(generation_time)
        self.token_usage.append(tokens)
    
    def add_pipeline(self, pipeline_time: float, claim_count: int, evidence_count: int, 
                    verdict_count: int, tokens: Dict[str, int]):
        """Add full pipeline benchmark result."""
        self.pipeline_times.append(pipeline_time)
        self.claim_counts.append(claim_count)
        self.evidence_counts.append(evidence_count)
        self.verdict_counts.append(verdict_count)
        self.token_usage.append(tokens)
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata for the benchmark run."""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "claim_detection": {
                "times": self.claim_detection_times,
                "average": sum(self.claim_detection_times) / len(self.claim_detection_times) if self.claim_detection_times else 0,
                "min": min(self.claim_detection_times) if self.claim_detection_times else 0,
                "max": max(self.claim_detection_times) if self.claim_detection_times else 0,
                "claim_counts": self.claim_counts[:len(self.claim_detection_times)]
            },
            "evidence_gathering": {
                "times": self.evidence_gathering_times,
                "average": sum(self.evidence_gathering_times) / len(self.evidence_gathering_times) if self.evidence_gathering_times else 0,
                "min": min(self.evidence_gathering_times) if self.evidence_gathering_times else 0,
                "max": max(self.evidence_gathering_times) if self.evidence_gathering_times else 0,
                "evidence_counts": self.evidence_counts[:len(self.evidence_gathering_times)]
            },
            "verdict_generation": {
                "times": self.verdict_generation_times,
                "average": sum(self.verdict_generation_times) / len(self.verdict_generation_times) if self.verdict_generation_times else 0,
                "min": min(self.verdict_generation_times) if self.verdict_generation_times else 0,
                "max": max(self.verdict_generation_times) if self.verdict_generation_times else 0
            },
            "pipeline": {
                "times": self.pipeline_times,
                "average": sum(self.pipeline_times) / len(self.pipeline_times) if self.pipeline_times else 0,
                "min": min(self.pipeline_times) if self.pipeline_times else 0,
                "max": max(self.pipeline_times) if self.pipeline_times else 0,
                "claim_counts": self.claim_counts[-len(self.pipeline_times):] if self.pipeline_times else [],
                "evidence_counts": self.evidence_counts[-len(self.pipeline_times):] if self.pipeline_times else [],
                "verdict_counts": self.verdict_counts
            },
            "token_usage": self.token_usage,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert results to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def save_json(self, filename: str):
        """Save results to JSON file."""
        with open(filename, 'w') as f:
            f.write(self.to_json())
    
    def print_summary(self):
        """Print a summary of benchmark results."""
        results = self.to_dict()
        
        print("\n===== VERIFACT BENCHMARK RESULTS =====\n")
        
        print("Component Performance:")
        table_data = [
            ["Claim Detection", f"{results['claim_detection']['average']:.2f}s", 
             f"{results['claim_detection']['min']:.2f}s", 
             f"{results['claim_detection']['max']:.2f}s"],
            ["Evidence Gathering", f"{results['evidence_gathering']['average']:.2f}s", 
             f"{results['evidence_gathering']['min']:.2f}s", 
             f"{results['evidence_gathering']['max']:.2f}s"],
            ["Verdict Generation", f"{results['verdict_generation']['average']:.2f}s", 
             f"{results['verdict_generation']['min']:.2f}s", 
             f"{results['verdict_generation']['max']:.2f}s"],
            ["Full Pipeline", f"{results['pipeline']['average']:.2f}s", 
             f"{results['pipeline']['min']:.2f}s", 
             f"{results['pipeline']['max']:.2f}s"]
        ]
        print(tabulate(table_data, headers=["Component", "Average", "Min", "Max"], tablefmt="grid"))
        
        print("\nPerformance Targets:")
        claim_detection_target = 5.0  # seconds
        evidence_gathering_target = 10.0  # seconds
        verdict_generation_target = 5.0  # seconds
        pipeline_target = 20.0  # seconds
        
        meets_targets = True
        target_data = [
            ["Claim Detection", f"{results['claim_detection']['average']:.2f}s", 
             f"{claim_detection_target:.2f}s", 
             "✅" if results['claim_detection']['average'] <= claim_detection_target else "❌"],
            ["Evidence Gathering", f"{results['evidence_gathering']['average']:.2f}s", 
             f"{evidence_gathering_target:.2f}s", 
             "✅" if results['evidence_gathering']['average'] <= evidence_gathering_target else "❌"],
            ["Verdict Generation", f"{results['verdict_generation']['average']:.2f}s", 
             f"{verdict_generation_target:.2f}s", 
             "✅" if results['verdict_generation']['average'] <= verdict_generation_target else "❌"],
            ["Full Pipeline", f"{results['pipeline']['average']:.2f}s", 
             f"{pipeline_target:.2f}s", 
             "✅" if results['pipeline']['average'] <= pipeline_target else "❌"]
        ]
        
        if results['claim_detection']['average'] > claim_detection_target:
            meets_targets = False
        if results['evidence_gathering']['average'] > evidence_gathering_target:
            meets_targets = False
        if results['verdict_generation']['average'] > verdict_generation_target:
            meets_targets = False
        if results['pipeline']['average'] > pipeline_target:
            meets_targets = False
            
        print(tabulate(target_data, headers=["Component", "Actual", "Target", "Status"], tablefmt="grid"))
        
        print(f"\nOverall Performance Status: {'✅ MEETS TARGETS' if meets_targets else '❌ BELOW TARGET'}")
        
        print("\nMetadata:")
        for key, value in results['metadata'].items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for subkey, subvalue in value.items():
                    print(f"    {subkey}: {subvalue}")
            else:
                print(f"  {key}: {value}")
    
    def plot_results(self, output_file: Optional[str] = None):
        """Plot benchmark results as charts."""
        results = self.to_dict()
        
        # Create figure with subplots
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('VeriFact Performance Benchmarks', fontsize=16)
        
        # Plot claim detection times
        axs[0, 0].bar(range(len(results["claim_detection"]["times"])), results["claim_detection"]["times"])
        axs[0, 0].axhline(y=results["claim_detection"]["average"], color='r', linestyle='-', label='Average')
        axs[0, 0].set_title('Claim Detection Time (s)')
        axs[0, 0].set_xlabel('Benchmark Run')
        axs[0, 0].set_ylabel('Time (s)')
        axs[0, 0].legend()
        
        # Plot evidence gathering times
        axs[0, 1].bar(range(len(results["evidence_gathering"]["times"])), results["evidence_gathering"]["times"])
        axs[0, 1].axhline(y=results["evidence_gathering"]["average"], color='r', linestyle='-', label='Average')
        axs[0, 1].set_title('Evidence Gathering Time (s)')
        axs[0, 1].set_xlabel('Benchmark Run')
        axs[0, 1].set_ylabel('Time (s)')
        axs[0, 1].legend()
        
        # Plot verdict generation times
        axs[1, 0].bar(range(len(results["verdict_generation"]["times"])), results["verdict_generation"]["times"])
        axs[1, 0].axhline(y=results["verdict_generation"]["average"], color='r', linestyle='-', label='Average')
        axs[1, 0].set_title('Verdict Generation Time (s)')
        axs[1, 0].set_xlabel('Benchmark Run')
        axs[1, 0].set_ylabel('Time (s)')
        axs[1, 0].legend()
        
        # Plot full pipeline times
        axs[1, 1].bar(range(len(results["pipeline"]["times"])), results["pipeline"]["times"])
        axs[1, 1].axhline(y=results["pipeline"]["average"], color='r', linestyle='-', label='Average')
        axs[1, 1].set_title('Full Pipeline Time (s)')
        axs[1, 1].set_xlabel('Benchmark Run')
        axs[1, 1].set_ylabel('Time (s)')
        axs[1, 1].legend()
        
        # Adjust layout
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # Save or show
        if output_file:
            plt.savefig(output_file)
            print(f"Plot saved to {output_file}")
        else:
            plt.show()


class Benchmarker:
    """Runner for VeriFact benchmarks."""
    
    BENCHMARK_CLAIMS = [
        "The Earth is approximately 4.54 billion years old.",
        "Water covers about 71% of the Earth's surface.",
        "Mount Everest is the highest mountain on Earth with a height of 8,848.86 meters above sea level.",
        "The average distance from Earth to the Sun is about 93 million miles (150 million kilometers).",
        "The Amazon rainforest produces approximately 20% of Earth's oxygen.",
        "There are 8 planets in our solar system.",
        "Human DNA is approximately 99.9% identical between individuals.",
        "The human brain contains about 86 billion neurons.",
        "The Great Wall of China is visible from space with the naked eye.",
        "Albert Einstein published his theory of general relativity in 1915."
    ]
    
    def __init__(self, args):
        """Initialize the benchmarker with command line arguments."""
        self.args = args
        self.results = BenchmarkResults()
        
        # Set up configuration and metadata
        self.results.set_metadata("command", f"python -m src.tests.test_benchmark_pipeline {' '.join(sys.argv[1:])}")
        self.results.set_metadata("environment", {
            "python_version": sys.version,
            "os": os.name,
            "cpu_count": os.cpu_count(),
        })
        self.results.set_metadata("configuration", {
            "claims": args.claims,
            "iterations": args.iterations,
            "output_format": args.format,
            "output_file": args.output
        })
    
    async def benchmark_claim_detector(self):
        """Benchmark the claim detector component."""
        print(f"\nBenchmarking Claim Detector ({self.args.iterations} iterations)...")
        
        # Create claim detector instance
        detector = ClaimDetector()
        
        for i in range(self.args.iterations):
            # Select claims for this iteration
            claims_to_test = self.BENCHMARK_CLAIMS[:self.args.claims]
            input_text = " ".join(claims_to_test)
            
            # Benchmark claim detection
            start_time = time.time()
            claims = await detector.detect_claims(input_text)
            end_time = time.time()
            
            # Record results
            duration = end_time - start_time
            token_usage = detector.get_token_usage()
            
            print(f"  Iteration {i+1}: {duration:.2f}s, {len(claims)} claims detected")
            self.results.add_claim_detection(duration, len(claims), token_usage)
    
    async def benchmark_evidence_hunter(self):
        """Benchmark the evidence hunter component."""
        print(f"\nBenchmarking Evidence Hunter ({self.args.iterations} iterations)...")
        
        # Create evidence hunter instance
        hunter = EvidenceHunter()
        
        for i in range(self.args.iterations):
            # Use a single claim for consistent benchmarking
            claim = self.BENCHMARK_CLAIMS[0]
            
            # Benchmark evidence gathering
            start_time = time.time()
            evidence = await hunter.gather_evidence(claim)
            end_time = time.time()
            
            # Record results
            duration = end_time - start_time
            token_usage = hunter.get_token_usage()
            
            print(f"  Iteration {i+1}: {duration:.2f}s, {len(evidence)} pieces of evidence gathered")
            self.results.add_evidence_gathering(duration, len(evidence), token_usage)
    
    async def benchmark_verdict_writer(self):
        """Benchmark the verdict writer component."""
        print(f"\nBenchmarking Verdict Writer ({self.args.iterations} iterations)...")
        
        # Create verdict writer instance
        writer = VerdictWriter()
        
        # Use a single claim and evidence set for consistent benchmarking
        claim = self.BENCHMARK_CLAIMS[0]
        evidence = [
            {
                "text": "Scientists have determined the Earth's age to be approximately 4.54 billion years.",
                "source": "https://example.com/earth-age",
                "credibility": 0.95,
            },
            {
                "text": "Research suggests that the Earth formed around 4.5 billion years ago, with an uncertainty of about 1%.",
                "source": "https://example.org/earth-formation",
                "credibility": 0.90,
            },
            {
                "text": "Multiple radiometric dating methods confirm the Earth is approximately 4.54 billion years old.",
                "source": "https://example.edu/geology/dating",
                "credibility": 0.98,
            }
        ]
        
        for i in range(self.args.iterations):
            # Benchmark verdict generation
            start_time = time.time()
            verdict = await writer.generate_verdict(claim, evidence)
            end_time = time.time()
            
            # Record results
            duration = end_time - start_time
            token_usage = writer.get_token_usage()
            
            print(f"  Iteration {i+1}: {duration:.2f}s, verdict: {verdict.verdict}")
            self.results.add_verdict_generation(duration, token_usage)
    
    async def benchmark_pipeline(self):
        """Benchmark the entire factchecking pipeline."""
        print(f"\nBenchmarking Full Pipeline ({self.args.iterations} iterations)...")
        
        # Create pipeline with configuration
        config = PipelineConfig(
            min_checkworthiness=0.5,  # Lower threshold to detect more claims in benchmark
            max_claims=self.args.claims,
            evidence_per_claim=3,
            timeout_seconds=300.0,  # Higher timeout for benchmarking
            enable_fallbacks=True,
            include_debug_info=True,
        )
        pipeline = FactcheckPipeline(config=config)
        
        for i in range(self.args.iterations):
            # Select input text for this iteration (combine multiple claims)
            input_text = " ".join(self.BENCHMARK_CLAIMS[:self.args.claims])
            
            # Benchmark full pipeline
            start_time = time.time()
            verdicts = await pipeline.process_text(input_text)
            end_time = time.time()
            
            # Record results
            duration = end_time - start_time
            claim_count = pipeline.stats.get("claims_detected", 0)
            evidence_count = pipeline.stats.get("evidence_gathered", 0)
            
            token_usage = {
                "claim_detection": pipeline.stats.get("claim_detection_tokens", 0),
                "evidence_gathering": pipeline.stats.get("evidence_gathering_tokens", 0),
                "verdict_generation": pipeline.stats.get("verdict_generation_tokens", 0),
                "total": pipeline.stats.get("total_tokens", 0)
            }
            
            print(f"  Iteration {i+1}: {duration:.2f}s, {len(verdicts)} verdicts generated")
            self.results.add_pipeline(duration, claim_count, evidence_count, len(verdicts), token_usage)
    
    async def run_benchmarks(self):
        """Run all benchmarks and report results."""
        print("=== VeriFact Performance Benchmarks ===")
        print(f"Claims: {self.args.claims}, Iterations: {self.args.iterations}")
        
        # Run individual component benchmarks
        await self.benchmark_claim_detector()
        await self.benchmark_evidence_hunter()
        await self.benchmark_verdict_writer()
        
        # Run full pipeline benchmark
        await self.benchmark_pipeline()
        
        # Report results
        self.results.print_summary()
        
        # Save results if output file specified
        if self.args.output:
            if self.args.format == "json":
                self.results.save_json(self.args.output)
            elif self.args.format == "plot":
                self.results.plot_results(self.args.output)
            else:
                print(f"Unknown output format: {self.args.format}")
        
        # Show plot if requested
        if self.args.plot:
            self.results.plot_results()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run VeriFact performance benchmarks")
    
    parser.add_argument("--claims", type=int, default=3, help="Number of claims to include (1-10)")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations for each benchmark")
    parser.add_argument("--format", choices=["json", "plot"], default="json", help="Output format")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--plot", action="store_true", help="Show plot of results")
    
    args = parser.parse_args()
    
    # Validate args
    args.claims = max(1, min(args.claims, 10))  # Clamp claims between 1-10
    args.iterations = max(1, args.iterations)  # At least 1 iteration
    
    return args


async def main():
    """Main entry point."""
    args = parse_args()
    benchmarker = Benchmarker(args)
    await benchmarker.run_benchmarks()


if __name__ == "__main__":
    asyncio.run(main()) 