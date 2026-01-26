"""
Working Memory Module for SomaBrain.

This module implements a working memory system that provides a small, fast buffer for short-term
context storage and retrieval. Working memory serves as a temporary holding area for information
currently being processed, with capacity limits and decay mechanisms.

Key Features:
- Vector-based storage with cosine similarity retrieval
- Fixed capacity with automatic truncation
- Dimension normalization (padding/truncation)
- Novelty detection based on similarity to existing items
- Fast, lightweight implementation for real-time processing

Classes:
    WMItem: Data structure for working memory items containing vectors and payloads.
    WorkingMemory: Main working memory buffer with admission, recall, and novelty detection.
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

import numpy as np
from django.conf import settings

from somabrain.math import cosine_similarity, normalize_vector
from somabrain.wm_eviction import evict_item, find_duplicate, find_lowest_salience_idx
from somabrain.wm_promotion import check_promotion
from somabrain.wm_salience import (
    compute_item_salience,
    compute_novelty,
    compute_salience,
)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from somabrain.memory.promotion import WMLTMPromoter
    from somabrain.memory.wm_persistence import WMPersister

    from .scoring import UnifiedScorer


@dataclass
class WMItem:
    """
    Working memory item containing vector representation and associated payload.

    This dataclass represents a single item stored in working memory, consisting of
    a vector embedding and arbitrary payload data. The vector is used for similarity
    calculations during recall operations.

    Attributes:
        vector (np.ndarray): Vector representation of the item.
        payload (dict): Associated data payload containing metadata or content.
        tick (int): Tick count when item was admitted.
        admitted_at (float): Timestamp when item was admitted.
        cleanup_overlap (float): HRR cleanup best-score for density weighting.
        recency (float): Recency score that decays exponentially over time (B1.3).
        item_id (str): Unique identifier for this item (for duplicate detection).

    Example:
        >>> import numpy as np
        >>> item = WMItem(vector=np.array([0.1, 0.2, 0.3]), payload={'text': 'example'})
    """

    vector: np.ndarray
    payload: dict
    tick: int = 0
    admitted_at: float = 0.0
    cleanup_overlap: float = 0.0
    recency: float = 1.0  # B1.3: Starts at 1.0, decays exponentially
    item_id: str = ""  # B1.4: For duplicate detection


class WorkingMemory:
    """
    Small, fast buffer for short-term context storage and retrieval.

    WorkingMemory implements a capacity-limited buffer that stores vector-payload pairs
    for short-term cognitive processing. It provides efficient similarity-based recall
    and novelty detection, with automatic dimension normalization and capacity management.

    The system maintains a fixed number of items, automatically removing oldest items
    when capacity is exceeded. Vectors are normalized to a consistent dimension through
    padding or truncation.

    Attributes:
        capacity (int): Maximum number of items to store.
        dim (int): Fixed dimension for all stored vectors.
        _items (List[WMItem]): Internal list of stored working memory items.

    Contract:
    - admit(vec, payload): Insert with dimension guard and capacity truncation.
    - recall(query_vec, top_k): Cosine-ranked payloads.
    - novelty(query_vec): 1 - best cosine over current items.

    Example:
        >>> wm = WorkingMemory(capacity=10, dim=128)
        >>> vector = np.random.rand(128)
        >>> wm.admit(vector, {'context': 'important_info'})
        >>> results = wm.recall(vector, top_k=3)
        >>> novelty_score = wm.novelty(vector)
    """

    def __init__(
        self,
        capacity: int,
        dim: int,
        alpha: float | None = None,
        beta: float | None = None,
        gamma: float | None = None,
        min_capacity: int | None = None,
        max_capacity: int | None = None,
        scorer: "UnifiedScorer | None" = None,
        recency_time_scale: float | None = None,
        recency_max_steps: float | None = None,
        now_fn: Callable[[], float] | None = None,
        salience_threshold: float | None = None,
        persister: "Optional[WMPersister]" = None,
        promoter: "Optional[WMLTMPromoter]" = None,
    ):
        """
        Initialize working memory with specified capacity and vector dimension.

        Args:
            capacity (int): Maximum number of items to store in working memory.
            dim (int): Fixed dimension for all vector representations.
            persister: Optional WMPersister for async persistence to SFM (A1.3).
            promoter: Optional WMLTMPromoter for WM→LTM promotion (A2.1-A2.5).

        Raises:
            ValueError: If capacity or dimension are not positive integers.
        """
        self.capacity = int(capacity)
        self.dim = int(dim)
        self._items: List[WMItem] = []
        # salience weights and capacity bounds
        self.alpha = float(settings.SOMABRAIN_WM_ALPHA if alpha is None else alpha)
        self.beta = float(settings.SOMABRAIN_WM_BETA if beta is None else beta)
        self.gamma = float(settings.SOMABRAIN_WM_GAMMA if gamma is None else gamma)
        self._min_cap = int(min_capacity) if min_capacity is not None else int(capacity)
        self._max_cap = int(max_capacity) if max_capacity is not None else int(capacity)
        self._t = 0  # simple timestep for recency
        self._scorer = scorer
        self._now: Callable[[], float] = now_fn or time.time
        r_scale = (
            settings.SOMABRAIN_WM_RECENCY_TIME_SCALE
            if recency_time_scale is None
            else recency_time_scale
        )
        r_cap = (
            settings.SOMABRAIN_WM_RECENCY_MAX_STEPS
            if recency_max_steps is None
            else recency_max_steps
        )
        self._recency_scale = self._validate_scale(
            r_scale, settings.SOMABRAIN_WM_RECENCY_TIME_SCALE
        )
        self._recency_cap = self._validate_scale(
            r_cap, settings.SOMABRAIN_WM_RECENCY_MAX_STEPS
        )
        self._default_salience_threshold = float(
            settings.SOMABRAIN_WM_SALIENCE_THRESHOLD
            if salience_threshold is None
            else salience_threshold
        )
        # WM Persistence (A1.3): Optional persister for async SFM persistence
        self._persister: Optional["WMPersister"] = persister
        # Track item IDs for eviction marking
        self._item_ids: List[str] = []
        # WM-LTM Promotion (A2.1-A2.5): Optional promoter for salient items
        self._promoter: Optional["WMLTMPromoter"] = promoter
        # B1.3: Exponential decay rate for recency (per second)
        self._recency_decay_rate: float = 0.1  # Decay constant (higher = faster decay)
        # B1.4: Duplicate detection threshold (cosine similarity)
        self._duplicate_threshold: float = 0.95  # Items with sim > 0.95 are duplicates

    @staticmethod
    def _validate_scale(value: float, default: float) -> float:
        """Execute validate scale.

        Args:
            value: The value.
            default: The default.
        """

        try:
            v = float(value)
        except Exception:
            return float(default)
        if not math.isfinite(v) or v <= 0:
            return float(default)
        return v

    def admit(
        self,
        item_id_or_vector: str | np.ndarray,
        vector_or_payload: np.ndarray | dict,
        payload: dict | None = None,
        *,
        cleanup_overlap: float | None = None,
    ) -> bool:
        """
        Admit a new item into working memory with dimension normalization and unit-norm.

        Enforces global HRR_DIM, HRR_DTYPE, and mathematical invariant: all vectors are unit-norm, reproducible.
        Adds a vector-payload pair to working memory, normalizing the vector dimension
        through padding (if shorter) or truncation (if longer). If capacity is exceeded,
        removes the item with lowest salience to maintain the capacity limit.

        Per Requirement B1.4: If an item with similarity > 0.95 already exists,
        updates the existing item instead of adding a duplicate.

        Supports two call signatures for backward compatibility:
        - admit(item_id, vector, payload) - new signature with item_id
        - admit(vector, payload) - legacy signature (item_id auto-generated)

        Args:
            item_id_or_vector: Either item_id (str) or vector (np.ndarray) for legacy calls.
            vector_or_payload: Either vector (np.ndarray) or payload (dict) for legacy calls.
            payload: Payload dict (only used with new signature).
            cleanup_overlap (float | None): Optional HRR cleanup best-score (0-1) used to
                down-weight dense/duplicated entries during recall.

        Returns:
            bool: True if a new item was added, False if an existing item was updated.

        Note:
            Vectors are converted to float32 for memory efficiency and always unit-norm.
            Payload is deep-copied to prevent external modifications.
        """
        # Handle both signatures: admit(item_id, vector, payload) and admit(vector, payload)
        # Type ignores are necessary here due to Union type narrowing limitations in Python's
        # type system when handling overloaded function signatures with runtime isinstance checks.
        if isinstance(item_id_or_vector, str):
            # New signature: admit(item_id, vector, payload)
            item_id = item_id_or_vector
            vector = vector_or_payload  # type: ignore[assignment] - narrowed by isinstance check above
            if payload is None:
                payload = {}
        else:
            # Legacy signature: admit(vector, payload)
            item_id = f"wm_{self._t + 1}_{time.time()}"
            vector = item_id_or_vector
            payload = vector_or_payload if isinstance(vector_or_payload, dict) else {}  # type: ignore[assignment] - Union narrowing

        # Handle both dict and numpy arrays for shape access - MUST be outside if/else
        # to ensure shape_val, dim_val, vector_np are always defined
        from typing import Any
        vector_np: Any = vector if hasattr(vector, "shape") else np.array(vector)
        shape_val = (
            (vector_np.shape[-1] if hasattr(vector_np, "shape") else len(vector_np))
            if hasattr(vector_np, "shape") and hasattr(vector_np, "__getitem__")
            else 0
        )
        dim_val = self.dim

        if shape_val != dim_val:
            if shape_val < dim_val:
                pad = np.zeros((dim_val - shape_val,), dtype=vector_np.dtype if hasattr(vector_np, "dtype") else np.float32)  # type: ignore
                vector_np = np.concatenate([vector_np, pad]) if hasattr(vector_np, "shape") else vector_np  # type: ignore
            else:
                vector_np = (
                    vector_np[:dim_val]
                    if hasattr(vector_np, "__getitem__")
                    else vector_np
                )
        vector = normalize_vector(vector_np, dtype=np.float32)  # type: ignore
        self._t += 1
        now = self._now()
        overlap = 0.0
        if cleanup_overlap is not None:
            try:
                overlap = float(cleanup_overlap)
            except Exception:
                overlap = 0.0
            if not math.isfinite(overlap) or overlap < 0.0:
                overlap = 0.0
            overlap = min(overlap, 1.0)

        # B1.4: Check for duplicates - update existing item if similarity > threshold
        duplicate_idx = self._find_duplicate(item_id, vector)
        if duplicate_idx is not None:
            # Update existing item instead of adding duplicate
            existing = self._items[duplicate_idx]
            existing.vector = vector.astype("float32")
            existing.payload = dict(payload)
            existing.tick = self._t
            existing.admitted_at = float(now)
            existing.cleanup_overlap = float(overlap)
            existing.recency = 1.0  # Reset recency on update
            return False  # Existing item updated, not new

        item = WMItem(
            vector=vector.astype("float32"),
            payload=dict(payload),
            tick=self._t,
            admitted_at=float(now),
            cleanup_overlap=float(overlap),
            recency=1.0,  # B1.3: Initial recency is 1.0
            item_id=item_id,
        )
        self._items.append(item)

        # WM Persistence (A1.3): Queue item for async persistence to SFM
        persisted_id = ""
        if self._persister is not None:
            try:
                # Schedule persistence without blocking
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._persister.queue_persist(item))
                else:
                    persisted_id = loop.run_until_complete(
                        self._persister.queue_persist(item)
                    )
            except RuntimeError:
                # No event loop - try to create one
                try:
                    persisted_id = asyncio.run(self._persister.queue_persist(item))
                except Exception:
                    pass  # Persistence is best-effort
            except Exception:
                pass  # Persistence is best-effort
        self._item_ids.append(persisted_id)

        if len(self._items) > self.capacity:
            self._evict_lowest_salience()

        return True  # New item added

    def _find_duplicate(self, item_id: str, vector: np.ndarray) -> Optional[int]:
        """Find an existing item that is a duplicate of the given vector.

        Delegates to wm_eviction module for the actual duplicate detection.
        """
        return find_duplicate(self._items, item_id, vector, self._duplicate_threshold)

    def _evict_lowest_salience(self) -> None:
        """Evict the item with the lowest salience score.

        Delegates to wm_eviction module for the actual eviction logic.

        Per Requirement B1.1: WHEN WM reaches capacity THEN the system SHALL
        evict the item with lowest salience score.
        """
        if len(self._items) <= self.capacity:
            return

        now = self._now()
        min_idx = find_lowest_salience_idx(
            self._items, self.alpha, self.gamma, now, self._recency_scale
        )
        evict_item(self._items, self._item_ids, min_idx, self._persister)

    def salience(self, query_vec: np.ndarray, reward: float = 0.0) -> float:
        """Compute salience = alpha·novelty + beta·reward + gamma·recency.

        Delegates to wm_salience module for the actual computation.
        """
        return compute_salience(
            query_vec, self._items, self.alpha, self.beta, self.gamma, reward
        )

    def admit_if_salient(
        self,
        vector: np.ndarray,
        payload: dict,
        threshold: float | None = None,
        reward: float = 0.0,
        cleanup_overlap: float | None = None,
    ) -> bool:
        """Admit item only if salience exceeds threshold; adapt capacity slightly.

        Returns True if admitted.
        """
        s = self.salience(vector, reward=reward)
        th = self._default_salience_threshold if threshold is None else threshold
        if s >= float(th):
            self.admit(vector, payload, cleanup_overlap=cleanup_overlap)
            # adapt capacity towards max if many salient items; else shrink to min
            if self._max_cap > self.capacity and s > 0.8:
                self.capacity = min(self._max_cap, self.capacity + 1)
            elif self._min_cap < self.capacity and s < 0.3:
                self.capacity = max(self._min_cap, self.capacity - 1)
            return True
        return False

    def recall(self, query_vec: np.ndarray, top_k: int = 3) -> List[Tuple[float, dict]]:
        """
        Recall most similar items from working memory using cosine similarity.

        Searches working memory for items most similar to the query vector, ranked
        by cosine similarity score. Returns the top-k most similar items with their
        similarity scores and payloads.

        Also checks for WM→LTM promotion eligibility per Requirement A2.1:
        Items with salience >= 0.85 for 3+ consecutive ticks are promoted.

        Args:
            query_vec (np.ndarray): Query vector for similarity search.
            top_k (int, optional): Number of top similar items to return. Defaults to 3.

        Returns:
            List[Tuple[float, dict]]: List of (similarity_score, payload) tuples,
                                     sorted by similarity in descending order.

        Example:
            >>> results = wm.recall(query_vector, top_k=5)
            >>> for score, payload in results:
            ...     print(f"Similarity: {score:.3f}, Data: {payload}")
        """
        scored: List[Tuple[float, dict]] = []
        now = self._now()
        for idx, it in enumerate(self._items):
            cos = cosine_similarity(query_vec, it.vector)
            if self._scorer is not None:
                steps = self._recency_steps(now, it.admitted_at)
                s = self._scorer.score(
                    query_vec,
                    it.vector,
                    recency_steps=steps,
                    cosine=cos,
                )
            else:
                s = cos

            overlap = max(0.0, min(1.0, float(it.cleanup_overlap)))
            density_factor = max(0.1, 1.0 - overlap)
            adjusted = float(s) * density_factor
            scored.append((adjusted, it.payload))

            # WM-LTM Promotion (A2.1): Check for promotion eligibility
            # Use adjusted score as salience proxy for promotion check
            if self._promoter is not None:
                item_id = (
                    self._item_ids[idx]
                    if idx < len(self._item_ids)
                    else f"wm_{idx}_{it.tick}"
                )
                self._check_promotion(item_id, adjusted, it)

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[: max(0, int(top_k))]

    def _check_promotion(self, item_id: str, salience: float, item: WMItem) -> None:
        """Check if item should be promoted to LTM.

        Delegates to wm_promotion module for the actual promotion check.

        Per Requirement A2.1: Items with salience >= 0.85 for 3+ consecutive
        ticks are promoted to LTM.
        """
        if self._promoter is None:
            return
        check_promotion(self._promoter, item_id, salience, self._t, item)

    def novelty(self, query_vec: np.ndarray) -> float:
        """
        Calculate novelty score for a query vector relative to working memory contents.

        Delegates to wm_salience module for the actual computation.

        Args:
            query_vec (np.ndarray): Query vector to evaluate for novelty.

        Returns:
            float: Novelty score between 0.0 (not novel) and 1.0 (completely novel).
                   Returns 1.0 if working memory is empty.
        """
        return compute_novelty(query_vec, self._items)

    def _recency_steps(self, now: float, admitted_at: float) -> float:
        """Execute recency steps.

        Args:
            now: The now.
            admitted_at: The admitted_at.
        """

        age = max(0.0, float(now) - float(admitted_at))
        if age <= 0.0:
            return 0.0
        steps = age / self._recency_scale
        if steps <= 0.0:
            return 0.0
        return min(steps, self._recency_cap)

    def set_promoter(self, promoter: "WMLTMPromoter") -> None:
        """Set the WM-LTM promoter for this working memory instance.

        Per Requirement A2.1: Enables WM→LTM promotion for salient items.

        Args:
            promoter: WMLTMPromoter instance for handling promotions.
        """
        self._promoter = promoter

    def tick(self) -> None:
        """Advance the tick counter and check all items for promotion.

        Per Requirement A2.1: Items with salience >= 0.85 for 3+ consecutive
        ticks are promoted to LTM. This method should be called each cognitive
        cycle to advance the tick and check promotion eligibility.
        """
        self._t += 1

        if self._promoter is None:
            return

        # Check all items for promotion eligibility
        now = self._now()
        for idx, item in enumerate(self._items):
            # Compute salience for this item
            salience = self._compute_item_salience(item, now)
            item_id = (
                self._item_ids[idx]
                if idx < len(self._item_ids)
                else f"wm_{idx}_{item.tick}"
            )
            self._check_promotion(item_id, salience, item)

    def _compute_item_salience(self, item: WMItem, now: float) -> float:
        """Compute salience score for a single WM item.

        Delegates to wm_salience module for the actual computation.

        Per Requirement B1.3: Uses the item's stored recency value which
        decays exponentially over time via decay_recency().
        """
        return compute_item_salience(item, self._items, self.alpha, self.gamma)

    def decay_recency(self, elapsed_seconds: float | None = None) -> None:
        """Apply exponential decay to all items' recency scores.

        Per Requirement B1.3: Recency decays exponentially over time.
        Formula: recency = recency * exp(-decay_rate * elapsed_seconds)

        This method should be called periodically (e.g., each cognitive cycle)
        to update recency scores based on elapsed time.

        Args:
            elapsed_seconds: Time elapsed since last decay. If None, uses
                time since each item's last update based on admitted_at.
        """
        now = self._now()
        for item in self._items:
            if elapsed_seconds is not None:
                # Use provided elapsed time
                decay = math.exp(-self._recency_decay_rate * elapsed_seconds)
            else:
                # Compute decay based on time since admission
                age = max(0.0, now - item.admitted_at)
                decay = math.exp(-self._recency_decay_rate * age)

            # Apply decay, ensuring recency stays in [0, 1]
            item.recency = max(0.0, min(1.0, item.recency * decay))

    def get_item_recency(self, item_id: str) -> Optional[float]:
        """Get the current recency score for an item by ID.

        Per Requirement B1.3: Returns the exponentially decaying recency value.

        Args:
            item_id: Unique identifier of the item.

        Returns:
            Recency score (0.0-1.0) or None if item not found.
        """
        for item in self._items:
            if item.item_id == item_id:
                return item.recency
        return None
