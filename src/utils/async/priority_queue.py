"""
Priority Queue Implementation for VeriFact

This module provides a priority queue implementation for processing claims
in order of their importance. It supports:
- Sorting by priority scores
- Configurable thresholds
- Batch size control for processing
- Status tracking for claims
"""

import heapq
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar


class JobStatus(str, Enum):
    """Status of a job in the priority queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMEOUT = "timeout"


T = TypeVar('T')


@dataclass(order=True)
class PrioritizedItem(Generic[T]):
    """Wrapper class for items in the priority queue."""
    priority: float
    timestamp: float = field(default_factory=time.time)
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item: T = field(compare=False)
    status: JobStatus = field(default=JobStatus.PENDING, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    started_at: Optional[float] = field(default=None, compare=False)
    completed_at: Optional[float] = field(default=None, compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)


class PriorityQueue(Generic[T]):
    """
    Thread-safe priority queue implementation with status tracking.

    This queue allows items to be processed in order of their priority,
    with higher priority items (lower priority numbers) processed first.
    """

    def __init__(
        self,
        priority_function: Optional[Callable[[T], float]] = None,
        min_priority_threshold: float = 0.0,
        max_batch_size: int = 10,
        allow_duplicate_items: bool = False
    ):
        """
        Initialize the priority queue.

        Args:
            priority_function: Optional function to calculate priority from item.
                               Lower values = higher priority. Default uses 0 for all items.
            min_priority_threshold: Minimum priority threshold for items to be processed
            max_batch_size: Maximum number of items to process in a batch
            allow_duplicate_items: Whether to allow duplicate items in the queue
        """
        self._queue: List[PrioritizedItem[T]] = []
        self._lock = threading.RLock()
        # Maps item_id to prioritized item
        self._item_map: Dict[str, PrioritizedItem[T]] = {}
        self._priority_function = priority_function or (lambda _: 0.0)
        self._min_priority_threshold = min_priority_threshold
        self._max_batch_size = max_batch_size
        self._allow_duplicate_items = allow_duplicate_items
        self._processing_count = 0
        self._completed_count = 0
        self._failed_count = 0

    def put(self,
            item: T,
            priority: Optional[float] = None,
            metadata: Optional[Dict[str,
                                    Any]] = None) -> str:
        """
        Add an item to the priority queue.

        Args:
            item: The item to add
            priority: Optional explicit priority value (lower = higher priority).
                     If not provided, priority_function will be used
            metadata: Optional metadata to associate with the item

        Returns:
            str: The item_id that can be used to look up the item later

        Raises:
            ValueError: If item is below the priority threshold
        """
        if priority is None:
            priority = self._priority_function(item)

        # Check if item meets the priority threshold
        if priority < self._min_priority_threshold:
            raise ValueError(
                f"Item priority {priority} is below the minimum threshold {self._min_priority_threshold}")

        # Create prioritized item
        prioritized_item = PrioritizedItem(
            priority=priority,
            item=item,
            metadata=metadata or {}
        )

        with self._lock:
            # Check for duplicates if not allowed
            if not self._allow_duplicate_items:
                # Simple string representation comparison - can be customized
                # for more complex equality
                item_str = str(item)
                if any(str(pi.item) == item_str for pi in self._queue):
                    # Return ID of the existing item instead of adding a
                    # duplicate
                    for pi in self._queue:
                        if str(pi.item) == item_str:
                            return pi.item_id

            # Add to queue and map
            heapq.heappush(self._queue, prioritized_item)
            self._item_map[prioritized_item.item_id] = prioritized_item

        return prioritized_item.item_id

    def get(self, block: bool = True) -> Optional[PrioritizedItem[T]]:
        """
        Get the highest priority item from the queue.

        Args:
            block: Whether to block until an item is available

        Returns:
            The highest priority item, or None if queue is empty and block=False
        """
        with self._lock:
            if not self._queue and not block:
                return None

            # Wait until there's an item
            while not self._queue and block:
                self._lock.release()
                time.sleep(0.1)  # Small delay before rechecking
                self._lock.acquire()

            if not self._queue:
                return None

            # Get highest priority item
            item = heapq.heappop(self._queue)

            # Mark as processing
            item.status = JobStatus.PROCESSING
            item.started_at = time.time()
            self._processing_count += 1

            return item

    def get_batch(self, max_items: Optional[int]
                  = None) -> List[PrioritizedItem[T]]:
        """
        Get a batch of items from the queue, ordered by priority.

        Args:
            max_items: Maximum number of items to get (defaults to max_batch_size)

        Returns:
            List of highest priority items
        """
        result = []
        max_to_get = min(
            max_items or self._max_batch_size,
            self._max_batch_size)

        with self._lock:
            # Get up to max_to_get items
            for _ in range(min(len(self._queue), max_to_get)):
                item = self.get(block=False)
                if item:
                    result.append(item)

        return result

    def complete(self, item_id: str, result: Any = None) -> bool:
        """
        Mark an item as completed with an optional result.

        Args:
            item_id: ID of the item to mark as completed
            result: Optional result to store with the completed item

        Returns:
            bool: True if item was found and marked as completed, False otherwise
        """
        with self._lock:
            if item_id not in self._item_map:
                return False

            item = self._item_map[item_id]
            item.status = JobStatus.COMPLETED
            item.result = result
            item.completed_at = time.time()
            self._processing_count -= 1
            self._completed_count += 1

            return True

    def fail(self, item_id: str, error: str) -> bool:
        """
        Mark an item as failed with an error message.

        Args:
            item_id: ID of the item to mark as failed
            error: Error message to store

        Returns:
            bool: True if item was found and marked as failed, False otherwise
        """
        with self._lock:
            if item_id not in self._item_map:
                return False

            item = self._item_map[item_id]
            item.status = JobStatus.FAILED
            item.error = error
            item.completed_at = time.time()
            self._processing_count -= 1
            self._failed_count += 1

            return True

    def requeue(
            self,
            item_id: str,
            new_priority: Optional[float] = None) -> bool:
        """
        Requeue a previously processed item.

        Args:
            item_id: ID of the item to requeue
            new_priority: Optional new priority for the item

        Returns:
            bool: True if item was found and requeued, False otherwise
        """
        with self._lock:
            if item_id not in self._item_map:
                return False

            item = self._item_map[item_id]

            # Only requeue if not already pending
            if item.status == JobStatus.PENDING:
                return True

            # Update priority if provided
            if new_priority is not None:
                item.priority = new_priority

            # Reset status and timestamps
            item.status = JobStatus.PENDING
            item.started_at = None
            item.completed_at = None
            item.result = None
            item.error = None

            # Add back to queue
            heapq.heappush(self._queue, item)

            # Update processing count if it was previously processing
            if item.status == JobStatus.PROCESSING:
                self._processing_count -= 1

            return True

    def cancel(self, item_id: str) -> bool:
        """
        Cancel a pending or processing item.

        Args:
            item_id: ID of the item to cancel

        Returns:
            bool: True if item was found and canceled, False otherwise
        """
        with self._lock:
            if item_id not in self._item_map:
                return False

            item = self._item_map[item_id]
            prev_status = item.status

            # Set status to canceled
            item.status = JobStatus.CANCELED
            item.completed_at = time.time()

            # If it was in the queue, rebuild queue without the item
            if prev_status == JobStatus.PENDING:
                self._queue = [i for i in self._queue if i.item_id != item_id]
                heapq.heapify(self._queue)
            elif prev_status == JobStatus.PROCESSING:
                # Update processing count
                self._processing_count -= 1

            return True

    def get_item(self, item_id: str) -> Optional[PrioritizedItem[T]]:
        """
        Get an item by its ID.

        Args:
            item_id: ID of the item to get

        Returns:
            The item if found, None otherwise
        """
        with self._lock:
            return self._item_map.get(item_id)

    def get_all_items(self) -> List[PrioritizedItem[T]]:
        """
        Get all items in the queue and tracking system.

        Returns:
            List of all items, sorted by priority
        """
        with self._lock:
            all_items = list(self._item_map.values())
            all_items.sort()  # Sort by priority
            return all_items

    def get_status_counts(self) -> Dict[JobStatus, int]:
        """
        Get counts of items by status.

        Returns:
            Dictionary of status counts
        """
        status_counts = {status: 0 for status in JobStatus}

        with self._lock:
            for item in self._item_map.values():
                status_counts[item.status] += 1

        return status_counts

    def get_queue_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the queue.

        Returns:
            Dictionary of queue statistics
        """
        with self._lock:
            status_counts = self.get_status_counts()

            # Calculate average waiting time for pending items
            current_time = time.time()
            pending_wait_times = [
                current_time - item.timestamp
                for item in self._item_map.values()
                if item.status == JobStatus.PENDING
            ]

            # Calculate average processing time for completed items
            processing_times = [
                (item.completed_at or current_time) - (item.started_at or current_time)
                for item in self._item_map.values()
                if item.status in [JobStatus.COMPLETED, JobStatus.FAILED]
                and item.started_at and item.completed_at
            ]

            avg_pending_time = sum(
                pending_wait_times) / len(pending_wait_times) if pending_wait_times else 0
            avg_processing_time = sum(
                processing_times) / len(processing_times) if processing_times else 0

            return {
                "total_items": len(self._item_map),
                "pending_items": len(self._queue),
                "processing_items": self._processing_count,
                "completed_items": self._completed_count,
                "failed_items": self._failed_count,
                "status_counts": {str(k): v for k, v in status_counts.items()},
                "avg_pending_time": avg_pending_time,
                "avg_processing_time": avg_processing_time,
                "min_priority_threshold": self._min_priority_threshold,
                "max_batch_size": self._max_batch_size,
            }

    def clear(self) -> int:
        """
        Clear all items from the queue.

        Returns:
            Number of items cleared
        """
        with self._lock:
            count = len(self._item_map)
            self._queue = []
            self._item_map = {}
            self._processing_count = 0
            self._completed_count = 0
            self._failed_count = 0
            return count

    def __len__(self) -> int:
        """Get the number of pending items in the queue."""
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        with self._lock:
            return len(self._queue) == 0

    @property
    def size(self) -> int:
        """Get the number of pending items in the queue."""
        return len(self)

    @property
    def total_items(self) -> int:
        """Get the total number of items (pending, processing, completed, failed)."""
        with self._lock:
            return len(self._item_map)


