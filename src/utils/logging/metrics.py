"""
Metrics tracking utilities for VeriFact.

This module provides tools for tracking various metrics about the application's performance.
"""

import os
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from src.utils.cache.cache import Cache
from src.utils.logging.logger import get_component_logger

# Get logger
logger = get_component_logger("metrics")

# Metrics cache
metrics_cache = Cache("metrics")


class MetricsTracker:
    """Tracks performance metrics for VeriFact components."""

    def __init__(self, component: str):
        """
        Initialize a metrics tracker for a specific component.

        Args:
            component: The name of the component being tracked
        """
        self.component = component
        self.logger = get_component_logger(f"metrics.{component}")
        self._current_batch = defaultdict(list)
        self._batch_size = int(os.environ.get("METRICS_BATCH_SIZE", "100"))
        self._storage_ttl = int(
            os.environ.get(
                "METRICS_STORAGE_TTL", str(
                    60 * 60 * 24 * 90)))  # 90 days

    def track_accuracy(self, prediction: str, ground_truth: str,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Track an accuracy measurement.

        Args:
            prediction: The predicted value
            ground_truth: The actual ground truth value
            metadata: Optional additional data about the measurement
        """
        # Simple binary accuracy (exact match)
        accuracy = 1.0 if prediction.strip() == ground_truth.strip() else 0.0

        self._track_metric("accuracy", accuracy, metadata)

    def track_claim_detection(self,
                              detected_claims: List[Dict[str, Any]],
                              expected_claims: List[Dict[str, Any]],
                              text: Optional[str] = None) -> Dict[str, float]:
        """
        Track claim detection performance.

        Args:
            detected_claims: List of detected claims
            expected_claims: List of expected ground truth claims
            text: Optional original text

        Returns:
            Dict with precision, recall, and f1 scores
        """
        # Count correct detections (simple text matching for demo purposes)
        # In a real implementation, this would use semantic similarity
        detected_texts = [claim.get("text", "").strip()
                          for claim in detected_claims]
        expected_texts = [claim.get("text", "").strip()
                          for claim in expected_claims]

        # Calculate true positives, false positives, false negatives
        tp = sum(
            1 for dt in detected_texts if any(
                dt == et for et in expected_texts))
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
            "false_negatives": fn
        }

        # Track the metrics
        metadata = {
            "text_length": len(text) if text else None,
            "detected_count": len(detected_claims),
            "expected_count": len(expected_claims)
        }

        for name, value in metrics.items():
            self._track_metric(name, value, metadata)

        return metrics

    def track_check_worthiness(self,
                               predictions: List[float],
                               ground_truths: List[float]) -> Dict[str, float]:
        """
        Track check-worthiness scoring performance.

        Args:
            predictions: List of predicted check-worthiness scores (0-1)
            ground_truths: List of ground truth check-worthiness scores (0-1)

        Returns:
            Dict with error metrics
        """
        if len(predictions) != len(ground_truths) or not predictions:
            raise ValueError(
                "Prediction and ground truth lists must be non-empty and of equal length")

        # Calculate error metrics
        errors = [abs(p - gt) for p, gt in zip(predictions, ground_truths, strict=False)]
        mae = statistics.mean(errors)
        mse = statistics.mean([e**2 for e in errors])
        rmse = mse ** 0.5

        # Calculate correlation if we have more than one data point
        correlation = 0.0
        if len(predictions) > 1:
            try:
                correlation = statistics.correlation(
                    predictions, ground_truths)
            except BaseException:
                # Handle potential calculation errors
                correlation = 0.0

        # Create metrics dict
        metrics = {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "correlation": correlation
        }

        # Track the metrics
        metadata = {"sample_size": len(predictions)}

        for name, value in metrics.items():
            self._track_metric(name, value, metadata)

        return metrics

    def track_domain_classification(self,
                                    predictions: List[str],
                                    ground_truths: List[str]) -> Dict[str, float]:
        """
        Track domain classification performance.

        Args:
            predictions: List of predicted domains
            ground_truths: List of ground truth domains

        Returns:
            Dict with accuracy metrics
        """
        if len(predictions) != len(ground_truths) or not predictions:
            raise ValueError(
                "Prediction and ground truth lists must be non-empty and of equal length")

        # Calculate accuracy
        correct = sum(
            1 for p,
            gt in zip(
                predictions,
                ground_truths, strict=False) if p == gt)
        accuracy = correct / len(predictions)

        # Create metrics dict
        metrics = {
            "accuracy": accuracy,
            "correct": correct,
            "total": len(predictions)
        }

        # Track the metrics
        metadata = {"sample_size": len(predictions)}
        self._track_metric("domain_accuracy", accuracy, metadata)

        return metrics

    def _track_metric(self,
                      name: str,
                      value: float,
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Track a single metric value.

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
            "metadata": metadata or {}
        }

        # Add to current batch
        metric_key = f"{self.component}.{name}"
        self._current_batch[metric_key].append(record)

        # If batch is full, store it
        if sum(len(batch)
               for batch in self._current_batch.values()) >= self._batch_size:
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
                    extra={"metric": metric_key, "count": len(records)}
                )

            # Clear the batch
            self._current_batch.clear()

        except Exception as e:
            self.logger.error(
                f"Error storing metrics: {str(e)}",
                extra={"error": str(e)},
                exc_info=True
            )

    def get_metrics(self,
                    metric_name: str,
                    start_time: Optional[str] = None,
                    end_time: Optional[str] = None,
                    aggregate: bool = True) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get metrics for analysis.

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
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std_dev": 0.0
            }

        try:
            return {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0
            }
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {str(e)}")
            return {
                "count": len(values),
                "error": str(e)
            }


# Create instances for common components
claim_detector_metrics = MetricsTracker("claim_detector")
evidence_hunter_metrics = MetricsTracker("evidence_hunter")
fact_checker_metrics = MetricsTracker("fact_checker")
