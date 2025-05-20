#!/usr/bin/env python
"""Command-line interface for Verifact factchecking.

This module provides a command-line interface for accessing
Verifact factchecking capabilities without using the API.
"""

import argparse
import asyncio
import csv
import io
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

import colorama
from colorama import Fore, Style
from rich.console import Console
from rich.panel import Panel
from tqdm import tqdm

from src.pipeline import PipelineConfig, PipelineEvent
from src.utils.exceptions import InputTooLongError, ValidationError, VerifactError
from src.utils.logger import configure_logging
from src.utils.validation import sanitize_text, validate_text_length

# Initialize colorama for cross-platform color support
colorama.init()

# Constants
DEFAULT_TEST_DATA_PATH = "src/tests/data/test_claims.json"
MAX_TEXT_DISPLAY_LENGTH = 100  # Maximum length of text to display in console output

# Color definitions for different verdicts
VERDICT_COLORS = {
    "true": Fore.GREEN,
    "false": Fore.RED,
    "partially_true": Fore.YELLOW,
    "unverifiable": Fore.BLUE,
    "misleading": Fore.MAGENTA,
    "outdated": Fore.CYAN,
}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="VeriFact - AI-powered factchecking tool",
        epilog="Example: python -m src.cli --file article.txt",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Factcheck command
    factcheck_parser = subparsers.add_parser(
        "factcheck", help="Factcheck text from various sources"
    )

    # Input options for factcheck
    input_group = factcheck_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-t", "--text", help="Text to factcheck")
    input_group.add_argument("-f", "--file", help="File containing text to factcheck")
    input_group.add_argument("-u", "--url", help="URL to fetch and factcheck content from")

    # Output options for factcheck
    factcheck_parser.add_argument(
        "-o", "--output", help="Output file for results (default: stdout)"
    )
    factcheck_parser.add_argument(
        "--format",
        choices=["json", "text", "csv"],
        default="text",
        help="Output format (default: text)",
    )

    # Pipeline options for factcheck
    factcheck_parser.add_argument("--claim-model", help="Model to use for claim detection")
    factcheck_parser.add_argument("--evidence-model", help="Model to use for evidence gathering")
    factcheck_parser.add_argument("--verdict-model", help="Model to use for verdict generation")
    factcheck_parser.add_argument(
        "--min-checkworthiness",
        type=float,
        default=0.5,
        help="Minimum checkworthiness threshold (0-1)",
    )
    factcheck_parser.add_argument(
        "--max-claims", type=int, help="Maximum number of claims to process"
    )
    factcheck_parser.add_argument(
        "--evidence-per-claim",
        type=int,
        default=5,
        help="Number of evidence items to gather per claim",
    )
    factcheck_parser.add_argument("--timeout", type=float, default=120.0, help="Timeout in seconds")
    factcheck_parser.add_argument(
        "--no-fallbacks", action="store_true", help="Disable model fallbacks"
    )
    factcheck_parser.add_argument(
        "--retries", type=int, default=2, help="Number of retry attempts for failed operations"
    )
    factcheck_parser.add_argument(
        "--silent", action="store_true", help="Do not show progress indicators"
    )
    factcheck_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    factcheck_parser.add_argument(
        "--debug", action="store_true", help="Include debug information in output"
    )
    factcheck_parser.add_argument(
        "--verbose", action="store_true", help="Show verbose progress updates"
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests on sample datasets")
    test_parser.add_argument(
        "--dataset",
        default=DEFAULT_TEST_DATA_PATH,
        help=f"Path to test dataset (default: {DEFAULT_TEST_DATA_PATH})",
    )
    test_parser.add_argument(
        "--filter", help="Filter tests by category (e.g., 'political', 'scientific')"
    )
    test_parser.add_argument(
        "--level",
        choices=["easy", "medium", "hard", "all"],
        default="all",
        help="Filter tests by difficulty level (default: all)",
    )
    test_parser.add_argument(
        "--timeout", type=float, default=300.0, help="Timeout for entire test run in seconds"
    )
    test_parser.add_argument("--output", help="Output file for test results")
    test_parser.add_argument(
        "--format",
        choices=["json", "text", "csv"],
        default="text",
        help="Output format for test results (default: text)",
    )
    test_parser.add_argument("--verbose", action="store_true", help="Show verbose test progress")

    # Version command
    subparsers.add_parser("version", help="Show version information")

    return parser.parse_args()


def build_pipeline_config(args) -> PipelineConfig:
    """Build pipeline configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        PipelineConfig object
    """
    config_args = {
        "claim_detection_threshold": args.min_checkworthiness,
        "max_claims": args.max_claims if hasattr(args, "max_claims") and args.max_claims else 10,
        "max_evidence_per_claim": (
            args.evidence_per_claim if hasattr(args, "evidence_per_claim") else 5
        ),
    }

    # Add model-specific settings if provided
    if hasattr(args, "claim_model") and args.claim_model:
        config_args["claim_detector_model"] = args.claim_model
    if hasattr(args, "evidence_model") and args.evidence_model:
        config_args["evidence_hunter_model"] = args.evidence_model
    if hasattr(args, "verdict_model") and args.verdict_model:
        config_args["verdict_writer_model"] = args.verdict_model

    return PipelineConfig(**config_args)


def create_progress_callback(total_claims: int, use_progress_bar: bool = True):
    """Create a callback for tracking pipeline progress.

    Args:
        total_claims: Total number of claims to process
        use_progress_bar: Whether to use a progress bar

    Returns:
        A callback function
    """
    if not use_progress_bar:
        return lambda event, data: None

    pbar = tqdm(total=100, desc="Overall progress", unit="%")

    def progress_callback(event: PipelineEvent, data: dict[str, Any]):
        """Handle progress events from the pipeline."""
        if event == PipelineEvent.STAGE_STARTED and "message" in data:
            stage = data.get("stage", "")
            tqdm.write(f"{Fore.CYAN}Progress: {data['message']}{Style.RESET_ALL}")

            # Update progress bar based on stage
            if stage == "claim_detection":
                pbar.update(5)
            elif stage == "evidence_gathering_started":
                pbar.update(10)
            elif stage == "verdict_generation_started":
                pbar.update(40)
            elif stage == "complete":
                pbar.update(100 - pbar.n)  # Complete the progress

        elif event == PipelineEvent.CLAIM_DETECTED:
            tqdm.write(
                f"  {Fore.GREEN}Claim detected: {truncate_text(data.get('claim', ''))}{Style.RESET_ALL}"
            )

        elif event == PipelineEvent.EVIDENCE_GATHERED:
            claim = data.get("claim", "")
            count = data.get("count", 0)
            tqdm.write(
                f"  {Fore.YELLOW}Evidence gathered for: {truncate_text(claim)} ({count} items){Style.RESET_ALL}"
            )
            pbar.update(5)

        elif event == PipelineEvent.VERDICT_GENERATED:
            claim = data.get("claim", "")
            verdict = data.get("verdict", "")
            verdict_color = VERDICT_COLORS.get(verdict.lower(), Fore.WHITE)
            tqdm.write(
                f"  {verdict_color}Verdict for: {truncate_text(claim)} - {verdict.upper()}{Style.RESET_ALL}"
            )

        elif event == PipelineEvent.ERROR:
            tqdm.write(f"{Fore.RED}Error: {data.get('error', 'Unknown error')}{Style.RESET_ALL}")

        elif event == PipelineEvent.WARNING:
            tqdm.write(
                f"{Fore.YELLOW}Warning: {data.get('message', 'Unknown warning')}{Style.RESET_ALL}"
            )

    return progress_callback


def truncate_text(text: str, max_length: int = MAX_TEXT_DISPLAY_LENGTH) -> str:
    """Truncate text to a maximum length for display purposes."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def format_results_as_text(verdicts, stats, use_color: bool = True):
    """Format factchecking results as text for display.

    Args:
        verdicts: List of verdict objects
        stats: Processing statistics
        use_color: Whether to use colored output

    Returns:
        Formatted text output
    """
    Console(color_system="auto" if use_color else None)

    # Check if we have any results
    if not verdicts:
        return "No claims were found that met the check-worthiness threshold."

    # Format results
    output = []

    # Add header
    output.append("\n=== VeriFact Results ===\n")

    # Add summary
    output.append(f"Found {len(verdicts)} claim(s) to verify")

    if stats and "processing_time" in stats:
        output.append(f"Processing time: {stats['processing_time']:.2f} seconds")

    # Add claims and verdicts
    for i, verdict in enumerate(verdicts, 1):
        # Create heading
        claim_text = truncate_text(verdict.claim)

        # Create panel with the verdict information
        panel_content = []

        # Add the verdict assessment
        verdict_text = f"Verdict: {verdict.verdict.upper()}"
        if hasattr(verdict, "confidence") and verdict.confidence is not None:
            verdict_text += f" (Confidence: {verdict.confidence:.0%})"

        panel_content.append(verdict_text)

        # Add explanation if available
        if hasattr(verdict, "explanation") and verdict.explanation:
            panel_content.append(f"\nExplanation: {verdict.explanation}")

        # Add sources if available
        if hasattr(verdict, "sources") and verdict.sources:
            source_list = "\n".join(f"- {s}" for s in verdict.sources)
            panel_content.append(f"\nSources:\n{source_list}")

        # Create and add panel to output
        panel_str = str(Panel(
            "\n".join(panel_content),
            title=f"Claim {i}: {claim_text}",
            expand=False,
            padding=(1, 2),
        ))
        output.append(panel_str)

    # Return formatted output
    return "\n".join(output)


def format_results_as_csv(verdicts, stats):
    """Format results as CSV.

    Args:
        verdicts: List of verdict objects
        stats: Statistics dictionary

    Returns:
        CSV formatted string
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write header
    writer.writerow(
        [
            "Claim",
            "Verdict",
            "Confidence",
            "Explanation",
            "Sources",
            "Evidence Count",
            "Generated At",
        ]
    )

    # Write data rows
    for verdict in verdicts:
        sources_str = "; ".join(verdict.sources)
        evidence_count = len(verdict.key_evidence) if hasattr(verdict, "key_evidence") else 0
        generated_at = verdict.generated_at.isoformat() if hasattr(verdict, "generated_at") else ""

        writer.writerow(
            [
                verdict.claim,
                verdict.verdict,
                f"{verdict.confidence:.2f}",
                verdict.explanation,
                sources_str,
                evidence_count,
                generated_at,
            ]
        )

    # Add stats as comment rows
    writer.writerow([])
    writer.writerow(["# Statistics"])
    writer.writerow(
        [
            "Processing time (s)",
            f"{stats.get('processing_time_seconds', stats.get('total_processing_time', 0)):.2f}",
        ]
    )
    writer.writerow(["Claims detected", stats.get("claims_detected", 0)])
    writer.writerow(["Evidence gathered", stats.get("evidence_gathered", 0)])
    writer.writerow(["Verdicts generated", stats.get("verdicts_generated", 0)])

    return output.getvalue()


async def run_pipeline(text, config, progress_callback=None):
    """Run the factchecking pipeline.

    Args:
        text: Input text to process
        config: Pipeline configuration
        progress_callback: Callback function for progress updates

    Returns:
        Tuple of (verdicts, stats)
    """
    from src.pipeline.factcheck_pipeline import create_default_pipeline

    pipeline = create_default_pipeline(config=config)

    if progress_callback:
        # Register for progress events
        pipeline.register_event_handler(PipelineEvent.STAGE_STARTED, progress_callback)
        pipeline.register_event_handler(PipelineEvent.CLAIM_DETECTED, progress_callback)
        pipeline.register_event_handler(PipelineEvent.EVIDENCE_GATHERED, progress_callback)
        pipeline.register_event_handler(PipelineEvent.VERDICT_GENERATED, progress_callback)
        pipeline.register_event_handler(PipelineEvent.ERROR, progress_callback)
        pipeline.register_event_handler(PipelineEvent.WARNING, progress_callback)

    verdicts = await pipeline.process_text(text)
    return verdicts, pipeline.stats


def fetch_url_content(url: str) -> str:
    """Fetch content from a URL.

    Args:
        url: URL to fetch content from

    Returns:
        Text content from the URL

    Raises:
        ValueError: If URL is invalid or content cannot be fetched
    """
    # Validate URL
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
    except Exception:
        raise ValueError("Invalid URL format") from None

    # Fetch content
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode("utf-8")
            return content
    except urllib.error.URLError as e:
        raise ValueError(f"Failed to fetch URL: {str(e)}") from e
    except UnicodeDecodeError as e:
        raise ValueError("Failed to decode content as UTF-8") from e


def load_test_dataset(path: str) -> list[dict[str, Any]]:
    """Load test dataset from a JSON file.

    Args:
        path: Path to the test dataset file

    Returns:
        List of test cases

    Raises:
        ValidationError: If file cannot be loaded or parsed
    """
    try:
        with open(path, encoding="utf-8") as f:
            dataset = json.load(f)

            # Handle both formats:
            # 1. A list of test cases directly
            # 2. A dictionary with a 'test_cases' key containing the list
            if isinstance(dataset, list):
                return dataset
            elif isinstance(dataset, dict) and "test_cases" in dataset:
                return dataset["test_cases"]
            else:
                raise ValidationError(
                    code="INVALID_DATASET",
                    message="Invalid test dataset format",
                    details={
                        "reason": "Dataset must be a list of test cases or a dictionary with a 'test_cases' key"
                    },
                )
    except FileNotFoundError as e:
        raise ValidationError(
            code="FILE_NOT_FOUND",
            message=f"Test dataset file not found: {path}",
            details={"path": path},
        ) from e
    except json.JSONDecodeError as e:
        raise ValidationError(
            code="INVALID_JSON",
            message="Invalid JSON in test dataset",
            details={"path": path, "error": str(e)},
        ) from e


def filter_test_cases(
    test_cases: list[dict[str, Any]], category: str | None = None, level: str | None = None
) -> list[dict[str, Any]]:
    """Filter test cases by category and level.

    Args:
        test_cases: List of test cases
        category: Category to filter by
        level: Difficulty level to filter by

    Returns:
        Filtered list of test cases
    """
    filtered_cases = test_cases

    if category:
        filtered_cases = [
            tc for tc in filtered_cases if tc.get("category", "").lower() == category.lower()
        ]

    if level and level != "all":
        filtered_cases = [
            tc
            for tc in filtered_cases
            if tc.get("level", tc.get("difficulty", "")).lower() == level.lower()
        ]

    return filtered_cases


async def run_test(
    test_case: dict[str, Any], config: PipelineConfig, verbose: bool = False
) -> dict[str, Any]:
    """Run a single test case.

    Args:
        test_case: Test case dictionary
        config: Pipeline configuration
        verbose: Whether to show verbose progress

    Returns:
        Test result dictionary
    """
    claim = test_case.get("claim", "")
    expected_verdict = test_case.get("expected_verdict", "")

    start_time = time.time()

    try:
        # Create progress callback if verbose
        progress_callback = None
        if verbose:

            def simple_progress(event, data):
                if event == PipelineEvent.STAGE_STARTED and "message" in data:
                    print(f"  Progress: {data['message']}")
                elif event == PipelineEvent.CLAIM_DETECTED:
                    print(f"  Detected claim: {data.get('claim', '')[:50]}...")
                elif event == PipelineEvent.VERDICT_GENERATED:
                    print(f"  Generated verdict: {data.get('verdict', '')}")

            progress_callback = simple_progress

        # Create a request object using our Pydantic model
        from src.models.factcheck import FactcheckRequest
        request = FactcheckRequest(
            text=claim,
            options={
                "max_claims": 1,  # We're testing a single claim
                "min_checkworthiness": 0.0,  # Ensure the claim is checked regardless of score
            },
        )

        # Run the pipeline
        response = await run_pipeline(request.text, config, progress_callback)

        if isinstance(response, tuple) and len(response) == 2:
            verdicts, stats = response
        else:
            # Handle the case where run_pipeline might return just verdicts
            verdicts = response

        # Get the first verdict (there should only be one since we're checking a single claim)
        actual_verdict = None
        if verdicts and len(verdicts) > 0:
            actual_verdict = (
                verdicts[0].verdict
                if hasattr(verdicts[0], "verdict")
                else verdicts[0].get("verdict", "")
            )

        # Check if verdict matches expected
        verdict_correct = False
        if actual_verdict:
            verdict_correct = expected_verdict.lower() == actual_verdict.lower()

        elapsed = time.time() - start_time

        return {
            "test_id": test_case.get("id", ""),
            "category": test_case.get("category", ""),
            "level": test_case.get("level", test_case.get("difficulty", "")),
            "claim": claim,
            "expected_verdict": expected_verdict,
            "actual_verdict": actual_verdict,
            "correct": verdict_correct,
            "processing_time": elapsed,
            "metadata": test_case.get("metadata", {}),
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "test_id": test_case.get("id", ""),
            "category": test_case.get("category", ""),
            "level": test_case.get("level", test_case.get("difficulty", "")),
            "claim": claim,
            "expected_verdict": expected_verdict,
            "actual_verdict": None,
            "error": str(e),
            "processing_time": elapsed,
            "correct": False,
        }


async def run_tests(
    test_cases: list[dict[str, Any]], config: PipelineConfig, verbose: bool = False
) -> dict[str, Any]:
    """Run multiple test cases and summarize results.

    Args:
        test_cases: List of test cases to run
        config: Pipeline configuration
        verbose: Whether to show verbose progress

    Returns:
        Dictionary with test summary and results
    """
    if not test_cases:
        return {"total_cases": 0, "total_correct": 0, "total_accuracy": 0, "results": []}

    print(f"Running {len(test_cases)} test cases...")
    results = []

    with tqdm(total=len(test_cases), disable=verbose) as progress_bar:
        for i, test_case in enumerate(test_cases):
            test_id = test_case.get("id", f"test-{i + 1}")
            category = test_case.get("category", "unknown")
            level = test_case.get("level", test_case.get("difficulty", "unknown"))

            if verbose:
                print(f"\nRunning test {test_id} (Category: {category}, Level: {level})")
                print(f"Claim: {test_case.get('claim', '')}")
                print(f"Expected verdict: {test_case.get('expected_verdict', '')}")

            # Run the test
            result = await run_test(test_case, config, verbose)
            results.append(result)

            # Update progress
            progress_bar.update(1)

            # Print result if verbose
            if verbose:
                if "error" in result:
                    print(f"  {Fore.RED}Error: {result['error']}{Style.RESET_ALL}")
                else:
                    correct = result["correct"]
                    color = Fore.GREEN if correct else Fore.RED
                    mark = "✓" if correct else "✗"
                    print(
                        f"  {color}{mark} Result: {result['actual_verdict']} (Expected: {result['expected_verdict']}){Style.RESET_ALL}"
                    )
                    print(f"  Processing time: {result['processing_time']:.2f}s")

    # Aggregate results
    total_correct = sum(1 for r in results if r.get("correct", False))
    total_cases = len(results)
    total_accuracy = total_correct / total_cases if total_cases > 0 else 0

    # Calculate stats by category
    categories = sorted({r["category"] for r in results})
    category_stats = {}

    for category in categories:
        category_results = [r for r in results if r["category"] == category]
        correct = sum(1 for r in category_results if r.get("correct", False))
        total = len(category_results)
        accuracy = correct / total if total > 0 else 0

        category_stats[category] = {"total": total, "correct": correct, "accuracy": accuracy}

    # Calculate stats by difficulty level
    levels = sorted({r["level"] for r in results})
    level_stats = {}

    for level in levels:
        level_results = [r for r in results if r["level"] == level]
        correct = sum(1 for r in level_results if r.get("correct", False))
        total = len(level_results)
        accuracy = correct / total if total > 0 else 0

        level_stats[level] = {"total": total, "correct": correct, "accuracy": accuracy}

    # Calculate verdict type stats
    verdict_types = {}
    for r in results:
        expected = r.get("expected_verdict", "")
        if expected:
            if expected not in verdict_types:
                verdict_types[expected] = {"total": 0, "correct": 0}

            verdict_types[expected]["total"] += 1
            if r.get("correct", False):
                verdict_types[expected]["correct"] += 1

    for vt in verdict_types:
        verdict_types[vt]["accuracy"] = (
            verdict_types[vt]["correct"] / verdict_types[vt]["total"]
            if verdict_types[vt]["total"] > 0
            else 0
        )

    # Calculate average processing time
    avg_processing_time = (
        sum(r.get("processing_time", 0) for r in results) / len(results) if results else 0
    )

    return {
        "total_cases": total_cases,
        "total_correct": total_correct,
        "total_accuracy": total_accuracy,
        "category_stats": category_stats,
        "level_stats": level_stats,
        "verdict_stats": verdict_types,
        "avg_processing_time": avg_processing_time,
        "results": results,
    }


def format_test_results_as_text(
    summary: dict[str, Any], detailed: bool = False, use_color: bool = True
) -> str:
    """Format test results as text.

    Args:
        summary: Test summary dictionary
        detailed: Whether to include detailed test results
        use_color: Whether to use colored output

    Returns:
        Formatted text output
    """
    lines = []

    # Setup colors
    header_style = Fore.CYAN + Style.BRIGHT if use_color else ""
    reset_style = Style.RESET_ALL if use_color else ""

    lines.append(f"{header_style}VeriFact Test Results{reset_style}")
    lines.append("=" * 30)

    # Overall summary
    accuracy = summary["total_accuracy"]
    accuracy_color = ""
    if use_color:
        if accuracy >= 0.8:
            accuracy_color = Fore.GREEN
        elif accuracy >= 0.5:
            accuracy_color = Fore.YELLOW
        else:
            accuracy_color = Fore.RED

    lines.append(
        f"Overall Accuracy: {accuracy_color}{accuracy:.1%}{reset_style} ({summary['total_correct']}/{summary['total_cases']})"
    )
    lines.append(f"Total Test Cases: {summary['total_cases']}")
    if "avg_processing_time" in summary:
        lines.append(f"Average Processing Time: {summary['avg_processing_time']:.2f}s")
    lines.append("")

    # Results by category
    lines.append(f"{header_style}Results by Category:{reset_style}")
    for category, cat_results in summary["category_stats"].items():
        cat_accuracy = cat_results["accuracy"]
        cat_color = ""
        if use_color:
            if cat_accuracy >= 0.8:
                cat_color = Fore.GREEN
            elif cat_accuracy >= 0.5:
                cat_color = Fore.YELLOW
            else:
                cat_color = Fore.RED

        lines.append(
            f"  {category}: {cat_color}{cat_accuracy:.1%}{reset_style} ({cat_results['correct']}/{cat_results['total']})"
        )

    lines.append("")

    # Results by difficulty
    lines.append(f"{header_style}Results by Difficulty:{reset_style}")
    for difficulty, diff_results in summary["level_stats"].items():
        diff_accuracy = diff_results["accuracy"]
        diff_color = ""
        if use_color:
            if diff_accuracy >= 0.8:
                diff_color = Fore.GREEN
            elif diff_accuracy >= 0.5:
                diff_color = Fore.YELLOW
            else:
                diff_color = Fore.RED

        lines.append(
            f"  {difficulty}: {diff_color}{diff_accuracy:.1%}{reset_style} ({diff_results['correct']}/{diff_results['total']})"
        )

    # Results by verdict type
    if "verdict_stats" in summary:
        lines.append("")
        lines.append(f"{header_style}Results by Verdict Type:{reset_style}")
        for verdict_type, verdict_results in summary["verdict_stats"].items():
            vt_accuracy = verdict_results["accuracy"]
            vt_color = ""
            if use_color:
                if vt_accuracy >= 0.8:
                    vt_color = Fore.GREEN
                elif vt_accuracy >= 0.5:
                    vt_color = Fore.YELLOW
                else:
                    vt_color = Fore.RED

            # Use the color mapping from VERDICT_COLORS if available
            type_color = ""
            if use_color and verdict_type.lower() in VERDICT_COLORS:
                type_color = VERDICT_COLORS[verdict_type.lower()]

            lines.append(
                f"  {type_color}{verdict_type}{reset_style}: {vt_color}{vt_accuracy:.1%}{reset_style} ({verdict_results['correct']}/{verdict_results['total']})"
            )

    # Detailed results
    if detailed:
        lines.append("")
        lines.append(f"{header_style}Detailed Test Results:{reset_style}")

        for i, result in enumerate(summary["results"], 1):
            test_id = result.get("test_id", f"case-{i}")
            category = result.get("category", "unknown")
            difficulty = result.get("level", "unknown")

            lines.append(f"\nTest {i}: {test_id} ({category}, {difficulty})")

            if "claim" in result:
                lines.append(f"  Claim: {truncate_text(result['claim'])}")

            if "error" in result:
                lines.append(f"  {Fore.RED}Error: {result['error']}{reset_style}")
            else:
                correct = result.get("correct", False)
                mark = "✓" if correct else "✗"
                color = Fore.GREEN if correct else Fore.RED

                expected_verdict = result.get("expected_verdict", "")
                actual_verdict = result.get("actual_verdict", "")

                # Use verdict colors if available
                expected_color = ""
                actual_color = ""
                if use_color:
                    if expected_verdict.lower() in VERDICT_COLORS:
                        expected_color = VERDICT_COLORS[expected_verdict.lower()]
                    if actual_verdict and actual_verdict.lower() in VERDICT_COLORS:
                        actual_color = VERDICT_COLORS[actual_verdict.lower()]

                lines.append(
                    f"  {color}{mark}{reset_style} Result: {actual_color}{actual_verdict}{reset_style}"
                )
                lines.append(f"  Expected: {expected_color}{expected_verdict}{reset_style}")
                lines.append(f"  Processing Time: {result.get('processing_time', 0):.2f}s")

    return "\n".join(lines)


async def run_factcheck_command(args):
    """Run the factcheck command."""
    # Determine input source
    input_text = None

    try:
        if args.text:
            input_text = args.text
        elif args.file:
            try:
                with open(args.file, encoding="utf-8") as f:
                    input_text = f.read()
            except FileNotFoundError as e:
                raise ValidationError(
                    code="FILE_NOT_FOUND",
                    message=f"Input file not found: {args.file}",
                    details={"file_path": args.file},
                ) from e
            except UnicodeDecodeError as e:
                raise ValidationError(
                    code="FILE_DECODE_ERROR",
                    message=f"Failed to decode file as UTF-8: {args.file}",
                    details={"file_path": args.file},
                ) from e
        elif args.url:
            try:
                input_text = fetch_url_content(args.url)
            except ValueError as e:
                raise ValidationError(code="URL_ERROR", message=str(e), details={"url": args.url}) from e

        # Validate input text
        if not input_text or not input_text.strip():
            raise ValidationError(
                code="EMPTY_INPUT",
                message="Input text is empty",
                details={"source": "text" if args.text else "file" if args.file else "url"},
            )

        # Sanitize input text
        try:
            input_text = sanitize_text(input_text)
            validate_text_length(input_text)
        except ValidationError as e:
            # Pass along validation errors
            raise e
        except InputTooLongError as e:
            raise ValidationError(
                code="INPUT_TOO_LONG",
                message=str(e),
                details={"max_length": e.max_length, "actual_length": e.length},
            ) from e

        # Build pipeline configuration from arguments
        config = build_pipeline_config(args)

        # Create a progress callback if not in silent mode
        progress_callback = None
        if not args.silent:
            # Determine whether to use color output
            # Create a progress callback with or without a progress bar
            progress_callback = create_progress_callback(
                total_claims=config.max_claims,
                use_progress_bar=not args.verbose,  # Use simple output when verbose
            )

        # Run the pipeline
        start_time = time.time()
        verdicts, stats = await run_pipeline(input_text, config, progress_callback)
        elapsed_time = time.time() - start_time

        # Format results
        if args.format == "json":
            # Convert to JSON
            result = {
                "meta": {
                    "processing_time": elapsed_time,
                    "timestamp": time.time(),
                    "version": "0.1.0",  # Will be replaced with proper version tracking
                    "total_claims": len(verdicts),
                    "stats": stats,
                },
                "verdicts": (
                    [verdict.model_dump() for verdict in verdicts]
                    if hasattr(verdicts[0], "model_dump")
                    else verdicts
                ),
            }

            # Handle debug output
            if args.debug:
                result["debug"] = {
                    "config": (
                        config.model_dump() if hasattr(config, "model_dump") else vars(config)
                    ),
                    "source_text_length": len(input_text),
                    "source_type": "text" if args.text else "file" if args.file else "url",
                }

            output = json.dumps(result, indent=2)
        elif args.format == "csv":
            output = format_results_as_csv(verdicts, stats)
        else:  # Default to text
            output = format_results_as_text(verdicts, stats, use_color=not args.no_color)

        # Output results
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Results saved to {args.output}")
        else:
            print(output)

        return 0  # Success

    except ValidationError as e:
        print(f"{Fore.RED}Validation error: {e.message}{Style.RESET_ALL}")
        if e.details:
            print(f"Details: {e.details}")
        return 1
    except VerifactError as e:
        print(f"{Fore.RED}Error: {e.message} (Code: {e.code}){Style.RESET_ALL}")
        if e.details:
            print(f"Details: {e.details}")
        return 1
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()
        return 1


async def run_test_command(args):
    """Run the test command."""
    dataset_path = args.dataset
    filter_category = args.filter
    filter_level = args.level
    timeout = args.timeout
    output_file = args.output
    output_format = args.format
    verbose = args.verbose

    try:
        # Load test dataset
        print(f"Loading test dataset from {dataset_path}...")
        try:
            test_cases = load_test_dataset(dataset_path)
        except ValidationError as e:
            print(f"{Fore.RED}Error loading test dataset: {e.message}{Style.RESET_ALL}")
            if e.details:
                print(f"{Fore.RED}Details: {e.details}{Style.RESET_ALL}")
            return 1

        # Filter test cases
        filtered_cases = filter_test_cases(test_cases, filter_category, filter_level)
        if not filtered_cases:
            print(
                f"{Fore.YELLOW}Warning: No test cases match the specified filters.{Style.RESET_ALL}"
            )
            return 0

        # Create pipeline config based on test needs
        config = PipelineConfig(
            timeout=timeout,
            retries=1,
            verbose=verbose,  # Reduce retries for faster testing
        )

        # Set a timeout for the entire test run
        try:
            # Run tests with a timeout
            test_results = await asyncio.wait_for(
                run_tests(filtered_cases, config, verbose), timeout=timeout
            )

            # Format results
            if output_format == "text":
                output = format_test_results_as_text(test_results, detailed=verbose, use_color=True)
            elif output_format == "json":
                # Strip non-serializable objects and format as JSON
                output = json.dumps(test_results, indent=2, default=str)
            elif output_format == "csv":
                output_buffer = io.StringIO()
                writer = csv.writer(output_buffer)

                writer.writerow(["Overall Accuracy", f"{test_results['total_accuracy']:.2f}"])
                writer.writerow(["Total Test Cases", test_results["total_cases"]])
                writer.writerow(["Correct", test_results["total_correct"]])

                writer.writerow([])
                writer.writerow(["Category", "Total", "Correct", "Accuracy"])
                for category, stats in test_results["category_stats"].items():
                    writer.writerow(
                        [category, stats["total"], stats["correct"], f"{stats['accuracy']:.2f}"]
                    )

                writer.writerow([])
                writer.writerow(["Difficulty", "Total", "Correct", "Accuracy"])
                for level, stats in test_results["level_stats"].items():
                    writer.writerow(
                        [level, stats["total"], stats["correct"], f"{stats['accuracy']:.2f}"]
                    )

                if verbose:
                    writer.writerow([])
                    writer.writerow(
                        [
                            "Test ID",
                            "Category",
                            "Level",
                            "Claim",
                            "Expected",
                            "Actual",
                            "Correct",
                            "Time",
                        ]
                    )

                    for result in test_results["results"]:
                        writer.writerow(
                            [
                                result.get("test_id", ""),
                                result.get("category", ""),
                                result.get("level", ""),
                                truncate_text(result.get("claim", ""), 30),
                                result.get("expected_verdict", ""),
                                result.get("actual_verdict", ""),
                                result.get("correct", False),
                                f"{result.get('processing_time', 0):.2f}",
                            ]
                        )

                output = output_buffer.getvalue()

            # Output results
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"Test results saved to {output_file}")
            else:
                print(output)

            # Return a success code based on accuracy threshold
            return 0 if test_results["total_accuracy"] >= 0.7 else 1

        except asyncio.TimeoutError:
            print(f"{Fore.RED}Error: Test run timed out after {timeout} seconds{Style.RESET_ALL}")
            return 1

    except ValidationError as e:
        print(f"{Fore.RED}Validation error: {e.message}{Style.RESET_ALL}")
        if e.details:
            print(f"Details: {e.details}")
        return 1
    except VerifactError as e:
        print(f"{Fore.RED}Error: {e.message} (Code: {e.code}){Style.RESET_ALL}")
        if e.details:
            print(f"Details: {e.details}")
        return 1
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()
        return 1


async def run_version_command(args):
    """Execute the version command."""
    version = "0.1.0"  # Hardcoded for simplicity
    print(f"VeriFact CLI version {version}")
    print("Copyright (c) 2023 VeriFact Team")
    print("Released under the MIT License")


async def main():
    """Main entry point for the CLI."""
    # Parse command line arguments
    args = parse_args()

    # Configure colorama
    colorama.init()

    # Configure logging
    configure_logging(debug=getattr(args, "debug", False))

    try:
        # Execute the selected command
        if args.command == "factcheck":
            return await run_factcheck_command(args)
        elif args.command == "test":
            return await run_test_command(args)
        elif args.command == "version":
            return await run_version_command(args)
        else:
            # No command specified, show help
            print("Please specify a command. Use --help for available commands.")
            return 1

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation interrupted by user{Style.RESET_ALL}")
        return 130
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        # Clean up colorama
        colorama.deinit()


if __name__ == "__main__":
    # Run the main function with asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
