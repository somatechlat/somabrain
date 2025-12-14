"""Recall operations for SomaBrain memory client.

This module contains the core recall (search/retrieve) operations extracted from
MemoryClient to reduce file size while maintaining the same functionality.

SECURITY: All recall operations MUST filter results by tenant_id to prevent
cross-tenant data leakage. See Requirements D1.1, D1.2.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, TYPE_CHECKING

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


def _filter_by_tenant(hits: List[RecallHit], tenant: Optional[str]) -> List[RecallHit]:
    """Filter hits to only include those belonging to the specified tenant.

    SECURITY: This is a critical security filter to prevent cross-tenant data leakage.
    See Requirements D1.1, D1.2.

    Args:
        hits: List of recall hits to filter.
        tenant: Tenant ID to filter by. If None or empty, no filtering is applied.

    Returns:
        List of hits belonging to the specified tenant.
    """
    if not tenant or not hits:
        return hits

    tenant_str = str(tenant).strip()
    if not tenant_str:
        return hits

    filtered = []
    for hit in hits:
        payload = hit.payload or {}
        # Check multiple possible tenant field locations
        hit_tenant = (
            payload.get("tenant")
            or payload.get("tenant_id")
            or (payload.get("meta") or {}).get("tenant")
            or (payload.get("meta") or {}).get("tenant_id")
        )
        if hit_tenant is not None:
            if str(hit_tenant).strip() == tenant_str:
                filtered.append(hit)
        else:
            # If no tenant field, check namespace which may contain tenant info
            namespace = payload.get("namespace") or ""
            if tenant_str in str(namespace):
                filtered.append(hit)
            # If no tenant info at all, exclude for safety (fail-closed)
            # This prevents data leakage when tenant metadata is missing

    return filtered


def process_search_response(
    data: Any,
    universe_value: str,
    query_text: str,
    top_k: int,
    rescore_fn: callable,
    tenant: Optional[str] = None,
) -> List[RecallHit]:
    """Process search response data into ranked RecallHit list.

    SECURITY: Results are filtered by tenant_id to prevent cross-tenant data leakage.
    See Requirements D1.1, D1.2.
    """
    hits = normalize_recall_hits(data)
    if not hits:
        return []

    # SECURITY: Filter by tenant FIRST before any other processing
    # This ensures no cross-tenant data leakage (D1.1, D1.2)
    if tenant:
        hits = _filter_by_tenant(hits, tenant)
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
    tenant: Optional[str] = None,
) -> List[RecallHit]:
    """Synchronous memory search via HTTP POST to /memories/search.

    SECURITY: Results are filtered by tenant_id to prevent cross-tenant data leakage.
    See Requirements D1.1, D1.2.

    Args:
        transport: HTTP transport for making requests.
        query: Search query string.
        top_k: Maximum number of results to return.
        universe: Universe/scope for the search.
        request_id: Request ID for tracing.
        http_post_fn: Function to make HTTP POST requests.
        rescore_fn: Function to rescore and rank hits.
        tenant: Tenant ID for filtering results (SECURITY: required for isolation).

    Returns:
        List of RecallHit objects filtered by tenant.
    """
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

    # Include tenant in request body for server-side filtering
    if tenant:
        body["tenant"] = str(tenant)

    success, status, data = http_post_fn(
        "/memories/search", body, headers, operation="recall"
    )
    if success:
        # SECURITY: Filter by tenant client-side as defense-in-depth
        return process_search_response(
            data, universe_value, query_text, top_k, rescore_fn, tenant=tenant
        )

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
    tenant: Optional[str] = None,
) -> List[RecallHit]:
    """Async memory search via HTTP POST to /memories/search.

    SECURITY: Results are filtered by tenant_id to prevent cross-tenant data leakage.
    See Requirements D1.1, D1.2.

    Args:
        transport: HTTP transport for making requests.
        query: Search query string.
        top_k: Maximum number of results to return.
        universe: Universe/scope for the search.
        request_id: Request ID for tracing.
        http_post_fn: Function to make HTTP POST requests.
        rescore_fn: Function to rescore and rank hits.
        tenant: Tenant ID for filtering results (SECURITY: required for isolation).

    Returns:
        List of RecallHit objects filtered by tenant.
    """
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

    # Include tenant in request body for server-side filtering
    if tenant:
        body["tenant"] = str(tenant)

    success, status, data = await http_post_fn(
        "/memories/search", body, headers, operation="recall"
    )
    if success:
        # SECURITY: Filter by tenant client-side as defense-in-depth
        return process_search_response(
            data, universe_value, query_text, top_k, rescore_fn, tenant=tenant
        )

    if status in (404, 405, 422):
        raise RuntimeError(
            "Memory search endpoint unavailable or incompatible with current SomaBrain build."
        )

    return []
