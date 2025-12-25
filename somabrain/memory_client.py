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


from django.conf import settings

# Infrastructure imports moved to transport module
from somabrain.interfaces.memory import MemoryBackend
from somabrain.memory.transport import (
    MemoryHTTPTransport,
    _response_json,
    create_memory_transport,
)
from somabrain.memory.types import RecallHit, BulkStoreResult
from somabrain.memory.normalization import _stable_coord
from somabrain.memory.hit_processing import normalize_recall_hits, deduplicate_hits
from somabrain.memory.scoring import (
    get_recency_normalisation,
    get_recency_profile,
    compute_recency_features,
    compute_density_factor,
    rescore_and_rank_hits,
)
from somabrain.memory.payload import enrich_payload, prepare_memory_payload
from somabrain.memory.health import check_memory_health, require_healthy
from somabrain.memory.hybrid import (
    extract_keywords,
    hybrid_recall_sync,
    hybrid_recall_async,
)


# logger for diagnostic output during tests
logger = logging.getLogger(__name__)
debug_memory_client = (
    bool(getattr(settings, "SOMABRAIN_DEBUG_MEMORY_CLIENT", False)) if settings else False
)
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

    def __init__(
        self,
        cfg: Optional[Any] = None,
        scorer: Optional[Any] = None,
        embedder: Optional[Any] = None,
        namespace: Optional[str] = None,
    ):
        # ``cfg`` was previously mandatory, causing instantiation failures in
        # contexts (e.g., the Oak option manager) that relied on the default
        # configuration singleton.  Making it optional restores backward
        # compatibility while preserving the ability to inject a custom Config
        # for advanced use‑cases.
        self.cfg = cfg if cfg is not None else settings  # type: ignore[assignment]
        self._scorer = scorer
        self._embedder = embedder
        self._namespace_override = namespace
        self._mode = "http"
        self._local = None
        self._transport: Optional[MemoryHTTPTransport] = None
        db_path = (
            str(getattr(settings, "SOMABRAIN_MEMORY_DB_PATH", "./data/memory.db"))
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
        """Create HTTP transport for memory service communication."""
        return create_memory_transport(self.cfg, logger)

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
        """Return health information from the external memory service."""
        return check_memory_health(self._transport, self._response_json)

    def _require_healthy(self) -> None:
        """Raise error if memory service is not fully healthy."""
        require_healthy(self.health)

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

        return store_http_sync(
            self._transport, body, headers, self._tenant_namespace()[0]
        )

    async def _store_http_async(self, body: dict, headers: dict) -> tuple[bool, Any]:
        from somabrain.memory.http_helpers import store_http_async

        return await store_http_async(
            self._transport, body, headers, self._tenant_namespace()[0]
        )

    def _store_bulk_http_sync(
        self, batch_request: dict, headers: dict
    ) -> tuple[bool, int, Any]:
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
    def _http_recall_aggregate_sync(
        self, q: str, k: int, u: str, r: str
    ) -> List[RecallHit]:
        return self._memories_search_sync(q, k, u, r)

    def _http_recall_aggregate_async(
        self, q: str, k: int, u: str, r: str
    ) -> List[RecallHit]:
        return self._memories_search_async(q, k, u, r)

    def _filter_hits_by_keyword(
        self, hits: List[RecallHit], keyword: str
    ) -> List[RecallHit]:
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

    def _rescore_and_rank_hits(
        self, hits: List[RecallHit], query: str
    ) -> List[RecallHit]:
        return rescore_and_rank_hits(
            hits, query, self.cfg, self._scorer, self._embedder
        )

    def _compat_enrich_payload(
        self, payload: dict, coord_key: str
    ) -> tuple[dict, str, dict]:
        tenant, namespace = self._tenant_namespace()
        return enrich_payload(payload, coord_key, namespace, tenant=tenant)

    def _tenant_namespace(self) -> tuple[str, str]:
        from somabrain.memory.utils import get_tenant_namespace

        return get_tenant_namespace(self.cfg, override_namespace=self._namespace_override)

    def _record_http_metrics(
        self, operation: str, success: bool, status: int, duration: float
    ) -> None:
        from somabrain.memory.http_helpers import record_http_metrics

        record_http_metrics(
            operation, self._tenant_namespace()[0], success, status, duration
        )

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
        fast_ack = (
            bool(getattr(settings, "SOMABRAIN_MEMORY_FAST_ACK", False)) if settings else False
        )
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

    def _schedule_async_persist(
        self, coord_key: str, payload: dict, rid: str, loop
    ) -> None:
        """Schedule async or executor-based persistence."""
        try:
            if self._transport is not None and self._transport.async_client is not None:
                try:
                    loop.create_task(
                        self._aremember_background(coord_key, payload, rid)
                    )
                except Exception:
                    loop.run_in_executor(
                        None, self._remember_sync_persist, coord_key, payload, rid
                    )
            else:
                loop.run_in_executor(
                    None, self._remember_sync_persist, coord_key, payload, rid
                )
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
        from somabrain.memory.remember_bulk import remember_bulk_sync
        from somabrain.memory.remember import prepare_bulk_items, process_bulk_response

        has_transport = (
            self._transport is not None and self._transport.client is not None
        )
        return remember_bulk_sync(
            self.cfg,
            items,
            request_id,
            self._require_healthy,
            self._store_bulk_http_sync,
            self._store_http_sync,
            prepare_bulk_items,
            process_bulk_response,
            has_transport,
        )

    def remember_bulk_optimized(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
        chunk_size: int = 100,
    ) -> "BulkStoreResult":
        """Optimized bulk store with chunking and partial failure handling."""
        from somabrain.memory.remember_bulk import (
            remember_bulk_optimized as _remember_bulk_optimized,
        )
        from somabrain.memory.remember import prepare_bulk_items, process_bulk_response

        tenant, _ = self._tenant_namespace()
        return _remember_bulk_optimized(
            self.cfg,
            items,
            request_id,
            tenant,
            self._require_healthy,
            self._store_bulk_http_sync,
            self._store_http_sync,
            prepare_bulk_items,
            process_bulk_response,
        )

    async def aremember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float]:
        """Async variant of remember for HTTP mode; falls back to thread executor."""
        from somabrain.memory.remember import aremember_single

        has_async = (
            self._transport is not None and self._transport.async_client is not None
        )
        return await aremember_single(
            self.cfg,
            coord_key,
            payload,
            request_id,
            self._require_healthy,
            self._store_http_async,
            self.remember,
            self._compat_enrich_payload,
            has_async,
        )

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Async companion to remember_bulk using the async HTTP client."""
        from somabrain.memory.remember_bulk import aremember_bulk as _aremember_bulk
        from somabrain.memory.remember import prepare_bulk_items, process_bulk_response

        has_async = (
            self._transport is not None and self._transport.async_client is not None
        )
        return await _aremember_bulk(
            self.cfg,
            items,
            request_id,
            self._require_healthy,
            self._store_bulk_http_async,
            self._store_http_async,
            self.remember_bulk,
            prepare_bulk_items,
            process_bulk_response,
            has_async,
        )

    def recall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Retrieve memories relevant to ``query`` via the HTTP backend."""
        from somabrain.memory.recall_ops import recall_with_degradation

        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()
        return recall_with_degradation(
            tenant,
            query,
            top_k,
            universe or "real",
            rid,
            self._require_healthy,
            self._http_recall_aggregate_sync,
        )

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
        """Async recall for HTTP mode; falls back to sync execution when needed."""
        from somabrain.memory.recall_ops import arecall_with_degradation

        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()
        has_async = (
            self._transport is not None and self._transport.async_client is not None
        )
        return await arecall_with_degradation(
            tenant,
            query,
            top_k,
            universe or "real",
            rid,
            self._require_healthy,
            self._http_recall_aggregate_async,
            self.recall,
            has_async,
        )

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
        """Extract keywords from query for hybrid recall."""
        return extract_keywords(query)

    def hybrid_recall(
        self,
        query: str,
        top_k: int = 5,
        universe: str | None = None,
        request_id: str | None = None,
        keywords: List[str] | None = None,
    ) -> List[RecallHit]:
        """Hybrid recall combining vector similarity with keyword matching."""
        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()
        return hybrid_recall_sync(
            self._transport,
            query,
            top_k,
            universe or "real",
            rid,
            tenant,
            keywords,
            self._http_post_with_retries_sync,
            self._rescore_and_rank_hits,
            self.recall,
            self._require_healthy,
        )

    async def ahybrid_recall(
        self,
        query: str,
        top_k: int = 5,
        universe: str | None = None,
        request_id: str | None = None,
        keywords: List[str] | None = None,
    ) -> List[RecallHit]:
        """Async version of hybrid_recall."""
        rid = request_id or str(uuid.uuid4())
        tenant, _ = self._tenant_namespace()
        return await hybrid_recall_async(
            self._transport,
            query,
            top_k,
            universe or "real",
            rid,
            tenant,
            keywords,
            self._http_post_with_retries_async,
            self._rescore_and_rank_hits,
            self.arecall,
            self._require_healthy,
        )

    # --- Compatibility helper methods ---
    def coord_for_key(
        self, key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
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

        return store_from_payload(
            payload, request_id, self._store_http_sync, self.remember
        )

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
