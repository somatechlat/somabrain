"""Recall operations for SomaBrain memory client.

This module contains the core recall (search/retrieve) operations extracted from
MemoryClient to reduce file size while maintaining the same functionality.
"""

from __future__ import annotations

import logging
from typing import Any, List, TYPE_CHECKING

from somabrain.memory.types import RecallHit
from somabrain.memory.hit_processing import normalize_recall_hits, deduplicate_hits
from somabrain.memory.filtering import _filter_payloads_by_keyword

if TYPE_CHECKING:
    from somabrain.memory.transport import MemoryHTTPTransport

logger = logging.getLogger(__name__)


def filter_hits_by_keyword(hits: List[RecallHit], keyword: str) -> List[RecallHit]:
    """Filter hits by keyword using payload filtering."""
    if not hits:
        return []
    payloads = [h.payload for h in hits if isinstance(h.payload, dict)]
    filtered = _filter_payloads_by_keyword(payloads, keyword)
    if filtered and len(filtered) <= len(payloads):
        allowed_ids = {id(p) for p in filtered}
        narrowed = [h for h in hits if id(h.payload) in allowed_ids]
        if narrowed:
            return narrowed
    return hits


def process_search_response(
    data: Any,
    universe_value: str,
    query_text: str,
    top_k: int,
    rescore_fn: callable,
) -> List[RecallHit]:
    """Process search response data into ranked RecallHit list."""
    hits = normalize_recall_hits(data)
    if not hits:
        return []

    if universe_value:
        filtered_hits = [
            hit
            for hit in hits
            if str((hit.payload or {}).get("universe") or universe_value)
            == universe_value
        ]
        hits = filtered_hits
        if not hits:
            return []

    hits = filter_hits_by_keyword(hits, query_text)
    if not hits:
        return []

    deduped = deduplicate_hits(hits)
    if not deduped:
        return []

    ranked = rescore_fn(deduped, query_text)
    limit = max(1, int(top_k))
    return ranked[:limit]


def memories_search_sync(
    transport: "MemoryHTTPTransport",
    query: str,
    top_k: int,
    universe: str,
    request_id: str,
    http_post_fn: callable,
    rescore_fn: callable,
) -> List[RecallHit]:
    """Synchronous memory search via HTTP POST to /memories/search."""
    if transport is None:
        raise RuntimeError("HTTP memory service required but not configured")

    headers = {"X-Request-ID": request_id}
    universe_value = str(universe or "real")
    query_text = str(query or "")
    body = {
        "query": query_text,
        "top_k": max(int(top_k), 1),
        "universe": universe_value,
    }

    success, status, data = http_post_fn(
        "/memories/search", body, headers, operation="recall"
    )
    if success:
        return process_search_response(data, universe_value, query_text, top_k, rescore_fn)

    if status in (404, 405, 422):
        raise RuntimeError(
            "Memory search endpoint unavailable or incompatible with current SomaBrain build."
        )

    return []


async def memories_search_async(
    transport: "MemoryHTTPTransport",
    query: str,
    top_k: int,
    universe: str,
    request_id: str,
    http_post_fn: callable,
    rescore_fn: callable,
) -> List[RecallHit]:
    """Async memory search via HTTP POST to /memories/search."""
    if transport is None or transport.async_client is None:
        raise RuntimeError("Async HTTP memory service required but not configured")

    headers = {"X-Request-ID": request_id}
    universe_value = str(universe or "real")
    query_text = str(query or "")
    body = {
        "query": query_text,
        "top_k": max(int(top_k), 1),
        "universe": universe_value,
    }

    success, status, data = await http_post_fn(
        "/memories/search", body, headers, operation="recall"
    )
    if success:
        return process_search_response(data, universe_value, query_text, top_k, rescore_fn)

    if status in (404, 405, 422):
        raise RuntimeError(
            "Memory search endpoint unavailable or incompatible with current SomaBrain build."
        )

    return []
