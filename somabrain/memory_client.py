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

# logger for diagnostic output during tests
logger = logging.getLogger(__name__)
debug_memory_client = (
    bool(getattr(settings, "debug_memory_client", False)) if settings else False
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
        self, cfg: Config, scorer: Optional[Any] = None, embedder: Optional[Any] = None
    ):
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

        ns = str(getattr(self.cfg, "namespace", ""))
        if ns:
            headers["X-Soma-Namespace"] = ns
            headers["X-Soma-Tenant"] = ns.split(":")[-1] if ":" in ns else ns

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
            limits = httpx.Limits(
                max_connections=max_conns, max_keepalive_connections=keepalive
            )
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
            logger.warning(
                "Memory HTTP client initialized without token; proceeding without auth."
            )
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
        """Return health information from the external memory service."""
        if self._transport is None or self._transport.client is None:
            return {"healthy": False, "error": "HTTP client not configured"}
        try:
            r = self._transport.client.get("/health")
            if int(getattr(r, "status_code", 0) or 0) != 200:
                return {"healthy": False, "status": r.status_code}
            data = self._response_json(r) or {}
            if not isinstance(data, dict):
                return {"healthy": False, "error": "unexpected health payload"}
            kv, vec, graph = (
                bool(data.get("kv_store")),
                bool(data.get("vector_store")),
                bool(data.get("graph_store")),
            )
            return {
                **data,
                "healthy": kv and vec and graph,
                "kv_store": kv,
                "vector_store": vec,
                "graph_store": graph,
            }
        except Exception as exc:
            return {"healthy": False, "error": str(exc)}

    def _require_healthy(self) -> None:
        """Raise error if memory service is not fully healthy."""
        health = self.health()
        if not health.get("healthy"):
            missing = [
                c
                for c in ("kv_store", "vector_store", "graph_store")
                if not health.get(c)
            ]
            raise RuntimeError(
                f"Memory service unavailable: {', '.join(missing) or 'unknown'}"
            )

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
    _http_recall_aggregate_sync = lambda self, q, k, u, r: self._memories_search_sync(
        q, k, u, r
    )
    _http_recall_aggregate_async = lambda self, q, k, u, r: self._memories_search_async(
        q, k, u, r
    )

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

        return get_tenant_namespace(self.cfg)

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
            bool(getattr(settings, "memory_fast_ack", False)) if settings else False
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
        from somabrain.memory.remember import prepare_bulk_items, process_bulk_response

        self._require_healthy()

        prepared, universes, coords, tenant, namespace = prepare_bulk_items(
            self.cfg, items
        )
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

    async def aremember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float]:
        """Async variant of remember for HTTP mode; falls back to thread executor."""
        self._require_healthy()
        if self._transport is not None and self._transport.async_client is not None:
            try:
                enriched, universe, compat_hdr = self._compat_enrich_payload(
                    payload, coord_key
                )
                coord = _stable_coord(f"{universe}::{coord_key}")
                enriched = dict(enriched)
                enriched.setdefault("coordinate", coord)
                memory_type = str(
                    enriched.get("memory_type") or enriched.get("type") or "episodic"
                )
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
                    server_coord = _extract_memory_coord(
                        response_data, idempotency_key=rid
                    )
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

        prepared, universes, coords, tenant, namespace = prepare_bulk_items(
            self.cfg, records
        )
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

        success, status, response = await self._store_bulk_http_async(
            batch_payload, headers
        )
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
        """Retrieve memories relevant to ``query`` via the HTTP backend."""
        self._require_healthy()
        rid = request_id or str(uuid.uuid4())
        return self._http_recall_aggregate_sync(query, top_k, universe or "real", rid)

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
        if self._transport is not None and self._transport.async_client is not None:
            return await self._http_recall_aggregate_async(
                query, top_k, universe or "real", request_id or str(uuid.uuid4())
            )
        return await asyncio.get_event_loop().run_in_executor(
            None, self.recall, query, top_k, universe, request_id
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
