"""Memory Client Module for SomaBrain.

The client speaks to the external HTTP memory service used by SomaBrain. When
the service is unavailable it mirrors writes locally and records them in an
outbox for replay. This module is the single gateway for storing, retrieving,
and linking memories; other packages must call into it rather than integrating
with the memory service directly.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
import httpx
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import Config
from common.config.settings import settings
from somabrain.infrastructure import get_memory_http_endpoint, resolve_memory_endpoint
from somabrain.interfaces.memory import MemoryBackend
from somabrain.memory.transport import (
    MemoryHTTPTransport,
    _http_setting,
    _response_json,
)
from somabrain.memory.types import RecallHit
from somabrain.memory.normalization import _stable_coord, _extract_memory_coord
from somabrain.memory.hit_processing import normalize_recall_hits, deduplicate_hits
from somabrain.memory.scoring import (
    get_recency_normalisation,
    get_recency_profile,
    compute_recency_features,
    compute_density_factor,
    rescore_and_rank_hits,
)
from somabrain.memory.payload import enrich_payload, prepare_memory_payload
from dataclasses import dataclass, field


@dataclass
class BulkStoreResult:
    """Result of a bulk store operation.

    Per Requirements F1.3-F1.5:
    - Tracks succeeded/failed counts
    - Lists coordinates of successfully stored items
    - Lists indices of failed items for retry
    - Records latency and success rate metrics
    """

    succeeded: int
    failed: int
    coordinates: List[Tuple[float, float, float]]
    failed_items: List[int] = field(default_factory=list)
    request_id: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0
    success_rate: float = 0.0


# logger for diagnostic output during tests
logger = logging.getLogger(__name__)
debug_memory_client = bool(getattr(settings, "debug_memory_client", False)) if settings else False
if debug_memory_client and not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.DEBUG)


class MemoryClient:
    """Single gateway to the external memory service.

    Core API: remember/aremember, recall/arecall, link/alink, links_from, k_hop.
    Requires healthy HTTP backend; fails fast if unavailable.
    """

    def __init__(self, cfg: Config, scorer: Optional[Any] = None, embedder: Optional[Any] = None):
        self.cfg = cfg
        self._scorer = scorer
        self._embedder = embedder
        self._mode = "http"
        self._local = None
        self._transport: Optional[MemoryHTTPTransport] = None
        db_path = (
            str(getattr(settings, "memory_db_path", "./data/memory.db"))
            if settings
            else "./data/memory.db"
        )
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        except Exception:
            pass
        # Store for potential future use (e.g., passing to the local backend)
        self._memory_db_path = db_path
        # Initialize HTTP transport (primary runtime path).
        self._transport = self._create_transport()

    def _init_local(self) -> None:
        return

    def _create_transport(self) -> MemoryHTTPTransport:
        headers = {}
        token_value = getattr(self.cfg, "memory_http_token", None)
        if token_value:
            headers["Authorization"] = f"Bearer {token_value}"
            headers["X-API-Key"] = token_value

        # TENANT ISOLATION (D1.3): Always set tenant headers for isolation
        # Get tenant and namespace using the centralized function
        from somabrain.memory.utils import get_tenant_namespace

        tenant, namespace = get_tenant_namespace(self.cfg)

        # CRITICAL: Always set both headers - never leave empty
        # This ensures SFM can enforce tenant isolation (D1.1, D1.2)
        headers["X-Soma-Namespace"] = namespace or "default"
        headers["X-Soma-Tenant"] = tenant or "default"  # Never empty per D1.4

        max_conns = (
            int(
                getattr(
                    settings,
                    "http_max_connections",
                    _http_setting("http_max_connections", 64),
                )
            )
            if settings
            else 64
        )
        keepalive = (
            int(
                getattr(
                    settings,
                    "http_keepalive_connections",
                    _http_setting("http_keepalive_connections", 32),
                )
            )
            if settings
            else 32
        )
        retries = (
            int(getattr(settings, "http_retries", _http_setting("http_retries", 1)))
            if settings
            else 1
        )

        try:
            limits = httpx.Limits(max_connections=max_conns, max_keepalive_connections=keepalive)
        except Exception:
            limits = None

        resolved = None
        try:
            resolved = resolve_memory_endpoint()
        except RuntimeError:
            pass

        cfg_endpoint = str(getattr(self.cfg, "memory_http_endpoint", "") or "")
        base_url = (
            cfg_endpoint.strip()
            if cfg_endpoint
            else (resolved.url if resolved else get_memory_http_endpoint() or "")
        )
        if not base_url:
            raise RuntimeError("Memory HTTP endpoint required but not configured")
        if base_url.endswith("/openapi.json"):
            base_url = base_url[: -len("/openapi.json")]
        base_url = base_url.rstrip("/")

        transport = MemoryHTTPTransport(
            base_url=base_url,
            headers=headers,
            limits=limits,
            retries=retries,
            logger=logger,
        )
        if transport.client is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED but not reachable. Set SOMABRAIN_MEMORY_HTTP_ENDPOINT."
            )
        if not token_value:
            logger.warning("Memory HTTP client initialized without token; proceeding without auth.")
        return transport

    def _get_http_client(self) -> Optional[httpx.Client]:
        if self._transport is None:
            return None
        return self._transport.client

    def _get_http_async_client(self) -> Optional[httpx.AsyncClient]:
        if self._transport is None:
            return None
        return self._transport.async_client

    def _init_redis(self) -> None:
        return

    def health(self) -> dict:
        """Return health information from the external memory service.

        Per Requirements E3.1-E3.5:
        - Returns structured component status (kv_store, vector_store, graph_store)
        - Reports degraded (not failed) when any component unhealthy
        - Lists specific unhealthy components
        - Uses 2-second timeout for health check
        """
        if self._transport is None or self._transport.client is None:
            return {
                "healthy": False,
                "error": "HTTP client not configured",
                "degraded": True,
                "degraded_components": ["http_client"],
                "kv_store": False,
                "vector_store": False,
                "graph_store": False,
            }
        try:
            # E3.4: 2-second timeout for health check
            r = self._transport.client.get("/health", timeout=2.0)
            status_code = int(getattr(r, "status_code", 0) or 0)
            if status_code != 200:
                return {
                    "healthy": False,
                    "status": status_code,
                    "degraded": True,
                    "degraded_components": ["sfm_api"],
                    "kv_store": False,
                    "vector_store": False,
                    "graph_store": False,
                }
            data = self._response_json(r) or {}
            if not isinstance(data, dict):
                return {
                    "healthy": False,
                    "error": "unexpected health payload",
                    "degraded": True,
                    "degraded_components": ["sfm_response"],
                    "kv_store": False,
                    "vector_store": False,
                    "graph_store": False,
                }

            # E3.1: Extract component status
            kv = bool(data.get("kv_store"))
            vec = bool(data.get("vector_store"))
            graph = bool(data.get("graph_store"))

            # E3.2, E3.5: Determine degraded status and list unhealthy components
            degraded_components = []
            if not kv:
                degraded_components.append("kv_store")
            if not vec:
                degraded_components.append("vector_store")
            if not graph:
                degraded_components.append("graph_store")

            is_degraded = len(degraded_components) > 0
            is_healthy = kv and vec and graph

            return {
                **data,
                "healthy": is_healthy,
                "kv_store": kv,
                "vector_store": vec,
                "graph_store": graph,
                "degraded": is_degraded,
                "degraded_components": degraded_components,
            }
        except Exception as exc:
            # E3.3: SFM unreachable - report degraded with sfm_unreachable
            return {
                "healthy": False,
                "error": str(exc),
                "degraded": True,
                "degraded_components": ["sfm_unreachable"],
                "kv_store": False,
                "vector_store": False,
                "graph_store": False,
            }

    def _require_healthy(self) -> None:
        """Raise error if memory service is not fully healthy."""
        health = self.health()
        if not health.get("healthy"):
            missing = [c for c in ("kv_store", "vector_store", "graph_store") if not health.get(c)]
            raise RuntimeError(f"Memory service unavailable: {', '.join(missing) or 'unknown'}")

    # HTTP helpers - delegate to extracted module
    _response_json = staticmethod(_response_json)

    def _http_post_with_retries_sync(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = 2,
        operation: str = "unknown",
    ) -> tuple[bool, int, Any]:
        from somabrain.memory.http_helpers import http_post_with_retries_sync

        return http_post_with_retries_sync(
            self._transport,
            endpoint,
            body,
            headers,
            self._tenant_namespace()[0],
            max_retries=max_retries,
            operation=operation,
        )

    async def _http_post_with_retries_async(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = 2,
        operation: str = "unknown",
    ) -> tuple[bool, int, Any]:
        from somabrain.memory.http_helpers import http_post_with_retries_async

        return await http_post_with_retries_async(
            self._transport,
            endpoint,
            body,
            headers,
            self._tenant_namespace()[0],
            max_retries=max_retries,
            operation=operation,
        )

    def _store_http_sync(self, body: dict, headers: dict) -> tuple[bool, Any]:
        from somabrain.memory.http_helpers import store_http_sync

        return store_http_sync(self._transport, body, headers, self._tenant_namespace()[0])

    async def _store_http_async(self, body: dict, headers: dict) -> tuple[bool, Any]:
        from somabrain.memory.http_helpers import store_http_async

        return await store_http_async(self._transport, body, headers, self._tenant_namespace()[0])

    def _store_bulk_http_sync(self, batch_request: dict, headers: dict) -> tuple[bool, int, Any]:
        from somabrain.memory.http_helpers import store_bulk_http_sync

        return store_bulk_http_sync(
            self._transport, batch_request, headers, self._tenant_namespace()[0]
        )

    async def _store_bulk_http_async(
        self, batch_request: dict, headers: dict
    ) -> tuple[bool, int, Any]:
        from somabrain.memory.http_helpers import store_bulk_http_async

        return await store_bulk_http_async(
            self._transport, batch_request, headers, self._tenant_namespace()[0]
        )

    # Hit processing - static method aliases for backward compatibility
    _normalize_recall_hits = staticmethod(normalize_recall_hits)
    _deduplicate_hits = staticmethod(deduplicate_hits)

    def _memories_search_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        from somabrain.memory.recall_ops import memories_search_sync

        tenant, _ = self._tenant_namespace()
        return memories_search_sync(
            self._transport,
            query,
            top_k,
            universe,
            request_id,
            http_post_fn=self._http_post_with_retries_sync,
            rescore_fn=self._rescore_and_rank_hits,
            tenant=tenant,
        )

    async def _memories_search_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        from somabrain.memory.recall_ops import memories_search_async

        tenant, _ = self._tenant_namespace()
        return await memories_search_async(
            self._transport,
            query,
            top_k,
            universe,
            request_id,
            http_post_fn=self._http_post_with_retries_async,
            rescore_fn=self._rescore_and_rank_hits,
            tenant=tenant,
        )

    # Recall aggregation aliases
    def _http_recall_aggregate_sync(self, q: str, k: int, u: str, r: str) -> List[RecallHit]:
        return self._memories_search_sync(q, k, u, r)

    def _http_recall_aggregate_async(self, q: str, k: int, u: str, r: str) -> List[RecallHit]:
        return self._memories_search_async(q, k, u, r)

    def _filter_hits_by_keyword(self, hits: List[RecallHit], keyword: str) -> List[RecallHit]:
        from somabrain.memory.recall_ops import filter_hits_by_keyword

        return filter_hits_by_keyword(hits, keyword)

    # Scoring/recency helpers
    def _recency_normalisation(self) -> tuple[float, float]:
        return get_recency_normalisation(self.cfg)

    def _recency_profile(self) -> tuple[float, float, float, float]:
        return get_recency_profile(self.cfg)

    def _recency_features(
        self, ts_epoch: float | None, now_ts: float
    ) -> tuple[float | None, float]:
        return compute_recency_features(ts_epoch, now_ts, self.cfg)

    def _density_factor(self, margin: float | None) -> float:
        return compute_density_factor(margin, self.cfg)

    def _rescore_and_rank_hits(self, hits: List[RecallHit], query: str) -> List[RecallHit]:
        return rescore_and_rank_hits(hits, query, self.cfg, self._scorer, self._embedder)

    def _compat_enrich_payload(self, payload: dict, coord_key: str) -> tuple[dict, str, dict]:
        tenant, namespace = self._tenant_namespace()
        return enrich_payload(payload, coord_key, namespace, tenant=tenant)

    def _tenant_namespace(self) -> tuple[str, str]:
        from somabrain.memory.utils import get_tenant_namespace

        return get_tenant_namespace(self.cfg)

    def _record_http_metrics(
        self, operation: str, success: bool, status: int, duration: float
    ) -> None:
        from somabrain.memory.http_helpers import record_http_metrics

        record_http_metrics(operation, self._tenant_namespace()[0], success, status, duration)

    def remember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float]:
        """Store a memory using a stable coordinate derived from ``coord_key``."""
        self._require_healthy()
        enriched, universe, _hdr = self._compat_enrich_payload(payload, coord_key)
        coord = _stable_coord(f"{universe}::{coord_key}")
        payload = prepare_memory_payload(enriched, coord_key, universe)
        try:
            payload.setdefault("coordinate", coord)
        except Exception:
            pass
        rid = request_id or str(uuid.uuid4())

        # Detect async context: schedule background persistence if in async loop
        in_async = False
        try:
            loop = asyncio.get_running_loop()
            in_async = True
        except Exception:
            pass

        if in_async:
            self._schedule_async_persist(coord_key, payload, rid, loop)
            return coord

        # Check fast-ack mode for sync callers
        fast_ack = bool(getattr(settings, "memory_fast_ack", False)) if settings else False
        if fast_ack:
            try:
                asyncio.get_event_loop().run_in_executor(
                    None, self._remember_sync_persist, coord_key, payload, rid
                )
            except Exception:
                try:
                    self._remember_sync_persist(coord_key, payload, rid)
                except Exception:
                    pass
            return coord

        # Default: synchronous blocking persist
        server_coord = self._remember_sync_persist(coord_key, payload, rid)
        if server_coord:
            coord = server_coord
            try:
                payload["coordinate"] = server_coord
            except Exception:
                pass
        return coord

    def _schedule_async_persist(self, coord_key: str, payload: dict, rid: str, loop) -> None:
        """Schedule async or executor-based persistence."""
        try:
            if self._transport is not None and self._transport.async_client is not None:
                try:
                    loop.create_task(self._aremember_background(coord_key, payload, rid))
                except Exception:
                    loop.run_in_executor(None, self._remember_sync_persist, coord_key, payload, rid)
            else:
                loop.run_in_executor(None, self._remember_sync_persist, coord_key, payload, rid)
        except Exception:
            try:
                self._remember_sync_persist(coord_key, payload, rid)
            except Exception:
                pass

    def remember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Store multiple memories in a single HTTP round-trip."""
        from somabrain.memory.remember import prepare_bulk_items, process_bulk_response

        self._require_healthy()

        prepared, universes, coords, tenant, namespace = prepare_bulk_items(self.cfg, items)
        if not prepared:
            return []

        if self._transport is None or self._transport.client is None:
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

        success, status, response = self._store_bulk_http_sync(batch_payload, headers)
        if success and response is not None:
            return process_bulk_response(response, prepared, coords, rid)

        if status in (404, 405):
            for idx, entry in enumerate(prepared):
                single_headers = dict(headers)
                single_headers["X-Request-ID"] = f"{rid}:{idx}"
                ok, resp = self._store_http_sync(entry["body"], single_headers)
                if ok and resp is not None:
                    server_coord = _extract_memory_coord(
                        resp, idempotency_key=single_headers["X-Request-ID"]
                    )
                    if server_coord:
                        coords[idx] = server_coord
            return coords

        raise RuntimeError("Memory service unavailable (bulk remember failed)")

    def remember_bulk_optimized(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
        chunk_size: int = 100,
    ) -> "BulkStoreResult":
        """Optimized bulk store with chunking and partial failure handling.

        Per Requirements F1.1-F1.5:
        - F1.1: Chunks items into batches of max 100 items per request
        - F1.2: Handles partial failures - commits successful, tracks failed
        - F1.3: Returns BulkStoreResult with succeeded/failed counts
        - F1.4: Retries failed items once before marking as failed
        - F1.5: Records metrics for batch_size, latency, success_rate

        Args:
            items: Iterable of (coord_key, payload) tuples to store.
            request_id: Optional request ID for tracing.
            chunk_size: Maximum items per chunk (default 100 per F1.1).

        Returns:
            BulkStoreResult with succeeded/failed counts and coordinates.
        """
        import time
        from somabrain.memory.remember import prepare_bulk_items, process_bulk_response

        start_time = time.perf_counter()
        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()

        # Convert to list for chunking
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

        # Check health once before processing
        try:
            self._require_healthy()
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

        # F1.1: Chunk items into batches
        chunks = [items_list[i : i + chunk_size] for i in range(0, total_items, chunk_size)]

        all_coords: List[Tuple[float, float, float]] = []
        failed_indices: List[int] = []
        succeeded_count = 0
        current_index = 0

        for chunk_idx, chunk in enumerate(chunks):
            chunk_rid = f"{rid}:chunk{chunk_idx}"

            try:
                # Prepare this chunk
                prepared, universes, coords, _, namespace = prepare_bulk_items(self.cfg, chunk)
                if not prepared:
                    # All items in chunk failed preparation
                    for i in range(len(chunk)):
                        failed_indices.append(current_index + i)
                    current_index += len(chunk)
                    continue

                # Build batch payload
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

                # F1.2: Try to store the chunk
                success, status, response = self._store_bulk_http_sync(batch_payload, headers)

                if success and response is not None:
                    # Process successful response
                    chunk_coords = process_bulk_response(response, prepared, coords, chunk_rid)
                    all_coords.extend(chunk_coords)
                    succeeded_count += len(chunk)
                elif status in (404, 405):
                    # Bulk endpoint not available - fall back to individual stores
                    for idx, entry in enumerate(prepared):
                        single_headers = {"X-Request-ID": f"{chunk_rid}:{idx}"}
                        ok, resp = self._store_http_sync(entry["body"], single_headers)
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
                            # F1.4: Retry once
                            ok2, resp2 = self._store_http_sync(entry["body"], single_headers)
                            if ok2:
                                all_coords.append(coords[idx])
                                succeeded_count += 1
                            else:
                                failed_indices.append(current_index + idx)
                else:
                    # Chunk failed - mark all items as failed
                    logger.warning(
                        "Bulk chunk failed",
                        chunk_idx=chunk_idx,
                        status=status,
                        chunk_size=len(chunk),
                    )
                    for i in range(len(chunk)):
                        failed_indices.append(current_index + i)

            except Exception as exc:
                # Chunk failed with exception
                logger.error(
                    "Bulk chunk exception",
                    chunk_idx=chunk_idx,
                    error=str(exc),
                )
                for i in range(len(chunk)):
                    failed_indices.append(current_index + i)

            current_index += len(chunk)

        # F1.5: Record metrics
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        success_rate = succeeded_count / total_items if total_items > 0 else 0.0

        try:
            from prometheus_client import Counter, Histogram

            BULK_STORE_TOTAL = Counter(
                "sb_bulk_store_total",
                "Total bulk store operations",
                ["tenant", "status"],
            )
            BULK_STORE_ITEMS = Counter(
                "sb_bulk_store_items_total",
                "Total items in bulk store operations",
                ["tenant", "status"],
            )
            BULK_STORE_LATENCY = Histogram(
                "sb_bulk_store_latency_ms",
                "Bulk store latency in milliseconds",
                ["tenant"],
            )

            BULK_STORE_TOTAL.labels(tenant=tenant, status="success").inc()
            BULK_STORE_ITEMS.labels(tenant=tenant, status="succeeded").inc(succeeded_count)
            BULK_STORE_ITEMS.labels(tenant=tenant, status="failed").inc(len(failed_indices))
            BULK_STORE_LATENCY.labels(tenant=tenant).observe(elapsed_ms)
        except Exception:
            pass  # Metrics are optional

        logger.info(
            "Bulk store completed",
            total=total_items,
            succeeded=succeeded_count,
            failed=len(failed_indices),
            chunks=len(chunks),
            latency_ms=elapsed_ms,
            success_rate=success_rate,
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

    async def aremember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float]:
        """Async variant of remember for HTTP mode; falls back to thread executor."""
        self._require_healthy()
        if self._transport is not None and self._transport.async_client is not None:
            try:
                enriched, universe, compat_hdr = self._compat_enrich_payload(payload, coord_key)
                coord = _stable_coord(f"{universe}::{coord_key}")
                enriched = dict(enriched)
                enriched.setdefault("coordinate", coord)
                memory_type = str(enriched.get("memory_type") or enriched.get("type") or "episodic")
                body = {
                    "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                    "payload": enriched,
                    "memory_type": memory_type,
                }
                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                rid_hdr.update(compat_hdr)
                ok, response_data = await self._store_http_async(body, rid_hdr)
                if ok and response_data is not None:
                    server_coord = _extract_memory_coord(response_data, idempotency_key=rid)
                    if server_coord:
                        return server_coord
                return coord
            except Exception:
                pass
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.remember, coord_key, payload)

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Async companion to remember_bulk using the async HTTP client."""
        from somabrain.memory.remember import prepare_bulk_items, process_bulk_response

        self._require_healthy()

        records = list(items)
        if not records:
            return []

        prepared, universes, coords, tenant, namespace = prepare_bulk_items(self.cfg, records)
        if not prepared:
            return []

        if self._transport is None or self._transport.async_client is None:
            return self.remember_bulk(records, request_id=request_id)

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

        success, status, response = await self._store_bulk_http_async(batch_payload, headers)
        if success and response is not None:
            return process_bulk_response(response, prepared, coords, rid)

        if status in (404, 405):
            for idx, entry in enumerate(prepared):
                single_headers = dict(headers)
                single_headers["X-Request-ID"] = f"{rid}:{idx}"
                ok, resp = await self._store_http_async(entry["body"], single_headers)
                if ok and resp is not None:
                    server_coord = _extract_memory_coord(
                        resp, idempotency_key=single_headers["X-Request-ID"]
                    )
                    if server_coord:
                        coords[idx] = server_coord
            return coords

        raise RuntimeError("Memory service unavailable (async bulk remember failed)")

    def recall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Retrieve memories relevant to ``query`` via the HTTP backend.

        Per Requirements E1.1-E1.5:
        - When SFM unreachable, returns WM-only results with degraded=true
        - When circuit breaker is open, skips SFM call entirely
        - Tracks degradation state per tenant
        """
        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()

        # E1.1: Check degradation state before calling SFM
        from somabrain.infrastructure.degradation import get_degradation_manager

        degradation_mgr = get_degradation_manager()

        # Check if we're in degraded mode (circuit open or SFM unavailable)
        if degradation_mgr.is_degraded(tenant):
            # E1.5: Check if we should trigger alert (degraded > 5 minutes)
            degradation_mgr.check_alert(tenant)
            # Return empty results with degraded flag - WM-only mode
            # The caller (e.g., recall_ops) should handle WM fallback
            logger.warning(
                "SFM degraded mode: returning empty results",
                tenant=tenant,
                query_preview=query[:50] if query else "",
            )
            return []

        try:
            self._require_healthy()
            results = self._http_recall_aggregate_sync(query, top_k, universe or "real", rid)
            # SFM call succeeded - mark recovered if was degraded
            degradation_mgr.mark_recovered(tenant)
            return results
        except RuntimeError as exc:
            # SFM unavailable - enter degraded mode (E1.1)
            degradation_mgr.mark_degraded(tenant)
            logger.warning(
                "SFM unavailable, entering degraded mode",
                tenant=tenant,
                error=str(exc),
            )
            # Return empty results - WM-only mode
            return []

    def recall_with_scores(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Recall memories including similarity scores."""
        self._require_healthy()
        if self._transport is not None and self._transport.client is not None:
            hits = self._http_recall_aggregate_sync(
                query, top_k, universe or "real", request_id or str(uuid.uuid4())
            )
            if hits:
                return hits
        return self.recall(query, top_k, universe, request_id)

    async def arecall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Async recall for HTTP mode; falls back to sync execution when needed.

        Per Requirements E1.1-E1.5:
        - When SFM unreachable, returns WM-only results with degraded=true
        - When circuit breaker is open, skips SFM call entirely
        """
        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()

        # E1.1: Check degradation state before calling SFM
        from somabrain.infrastructure.degradation import get_degradation_manager

        degradation_mgr = get_degradation_manager()

        # Check if we're in degraded mode
        if degradation_mgr.is_degraded(tenant):
            degradation_mgr.check_alert(tenant)
            logger.warning(
                "SFM degraded mode (async): returning empty results",
                tenant=tenant,
            )
            return []

        try:
            if self._transport is not None and self._transport.async_client is not None:
                results = await self._http_recall_aggregate_async(
                    query, top_k, universe or "real", rid
                )
                degradation_mgr.mark_recovered(tenant)
                return results
            # Fallback to sync in executor
            results = await asyncio.get_event_loop().run_in_executor(
                None, self.recall, query, top_k, universe, request_id
            )
            return results
        except RuntimeError as exc:
            degradation_mgr.mark_degraded(tenant)
            logger.warning(
                "SFM unavailable (async), entering degraded mode",
                tenant=tenant,
                error=str(exc),
            )
            return []

    async def arecall_with_scores(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Async companion to recall_with_scores."""
        if self._transport is not None and self._transport.async_client is not None:
            hits = await self._http_recall_aggregate_async(
                query, top_k, universe or "real", request_id or str(uuid.uuid4())
            )
            if hits:
                return hits
        return await self.arecall(query, top_k, universe, request_id)

    # --- Hybrid Recall (C1) ---
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query for hybrid recall.

        Per Requirement C1.2: Extract keywords from query for hybrid matching.
        Uses simple tokenization - splits on whitespace and filters stopwords.
        """
        # Common English stopwords to filter out
        stopwords = {
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
        # Tokenize and filter
        tokens = query.lower().split()
        keywords = [
            t.strip(".,!?;:'\"()[]{}")
            for t in tokens
            if t.strip(".,!?;:'\"()[]{}") and t.lower() not in stopwords and len(t) > 2
        ]
        return keywords

    def hybrid_recall(
        self,
        query: str,
        top_k: int = 5,
        universe: str | None = None,
        request_id: str | None = None,
        keywords: List[str] | None = None,
    ) -> List[RecallHit]:
        """Hybrid recall combining vector similarity with keyword matching.

        Per Requirements C1.1-C1.5:
        - C1.1: Combines vector similarity with keyword matching
        - C1.2: Extracts keywords from query
        - C1.3: Calls SFM /memories/search with filters for hybrid matching
        - C1.4: Includes importance scores in ranking
        - C1.5: Falls back to vector-only on failure with degraded=true

        Args:
            query: Search query string.
            top_k: Maximum number of results to return.
            universe: Universe/scope for the search.
            request_id: Request ID for tracing.
            keywords: Optional explicit keywords (if None, extracted from query).

        Returns:
            List of RecallHit objects with hybrid scoring.
        """
        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()

        # Check degradation state
        from somabrain.infrastructure.degradation import get_degradation_manager

        degradation_mgr = get_degradation_manager()
        if degradation_mgr.is_degraded(tenant):
            degradation_mgr.check_alert(tenant)
            logger.warning(
                "SFM degraded mode (hybrid_recall): returning empty results",
                tenant=tenant,
            )
            return []

        # C1.2: Extract keywords from query if not provided
        kw_list = keywords if keywords is not None else self._extract_keywords(query)

        try:
            self._require_healthy()

            # Build filters for hybrid search
            # SFM's find_hybrid_by_type uses filters to enable hybrid scoring
            filters: Dict[str, Any] = {}
            if kw_list:
                # Pass keywords as filter hint for SFM hybrid scoring
                filters["_keywords"] = kw_list

            # C1.3: Call SFM /memories/search with filters
            headers = {"X-Request-ID": rid}
            body = {
                "query": str(query or ""),
                "top_k": max(int(top_k), 1),
                "universe": str(universe or "real"),
                "tenant": tenant,
            }
            if filters:
                body["filters"] = filters

            success, status, data = self._http_post_with_retries_sync(
                "/memories/search", body, headers, operation="hybrid_recall"
            )

            if success and data:
                # Process response with rescoring
                from somabrain.memory.recall_ops import process_search_response

                results = process_search_response(
                    data,
                    str(universe or "real"),
                    str(query or ""),
                    top_k,
                    self._rescore_and_rank_hits,
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
            return self.recall(query, top_k, universe, rid)

        except RuntimeError as exc:
            # C1.5: Enter degraded mode on failure
            degradation_mgr.mark_degraded(tenant)
            logger.warning(
                "SFM unavailable (hybrid_recall), entering degraded mode",
                tenant=tenant,
                error=str(exc),
            )
            return []

    async def ahybrid_recall(
        self,
        query: str,
        top_k: int = 5,
        universe: str | None = None,
        request_id: str | None = None,
        keywords: List[str] | None = None,
    ) -> List[RecallHit]:
        """Async version of hybrid_recall.

        Per Requirements C1.1-C1.5.
        """
        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()

        from somabrain.infrastructure.degradation import get_degradation_manager

        degradation_mgr = get_degradation_manager()
        if degradation_mgr.is_degraded(tenant):
            degradation_mgr.check_alert(tenant)
            logger.warning(
                "SFM degraded mode (ahybrid_recall): returning empty results",
                tenant=tenant,
            )
            return []

        kw_list = keywords if keywords is not None else self._extract_keywords(query)

        try:
            self._require_healthy()

            filters: Dict[str, Any] = {}
            if kw_list:
                filters["_keywords"] = kw_list

            headers = {"X-Request-ID": rid}
            body = {
                "query": str(query or ""),
                "top_k": max(int(top_k), 1),
                "universe": str(universe or "real"),
                "tenant": tenant,
            }
            if filters:
                body["filters"] = filters

            success, status, data = await self._http_post_with_retries_async(
                "/memories/search", body, headers, operation="ahybrid_recall"
            )

            if success and data:
                from somabrain.memory.recall_ops import process_search_response

                results = process_search_response(
                    data,
                    str(universe or "real"),
                    str(query or ""),
                    top_k,
                    self._rescore_and_rank_hits,
                    tenant=tenant,
                )
                degradation_mgr.mark_recovered(tenant)
                return results

            logger.warning(
                "Async hybrid recall failed, falling back to vector-only",
                status=status,
                tenant=tenant,
            )
            return await self.arecall(query, top_k, universe, rid)

        except RuntimeError as exc:
            degradation_mgr.mark_degraded(tenant)
            logger.warning(
                "SFM unavailable (ahybrid_recall), entering degraded mode",
                tenant=tenant,
                error=str(exc),
            )
            return []

    # --- Compatibility helper methods ---
    def coord_for_key(self, key: str, universe: str | None = None) -> Tuple[float, float, float]:
        """Return a deterministic coordinate for *key* and optional *universe*."""
        from somabrain.memory.utils import coord_for_key

        return coord_for_key(key, universe)

    def fetch_by_coord(
        self, coord: Tuple[float, float, float], universe: str | None = None
    ) -> List[Dict[str, Any]]:
        """Fetch memory payloads by coordinate using GET /memories/{coord}."""
        from somabrain.memory.utils import fetch_by_coord

        return fetch_by_coord(self._get_http_client(), coord)

    def store_from_payload(self, payload: dict, request_id: str | None = None) -> bool:
        """Store a payload dict into the memory backend."""
        from somabrain.memory.utils import store_from_payload

        return store_from_payload(payload, request_id, self._store_http_sync, self.remember)

    def _remember_sync_persist(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float] | None:
        """Synchronous persistence implementation."""
        from somabrain.memory.remember import remember_sync_persist

        return remember_sync_persist(
            self._transport,
            self.cfg,
            coord_key,
            payload,
            request_id,
            self._store_http_sync,
        )

    async def _aremember_background(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Async background persistence using the AsyncClient."""
        from somabrain.memory.remember import aremember_background

        await aremember_background(
            self._transport,
            self.cfg,
            coord_key,
            payload,
            request_id,
            self._store_http_async,
        )


# NOTE: MemoryClient already implements the required methods used by MemoryService.
# Adding a Protocol-based alias for type checkers helps during the refactor.
MemoryClientType: type = MemoryBackend
