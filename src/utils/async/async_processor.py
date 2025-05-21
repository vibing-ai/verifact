"""Asynchronous processing utilities for VeriFact.

This module provides tools for processing tasks asynchronously with priority handling.
"""

import asyncio
import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from ..logging.logger import get_component_logger

# Import using relative imports to avoid 'async' in import path
from .priority_queue import (
    ClaimPriorityQueue,
    PrioritizedItem,
    PriorityQueue,
)

# Type definitions
T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type


class ProcessingStatus(str, Enum):
    """Status of the overall processing job."""

    IDLE = "idle"
    STARTING = "starting"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class ProcessingProgress:
    """Progress information for processing job."""

    total_items: int
    processed_items: int
    pending_items: int
    failed_items: int
    success_rate: float
    estimated_time_remaining: float | None = None
    avg_processing_time: float | None = None
    start_time: float | None = None
    last_update_time: float = field(default_factory=time.time)


@dataclass
class ProcessingResult(Generic[T, R]):
    """Result of a processing operation."""

    item: T
    result: R | None = None
    success: bool = True
    error: str | None = None
    processing_time: float = 0.0
    item_id: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class AsyncProcessor(Generic[T, R]):
    """Generic asynchronous processor for handling multiple items concurrently.

    This class provides:
    - Controlled concurrency with semaphores
    - Timeout handling for long-running operations
    - Error handling and recovery
    - Progress tracking
    - Result collection with original ordering
    """

    def __init__(
        self,
        process_func: Callable[[T], R],
        max_concurrency: int = 5,
        timeout_seconds: float = 60.0,
        retry_attempts: int = 1,
        logger: logging.Logger | None = None,
        priority_queue: PriorityQueue[T] | None = None,
    ):
        """Initialize the asynchronous processor.

        Args:
            process_func: Function that processes a single item
            max_concurrency: Maximum number of concurrent processing tasks
            timeout_seconds: Timeout for individual processing tasks
            retry_attempts: Number of retry attempts for failed tasks
            logger: Optional logger instance
            priority_queue: Optional priority queue for item ordering
        """
        self.process_func = process_func
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.logger = logger or logging.getLogger(__name__)

        # Create semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrency)

        # Create or use priority queue
        self._queue = priority_queue or PriorityQueue[T]()

        # Status and progress tracking
        self._status = ProcessingStatus.IDLE
        self._progress = ProcessingProgress(
            total_items=0, processed_items=0, pending_items=0, failed_items=0, success_rate=1.0
        )

        # Processing statistics
        self._processing_times: list[float] = []
        self._start_time: float | None = None
        self._results: dict[str, ProcessingResult[T, R]] = {}

        # Task management
        self._processing_task: asyncio.Task | None = None
        self._paused = False
        self._cancel_requested = False

        # Progress callback
        self._progress_callback: Callable[[ProcessingProgress], None] | None = None

    async def process_items(
        self,
        items: list[T],
        progress_callback: Callable[[ProcessingProgress], None] | None = None,
        wait_for_completion: bool = True,
    ) -> list[ProcessingResult[T, R]]:
        """Process multiple items concurrently.

        Args:
            items: List of items to process
            progress_callback: Optional callback for progress updates
            wait_for_completion: Whether to wait for all items to complete

        Returns:
            List of processing results in the same order as input items
        """
        # Reset state
        self._cancel_requested = False
        self._paused = False
        self._progress_callback = progress_callback

        # Add items to queue
        item_ids = []
        for item in items:
            item_id = self._queue.put(item)
            item_ids.append(item_id)

        # Update progress and status
        self._status = ProcessingStatus.STARTING
        self._progress = ProcessingProgress(
            total_items=len(items),
            processed_items=0,
            pending_items=len(items),
            failed_items=0,
            success_rate=1.0,
        )
        self._start_time = time.time()
        self._progress.start_time = self._start_time

        # Start processing task
        self._processing_task = asyncio.create_task(self._process_queue())

        # Wait for completion if requested
        if wait_for_completion:
            await self._processing_task

            # Collect results in original order
            results = []
            for item_id in item_ids:
                result = self._results.get(item_id)
                if result:
                    results.append(result)
                else:
                    # Create failed result for items that weren't processed
                    item = self._queue.get_item(item_id)
                    if item:
                        results.append(
                            ProcessingResult(
                                item=item.item,
                                success=False,
                                error="Processing not completed",
                                item_id=item_id,
                            )
                        )

            return results

        # Return empty list if not waiting for completion
        return []

    async def _process_queue(self) -> None:
        """Process all items in the queue until empty."""
        self._status = ProcessingStatus.PROCESSING
        self.logger.info(
            f"Starting processing of {self._progress.total_items} items with concurrency {self.max_concurrency}"
        )

        try:
            while not self._queue.is_empty() and not self._cancel_requested:
                # Pause if requested
                if self._paused:
                    self._status = ProcessingStatus.PAUSED
                    await asyncio.sleep(0.5)
                    continue

                # Get a batch of items to process
                batch = self._queue.get_batch(self.max_concurrency)
                if not batch:
                    break

                # Process batch concurrently
                tasks = [self._process_item_with_semaphore(item) for item in batch]

                # Wait for all tasks to complete
                await asyncio.gather(*tasks)

                # Update progress
                self._update_progress()

            if self._cancel_requested:
                self._status = ProcessingStatus.CANCELED
                self.logger.info("Processing canceled")
            else:
                self._status = ProcessingStatus.COMPLETED
                self.logger.info(
                    f"Processing completed: {self._progress.processed_items} items processed, {self._progress.failed_items} failed"
                )

        except Exception as e:
            self._status = ProcessingStatus.FAILED
            self.logger.error(f"Processing failed: {str(e)}", exc_info=True)

        finally:
            # Final progress update
            self._update_progress()

    async def _process_item_with_semaphore(self, prioritized_item: PrioritizedItem[T]) -> None:
        """Process an item with semaphore control for concurrency."""
        async with self._semaphore:
            await self._process_item(prioritized_item)

    async def _process_item(self, prioritized_item: PrioritizedItem[T]) -> None:
        """Process a single item with timeout and retry handling.

        Args:
            prioritized_item: The prioritized item to process
        """
        item_id = prioritized_item.item_id
        item = prioritized_item.item

        # Initialize result
        result = ProcessingResult(
            item=item, item_id=item_id, success=False, metadata=prioritized_item.metadata.copy()
        )

        start_time = time.time()
        attempts = 0

        while attempts <= self.retry_attempts:
            attempts += 1

            try:
                # Apply timeout to the processing function
                if asyncio.iscoroutinefunction(self.process_func):
                    # Async function
                    process_task = asyncio.create_task(self.process_func(item))
                    process_result = await asyncio.wait_for(
                        process_task, timeout=self.timeout_seconds
                    )
                else:
                    # Sync function
                    loop = asyncio.get_event_loop()
                    process_result = await loop.run_in_executor(
                        None, lambda: self.process_func(item)
                    )

                # Processing succeeded
                processing_time = time.time() - start_time
                result.result = process_result
                result.success = True
                result.processing_time = processing_time
                result.error = None

                # Add processing time to statistics
                self._processing_times.append(processing_time)

                # Mark as completed in queue
                self._queue.complete(item_id, process_result)

                # Log success
                self.logger.debug(
                    f"Item {item_id} processed successfully in {processing_time:.2f}s"
                )

                break

            except asyncio.TimeoutError:
                error_msg = f"Processing timed out after {self.timeout_seconds}s"
                result.error = error_msg

                if attempts > self.retry_attempts:
                    self.logger.warning(f"Item {item_id} {error_msg}, no more retries")
                    self._queue.fail(item_id, error_msg)
                else:
                    self.logger.info(
                        f"Item {item_id} {error_msg}, retrying (attempt {attempts}/{self.retry_attempts + 1})"
                    )

            except Exception as e:
                error_msg = f"Processing failed: {str(e)}"
                result.error = error_msg

                if attempts > self.retry_attempts:
                    self.logger.warning(f"Item {item_id} {error_msg}, no more retries")
                    self.logger.debug(traceback.format_exc())
                    self._queue.fail(item_id, error_msg)
                else:
                    self.logger.info(
                        f"Item {item_id} {error_msg}, retrying (attempt {attempts}/{self.retry_attempts + 1})"
                    )

        # Record final result
        self._results[item_id] = result

    def _update_progress(self) -> None:
        """Update processing progress and invoke callback if provided."""
        # Get current state
        queue_stats = self._queue.get_queue_statistics()

        # Calculate success rate
        total_processed = queue_stats["completed_items"] + queue_stats["failed_items"]
        success_rate = queue_stats["completed_items"] / max(total_processed, 1)

        # Calculate average processing time
        avg_processing_time = sum(self._processing_times) / max(len(self._processing_times), 1)

        # Estimate remaining time
        estimated_time_remaining = None
        if self._start_time and avg_processing_time > 0 and queue_stats["pending_items"] > 0:
            estimated_time_remaining = avg_processing_time * queue_stats["pending_items"]

        # Update progress object
        self._progress = ProcessingProgress(
            total_items=queue_stats["total_items"],
            processed_items=total_processed,
            pending_items=queue_stats["pending_items"],
            failed_items=queue_stats["failed_items"],
            success_rate=success_rate,
            estimated_time_remaining=estimated_time_remaining,
            avg_processing_time=avg_processing_time,
            start_time=self._start_time,
            last_update_time=time.time(),
        )

        # Call progress callback
        if self._progress_callback:
            try:
                self._progress_callback(self._progress)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {str(e)}")

    def pause(self) -> None:
        """Pause processing."""
        if self._status == ProcessingStatus.PROCESSING:
            self._paused = True
            self.logger.info("Processing paused")

    def resume(self) -> None:
        """Resume processing."""
        if self._status == ProcessingStatus.PAUSED:
            self._paused = False
            self.logger.info("Processing resumed")

    def cancel(self) -> None:
        """Cancel processing."""
        self._cancel_requested = True
        self.logger.info("Processing cancellation requested")

    @property
    def status(self) -> ProcessingStatus:
        """Get current processing status."""
        return self._status

    @property
    def progress(self) -> ProcessingProgress:
        """Get current processing progress."""
        return self._progress

    def get_results(self) -> dict[str, ProcessingResult[T, R]]:
        """Get all processing results."""
        return self._results.copy()

    def clear_results(self) -> None:
        """Clear results and reset statistics."""
        self._results = {}
        self._processing_times = []


class AsyncClaimProcessor(AsyncProcessor[T, R]):
    """Specialized asynchronous processor for handling claims.

    Extends AsyncProcessor with claim-specific functionality:
    - Claim prioritization based on check-worthiness
    - Claim relationship tracking
    - Special handling for claim-specific errors
    """

    def __init__(
        self,
        process_func: Callable[[T], R],
        max_concurrency: int = 3,
        timeout_seconds: float = 120.0,
        retry_attempts: int = 1,
        min_check_worthiness: float = 0.5,
        max_batch_size: int = 5,
        allow_duplicate_claims: bool = False,
    ):
        """Initialize the claim processor.

        Args:
            process_func: Function that processes a single claim
            max_concurrency: Maximum number of concurrent claim processing tasks
            timeout_seconds: Timeout for individual claim processing
            retry_attempts: Number of retry attempts for failed tasks
            min_check_worthiness: Minimum check-worthiness threshold for claims
            max_batch_size: Maximum number of claims to process in a batch
            allow_duplicate_claims: Whether to allow duplicate claims
        """
        # Create specialized claim priority queue
        claim_queue = ClaimPriorityQueue[T](
            min_check_worthiness=min_check_worthiness,
            max_batch_size=max_batch_size,
            allow_duplicate_claims=allow_duplicate_claims,
        )

        # Create specialized logger
        logger = get_component_logger("claim_processor")

        # Initialize base class
        super().__init__(
            process_func=process_func,
            max_concurrency=max_concurrency,
            timeout_seconds=timeout_seconds,
            retry_attempts=retry_attempts,
            logger=logger,
            priority_queue=claim_queue,
        )

        # Claim-specific tracking
        self._claim_relationships: dict[str, list[str]] = {}

    def get_related_claims(self, item: T) -> list[tuple[str, T, R | None]]:
        """Get claims related to the specified item.

        Args:
            item: The item to find related claims for

        Returns:
            List of (item_id, claim, result) tuples for related claims
        """
        # Use the claim queue to find related claims
        claim_queue = self._queue
        if isinstance(claim_queue, ClaimPriorityQueue):
            related_items = claim_queue.get_related_claims(item)

            # Add results if available
            result_items = []
            for item_id, related_item in related_items:
                result = self._results.get(item_id)
                result_value = result.result if result and result.success else None
                result_items.append((item_id, related_item, result_value))

            return result_items

        return []

    def get_claim_result(self, item_id: str) -> R | None:
        """Get the result for a specific claim by ID.

        Args:
            item_id: ID of the claim

        Returns:
            Result if claim was processed successfully, None otherwise
        """
        result = self._results.get(item_id)
        if result and result.success:
            return result.result
        return None

    def set_result_relationships(self) -> None:
        """Establish relationships between results based on claim content.

        This method analyzes the results and establishes relationships
        between claims that are related but were processed separately.
        """
        # First find all relationships
        relationship_pairs = []
        processed_ids = list(self._results.keys())

        for i, item_id1 in enumerate(processed_ids):
            result1 = self._results.get(item_id1)
            if not result1 or not result1.success:
                continue

            # Get the item
            item1 = result1.item

            # Compare with other items
            for item_id2 in processed_ids[i + 1 :]:
                result2 = self._results.get(item_id2)
                if not result2 or not result2.success:
                    continue

                # Get the item
                item2 = result2.item

                # Check if related using the queue's relationship detection
                claim_queue = self._queue
                if isinstance(claim_queue, ClaimPriorityQueue):
                    # Use simple text comparison for now
                    item1_text = (
                        str(getattr(item1, "text", "")) if hasattr(item1, "text") else str(item1)
                    )
                    item2_text = (
                        str(getattr(item2, "text", "")) if hasattr(item2, "text") else str(item2)
                    )

                    if claim_queue._calculate_similarity(item1_text, item2_text) > 0.7:
                        relationship_pairs.append((item_id1, item_id2))

        # Build relationship map
        self._claim_relationships = {}
        for id1, id2 in relationship_pairs:
            if id1 not in self._claim_relationships:
                self._claim_relationships[id1] = []
            if id2 not in self._claim_relationships:
                self._claim_relationships[id2] = []

            self._claim_relationships[id1].append(id2)
            self._claim_relationships[id2].append(id1)

        # Log relationship info
        self.logger.info(
            f"Found {len(relationship_pairs)} relationships between {len(self._claim_relationships)} claims"
        )

    def get_claim_relationships(self, item_id: str) -> list[tuple[str, T, R | None]]:
        """Get all claims related to the specified claim.

        Args:
            item_id: ID of the claim to find relationships for

        Returns:
            List of (item_id, claim, result) tuples for related claims
        """
        related_ids = self._claim_relationships.get(item_id, [])

        # Build result tuples
        related_items = []
        for related_id in related_ids:
            result = self._results.get(related_id)
            if result:
                result_value = result.result if result.success else None
                item = result.item
                related_items.append((related_id, item, result_value))

        return related_items
