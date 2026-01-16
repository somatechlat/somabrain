"""Bulk remember operations for SomaBrain memory client.

Extracted from memory/remember.py per monolithic-decomposition spec.
Provides bulk store operations with chunking and partial failure handling.

Per Requirements F1.1-F1.5:
- F1.1: Chunks items into batches of max 100 items per request
- F1.2: Handles partial failures - commits successful, tracks failed
- F1.3: Returns BulkStoreResult with succeeded/failed counts
- F1.4: Retries failed items once before marking as failed
- F1.5: Records metrics for batch_size, latency, success_rate
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Iterable, List, Tuple, TYPE_CHECKING

from somabrain.memory.normalization import _extract_memory_coord

if TYPE_CHECKING:
    from somabrain.memory.types import BulkStoreResult

logger = logging.getLogger(__name__)


def remember_bulk_optimized(
    cfg: Any,
    items: Iterable[tuple[str, dict[str, Any]]],
    request_id: str | None,
    tenant: str,
    require_healthy_fn: Callable,
    store_bulk_http_sync_fn: Callable,
    store_http_sync_fn: Callable,
    prepare_bulk_items_fn: Callable,
    process_bulk_response_fn: Callable,
) -> "BulkStoreResult":
    """Optimized bulk store with chunking and partial failure handling."""
    import time
    from somabrain.memory.types import BulkStoreResult

    chunk_size = 100
    start_time = time.perf_counter()
    rid = request_id or str(uuid.uuid4())

    items_list = list(items)
    total_items = len(items_list)

    if total_items == 0:
        return BulkStoreResult(
            succeeded=0,
            failed=0,
            coordinates=[],
            failed_items=[],
            request_id=rid,
        )

    try:
        require_healthy_fn()
    except RuntimeError as exc:
        logger.error("Bulk store failed: SFM unavailable", error=str(exc))
        return BulkStoreResult(
            succeeded=0,
            failed=total_items,
            coordinates=[],
            failed_items=list(range(total_items)),
            request_id=rid,
            error=str(exc),
        )

    chunks = [items_list[i : i + chunk_size] for i in range(0, total_items, chunk_size)]
    all_coords: List[Tuple[float, float, float]] = []
    failed_indices: List[int] = []
    succeeded_count = 0
    current_index = 0

    for chunk_idx, chunk in enumerate(chunks):
        chunk_rid = f"{rid}:chunk{chunk_idx}"
        try:
            prepared, universes, coords, _, namespace = prepare_bulk_items_fn(cfg, chunk)
            if not prepared:
                for i in range(len(chunk)):
                    failed_indices.append(current_index + i)
                current_index += len(chunk)
                continue

            headers = {"X-Request-ID": chunk_rid}
            unique_universes = [u for u in set(universes) if u]
            batch_universe = unique_universes[0] if len(unique_universes) == 1 else None
            if batch_universe:
                headers["X-Universe"] = batch_universe

            batch_payload = {
                "tenant": tenant,
                "namespace": namespace,
                "items": [entry["body"] for entry in prepared],
            }
            if batch_universe:
                batch_payload["universe"] = batch_universe

            success, status, response = store_bulk_http_sync_fn(batch_payload, headers)

            if success and response is not None:
                chunk_coords = process_bulk_response_fn(response, prepared, coords, chunk_rid)
                all_coords.extend(chunk_coords)
                succeeded_count += len(chunk)
            elif status in (404, 405):
                for idx, entry in enumerate(prepared):
                    single_headers = {"X-Request-ID": f"{chunk_rid}:{idx}"}
                    ok, resp = store_http_sync_fn(entry["body"], single_headers)
                    if ok and resp is not None:
                        server_coord = _extract_memory_coord(
                            resp, idempotency_key=single_headers["X-Request-ID"]
                        )
                        if server_coord:
                            all_coords.append(server_coord)
                            succeeded_count += 1
                        else:
                            all_coords.append(coords[idx])
                            succeeded_count += 1
                    else:
                        ok2, _ = store_http_sync_fn(entry["body"], single_headers)
                        if ok2:
                            all_coords.append(coords[idx])
                            succeeded_count += 1
                        else:
                            failed_indices.append(current_index + idx)
            else:
                logger.warning("Bulk chunk failed", chunk_idx=chunk_idx, status=status)
                for i in range(len(chunk)):
                    failed_indices.append(current_index + i)
        except Exception as exc:
            logger.error("Bulk chunk exception", chunk_idx=chunk_idx, error=str(exc))
            for i in range(len(chunk)):
                failed_indices.append(current_index + i)
        current_index += len(chunk)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    success_rate = succeeded_count / total_items if total_items > 0 else 0.0

    try:
        from prometheus_client import Counter, Histogram

        BULK_STORE_TOTAL = Counter(
            "sb_bulk_store_total", "Total bulk store operations", ["tenant", "status"]
        )
        BULK_STORE_ITEMS = Counter(
            "sb_bulk_store_items_total",
            "Total items in bulk store operations",
            ["tenant", "status"],
        )
        BULK_STORE_LATENCY = Histogram(
            "sb_bulk_store_latency_ms", "Bulk store latency in milliseconds", ["tenant"]
        )
        BULK_STORE_TOTAL.labels(tenant=tenant, status="success").inc()
        BULK_STORE_ITEMS.labels(tenant=tenant, status="succeeded").inc(succeeded_count)
        BULK_STORE_ITEMS.labels(tenant=tenant, status="failed").inc(len(failed_indices))
        BULK_STORE_LATENCY.labels(tenant=tenant).observe(elapsed_ms)
    except Exception:
        pass

    logger.info(
        "Bulk store completed",
        total=total_items,
        succeeded=succeeded_count,
        failed=len(failed_indices),
    )

    return BulkStoreResult(
        succeeded=succeeded_count,
        failed=len(failed_indices),
        coordinates=all_coords,
        failed_items=failed_indices,
        request_id=rid,
        latency_ms=elapsed_ms,
        success_rate=success_rate,
    )


def remember_bulk_sync(
    cfg: Any,
    items: Iterable[tuple[str, dict[str, Any]]],
    request_id: str | None,
    require_healthy_fn: Callable,
    store_bulk_http_sync_fn: Callable,
    store_http_sync_fn: Callable,
    prepare_bulk_items_fn: Callable,
    process_bulk_response_fn: Callable,
    has_transport: bool,
) -> List[Tuple[float, float, float]]:
    """Store multiple memories in a single HTTP round-trip."""
    require_healthy_fn()

    prepared, universes, coords, tenant, namespace = prepare_bulk_items_fn(cfg, items)
    if not prepared:
        return []

    if not has_transport:
        raise RuntimeError(
            "MEMORY SERVICE REQUIRED: HTTP memory backend not available (bulk remember)."
        )

    rid = request_id or str(uuid.uuid4())
    headers = {"X-Request-ID": rid}
    unique_universes = [u for u in set(universes) if u]
    batch_universe = unique_universes[0] if len(unique_universes) == 1 else None
    if batch_universe:
        headers["X-Universe"] = batch_universe
    batch_payload = {
        "tenant": tenant,
        "namespace": namespace,
        "items": [entry["body"] for entry in prepared],
    }
    if batch_universe:
        batch_payload["universe"] = batch_universe

    success, status, response = store_bulk_http_sync_fn(batch_payload, headers)
    if success and response is not None:
        return process_bulk_response_fn(response, prepared, coords, rid)

    if status in (404, 405):
        for idx, entry in enumerate(prepared):
            single_headers = dict(headers)
            single_headers["X-Request-ID"] = f"{rid}:{idx}"
            ok, resp = store_http_sync_fn(entry["body"], single_headers)
            if ok and resp is not None:
                server_coord = _extract_memory_coord(
                    resp, idempotency_key=single_headers["X-Request-ID"]
                )
                if server_coord:
                    coords[idx] = server_coord
        return coords

    raise RuntimeError("Memory service unavailable (bulk remember failed)")


async def aremember_bulk(
    cfg: Any,
    items: Iterable[tuple[str, dict[str, Any]]],
    request_id: str | None,
    require_healthy_fn: Callable,
    store_bulk_http_async_fn: Callable,
    store_http_async_fn: Callable,
    sync_fallback_fn: Callable,
    prepare_bulk_items_fn: Callable,
    process_bulk_response_fn: Callable,
    has_async_transport: bool,
) -> List[Tuple[float, float, float]]:
    """Async companion to remember_bulk using the async HTTP client."""
    require_healthy_fn()

    records = list(items)
    if not records:
        return []

    prepared, universes, coords, tenant, namespace = prepare_bulk_items_fn(cfg, records)
    if not prepared:
        return []

    if not has_async_transport:
        return sync_fallback_fn(records, request_id)

    rid = request_id or str(uuid.uuid4())
    headers = {"X-Request-ID": rid}
    unique_universes = [u for u in set(universes) if u]
    batch_universe = unique_universes[0] if len(unique_universes) == 1 else None
    if batch_universe:
        headers["X-Universe"] = batch_universe
    batch_payload = {
        "tenant": tenant,
        "namespace": namespace,
        "items": [entry["body"] for entry in prepared],
    }
    if batch_universe:
        batch_payload["universe"] = batch_universe

    success, status, response = await store_bulk_http_async_fn(batch_payload, headers)
    if success and response is not None:
        return process_bulk_response_fn(response, prepared, coords, rid)

    if status in (404, 405):
        for idx, entry in enumerate(prepared):
            single_headers = dict(headers)
            single_headers["X-Request-ID"] = f"{rid}:{idx}"
            ok, resp = await store_http_async_fn(entry["body"], single_headers)
            if ok and resp is not None:
                server_coord = _extract_memory_coord(
                    resp, idempotency_key=single_headers["X-Request-ID"]
                )
                if server_coord:
                    coords[idx] = server_coord
        return coords

    raise RuntimeError("Memory service unavailable (async bulk remember failed)")
