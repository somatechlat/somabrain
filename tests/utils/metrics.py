"""
Metrics Utilities for Recall Testing.

Provides functions to compute standard information retrieval metrics.
Implementation follows VIBE rules: explicit, typed, no placeholders.
"""

from typing import List
import numpy as np


def compute_precision_at_k(relevant: List[str], retrieved: List[str], k: int) -> float:
    """Compute Precision@K.

    Args:
        relevant: List of IDs considered relevant ground truth.
        retrieved: List of IDs retrieved by the system.
        k: The cutoff rank.

    Returns:
        float: The fraction of relevant items in the top k retrieved.
    """
    if k <= 0:
        return 0.0
    # Truncate
    retrieved_k = retrieved[:k]
    if not retrieved_k:
        return 0.0

    relevant_set = set(relevant)
    retrieved_set = set(retrieved_k)

    intersection = relevant_set.intersection(retrieved_set)
    return len(intersection) / k


def compute_recall_at_k(relevant: List[str], retrieved: List[str], k: int) -> float:
    """Compute Recall@K.

    Args:
        relevant: List of IDs considered relevant ground truth.
        retrieved: List of IDs retrieved by the system.
        k: The cutoff rank.

    Returns:
        float: The fraction of relevant items retrieved in the top k out of all relevant items.
    """
    if not relevant:
        return 0.0
    if k <= 0:
        return 0.0

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)
    retrieved_set = set(retrieved_k)

    intersection = relevant_set.intersection(retrieved_set)
    return len(intersection) / len(relevant)


def compute_ndcg_at_k(relevant: List[str], retrieved: List[str], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain (nDCG) @ K.

    This implementation assumes binary relevance (1 if in `relevant`, 0 otherwise).

    Args:
        relevant: List of IDs considered relevant ground truth.
        retrieved: List of IDs retrieved by the system.
        k: The cutoff rank.

    Returns:
        float: nDCG score between 0.0 and 1.0.
    """
    if k <= 0 or not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)

    # Calculate DCG
    dcg = 0.0
    for i, item_id in enumerate(retrieved_k):
        rel_score = 1.0 if item_id in relevant_set else 0.0
        # Using log2(i+2) because rank is 0-indexed here (i+1), so i+2 matches standard formula log2(rank+1)
        dcg += rel_score / np.log2(i + 2)

    # Calculate IDCG (Ideal DCG)
    # In the ideal ranking, all relevant items appear first.
    idcg = 0.0
    num_relevant_in_top_k = min(len(relevant), k)
    for i in range(num_relevant_in_top_k):
        idcg += 1.0 / np.log2(i + 2)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg
