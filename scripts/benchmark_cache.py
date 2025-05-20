#!/usr/bin/env python
"""
Benchmark script for the cache layer performance.

This script tests the performance of the Redis cache for evidence gathering.
"""

import os
import sys
import time
import json
import asyncio
import argparse
import statistics
from typing import List, Dict, Any
import random

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.evidence_hunter.hunter import EvidenceHunter, Evidence
from src.agents.claim_detector.detector import Claim
from src.utils.cache.cache import evidence_cache
from src.utils.metrics import evidence_metrics
from src.utils.logger import get_component_logger

# Initialize logger
logger = get_component_logger("benchmark")

# Sample claims for benchmarking
SAMPLE_CLAIMS = [
    "The Earth is round.",
    "Water boils at 100 degrees Celsius at sea level.",
    "The Great Wall of China is visible from space.",
    "Humans have been to the Moon.",
    "Vaccines cause autism.",
    "Climate change is not caused by human activities.",
    "The COVID-19 pandemic started in Wuhan, China.",
    "The United States has 50 states.",
    "Napoleon Bonaparte was born in France.",
    "Coffee is the world's most valuable traded commodity after oil."
]


async def run_benchmark(
    num_iterations: int = 3,
    cache_enabled: bool = True,
    clear_cache: bool = True,
    unique_claims: bool = False,
) -> Dict[str, Any]:
    """
    Run a benchmark of the evidence hunter with and without caching.
    
    Args:
        num_iterations: Number of iterations to run
        cache_enabled: Whether to enable the cache
        clear_cache: Whether to clear the cache before running
        unique_claims: Whether to use unique claims for each iteration
        
    Returns:
        Dict[str, Any]: Benchmark results
    """
    # Initialize evidence hunter
    hunter = EvidenceHunter()
    
    # Clear cache if requested
    if clear_cache:
        evidence_cache.clear_namespace()
        logger.info("Cache cleared for benchmarking")
    
    # Reset metrics
    evidence_metrics.reset()
    
    # Track timings
    timings = {
        "cache_enabled": cache_enabled,
        "iterations": num_iterations,
        "claim_timings": [],
        "summary": {}
    }
    
    # Run the benchmark
    for i in range(num_iterations):
        if unique_claims:
            # Use a different claim for each iteration
            claim_idx = i % len(SAMPLE_CLAIMS)
            claim_text = SAMPLE_CLAIMS[claim_idx]
        else:
            # Always use the same claim to test caching
            claim_text = SAMPLE_CLAIMS[0]
        
        claim = Claim(
            text=claim_text,
            context="Testing cache performance",
            source="benchmark",
            confidence=1.0
        )
        
        # Create a temp environment variable to toggle cache for this run
        original_enabled = os.environ.get("REDIS_ENABLED", "true")
        if not cache_enabled:
            os.environ["REDIS_ENABLED"] = "false"
        
        # Measure time
        start_time = time.time()
        
        try:
            # Gather evidence
            evidence = await hunter.gather_evidence(claim)
            
            elapsed = time.time() - start_time
            
            # Record timing
            timings["claim_timings"].append({
                "iteration": i + 1,
                "claim": claim_text,
                "time_seconds": elapsed,
                "evidence_count": len(evidence) if evidence else 0,
                "cache_hit": i > 0 and not unique_claims and cache_enabled
            })
            
            logger.info(f"Iteration {i + 1}/{num_iterations} completed in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in benchmark iteration {i + 1}: {str(e)}")
        finally:
            # Restore original environment
            os.environ["REDIS_ENABLED"] = original_enabled
    
    # Calculate summary statistics
    if timings["claim_timings"]:
        times = [entry["time_seconds"] for entry in timings["claim_timings"]]
        timings["summary"] = {
            "total_time": sum(times),
            "mean_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0
        }
        
        # Add cache metrics
        if cache_enabled:
            timings["cache_metrics"] = evidence_metrics.stats()
    
    return timings


async def compare_performance(iterations: int = 3, unique_claims: bool = False) -> Dict[str, Any]:
    """
    Compare performance with and without caching.
    
    Args:
        iterations: Number of iterations to run
        unique_claims: Whether to use unique claims for each iteration
        
    Returns:
        Dict[str, Any]: Comparison results
    """
    # Clear cache before running
    evidence_cache.clear_namespace()
    
    logger.info("Running benchmark WITHOUT cache...")
    no_cache_results = await run_benchmark(
        num_iterations=iterations,
        cache_enabled=False,
        unique_claims=unique_claims
    )
    
    logger.info("Running benchmark WITH cache...")
    with_cache_results = await run_benchmark(
        num_iterations=iterations,
        cache_enabled=True,
        unique_claims=unique_claims
    )
    
    # Calculate performance improvement
    no_cache_mean = no_cache_results["summary"]["mean_time"]
    with_cache_mean = with_cache_results["summary"]["mean_time"]
    
    improvement = {
        "without_cache_mean": no_cache_mean,
        "with_cache_mean": with_cache_mean,
        "time_saved": no_cache_mean - with_cache_mean,
        "percentage_improvement": ((no_cache_mean - with_cache_mean) / no_cache_mean) * 100 if no_cache_mean > 0 else 0,
        "cache_metrics": with_cache_results.get("cache_metrics", {})
    }
    
    return {
        "without_cache": no_cache_results,
        "with_cache": with_cache_results,
        "improvement": improvement
    }


async def run_claim_variants(base_claims: List[str], variants_per_claim: int = 3) -> Dict[str, Any]:
    """
    Test cache effectiveness with claim variants.
    
    Args:
        base_claims: List of base claims to test
        variants_per_claim: Number of variants to generate per claim
        
    Returns:
        Dict[str, Any]: Results of the variant testing
    """
    # Clear cache before running
    evidence_cache.clear_namespace()
    
    # Initialize evidence hunter
    hunter = EvidenceHunter()
    
    results = {
        "base_claims": base_claims,
        "variants_per_claim": variants_per_claim,
        "variant_results": []
    }
    
    for base_claim in base_claims:
        claim_results = {
            "base_claim": base_claim,
            "variants": [],
            "cache_hits": 0
        }
        
        # First, run the base claim to ensure it's cached
        base_claim_obj = Claim(
            text=base_claim,
            context="Testing cache with variants",
            source="benchmark",
            confidence=1.0
        )
        
        # Get evidence for base claim (this should cache it)
        await hunter.gather_evidence(base_claim_obj)
        
        # Now test variants
        for i in range(variants_per_claim):
            # Create a variant by adding/removing words or changing capitalization
            variant = create_claim_variant(base_claim)
            
            variant_obj = Claim(
                text=variant,
                context="Testing cache with variants",
                source="benchmark",
                confidence=1.0
            )
            
            # Reset metrics
            evidence_metrics.reset()
            
            # Measure time
            start_time = time.time()
            
            # Gather evidence
            evidence = await hunter.gather_evidence(variant_obj)
            
            elapsed = time.time() - start_time
            
            # Check if it was a cache hit
            cache_hit = evidence_metrics.hits > 0
            
            # Record results
            variant_result = {
                "variant": variant,
                "cache_hit": cache_hit,
                "time_seconds": elapsed,
                "cache_key": hunter._generate_cache_key(variant_obj),
                "base_key": hunter._generate_cache_key(base_claim_obj)
            }
            
            claim_results["variants"].append(variant_result)
            
            if cache_hit:
                claim_results["cache_hits"] += 1
        
        # Add claim results to overall results
        claim_results["hit_rate"] = claim_results["cache_hits"] / variants_per_claim if variants_per_claim > 0 else 0
        results["variant_results"].append(claim_results)
    
    # Calculate overall hit rate
    total_variants = len(base_claims) * variants_per_claim
    total_hits = sum(claim_result["cache_hits"] for claim_result in results["variant_results"])
    results["overall_hit_rate"] = total_hits / total_variants if total_variants > 0 else 0
    
    return results


def create_claim_variant(original_claim: str) -> str:
    """
    Create a variant of a claim that should still hit the same cache entry.
    
    Args:
        original_claim: The original claim
        
    Returns:
        str: A variant of the claim
    """
    # Create a list of possible transformations
    transformations = [
        # Capitalization changes
        lambda s: s.lower(),
        lambda s: s.upper(),
        lambda s: s.capitalize(),
        
        # Punctuation changes
        lambda s: s + ".",
        lambda s: s + "!",
        lambda s: s + "?",
        lambda s: s.replace(".", ""),
        
        # Whitespace changes
        lambda s: s + " ",
        lambda s: " " + s,
        lambda s: s.replace(" ", "  "),
        
        # Minor word changes (that shouldn't affect the meaning)
        lambda s: s.replace("is", "is really"),
        lambda s: s.replace("the", "the actual"),
        lambda s: "I believe that " + s,
        lambda s: "It is claimed that " + s,
    ]
    
    # Choose a random transformation
    transform = random.choice(transformations)
    return transform(original_claim)


def save_results(results: Dict[str, Any], filename: str) -> None:
    """
    Save benchmark results to a file.
    
    Args:
        results: The results to save
        filename: The filename to save to
    """
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {filename}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark the cache performance")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations")
    parser.add_argument("--unique", action="store_true", help="Use unique claims for each iteration")
    parser.add_argument("--variants", type=int, default=3, help="Number of variants per claim")
    parser.add_argument("--output", type=str, default="cache_benchmark_results.json", help="Output file")
    
    args = parser.parse_args()
    
    logger.info("Starting cache benchmark")
    
    # Run the benchmark with and without cache
    comparison = await compare_performance(args.iterations, args.unique)
    
    # Test with claim variants
    variant_results = await run_claim_variants(SAMPLE_CLAIMS[:3], args.variants)
    
    # Combine results
    results = {
        "timestamp": time.time(),
        "parameters": vars(args),
        "performance_comparison": comparison,
        "variant_testing": variant_results
    }
    
    # Print summary
    improvement = comparison["improvement"]
    print("\n===== Cache Performance Summary =====")
    print(f"Mean time without cache: {improvement['without_cache_mean']:.2f}s")
    print(f"Mean time with cache: {improvement['with_cache_mean']:.2f}s")
    print(f"Time saved: {improvement['time_saved']:.2f}s")
    print(f"Improvement: {improvement['percentage_improvement']:.2f}%")
    print(f"Cache hit rate: {variant_results['overall_hit_rate'] * 100:.2f}%")
    
    # Save results
    save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main()) 