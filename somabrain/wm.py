from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Callable, List, Tuple, TYPE_CHECKING
import numpy as np
from common.config.settings import settings
from common.logging import logger
from .scoring import UnifiedScorer

"""
Working Memory Module for SomaBrain.

This module implements a working memory system that provides a small, fast buffer for short-term
context storage and retrieval. Working memory serves as a temporary holding area for information
currently being processed, with capacity limits and decay mechanisms.

Key Features:
    pass
- Vector-based storage with cosine similarity retrieval
- Fixed capacity with automatic truncation
- Dimension normalization (padding/truncation)
- Novelty detection based on similarity to existing items
- Fast, lightweight implementation for real-time processing

Classes:
    WMItem: Data structure for working memory items containing vectors and payloads.
    WorkingMemory: Main working memory buffer with admission, recall, and novelty detection.
"""





if TYPE_CHECKING:  # pragma: no cover - type checking only


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

    Example:
        >>> import numpy as np
        >>> item = WMItem(vector=np.array([0.1, 0.2, 0.3]), payload={'text': 'example'})
    """

    vector: np.ndarray
    payload: dict
    tick: int = 0
    admitted_at: float = 0.0
    cleanup_overlap: float = 0.0


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
        pass
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
        salience_threshold: float | None = None, ):
            pass
        """
        Initialize working memory with specified capacity and vector dimension.

        Args:
            capacity (int): Maximum number of items to store in working memory.
            dim (int): Fixed dimension for all vector representations.

        Raises:
            ValueError: If capacity or dimension are not positive integers.
        """
        self.capacity = int(capacity)
        self.dim = int(dim)
        self._items: List[WMItem] = []
        # salience weights and capacity bounds
        self.alpha = float(settings.wm_alpha if alpha is None else alpha)
        self.beta = float(settings.wm_beta if beta is None else beta)
        self.gamma = float(settings.wm_gamma if gamma is None else gamma)
        self._min_cap = int(min_capacity) if min_capacity is not None else int(capacity)
        self._max_cap = int(max_capacity) if max_capacity is not None else int(capacity)
        self._t = 0  # simple timestep for recency
        self._scorer = scorer
        self._now: Callable[[], float] = now_fn or time.time
        r_scale = settings.wm_recency_time_scale if recency_time_scale is None else recency_time_scale
        r_cap = settings.wm_recency_max_steps if recency_max_steps is None else recency_max_steps
        self._recency_scale = self._validate_scale(r_scale, settings.wm_recency_time_scale)
        self._recency_cap = self._validate_scale(r_cap, settings.wm_recency_max_steps)
        self._default_salience_threshold = float(
            settings.wm_salience_threshold if salience_threshold is None else salience_threshold
        )

@staticmethod
def _validate_scale(value: float, default: float) -> float:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            v = float(value)
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            return float(default)
        if not math.isfinite(v) or v <= 0:
            return float(default)
        return v

@staticmethod
def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a (np.ndarray): First vector.
            b (np.ndarray): Second vector.

        Returns:
            float: Cosine similarity score between 0.0 and 1.0.
                   Returns 0.0 if either vector has zero norm.

        Note:
            Uses numpy for efficient computation with proper handling of edge cases.
        """
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na <= 0 or nb <= 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

