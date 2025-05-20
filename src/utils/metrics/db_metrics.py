"""Database connection pool metrics for VeriFact.

This module provides utilities for monitoring database connection pool usage.
"""

from typing import Any

from src.utils.db.pool import get_db_metrics


class ConnectionPoolMetrics:
    """Metrics collector for database connection pool."""

    @staticmethod
    async def collect() -> dict[str, Any]:
        """Collect current connection pool metrics.

        Returns:
            Dictionary with pool metrics
        """
        try:
            metrics = await get_db_metrics()

            # Add usage percentage
            if metrics["max_size"] > 0:
                metrics["usage_percent"] = round(
                    (metrics["used_connections"] / metrics["max_size"]) * 100, 2
                )
            else:
                metrics["usage_percent"] = 0

            # Add color-coded status based on usage
            if metrics["usage_percent"] < 70:
                metrics["status"] = "ok"
            elif metrics["usage_percent"] < 90:
                metrics["status"] = "warning"
            else:
                metrics["status"] = "critical"

            return metrics
        except Exception as e:
            return {"status": "error", "error": str(e), "error_type": type(e).__name__}
