"""Metrics tracking utilities for VeriFact.

This module provides tools for tracking various metrics about the application's performance.
"""

import os
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any

from src.utils.cache.cache import Cache
from src.utils.logging.logger import get_component_logger

# Get logger
logger = get_component_logger("metrics")

# Metrics cache
metrics_cache = Cache("metrics")


class MetricsTracker:
    """Tracks performance metrics for VeriFact components."""

    def __init__(self, component: str):
        """Initialize a metrics tracker for a specific component.

        Args:
            component: The name of the component being tracked
        """
        self.component = component
        self.logger = get_component_logger(f"metrics.{component}")
        self._current_batch = defaultdict(list)
        self._batch_size = int(os.environ.get("METRICS_BATCH_SIZE", "100"))
        self._storage_ttl = int(
            os.environ.get("METRICS_STORAGE_TTL", str(60 * 60 * 24 * 90))
        )  # 90 days

    def track_accuracy(
        self, prediction: str, ground_truth: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Track an accuracy measurement.

        Args:
            prediction: The predicted value
            ground_truth: The actual ground truth value
            metadata: Optional additional data about the measurement
        """
        # Simple binary accuracy (exact match)
        accuracy = 1.0 if prediction.strip() == ground_truth.strip() else 0.0

        self._track_metric("accuracy", accuracy, metadata)

    def track_claim_detection(
        self,
        detected_claims: list[dict[str, Any]],
        expected_claims: list[dict[str, Any]],
        text: str | None = None,
    ) -> dict[str, float]:
        """Track claim detection performance.

        Args:
            detected_claims: List of detected claims
            expected_claims: List of expected ground truth claims
            text: Optional original text

        Returns:
            Dict with precision, recall, and f1 scores
        """
        # Count correct detections (simple text matching for demo purposes)
        # In a real implementation, this would use semantic similarity
        detected_texts = [claim.get("text", "").strip() for claim in detected_claims]
        expected_texts = [claim.get("text", "").strip() for claim in expected_claims]

        # Calculate true positives, false positives, false negatives
        tp = sum(1 for dt in detected_texts if any(dt == et for et in expected_texts))
        fp = len(detected_texts) - tp
        fn = len(expected_texts) - tp

        # Calculate precision, recall, F1
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-10)

        # Create metrics dict
        metrics = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        }

        # Track the metrics
        metadata = {
            "text_length": len(text) if text else None,
            "detected_count": len(detected_claims),
            "expected_count": len(expected_claims),
        }

        for name, value in metrics.items():
            self._track_metric(name, value, metadata)

        return metrics

    def track_check_worthiness(
        self, predictions: list[float], ground_truths: list[float]
    ) -> dict[str, float]:
        """Track check-worthiness scoring performance.

        Args:
            predictions: List of predicted check-worthiness scores (0-1)
            ground_truths: List of ground truth check-worthiness scores (0-1)

        Returns:
            Dict with error metrics
        """
        if len(predictions) != len(ground_truths) or not predictions:
            raise ValueError(
                "Prediction and ground truth lists must be non-empty and of equal length"
            )

        # Calculate error metrics
        errors = [abs(p - gt) for p, gt in zip(predictions, ground_truths, strict=False)]
        mae = statistics.mean(errors)
        mse = statistics.mean([e**2 for e in errors])
        rmse = mse**0.5

        # Calculate correlation if we have more than one data point
        correlation = 0.0
        if len(predictions) > 1:
            try:
                correlation = statistics.correlation(predictions, ground_truths)
            except BaseException:
                # Handle potential calculation errors
                correlation = 0.0

        # Create metrics dict
        metrics = {"mae": mae, "mse": mse, "rmse": rmse, "correlation": correlation}

        # Track the metrics
        metadata = {"sample_size": len(predictions)}

        for name, value in metrics.items():
            self._track_metric(name, value, metadata)

        return metrics

    def track_domain_classification(
        self, predictions: list[str], ground_truths: list[str]
    ) -> dict[str, float]:
        """Track domain classification performance.

        Args:
            predictions: List of predicted domains
            ground_truths: List of ground truth domains

        Returns:
            Dict with accuracy metrics
        """
        if len(predictions) != len(ground_truths) or not predictions:
            raise ValueError(
                "Prediction and ground truth lists must be non-empty and of equal length"
            )

        # Calculate accuracy
        correct = sum(1 for p, gt in zip(predictions, ground_truths, strict=False) if p == gt)
        accuracy = correct / len(predictions)

        # Create metrics dict
        metrics = {"accuracy": accuracy, "correct": correct, "total": len(predictions)}

        # Track the metrics
        metadata = {"sample_size": len(predictions)}
        self._track_metric("domain_accuracy", accuracy, metadata)

        return metrics

    def _track_metric(
        self, name: str, value: float, metadata: dict[str, Any] | None = None
    ) -> None:
        """Track a single metric value.

        Args:
            name: Metric name
            value: Metric value
            metadata: Optional metadata
        """
        timestamp = datetime.datetime.now().isoformat()

        # Create metric record
        record = {
            "component": self.component,
            "metric": name,
            "value": value,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }

        # Add to current batch
        metric_key = f"{self.component}.{name}"
        self._current_batch[metric_key].append(record)

        # If batch is full, store it
        if sum(len(batch) for batch in self._current_batch.values()) >= self._batch_size:
            self._store_metrics()

    def _store_metrics(self) -> None:
        """Store the current batch of metrics."""
        if not self._current_batch:
            return

        try:
            # Store each metric type separately
            for metric_key, records in self._current_batch.items():
                if not records:
                    continue

                # Get existing records for this metric
                existing = metrics_cache.get(metric_key, [])

                # Add new records
                updated = existing + records

                # Store back in cache with TTL
                metrics_cache.set(metric_key, updated, ttl=self._storage_ttl)

                self.logger.debug(
                    f"Stored {len(records)} metrics for {metric_key}",
                    extra={"metric": metric_key, "count": len(records)},
                )

            # Clear the batch
            self._current_batch.clear()

        except Exception as e:
            self.logger.error(
                f"Error storing metrics: {str(e)}", extra={"error": str(e)}, exc_info=True
            )

    def get_metrics(
        self,
        metric_name: str,
        start_time: str | None = None,
        end_time: str | None = None,
        aggregate: bool = True,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Get metrics for analysis.

        Args:
            metric_name: Name of the metric to retrieve
            start_time: Optional ISO format start time filter
            end_time: Optional ISO format end time filter
            aggregate: Whether to return aggregate statistics or raw data

        Returns:
            List of metric records or aggregated statistics
        """
        metric_key = f"{self.component}.{metric_name}"

        # Flush current batch to ensure we have the latest data
        self._store_metrics()

        # Get metrics from cache
        metrics = metrics_cache.get(metric_key, [])

        # Apply time filters if provided
        if start_time or end_time:
            filtered_metrics = []
            for metric in metrics:
                timestamp = metric.get("timestamp", "")

                if start_time and timestamp < start_time:
                    continue

                if end_time and timestamp > end_time:
                    continue

                filtered_metrics.append(metric)

            metrics = filtered_metrics

        # Return raw data if not aggregating
        if not aggregate:
            return metrics

        # Calculate aggregate statistics
        values = [m.get("value", 0.0) for m in metrics]

        if not values:
            return {"count": 0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "std_dev": 0.0}

        try:
            return {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            }
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {str(e)}")
            return {"count": len(values), "error": str(e)}


# Create instances for common components
claim_detector_metrics = MetricsTracker("claim_detector")
evidence_hunter_metrics = MetricsTracker("evidence_hunter")
fact_checker_metrics = MetricsTracker("fact_checker")

class ClaimDetectorMetrics(MetricsTracker):
    """Metrics tracker specific to the claim detector agent."""
    
    def __init__(self):
        """Initialize a metrics tracker for the claim detector component."""
        super().__init__("claim_detector")
        
    def track_claim_detection_batch(
        self,
        batch_results: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Track a batch of claim detection results.
        
        Args:
            batch_results: List of dictionaries with detection results
                Each dict should have 'detected_claims', 'expected_claims', and optional 'text'
                
        Returns:
            Aggregated metrics across the batch
        """
        all_metrics = []
        
        for result in batch_results:
            detected = result.get("detected_claims", [])
            expected = result.get("expected_claims", [])
            text = result.get("text", "")
            
            metrics = self.track_claim_detection(detected, expected, text)
            all_metrics.append(metrics)
            
        # Aggregate metrics
        if not all_metrics:
            return {"precision": 0, "recall": 0, "f1": 0}
            
        agg_metrics = {
            "precision": statistics.mean([m["precision"] for m in all_metrics]),
            "recall": statistics.mean([m["recall"] for m in all_metrics]),
            "f1": statistics.mean([m["f1"] for m in all_metrics]),
            "batch_size": len(all_metrics)
        }
        
        return agg_metrics
        
    def track_check_worthiness_batch(
        self,
        batch_results: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Track a batch of check-worthiness scoring results.
        
        Args:
            batch_results: List of dictionaries with prediction results
                Each dict should have 'predictions' and 'ground_truths' lists
                
        Returns:
            Aggregated metrics across the batch
        """
        all_metrics = []
        
        for result in batch_results:
            predictions = result.get("predictions", [])
            ground_truths = result.get("ground_truths", [])
            
            if predictions and ground_truths and len(predictions) == len(ground_truths):
                metrics = self.track_check_worthiness(predictions, ground_truths)
                all_metrics.append(metrics)
            
        # Aggregate metrics
        if not all_metrics:
            return {"mae": 0, "rmse": 0, "correlation": 0}
            
        agg_metrics = {
            "mae": statistics.mean([m["mae"] for m in all_metrics]),
            "rmse": statistics.mean([m["rmse"] for m in all_metrics]),
            "correlation": statistics.mean([m["correlation"] for m in all_metrics]),
            "batch_size": len(all_metrics)
        }
        
        return agg_metrics


def create_performance_report(
    component: str = None,
    metrics: list[str] = None,
    start_time: str = None,
    end_time: str = None
) -> dict[str, Any]:
    """Create a performance report for specified components and metrics.
    
    Args:
        component: Optional filter for specific component
        metrics: Optional list of specific metrics to include
        start_time: Optional start time filter (ISO format)
        end_time: Optional end time filter (ISO format)
        
    Returns:
        Dict with performance report data
    """
    # Get all available components if not specified
    if not component:
        # Extract unique components from cache keys
        all_keys = metrics_cache.get_keys("*")
        components = set(k.split('.')[0] for k in all_keys if '.' in k)
    else:
        components = [component]
        
    report = {}
    
    # Create tracker for each component
    for comp in components:
        tracker = MetricsTracker(comp)
        
        # Get all metrics for this component
        comp_metrics = {}
        
        # Get metric names for this component if not specified
        if not metrics:
            comp_keys = metrics_cache.get_keys(f"{comp}.*")
            metric_names = [k.split('.')[1] for k in comp_keys]
        else:
            metric_names = metrics
            
        # Get each metric
        for metric in metric_names:
            data = tracker.get_metrics(metric, start_time, end_time, aggregate=True)
            comp_metrics[metric] = data
            
        report[comp] = comp_metrics
        
    return report


def reset_metrics(component: str = None, metrics: list[str] = None) -> None:
    """Reset (clear) metrics data.
    
    Args:
        component: Optional specific component to reset, or all if None
        metrics: Optional list of specific metrics to reset, or all if None
    """
    if component and metrics:
        # Reset specific metrics for a component
        for metric in metrics:
            metrics_cache.delete(f"{component}.{metric}")
    elif component:
        # Reset all metrics for a component
        keys = metrics_cache.get_keys(f"{component}.*")
        for key in keys:
            metrics_cache.delete(key)
    else:
        # Reset all metrics
        keys = metrics_cache.get_keys("*")
        for key in keys:
            metrics_cache.delete(key)
