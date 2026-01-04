"""Hybrid recall functionality for SomaBrain memory client.

Extracted from memory_client.py per monolithic-decomposition spec.
Provides hybrid recall combining vector similarity with keyword matching.

Per Requirements C1.1-C1.5:
- C1.1: Combines vector similarity with keyword matching
- C1.2: Extracts keywords from query
- C1.3: Calls SFM /memories/search with filters for hybrid matching
- C1.4: Includes importance scores in ranking
- C1.5: Falls back to vector-only on failure with degraded=true
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from somabrain.memory.types import RecallHit
    from somabrain.memory.transport import MemoryHTTPTransport

logger = logging.getLogger(__name__)

# Common English stopwords to filter out during keyword extraction
STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "shall",
    "can",
    "need",
    "dare",
    "ought",
    "used",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "and",
    "but",
    "if",
    "or",
    "because",
    "until",
    "while",
    "about",
    "against",
    "what",
    "which",
    "who",
    "whom",
    "this",
    "that",
    "these",
    "those",
    "am",
    "i",
    "me",
    "my",
    "myself",
    "we",
    "our",
    "ours",
    "ourselves",
    "you",
    "your",
    "yours",
    "yourself",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
}


def extract_keywords(query: str) -> List[str]:
    """Extract keywords from query for hybrid recall.

    Per Requirement C1.2: Extract keywords from query for hybrid matching.
    Uses simple tokenization - splits on whitespace and filters stopwords.

    Args:
        query: Search query string.

    Returns:
        List of extracted keywords.
    """
    tokens = query.lower().split()
    keywords = [
        t.strip(".,!?;:'\"()[]{}")
        for t in tokens
        if t.strip(".,!?;:'\"()[]{}") and t.lower() not in STOPWORDS and len(t) > 2
    ]
    return keywords


def hybrid_recall_sync(
    transport: "MemoryHTTPTransport",
    query: str,
    top_k: int,
    universe: str,
    request_id: str,
    tenant: str,
    keywords: Optional[List[str]],
    http_post_fn: Callable,
    rescore_fn: Callable,
    recall_fallback_fn: Callable,
    require_healthy_fn: Callable,
) -> List["RecallHit"]:
    """Synchronous hybrid recall combining vector similarity with keyword matching.

    Per Requirements C1.1-C1.5.

    Args:
        transport: HTTP transport for SFM communication.
        query: Search query string.
        top_k: Maximum number of results to return.
        universe: Universe/scope for the search.
        request_id: Request ID for tracing.
        tenant: Tenant identifier.
        keywords: Optional explicit keywords (if None, extracted from query).
        http_post_fn: Function to make HTTP POST requests.
        rescore_fn: Function to rescore and rank hits.
        recall_fallback_fn: Fallback function for vector-only recall.
        require_healthy_fn: Function to check SFM health.

    Returns:
        List of RecallHit objects with hybrid scoring.
    """
    from somabrain.infrastructure.degradation import get_degradation_manager

    degradation_mgr = get_degradation_manager()

    # Check degradation state
    if degradation_mgr.is_degraded(tenant):
        degradation_mgr.check_alert(tenant)
        logger.warning(
            "SFM degraded mode (hybrid_recall): returning empty results",
            tenant=tenant,
        )
        return []

    # C1.2: Extract keywords from query if not provided
    kw_list = keywords if keywords is not None else extract_keywords(query)

    try:
        require_healthy_fn()

        # Build filters for hybrid search
        filters: Dict[str, Any] = {}
        if kw_list:
            filters["_keywords"] = kw_list

        # C1.3: Call SFM /memories/search with filters
        headers = {"X-Request-ID": request_id}
        body = {
            "query": str(query or ""),
            "top_k": max(int(top_k), 1),
            "universe": str(universe or "real"),
            "tenant": tenant,
        }
        if filters:
            body["filters"] = filters

        success, status, data = http_post_fn(
            "/memories/search", body, headers, operation="hybrid_recall"
        )

        if success and data:
            from somabrain.memory.recall_ops import process_search_response

            results = process_search_response(
                data,
                str(universe or "real"),
                str(query or ""),
                top_k,
                rescore_fn,
                tenant=tenant,
            )
            degradation_mgr.mark_recovered(tenant)
            return results

        # C1.5: Fallback to vector-only on failure
        logger.warning(
            "Hybrid recall failed, falling back to vector-only",
            status=status,
            tenant=tenant,
        )
        return recall_fallback_fn(query, top_k, universe, request_id)

    except RuntimeError as exc:
        # C1.5: Enter degraded mode on failure
        degradation_mgr.mark_degraded(tenant)
        logger.warning(
            "SFM unavailable (hybrid_recall), entering degraded mode",
            tenant=tenant,
            error=str(exc),
        )
        return []


async def hybrid_recall_async(
    transport: "MemoryHTTPTransport",
    query: str,
    top_k: int,
    universe: str,
    request_id: str,
    tenant: str,
    keywords: Optional[List[str]],
    http_post_fn: Callable,
    rescore_fn: Callable,
    recall_fallback_fn: Callable,
    require_healthy_fn: Callable,
) -> List["RecallHit"]:
    """Async hybrid recall combining vector similarity with keyword matching.

    Per Requirements C1.1-C1.5.

    Args:
        transport: HTTP transport for SFM communication.
        query: Search query string.
        top_k: Maximum number of results to return.
        universe: Universe/scope for the search.
        request_id: Request ID for tracing.
        tenant: Tenant identifier.
        keywords: Optional explicit keywords (if None, extracted from query).
        http_post_fn: Async function to make HTTP POST requests.
        rescore_fn: Function to rescore and rank hits.
        recall_fallback_fn: Async fallback function for vector-only recall.
        require_healthy_fn: Function to check SFM health.

    Returns:
        List of RecallHit objects with hybrid scoring.
    """
    from somabrain.infrastructure.degradation import get_degradation_manager

    degradation_mgr = get_degradation_manager()

    if degradation_mgr.is_degraded(tenant):
        degradation_mgr.check_alert(tenant)
        logger.warning(
            "SFM degraded mode (ahybrid_recall): returning empty results",
            tenant=tenant,
        )
        return []

    kw_list = keywords if keywords is not None else extract_keywords(query)

    try:
        require_healthy_fn()

        filters: Dict[str, Any] = {}
        if kw_list:
            filters["_keywords"] = kw_list

        headers = {"X-Request-ID": request_id}
        body = {
            "query": str(query or ""),
            "top_k": max(int(top_k), 1),
            "universe": str(universe or "real"),
            "tenant": tenant,
        }
        if filters:
            body["filters"] = filters

        success, status, data = await http_post_fn(
            "/memories/search", body, headers, operation="ahybrid_recall"
        )

        if success and data:
            from somabrain.memory.recall_ops import process_search_response

            results = process_search_response(
                data,
                str(universe or "real"),
                str(query or ""),
                top_k,
                rescore_fn,
                tenant=tenant,
            )
            degradation_mgr.mark_recovered(tenant)
            return results

        logger.warning(
            "Async hybrid recall failed, falling back to vector-only",
            status=status,
            tenant=tenant,
        )
        return await recall_fallback_fn(query, top_k, universe, request_id)

    except RuntimeError as exc:
        degradation_mgr.mark_degraded(tenant)
        logger.warning(
            "SFM unavailable (ahybrid_recall), entering degraded mode",
            tenant=tenant,
            error=str(exc),
        )
        return []