class ClaimPriorityQueue(PriorityQueue[T]):
    """
    Specialized priority queue for processing claims.

    This extends the generic PriorityQueue with claim-specific functionality:
    - Priority calculation based on claim check-worthiness
    - Domain-specific priority adjustments
    - Tracking of claim processing status
    """

    def __init__(
        self,
        min_check_worthiness: float = 0.5,
        max_batch_size: int = 5,
        allow_duplicate_claims: bool = False
    ):
        """
        Initialize the claim priority queue.

        Args:
            min_check_worthiness: Minimum check-worthiness threshold for claims to be processed
            max_batch_size: Maximum number of claims to process in a batch
            allow_duplicate_claims: Whether to allow duplicate claims in the queue
        """
        # Define claim priority function (inverting check-worthiness since
        # lower values = higher priority)
        def claim_priority_function(claim: Any) -> float:
            # Check if the object has the necessary attributes
            if not hasattr(claim, 'check_worthiness'):
                return 1.0  # Default lowest priority

            # Invert check-worthiness so higher check-worthiness = higher
            # priority (lower value)
            priority = 1.0 - getattr(claim, 'check_worthiness', 0.0)

            # Apply domain-specific adjustments if available
            if hasattr(claim, 'domain'):
                domain = getattr(claim, 'domain', None)
                # Prioritize health and safety related claims
                if str(domain).lower() in ['health', 'science']:
                    priority *= 0.8  # Boost priority by reducing score

            return priority

        # Initialize base class with claim-specific settings
        super().__init__(
            priority_function=claim_priority_function,
            min_priority_threshold=0.0,  # We use min_check_worthiness instead
            max_batch_size=max_batch_size,
            allow_duplicate_items=allow_duplicate_claims
        )

        # Store claim-specific settings
        self.min_check_worthiness = min_check_worthiness

    def put_claim(self, claim: T,
                  metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a claim to the priority queue.

        Args:
            claim: The claim to add
            metadata: Optional metadata to associate with the claim

        Returns:
            str: The item_id for the claim

        Raises:
            ValueError: If claim is below the check-worthiness threshold
        """
        # Check if claim meets the check-worthiness threshold
        if hasattr(claim, 'check_worthiness'):
            check_worthiness = getattr(claim, 'check_worthiness', 0.0)
            if check_worthiness < self.min_check_worthiness:
                raise ValueError(
                    f"Claim check-worthiness {check_worthiness} is below the minimum threshold {self.min_check_worthiness}")

        # Add to queue using the generic put method
        return self.put(claim, metadata=metadata)

    def get_related_claims(self, claim: T) -> List[Tuple[str, T]]:
        """
        Find claims that may be related to the given claim.

        Args:
            claim: The claim to find related claims for

        Returns:
            List of (item_id, claim) tuples for potentially related claims
        """
        related_claims = []
        claim_text = str(
            getattr(
                claim,
                'text',
                '')) if hasattr(
            claim,
            'text') else str(claim)

        with self._lock:
            for item_id, prioritized_item in self._item_map.items():
                other_claim = prioritized_item.item
                other_text = str(
                    getattr(
                        other_claim,
                        'text',
                        '')) if hasattr(
                    other_claim,
                    'text') else str(other_claim)

                # Simple similarity check - this can be enhanced with more
                # sophisticated algorithms
                if claim_text != other_text and (
                    claim_text in other_text or
                    other_text in claim_text or
                    self._calculate_similarity(claim_text, other_text) > 0.7
                ):
                    related_claims.append((item_id, other_claim))

        return related_claims

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts (simple implementation).

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0 and 1
        """
        # Simple word overlap ratio - can be replaced with more sophisticated
        # algorithms
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)
