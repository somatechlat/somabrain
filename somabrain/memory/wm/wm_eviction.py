"""Working Memory Eviction Module.

This module provides eviction logic for the WorkingMemory class.
When working memory reaches capacity, the item with lowest salience
is evicted to make room for new items.

Extracted from wm.py to maintain <500 line file size per VIBE Coding Rules.

Key Functions:
    find_lowest_salience_idx: Find the index of the item with lowest salience
    evict_item: Evict an item and optionally mark it in persistence layer
    find_duplicate: Find an existing item that is a duplicate
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from somabrain.math import cosine_similarity

if TYPE_CHECKING:
    from somabrain.memory.wm_persistence import WMPersister
    from somabrain.memory.wm.core import WMItem

_EPS = 1e-12
logger = logging.getLogger(__name__)


def find_lowest_salience_idx(
    items: List["WMItem"],
    alpha: float,
    gamma: float,
    now: float,
    recency_scale: float,
) -> int:
    """Find the index of the item with lowest salience score.

    Per Requirement B1.1: WHEN WM reaches capacity THEN the system SHALL
    evict the item with lowest salience score.

    This implementation vectorises the pairwise novelty computation so the
    eviction decision is O(n^2) in numpy once per call instead of repeating
    O(n^2) work inside a Python loop.

    Args:
        items: List of working memory items.
        alpha: Weight for novelty component.
        gamma: Weight for recency component.
        now: Current timestamp.
        recency_scale: Time scale for recency decay.

    Returns:
        Index of the item with the lowest salience.
    """
    if not items:
        return 0
    n = len(items)
    if n == 1:
        return 0

    arr = np.asarray([it.vector for it in items], dtype=np.float64)
    norms = np.linalg.norm(arr, axis=1)
    valid = norms > _EPS
    novelty = np.ones(n, dtype=np.float64)

    if np.any(valid):
        # Normalise valid rows; zero-norm rows stay as zeros and get novelty 1.0
        arr_norm = arr.copy()
        arr_norm[valid] = arr[valid] / norms[valid, None]
        sims = arr_norm @ arr_norm.T
        # Ignore self-similarity
        np.fill_diagonal(sims, -1.0)
        max_sims = np.max(sims, axis=1)
        novelty = 1.0 - np.clip(max_sims, -1.0, 1.0)
        novelty[~valid] = 1.0

    ages = np.array([max(0.0, now - it.admitted_at) for it in items], dtype=np.float64)
    if recency_scale > 0:
        recency = np.exp(-ages / recency_scale)
    else:
        recency = np.ones(n, dtype=np.float64)

    salience = alpha * novelty + gamma * recency
    return int(np.argmin(salience))


def evict_item(
    items: List["WMItem"],
    item_ids: List[str],
    idx: int,
    persister: Optional["WMPersister"],
) -> None:
    """Evict an item from working memory.

    Per Requirement A1.4: Mark evicted item in SFM (not delete).

    Args:
        items: List of working memory items (will be modified).
        item_ids: List of item IDs for persistence tracking (will be modified).
        idx: Index of item to evict.
        persister: Optional persister for marking eviction in SFM.
    """
    if idx < 0 or idx >= len(items):
        return

    # WM Persistence (A1.4): Mark evicted item in SFM (not delete)
    if persister is not None and idx < len(item_ids):
        item_id = item_ids[idx]
        if item_id:
            _mark_evicted_async(persister, item_id)
        del item_ids[idx]

    # Remove the item
    del items[idx]


def _mark_evicted_async(persister: "WMPersister", item_id: str) -> None:
    """Mark an item as evicted in the persistence layer.

    This is a best-effort operation - failures are logged but don't
    block the eviction process.

    Args:
        persister: WMPersister instance.
        item_id: ID of the item to mark as evicted.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(persister.mark_evicted(item_id))
        else:
            loop.run_until_complete(persister.mark_evicted(item_id))
    except RuntimeError:
        try:
            asyncio.run(persister.mark_evicted(item_id))
        except Exception as exc:
            logger.debug(
                "Failed to mark item as evicted in SFM",
                extra={"item_id": item_id, "error": str(exc)},
            )
    except Exception as exc:
        logger.debug(
            "Failed to mark item as evicted in SFM",
            extra={"item_id": item_id, "error": str(exc)},
        )


def find_duplicate(
    items: List["WMItem"],
    item_id: str,
    vector: np.ndarray,
    duplicate_threshold: float,
) -> Optional[int]:
    """Find an existing item that is a duplicate of the given vector.

    Per Requirement B1.4: Items with cosine similarity > threshold are
    considered duplicates. Also checks for exact item_id match.

    Args:
        items: List of working memory items.
        item_id: Unique identifier to check for exact match.
        vector: Normalized vector to check for similarity match.
        duplicate_threshold: Cosine similarity threshold for duplicates.

    Returns:
        Index of duplicate item if found, None otherwise.
    """
    # First check for exact item_id match
    for idx, existing in enumerate(items):
        if existing.item_id and existing.item_id == item_id:
            return idx

    # Then check for high similarity (cosine > threshold)
    for idx, existing in enumerate(items):
        sim = cosine_similarity(vector, existing.vector)
        if sim > duplicate_threshold:
            return idx

    return None
