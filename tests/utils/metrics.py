"""Simple metrics helpers for recall quality assertions."""

from __future__ import annotations

import math
from typing import Sequence, Set


def precision_at_k(relevant: Set[str], retrieved: Sequence[str], k: int) -> float:
    """Execute precision at k.

    Args:
        relevant: The relevant.
        retrieved: The retrieved.
        k: The k.
    """

    if k <= 0:
        return 0.0
    hits = sum(1 for item in retrieved[:k] if item in relevant)
    return hits / float(k)


def recall_at_k(relevant: Set[str], retrieved: Sequence[str], k: int) -> float:
    """Execute recall at k.

    Args:
        relevant: The relevant.
        retrieved: The retrieved.
        k: The k.
    """

    if not relevant:
        return 0.0
    hits = sum(1 for item in retrieved[:k] if item in relevant)
    return hits / float(len(relevant))


def ndcg_at_k(relevance_scores: Sequence[int], k: int) -> float:
    """Compute nDCG given binary relevance scores aligned to retrieved list."""
    if k <= 0:
        return 0.0
    k = min(k, len(relevance_scores))
    dcg = sum(
        (score / math.log2(idx + 2)) for idx, score in enumerate(relevance_scores[:k])
    )
    ideal = sorted(relevance_scores, reverse=True)
    idcg = sum((score / math.log2(idx + 2)) for idx, score in enumerate(ideal[:k]))
    return dcg / idcg if idcg > 0 else 0.0
