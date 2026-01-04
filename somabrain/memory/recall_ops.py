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
    from somabrain.memory.graph_client import GraphClient

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
    # VIBE FIX: Align with MemorySearchRequest schema (universe/tenant in filters)
    body = {
        "query": query_text,
        "top_k": max(int(top_k), 1),
        "filters": {
            "universe": universe_value,
        }
    }

    # Include tenant in filters
    if tenant:
        body["filters"]["tenant"] = str(tenant)

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
    # VIBE FIX: Align with MemorySearchRequest schema (Async)
    body = {
        "query": query_text,
        "top_k": max(int(top_k), 1),
        "filters": {
            "universe": universe_value,
        }
    }

    # Include tenant in filters
    if tenant:
        body["filters"]["tenant"] = str(tenant)

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


def recall_with_graph_boost(
    hits: List[RecallHit],
    graph_client: "GraphClient",
    graph_boost_factor: float = 0.3,
    max_neighbors: int = 5,
) -> List[RecallHit]:
    """Boost recall results using graph neighbor relationships.

    Per Requirements B2.1-B2.5:
    - B2.1: Gets 1-hop neighbors for each result
    - B2.2: Boosts neighbor scores by link_strength × graph_boost_factor
    - B2.3: Returns vector-only results on timeout (degraded mode)

    Args:
        hits: Initial recall hits from vector search.
        graph_client: GraphClient instance for neighbor queries.
        graph_boost_factor: Multiplier for graph-based score boost (default 0.3).
        max_neighbors: Maximum neighbors to fetch per hit.

    Returns:
        List of RecallHit with boosted scores, sorted by final score.
    """
    if not hits or graph_client is None:
        return hits

    # Build a map of coordinate -> hit for quick lookup
    coord_to_hit: dict = {}
    for hit in hits:
        coord = hit.payload.get("coordinate") if hit.payload else None
        if coord:
            # Normalize coordinate to tuple
            if isinstance(coord, (list, tuple)):
                coord_key = tuple(coord)
            else:
                coord_key = coord
            coord_to_hit[coord_key] = hit

    # Track score boosts from graph relationships
    score_boosts: dict = {}

    # B2.1: Get 1-hop neighbors for each result
    for hit in hits:
        coord = hit.payload.get("coordinate") if hit.payload else None
        if not coord:
            continue

        # Normalize coordinate
        if isinstance(coord, list):
            coord = tuple(coord)

        try:
            # B2.5: 100ms timeout is handled by GraphClient
            neighbors = graph_client.get_neighbors(coord, k_hop=1, limit=max_neighbors)

            # B2.2: Boost neighbor scores
            for neighbor in neighbors:
                neighbor_coord = neighbor.coord
                if neighbor_coord in coord_to_hit:
                    # Calculate boost: link_strength × graph_boost_factor
                    boost = neighbor.strength * graph_boost_factor
                    if neighbor_coord not in score_boosts:
                        score_boosts[neighbor_coord] = 0.0
                    score_boosts[neighbor_coord] += boost

        except Exception as exc:
            # B2.3: On error/timeout, continue without graph boost
            logger.warning(
                "Graph neighbor query failed, continuing without boost",
                error=str(exc),
            )
            continue

    # Apply boosts to hits
    boosted_hits = []
    for hit in hits:
        coord = hit.payload.get("coordinate") if hit.payload else None
        if coord:
            if isinstance(coord, list):
                coord = tuple(coord)
            boost = score_boosts.get(coord, 0.0)
            if boost > 0:
                # Create new hit with boosted score
                new_score = (hit.score or 0.0) + boost
                boosted_hit = RecallHit(
                    payload=hit.payload,
                    score=new_score,
                    coordinate=hit.coordinate,
                )
                boosted_hits.append(boosted_hit)
            else:
                boosted_hits.append(hit)
        else:
            boosted_hits.append(hit)

    # Sort by score descending
    boosted_hits.sort(key=lambda h: h.score or 0.0, reverse=True)

    return boosted_hits


def recall_with_degradation(
    tenant: str,
    query: str,
    top_k: int,
    universe: str,
    request_id: str,
    require_healthy_fn: callable,
    http_recall_fn: callable,
) -> List[RecallHit]:
    """Recall memories with degradation handling.

    Per Requirements E1.1-E1.5:
    - E1.1: Check degradation state before calling SFM
    - E1.2: When circuit breaker is open, skip SFM call
    - E1.3: Track degradation state per tenant
    - E1.4: Return empty results in degraded mode
    - E1.5: Check if alert should be triggered

    Args:
        tenant: Tenant identifier.
        query: Search query string.
        top_k: Maximum number of results.
        universe: Universe/scope for search.
        request_id: Request ID for tracing.
        require_healthy_fn: Function to check SFM health.
        http_recall_fn: Function to perform HTTP recall.

    Returns:
        List of RecallHit objects.
    """
    from somabrain.infrastructure.degradation import get_degradation_manager

    degradation_mgr = get_degradation_manager()

    # E1.1: Check degradation state before calling SFM
    if degradation_mgr.is_degraded(tenant):
        # E1.5: Check if we should trigger alert
        degradation_mgr.check_alert(tenant)
        logger.warning(
            "SFM degraded mode: returning empty results",
            extra={"tenant": tenant, "query_preview": query[:50] if query else ""},
        )
        return []

    try:
        require_healthy_fn()
        results = http_recall_fn(query, top_k, universe, request_id)
        # SFM call succeeded - mark recovered
        degradation_mgr.mark_recovered(tenant)
        return results
    except RuntimeError as exc:
        # SFM unavailable - enter degraded mode
        degradation_mgr.mark_degraded(tenant)
        logger.warning(
            "SFM unavailable, entering degraded mode",
            extra={"tenant": tenant, "error": str(exc)},
        )
        return []


async def arecall_with_degradation(
    tenant: str,
    query: str,
    top_k: int,
    universe: str,
    request_id: str,
    require_healthy_fn: callable,
    http_recall_async_fn: callable,
    sync_fallback_fn: callable,
    has_async_client: bool,
) -> List[RecallHit]:
    """Async recall with degradation handling.

    Per Requirements E1.1-E1.5.

    Args:
        tenant: Tenant identifier.
        query: Search query string.
        top_k: Maximum number of results.
        universe: Universe/scope for search.
        request_id: Request ID for tracing.
        require_healthy_fn: Function to check SFM health.
        http_recall_async_fn: Async function to perform HTTP recall.
        sync_fallback_fn: Sync fallback function.
        has_async_client: Whether async client is available.

    Returns:
        List of RecallHit objects.
    """
    import asyncio
    from somabrain.infrastructure.degradation import get_degradation_manager

    degradation_mgr = get_degradation_manager()

    if degradation_mgr.is_degraded(tenant):
        degradation_mgr.check_alert(tenant)
        logger.warning(
            "SFM degraded mode (async): returning empty results",
            extra={"tenant": tenant},
        )
        return []

    try:
        if has_async_client:
            results = await http_recall_async_fn(query, top_k, universe, request_id)
            degradation_mgr.mark_recovered(tenant)
            return results
        # Fallback to sync in executor
        results = await asyncio.get_event_loop().run_in_executor(
            None, sync_fallback_fn, query, top_k, universe, request_id
        )
        return results
    except RuntimeError as exc:
        degradation_mgr.mark_degraded(tenant)
        logger.warning(
            "SFM unavailable (async), entering degraded mode",
            extra={"tenant": tenant, "error": str(exc)},
        )
        return []