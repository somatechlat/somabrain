"""Working Memory Salience Computation Module.

This module provides salience computation functions for the WorkingMemory class.
Salience determines which items are most important to retain in working memory
based on novelty, reward, and recency factors.

Extracted from wm.py to maintain <500 line file size per VIBE Coding Rules.

Key Functions:
    compute_salience: Compute salience = alpha·novelty + beta·reward + gamma·recency
    compute_item_salience: Compute salience for a single WM item
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List

import numpy as np

from somabrain.math import cosine_similarity

if TYPE_CHECKING:
    from somabrain.memory.wm.core import WMItem


def compute_salience(
    query_vec: np.ndarray,
    items: List["WMItem"],
    alpha: float,
    beta: float,
    gamma: float,
    reward: float = 0.0,
) -> float:
    """Compute salience = alpha·novelty + beta·reward + gamma·recency.

    Salience determines how important a query vector is relative to current
    working memory contents. Higher salience indicates the item should be
    prioritized for admission.

    Args:
        query_vec: Query vector to evaluate.
        items: Current working memory items.
        alpha: Weight for novelty component.
        beta: Weight for reward component.
        gamma: Weight for recency component.
        reward: External reward signal (default 0.0).

    Returns:
        Salience score between 0.0 and 1.0.
    """
    novelty = compute_novelty(query_vec, items)
    recency = 1.0
    if items:
        recent = items[-1]
        recency = max(0.0, 1.0 - cosine_similarity(query_vec, recent.vector))
    s = alpha * float(novelty) + beta * float(reward) + gamma * float(recency)
    return float(max(0.0, min(1.0, s)))


def compute_novelty(query_vec: np.ndarray, items: List["WMItem"]) -> float:
    """Calculate novelty score for a query vector relative to working memory contents.

    Novelty is defined as 1.0 minus the highest cosine similarity to any existing
    item in working memory. A score of 1.0 indicates complete novelty (no similar
    items), while 0.0 indicates the query is identical to an existing item.

    Args:
        query_vec: Query vector to evaluate for novelty.
        items: Current working memory items.

    Returns:
        Novelty score between 0.0 (not novel) and 1.0 (completely novel).
        Returns 1.0 if working memory is empty.
    """
    return _min_novelty_against(query_vec, items)


_EPS = 1e-12


def _min_novelty_against(query_vec: np.ndarray, others: List["WMItem"]) -> float:
    """Vectorized novelty of ``query_vec`` against a list of WM items.

    Novelty is defined as ``1 - max_similarity``. A vectorized implementation
    keeps WM eviction O(n) instead of O(n^2) per comparison.
    """
    if not others:
        return 1.0

    q = np.asarray(query_vec, dtype=np.float64).ravel()
    qn = np.linalg.norm(q)
    if qn <= _EPS:
        return 1.0

    arr = np.asarray([it.vector for it in others], dtype=np.float64)
    norms = np.linalg.norm(arr, axis=1)
    mask = norms > _EPS
    if not np.any(mask):
        return 1.0

    dots = arr[mask].dot(q)
    sims = dots / (norms[mask] * qn)
    sims = np.clip(sims, -1.0, 1.0)
    return float(max(0.0, min(1.0, 1.0 - float(sims.max()))))


def compute_item_salience(
    item: "WMItem",
    items: List["WMItem"],
    alpha: float,
    gamma: float,
) -> float:
    """Compute salience score for a single WM item.

    Salience combines novelty and recency per the salience formula:
    salience = alpha * novelty + gamma * recency

    Per Requirement B1.3: Uses the item's stored recency value which
    decays exponentially over time via decay_recency().

    Args:
        item: The WMItem to compute salience for.
        items: All items in working memory (for novelty calculation).
        alpha: Weight for novelty component.
        gamma: Weight for recency component.

    Returns:
        Salience score between 0.0 and 1.0.
    """
    # Compute novelty: how different is this item from others (vectorized)
    others = [other for other in items if other is not item]
    novelty = _min_novelty_against(item.vector, others)

    # B1.3: Use stored recency value (decays exponentially via decay_recency())
    recency = float(item.recency)

    # Combine: alpha * novelty + gamma * recency
    salience = alpha * novelty + gamma * recency
    return float(max(0.0, min(1.0, salience)))


def compute_eviction_salience(
    item: "WMItem",
    items: List["WMItem"],
    alpha: float,
    gamma: float,
    now: float,
    recency_scale: float,
) -> float:
    """Compute salience for eviction decision.

    Used during capacity management to determine which item to evict.
    Unlike compute_item_salience, this uses time-based recency calculation
    rather than the stored recency value.

    Args:
        item: The WMItem to compute salience for.
        items: All items in working memory.
        alpha: Weight for novelty component.
        gamma: Weight for recency component.
        now: Current timestamp.
        recency_scale: Time scale for recency decay.

    Returns:
        Salience score between 0.0 and 1.0.
    """
    # Compute novelty for this item relative to other items (vectorized)
    others = [other for other in items if other is not item]
    novelty = _min_novelty_against(item.vector, others)

    # Compute recency based on time since admission
    age = max(0.0, now - item.admitted_at)
    recency_decay = math.exp(-age / recency_scale) if age > 0 else 1.0
    recency = float(recency_decay)

    # Compute salience: alpha * novelty + gamma * recency
    salience = alpha * novelty + gamma * recency
    return float(max(0.0, min(1.0, salience)))
