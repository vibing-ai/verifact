"""
Metrics utilities for VeriFact.

This module provides classes and functions for tracking and reporting performance metrics.
"""

import threading
import time
from datetime import datetime
from typing import Any, Dict, List

# Thread-local storage for metrics
_local = threading.local()


class CacheMetrics:
    """Class to track and report cache performance metrics."""

    def __init__(self, namespace: str):
        """
        Initialize cache metrics for a namespace.

        Args:
            namespace: The cache namespace to track
        """
        self.namespace = namespace
        self.hits = 0
        self.misses = 0
        self.set_operations = 0
        self.last_reset_time = time.time()
        self.hit_latencies: List[float] = []
        self.miss_latencies: List[float] = []
        self._lock = threading.Lock()

    def record_hit(self, latency: float = 0.0) -> None:
        """
        Record a cache hit.

        Args:
            latency: Time taken for the cache operation in seconds
        """
        with self._lock:
            self.hits += 1
            if latency > 0:
                self.hit_latencies.append(latency)

    def record_miss(self, latency: float = 0.0) -> None:
        """
        Record a cache miss.

        Args:
            latency: Time taken for the cache operation in seconds
        """
        with self._lock:
            self.misses += 1
            if latency > 0:
                self.miss_latencies.append(latency)

    def record_set(self) -> None:
        """Record a cache set operation."""
        with self._lock:
            self.set_operations += 1

    def hit_rate(self) -> float:
        """
        Calculate the cache hit rate.

        Returns:
            float: The cache hit rate (0-1)
        """
        with self._lock:
            total = self.hits + self.misses
            return self.hits / total if total > 0 else 0

    def miss_rate(self) -> float:
        """
        Calculate the cache miss rate.

        Returns:
            float: The cache miss rate (0-1)
        """
        with self._lock:
            total = self.hits + self.misses
            return self.misses / total if total > 0 else 0

    def avg_hit_latency(self) -> float:
        """
        Calculate the average hit latency.

        Returns:
            float: The average hit latency in seconds
        """
        with self._lock:
            return sum(self.hit_latencies) / \
                len(self.hit_latencies) if self.hit_latencies else 0

    def avg_miss_latency(self) -> float:
        """
        Calculate the average miss latency.

        Returns:
            float: The average miss latency in seconds
        """
        with self._lock:
            return sum(self.miss_latencies) / \
                len(self.miss_latencies) if self.miss_latencies else 0

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.set_operations = 0
            self.hit_latencies = []
            self.miss_latencies = []
            self.last_reset_time = time.time()

    def stats(self) -> Dict[str, Any]:
        """
        Get metrics statistics.

        Returns:
            Dict[str, Any]: Metrics statistics
        """
        with self._lock:
            total = self.hits + self.misses
            uptime = time.time() - self.last_reset_time

            return {
                "namespace": self.namespace,
                "total_operations": total,
                "hits": self.hits,
                "misses": self.misses,
                "set_operations": self.set_operations,
                "hit_rate": self.hit_rate(),
                "miss_rate": self.miss_rate(),
                "avg_hit_latency": self.avg_hit_latency(),
                "avg_miss_latency": self.avg_miss_latency(),
                "uptime_seconds": uptime,
                "last_reset": datetime.fromtimestamp(
                    self.last_reset_time).isoformat()}


# Global metrics instances for common components
evidence_metrics = CacheMetrics("evidence")
claims_metrics = CacheMetrics("claims")
search_metrics = CacheMetrics("search_results")
model_metrics = CacheMetrics("model_responses")