def admit(
        self,
        vector: np.ndarray,
        payload: dict,
        *,
        cleanup_overlap: float | None = None, ) -> None:
            pass
        """
        Admit a new item into working memory with dimension normalization and unit-norm.
        Enforces global HRR_DIM, HRR_DTYPE, and mathematical invariant: all vectors are unit-norm, reproducible.
        Adds a vector-payload pair to working memory, normalizing the vector dimension
        through padding (if shorter) or truncation (if longer). If capacity is exceeded,
        removes the oldest item to maintain the capacity limit.
        Args:
            vector (np.ndarray): Vector representation to store. Will be normalized to dim and unit-norm.
            payload (dict): Associated data payload to store with the vector.
            cleanup_overlap (float | None): Optional HRR cleanup best-score (0-1) used to
                down-weight dense/duplicated entries during recall.
        Note:
            Vectors are converted to float32 for memory efficiency and always unit-norm.
            Payload is deep-copied to prevent external modifications.
        """
        if vector.shape[-1] != self.dim:
            if vector.shape[-1] < self.dim:
                pad = np.zeros((self.dim - vector.shape[-1],), dtype=vector.dtype)
                vector = np.concatenate([vector, pad])
            else:
                vector = vector[: self.dim]
        n = float(np.linalg.norm(vector))
        if n > 0:
            vector = vector / n
        self._t += 1
        now = self._now()
        overlap = 0.0
        if cleanup_overlap is not None:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                overlap = float(cleanup_overlap)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                overlap = 0.0
            if not math.isfinite(overlap) or overlap < 0.0:
                overlap = 0.0
            overlap = min(overlap, 1.0)

        self._items.append(
            WMItem(
                vector=vector.astype("float32"),
                payload=dict(payload),
                tick=self._t,
                admitted_at=float(now),
                cleanup_overlap=float(overlap), )
        )
        if len(self._items) > self.capacity:
            self._items = self._items[-self.capacity :]

def salience(self, query_vec: np.ndarray, reward: float = 0.0) -> float:
        """Compute salience = alpha·novelty + beta·reward + gamma·recency.

        Recency proxy: 1.0 for empty WM, else 1 - best cosine vs most recent item.
        """
        novelty = self.novelty(query_vec)
        recency = 1.0
        if self._items:
            recent = self._items[-1]
            recency = max(0.0, 1.0 - self._cosine(query_vec, recent.vector))
        s = (
            self.alpha * float(novelty)
            + self.beta * float(reward)
            + self.gamma * float(recency)
        )
        return float(max(0.0, min(1.0, s)))

def admit_if_salient(
        self,
        vector: np.ndarray,
        payload: dict,
        threshold: float | None = None,
        reward: float = 0.0,
        cleanup_overlap: float | None = None, ) -> bool:
            pass
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

        Args:
            query_vec (np.ndarray): Query vector for similarity search.
            top_k (int, optional): Number of top similar items to return. Defaults to 3.

        Returns:
            List[Tuple[float, dict]]: List of (similarity_score, payload) tuples,
                                     sorted by similarity in descending order.

        Example:
            >>> results = wm.recall(query_vector, top_k=5)
            >>> for score, payload in results:
                pass
            ...     print(f"Similarity: {score:.3f}, Data: {payload}")
        """
        scored: List[Tuple[float, dict]] = []
        now = self._now()
        for it in self._items:
            cos = self._cosine(query_vec, it.vector)
            if self._scorer is not None:
                steps = self._recency_steps(now, it.admitted_at)
                s = self._scorer.score(
                    query_vec,
                    it.vector,
                    recency_steps=steps,
                    cosine=cos, )
            else:
                s = cos

            overlap = max(0.0, min(1.0, float(it.cleanup_overlap)))
            density_factor = max(0.1, 1.0 - overlap)
            adjusted = float(s) * density_factor
            scored.append((adjusted, it.payload))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[: max(0, int(top_k))]

def novelty(self, query_vec: np.ndarray) -> float:
        """
        Calculate novelty score for a query vector relative to working memory contents.

        Novelty is defined as 1.0 minus the highest cosine similarity to any existing
        item in working memory. A score of 1.0 indicates complete novelty (no similar
        items), while 0.0 indicates the query is identical to an existing item.

        Args:
            query_vec (np.ndarray): Query vector to evaluate for novelty.

        Returns:
            float: Novelty score between 0.0 (not novel) and 1.0 (completely novel).
                   Returns 1.0 if working memory is empty.

        Example:
            >>> score = wm.novelty(new_vector)
            >>> if score > 0.8:
                pass
            ...     print("Highly novel information detected!")
        """
        if not self._items:
            return 1.0
        best = 0.0
        for it in self._items:
            best = max(best, self._cosine(query_vec, it.vector))
        return max(0.0, 1.0 - best)

def _recency_steps(self, now: float, admitted_at: float) -> float:
        age = max(0.0, float(now) - float(admitted_at))
        if age <= 0.0:
            return 0.0
        steps = age / self._recency_scale
        if steps <= 0.0:
            return 0.0
        return min(steps, self._recency_cap)
