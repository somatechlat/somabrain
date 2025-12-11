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
from somabrain.memory.transport import MemoryHTTPTransport, _http_setting, _response_json
from somabrain.memory.types import RecallHit
from somabrain.memory.normalization import _stable_coord, _extract_memory_coord
from somabrain.memory.filtering import _filter_payloads_by_keyword
from somabrain.memory.hit_processing import (
    normalize_recall_hits, hit_identity, hit_score, hit_timestamp,
    coerce_timestamp_value, prefer_candidate_hit, deduplicate_hits, lexical_bonus,
)
from somabrain.memory.scoring import (
    coerce_float, parse_payload_timestamp, get_recency_normalisation,
    get_recency_profile, compute_recency_features, compute_density_factor,
    extract_cleanup_margin, rank_hits, apply_weighting_to_hits, rescore_and_rank_hits,
)
from somabrain.memory.payload import enrich_payload, prepare_memory_payload

# logger for diagnostic output during tests
logger = logging.getLogger(__name__)
debug_memory_client = False
if settings is not None:
    try:
        debug_memory_client = bool(getattr(settings, "debug_memory_client", False))
    except Exception:
        debug_memory_client = False
if debug_memory_client:
    # ensure a stderr handler exists for quick interactive debugging
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(h)
    logger.setLevel(logging.DEBUG)

_TRUE_VALUES = ("1", "true", "yes", "on")


class MemoryClient:
    """Single gateway to the external memory service.

    Contract
    --------
    Core API surface intentionally small and stable:
        - remember(), aremember()
        - recall(), arecall()
        - link()/alink(), links_from(), k_hop()
        - payloads_for_coords()

    Metadata & Weighting (New)
    --------------------------
    Low‑complexity curriculum / data quality inspired fields can be attached to
    each memory payload. These are fully optional and *never* required by the
    base system. When provided they can influence ranking via a light‑weight
    weighting hook (disabled by default):

        phase            : str   (e.g., "bootstrap", "general", "specialized")
        quality_score    : float (bounded recommendation: [0, 1])
        domains          : list[str] or comma string (topic / domain tags)
        reasoning_chain  : list[str] | str (intermediate steps, retrieval synthesis notes)

    Feature Flags (env)
    -------------------
        SOMABRAIN_MEMORY_ENABLE_WEIGHTING=1
             Enable score modulation: final_sim = cosine_sim * W where W derived from
             optional quality_score (default 1.0) and phase prior.
        SOMABRAIN_MEMORY_PHASE_PRIORS="bootstrap:1.05,general:1.0,specialized:1.02"
             Comma list mapping phase->multiplier. Unknown phases => 1.0.
        SOMABRAIN_MEMORY_QUALITY_EXP=1.0
             Exponent applied to quality_score before multiplying (allows sharpening).

    Guarantees
    ----------
    - Tenancy scoping via namespace (separate local mirrors per namespace)
    - Legacy vendor-specific memory client imports stay isolated to this module (ADR‑0002)
    - Backend enforcement: If SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS is enabled,
        recall() raises a RuntimeError if the HTTP backend is unavailable. It does
        not silently fall back to any local mirror.

    Implementation Notes
    --------------------
    The weighting hook purposefully *post*‑multiplies cosine similarity; it does
    not change the embedding space and stays numerically stable (bounded factors
    in [~0, ~2]). We avoid injecting weighting into the embedding generation path
    to preserve determinism and test invariants.
    """

    def __init__(
        self, cfg: Config, scorer: Optional[Any] = None, embedder: Optional[Any] = None
    ):
        self.cfg = cfg
        self._scorer = scorer
        self._embedder = embedder
        # Always operate as an HTTP-first Memory client. Local/redis modes
        # and in-process memory service imports are disabled by default to
        # avoid heavy top-level imports and environment coupling.
        # Keep a _mode attribute for information.
        self._mode = "http"
        self._local = None
        self._transport: Optional[MemoryHTTPTransport] = None
        # NEW: Ensure the directory for the SQLite DB (if using local mode) exists.
        # MEMORY_DB_PATH is injected via docker‑compose; default to ./data/memory.db.
        if settings is not None:
            try:
                db_path = str(getattr(settings, "memory_db_path", "./data/memory.db"))
            except Exception:
                db_path = "./data/memory.db"
        else:
            db_path = "./data/memory.db"
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        except Exception:
            pass
        # Store for potential future use (e.g., passing to the local backend)
        self._memory_db_path = db_path
        # Initialize HTTP transport (primary runtime path).
        self._transport = self._create_transport()

    def _init_local(self) -> None:
        # Local in-process backend initialization has been removed. Running a
        # memory service must be done as a separate HTTP process.
        # If a developer needs an opt-in local backend, use an explicit
        # environment flag (e.g., `SOMABRAIN_ALLOW_LOCAL_MEMORY=1`) and implement that
        # code separately in a developer-only helper.
        return

    def _create_transport(self) -> MemoryHTTPTransport:
        # Default headers applied to all requests; per-request we add X-Request-ID
        headers = {}
        token_value = getattr(self.cfg, "memory_http_token", None)
        if token_value:
            headers["Authorization"] = f"Bearer {token_value}"
            headers.setdefault("X-API-Key", token_value)
            headers.setdefault("X-Auth-Token", token_value)

        # Propagate tenancy via standardized headers (best-effort)
        ns = str(getattr(self.cfg, "namespace", ""))
        if ns:
            headers["X-Soma-Namespace"] = ns
            try:
                tenant_guess = ns.split(":")[-1] if ":" in ns else ns
                headers["X-Soma-Tenant"] = tenant_guess
            except Exception:
                pass

        # Allow tuning via environment variables for production/dev use
        default_max = _http_setting("http_max_connections", 64)
        try:
            max_conns = int(getattr(settings, "http_max_connections", default_max))
        except Exception:
            max_conns = default_max
        default_keepalive = _http_setting("http_keepalive_connections", 32)
        try:
            keepalive = int(
                getattr(settings, "http_keepalive_connections", default_keepalive)
            )
        except Exception:
            keepalive = default_keepalive
        default_retries = _http_setting("http_retries", 1)
        try:
            retries = int(getattr(settings, "http_retries", default_retries))
        except Exception:
            retries = default_retries

        limits = None
        try:
            limits = httpx.Limits(
                max_connections=max_conns, max_keepalive_connections=keepalive
            )
        except Exception:
            limits = None

        # Allow overriding the HTTP memory endpoint via environment variable
        # Useful for tests or local development where a memory service runs on
        # a non-default port. Accept either a base URL or a full openapi.json
        # URL and normalise to the service base URL.
        resolved = None
        try:
            resolved = resolve_memory_endpoint()
        except RuntimeError:
            resolved = None

        cfg_endpoint = str(getattr(self.cfg, "memory_http_endpoint", "") or "")
        if cfg_endpoint:
            base_url = cfg_endpoint.strip()
        elif resolved is not None:
            base_url = resolved.url
        else:
            base_url = get_memory_http_endpoint() or ""
        if not base_url:
            raise RuntimeError("Memory HTTP endpoint required but not configured")
        try:
            base_url = str(base_url).strip()
            if base_url.endswith("/openapi.json"):
                base_url = base_url[: -len("/openapi.json")]
            base_url = base_url.rstrip("/") or base_url
        except Exception:
            pass
        base_url = base_url or ""
        try:
            logger.debug("MemoryClient HTTP base_url=%r", base_url)
        except Exception:
            pass

        transport = MemoryHTTPTransport(
            base_url=base_url,
            headers=headers,
            limits=limits,
            retries=retries,
            logger=logger,
        )
        if transport.client is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED but not reachable or endpoint unset. Set SOMABRAIN_MEMORY_HTTP_ENDPOINT in the environment."
            )
        if not token_value:
            try:
                logger.warning(
                    "Memory HTTP client initialized without token; proceeding without auth."
                )
            except Exception:
                pass
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
        # Redis mode removed. Redis-backed behavior should be exposed via the
        # HTTP memory service if required.
        return

    def health(self) -> dict:
        """Return detailed health information from the external memory service.

        The service exposes a JSON payload that includes boolean flags for the
        three core components: ``kv_store``, ``vector_store`` and ``graph_store``.
        This method queries the service (preferring ``/health``) and returns a
        dictionary with the raw payload plus a top‑level ``healthy`` key that is
        ``True`` only when **all** component flags are true.
        """
        if self._transport is None or self._transport.client is None:
            return {"healthy": False, "error": "HTTP client not configured"}

        # Prefer the generic /health endpoint – the memory service currently
        # implements it and returns the component flags.
        try:
            r = self._transport.client.get("/health")
            status = int(getattr(r, "status_code", 0) or 0)
            if status != 200:
                return {"healthy": False, "status": status}
            data = self._response_json(r) or {}
            if not isinstance(data, dict):
                return {"healthy": False, "error": "unexpected health payload"}
            # Normalise missing keys to False so the overall health is safe.
            kv = bool(data.get("kv_store", False))
            vec = bool(data.get("vector_store", False))
            graph = bool(data.get("graph_store", False))
            overall = kv and vec and graph
            result = dict(data)
            result.update(
                {
                    "healthy": overall,
                    "kv_store": kv,
                    "vector_store": vec,
                    "graph_store": graph,
                }
            )
            return result
        except Exception as exc:
            return {"healthy": False, "error": str(exc)}

    def _require_healthy(self) -> None:
        """Raise a clear error if the memory service is not fully healthy.

        All public API calls invoke this guard first, ensuring fail‑fast
        behaviour as required by the VIBE rules.
        """
        health = self.health()
        if not health.get("healthy"):
            # Provide a concise message with the failing components.
            missing = []
            for comp in ("kv_store", "vector_store", "graph_store"):
                if not health.get(comp, False):
                    missing.append(comp)
            raise RuntimeError(
                f"Memory service unavailable or partially unhealthy: {', '.join(missing) or 'unknown'}"
            )

    # ---------------------------------------------------------------------
    # Degradation helpers
    # ---------------------------------------------------------------------
    # --- HTTP helpers ---------------------------------------------------------
    # _response_json moved to somabrain/memory/transport.py
    # Keeping static method for backward compatibility
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
        # Delegate to extracted module
        from somabrain.memory.http_helpers import http_post_with_retries_sync
        tenant, _ = self._tenant_namespace()
        return http_post_with_retries_sync(
            self._transport, endpoint, body, headers, tenant,
            max_retries=max_retries, operation=operation
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
        # Delegate to extracted module
        from somabrain.memory.http_helpers import http_post_with_retries_async
        tenant, _ = self._tenant_namespace()
        return await http_post_with_retries_async(
            self._transport, endpoint, body, headers, tenant,
            max_retries=max_retries, operation=operation
        )

    def _store_http_sync(self, body: dict, headers: dict) -> tuple[bool, Any]:
        """POST a memory to the HTTP memory service."""
        from somabrain.memory.http_helpers import store_http_sync
        tenant, _ = self._tenant_namespace()
        return store_http_sync(self._transport, body, headers, tenant)

    async def _store_http_async(self, body: dict, headers: dict) -> tuple[bool, Any]:
        """Async POST a memory to the HTTP memory service."""
        from somabrain.memory.http_helpers import store_http_async
        tenant, _ = self._tenant_namespace()
        return await store_http_async(self._transport, body, headers, tenant)

    def _store_bulk_http_sync(
        self, batch_request: dict, headers: dict
    ) -> tuple[bool, int, Any]:
        """Store multiple memories by iterating over items."""
        from somabrain.memory.http_helpers import store_bulk_http_sync
        tenant, _ = self._tenant_namespace()
        return store_bulk_http_sync(self._transport, batch_request, headers, tenant)

    async def _store_bulk_http_async(
        self, batch_request: dict, headers: dict
    ) -> tuple[bool, int, Any]:
        """Async bulk store via individual POST /memories calls."""
        from somabrain.memory.http_helpers import store_bulk_http_async
        tenant, _ = self._tenant_namespace()
        return await store_bulk_http_async(self._transport, batch_request, headers, tenant)

    # Hit processing - use module functions directly
    _normalize_recall_hits = staticmethod(normalize_recall_hits)
    _hit_identity = staticmethod(hit_identity)
    _hit_score = staticmethod(hit_score)
    _coerce_timestamp_value = staticmethod(coerce_timestamp_value)
    _hit_timestamp = staticmethod(hit_timestamp)
    _prefer_candidate_hit = staticmethod(prefer_candidate_hit)
    _deduplicate_hits = staticmethod(deduplicate_hits)
    _lexical_bonus = staticmethod(lexical_bonus)
    _rank_hits = staticmethod(rank_hits)

    def _memories_search_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        if self._transport is None:
            raise RuntimeError("HTTP memory service required but not configured")

        headers = {"X-Request-ID": request_id}
        universe_value = str(universe or "real")
        query_text = str(query or "")
        body = {
            "query": query_text,
            "top_k": max(int(top_k), 1),
            "universe": universe_value,
        }

        success, status, data = self._http_post_with_retries_sync(
            "/memories/search", body, headers, operation="recall"
        )
        if success:
            hits = self._normalize_recall_hits(data)
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

            hits = self._filter_hits_by_keyword(hits, query_text)
            if not hits:
                return []

            deduped = self._deduplicate_hits(hits)
            if not deduped:
                return []

            ranked = self._rescore_and_rank_hits(deduped, query_text)
            limit = max(1, int(top_k))
            return ranked[:limit]

        if status in (404, 405, 422):
            raise RuntimeError(
                "Memory search endpoint unavailable or incompatible with current SomaBrain build."
            )

        return []

    async def _memories_search_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        if self._transport is None or self._transport.async_client is None:
            raise RuntimeError("Async HTTP memory service required but not configured")

        headers = {"X-Request-ID": request_id}
        universe_value = str(universe or "real")
        query_text = str(query or "")
        body = {
            "query": query_text,
            "top_k": max(int(top_k), 1),
            "universe": universe_value,
        }

        success, status, data = await self._http_post_with_retries_async(
            "/memories/search", body, headers, operation="recall"
        )
        if success:
            hits = self._normalize_recall_hits(data)
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

            hits = self._filter_hits_by_keyword(hits, query_text)
            if not hits:
                return []

            deduped = self._deduplicate_hits(hits)
            if not deduped:
                return []

            ranked = self._rescore_and_rank_hits(deduped, query_text)
            limit = max(1, int(top_k))
            return ranked[:limit]

        if status in (404, 405, 422):
            raise RuntimeError(
                "Memory search endpoint unavailable or incompatible with current SomaBrain build."
            )

        return []

    def _http_recall_aggregate_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        return self._memories_search_sync(query, top_k, universe, request_id)

    async def _http_recall_aggregate_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        return await self._memories_search_async(query, top_k, universe, request_id)

    def _filter_hits_by_keyword(
        self, hits: List[RecallHit], keyword: str
    ) -> List[RecallHit]:
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

    # Scoring - static methods use module functions directly
    _coerce_float = staticmethod(coerce_float)
    _parse_payload_timestamp = staticmethod(parse_payload_timestamp)
    _extract_cleanup_margin = staticmethod(extract_cleanup_margin)
    _apply_weighting_to_hits = staticmethod(apply_weighting_to_hits)

    def _recency_normalisation(self) -> tuple[float, float]:
        return get_recency_normalisation(self.cfg)

    def _recency_profile(self) -> tuple[float, float, float, float]:
        return get_recency_profile(self.cfg)

    def _recency_features(self, ts_epoch: float | None, now_ts: float) -> tuple[float | None, float]:
        return compute_recency_features(ts_epoch, now_ts, self.cfg)

    def _density_factor(self, margin: float | None) -> float:
        return compute_density_factor(margin, self.cfg)

    def _rescore_and_rank_hits(self, hits: List[RecallHit], query: str) -> List[RecallHit]:
        return rescore_and_rank_hits(hits, query, self.cfg, self._scorer, self._embedder)

    # --- HTTP helpers -------------------------------------------------
    def _compat_enrich_payload(
        self, payload: dict, coord_key: str
    ) -> tuple[dict, str, dict]:
        """Return an enriched (payload_copy, universe, extra_headers).

        Ensures downstream HTTP memory services receive common fields that many
        implementations index on: text/content/id/universe. Does not mutate input.
        """
        namespace = None
        try:
            namespace = getattr(self.cfg, "namespace", None)
        except Exception:
            pass
        return enrich_payload(payload, coord_key, namespace)

    def _tenant_namespace(self) -> tuple[str, str]:
        """Resolve tenant and namespace from cfg/settings with hard requirements."""
        tenant = getattr(self.cfg, "tenant", None) or getattr(
            settings, "default_tenant", "public"
        )
        namespace = getattr(self.cfg, "namespace", None) or getattr(
            settings, "namespace", "public"
        )
        tenant = str(tenant or "public")
        namespace = str(namespace or "public")
        return tenant, namespace

    def _record_http_metrics(
        self, operation: str, success: bool, status: int, duration: float
    ) -> None:
        # Delegate to extracted module
        from somabrain.memory.http_helpers import record_http_metrics
        tenant, _ = self._tenant_namespace()
        record_http_metrics(operation, tenant, success, status, duration)

    def remember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float]:
        """Store a memory using a stable coordinate derived from ``coord_key``.

        Memory writes now always require the external HTTP backend to be healthy;
        degraded queuing is handled exclusively by :class:`MemoryService` and the
        outbox journal. This method therefore fails fast if the backend is
        unavailable, preserving a single source of truth.

        Normalisation of optional metadata (phase, quality_score, domains,
        reasoning_chain) remains unchanged.
        """
        # Fail fast if the memory backend is not fully healthy.
        self._require_healthy()

        # include universe in coordinate hashing to avoid collisions across branches
        # and enrich payload
        enriched, universe, _hdr = self._compat_enrich_payload(payload, coord_key)
        coord = _stable_coord(f"{universe}::{coord_key}")

        # ensure we don't mutate caller's dict; copy and normalize metadata
        payload = prepare_memory_payload(enriched, coord_key, universe)

        # Detect async context: if present, schedule background persistence
        try:
            loop = asyncio.get_running_loop()
            in_async = True
        except Exception:
            in_async = False

        try:
            payload.setdefault("coordinate", coord)
        except Exception:
            pass

        import uuid

        # Import uuid locally to avoid top‑level dependency.
        rid = request_id or str(uuid.uuid4())

        # If we're in an async loop, schedule an async background persist (non-blocking)
        if in_async:
            try:
                loop = asyncio.get_running_loop()
                if self._transport is not None and self._transport.async_client is not None:
                    try:
                        loop.create_task(
                            self._aremember_background(coord_key, payload, rid)
                        )
                    except Exception as e:
                        logger.debug("_aremember_background scheduling failed: %r", e)
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
            return coord

        # Synchronous callers: default is blocking persist, but allow an opt-in
        # fast-ack mode schedules persistence on a background executor so we don't block.
        if settings is not None:
            try:
                fast_ack = bool(getattr(settings, "memory_fast_ack", False))
            except Exception:
                fast_ack = False
        else:
            try:
                from common.config.settings import settings as _rt

                fast_ack = _rt.get_bool("memory_fast_ack", False)
            except Exception:
                fast_ack = False
        if fast_ack:
            try:
                loop = asyncio.get_event_loop()
                # schedule background sync persist in the executor so we don't block
                loop.run_in_executor(
                    None, self._remember_sync_persist, coord_key, payload, rid
                )
            except Exception:
                # last resort: run sync persist (best-effort)
                try:
                    self._remember_sync_persist(coord_key, payload, rid)
                except Exception:
                    pass
            return coord

        # Default (no fast-ack): perform the persist synchronously (blocking)
        server_coord: Tuple[float, float, float] | None = self._remember_sync_persist(
            coord_key, payload, rid
        )
        if server_coord:
            coord = server_coord
            try:
                payload["coordinate"] = server_coord
            except Exception:
                pass
        return coord

    def remember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Store multiple memories in a single HTTP round‑trip.

        The method now includes **tenant** and **namespace** on every batch item
        to satisfy the OpenAPI `MemoryWriteRequest` contract.  It also fails fast
        if the memory backend is not fully healthy.
        """

        # Fail fast if the service is unhealthy.
        self._require_healthy()

        records = list(items)
        if not records:
            return []

        prepared: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []
        tenant, namespace = self._tenant_namespace()

        for coord_key, payload in records:
            enriched, universe, _ = self._compat_enrich_payload(payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
            body: dict[str, Any] = {
                "tenant": tenant,
                "namespace": namespace,
                "key": coord_key,
                "value": dict(enriched),
                "universe": universe,
            }
            for optional_key in (
                "meta",
                "ttl_seconds",
                "tags",
                "policy_tags",
                "attachments",
                "links",
                "signals",
                "importance",
                "novelty",
                "trace_id",
            ):
                if isinstance(payload, dict) and optional_key in payload:
                    body[optional_key] = payload.get(optional_key)
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "universe": universe,
                }
            )

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
            returned: List[Any] = []
            if isinstance(response, dict):
                for key in ("items", "results", "memories", "entries"):
                    seq = response.get(key)
                    if isinstance(seq, list):
                        returned = seq
                        break
            elif isinstance(response, list):
                returned = response
            for idx, entry in enumerate(returned[: len(prepared)]):
                server_coord = _extract_memory_coord(
                    entry, idempotency_key=f"{rid}:{idx}"
                )
                if server_coord:
                    coords[idx] = server_coord
            return coords

        if status in (404, 405):
            # Fallback to individual calls when bulk is unsupported.
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
        """Async variant of remember for HTTP mode; falls back to thread executor.

        Returns the chosen 3‑tuple coord (server‑preferred if configured), or the
        locally computed coord. On failure, falls back to running the sync remember
        in a thread executor.
        """
        # Fail fast if the memory service is unhealthy.
        self._require_healthy()
        # Mirror locally first for read‑your‑writes semantics (optional)
        # Strict real mode: no local mirroring, only HTTP service
        p2: dict[str, Any] | None = None
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
                    "type": memory_type,
                }
                import uuid

                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                rid_hdr.update(compat_hdr)
                ok, response_data = await self._store_http_async(body, rid_hdr)
                if ok and response_data is not None:
                    server_coord = _extract_memory_coord(
                        response_data, idempotency_key=rid
                    )
                    if server_coord:
                        try:
                            enriched["coordinate"] = server_coord
                        except Exception:
                            pass
                        if p2 is not None:
                            try:
                                p2["coordinate"] = server_coord
                            except Exception:
                                pass
                        if getattr(self.cfg, "prefer_server_coords_for_links", False):
                            return server_coord
                        return server_coord
                return coord
            except Exception:
                pass
        # Alternative: run the synchronous remember in a thread executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.remember, coord_key, payload)

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Async companion to :meth:`remember_bulk` using the async HTTP client.

        Fails fast if the memory service is unhealthy.
        """
        self._require_healthy()

        records = list(items)
        if not records:
            return []

        prepared: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []
        tenant, namespace = self._tenant_namespace()

        for coord_key, payload in records:
            enriched, universe, _ = self._compat_enrich_payload(payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
            body: dict[str, Any] = {
                "key": coord_key,
                "value": dict(enriched),
                "universe": universe,
            }
            for optional_key in (
                "meta",
                "ttl_seconds",
                "tags",
                "policy_tags",
                "attachments",
                "links",
                "signals",
                "importance",
                "novelty",
                "trace_id",
            ):
                if isinstance(payload, dict) and optional_key in payload:
                    body[optional_key] = payload.get(optional_key)
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "universe": universe,
                }
            )

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
            returned: List[Any] = []
            if isinstance(response, dict):
                for key in ("items", "results", "memories", "entries"):
                    seq = response.get(key)
                    if isinstance(seq, list):
                        returned = seq
                        break
            elif isinstance(response, list):
                returned = response
            for idx, entry in enumerate(returned[: len(prepared)]):
                server_coord = _extract_memory_coord(
                    entry, idempotency_key=f"{rid}:{idx}"
                )
                if server_coord:
                    coords[idx] = server_coord
                    try:
                        prepared[idx]["body"]["payload"]["coordinate"] = server_coord
                    except Exception:
                        pass
            return coords

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
        """Recall memories including similarity scores via the `/memories/search` endpoint.

        Fails fast if the memory service is unhealthy.
        """
        self._require_healthy()
        if self._transport is not None and self._transport.client is not None:
            rid = request_id or str(uuid.uuid4())
            hits = self._http_recall_aggregate_sync(
                query, top_k, universe or "real", rid
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
            rid = request_id or str(uuid.uuid4())
            return await self._http_recall_aggregate_async(
                query, top_k, universe or "real", rid
            )
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.recall, query, top_k, universe, request_id
        )

    async def arecall_with_scores(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Async companion to :meth:`recall_with_scores`."""

        if self._transport is not None and self._transport.async_client is not None:
            rid = request_id or str(uuid.uuid4())
            hits = await self._http_recall_aggregate_async(
                query, top_k, universe or "real", rid
            )
            if hits:
                return hits
        return await self.arecall(query, top_k, universe, request_id)

    # --- Compatibility helper methods ---
    def coord_for_key(
        self, key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
        """Return a deterministic coordinate for *key* and optional *universe*.

        This is a lightweight helper used by migration scripts and
        higher-level services. It mirrors the stable hash used for remembered
        payloads.
        """
        # When universe is not provided, default to 'real' to match remember()
        # which uses payload.get('universe') or 'real'. Using the namespace here
        # would produce inconsistent coordinates and break tests that rely on
        # defaulting to the real universe.
        uni = universe or "real"
        return _stable_coord(f"{uni}::{key}")

    def fetch_by_coord(
        self, coord: Tuple[float, float, float], universe: str | None = None
    ) -> List[Dict[str, Any]]:
        """Fetch memory payloads by coordinate using GET /memories/{coord}.

        Returns a list of payload dicts for the given coordinate. Returns an
        empty list if no memory exists at that coordinate or if the request fails.
        """
        client = self._get_http_client()
        if client is None:
            return []
        try:
            coord_str = f"{coord[0]},{coord[1]},{coord[2]}"
            endpoint = f"/memories/{coord_str}"
            r = client.get(endpoint)
            status = int(getattr(r, "status_code", 0) or 0)
            if status == 404:
                return []
            if status != 200:
                return []
            data = self._response_json(r)
            if data is None:
                return []
            # Handle various response formats
            if isinstance(data, dict):
                payload = data.get("payload")
                if isinstance(payload, dict):
                    return [payload]
                memory = data.get("memory")
                if isinstance(memory, dict):
                    return [memory.get("payload") or memory]
                # If the response itself looks like a payload, return it
                if "task" in data or "fact" in data or "text" in data:
                    return [data]
            if isinstance(data, list):
                return [p for p in data if isinstance(p, dict)]
            return []
        except Exception:
            return []

    def store_from_payload(self, payload: dict, request_id: str | None = None) -> bool:
        """Store a payload dict into the memory backend.

        Tests and migration scripts call this helper. If the payload contains a
        concrete ``coordinate`` value we send it directly to the memory service.
        Otherwise we fall back to calling :meth:`remember` with a generated key
        derived from common payload fields.
        """

        try:
            coord = payload.get("coordinate")
            if coord is not None:
                try:
                    c = (
                        float(coord[0]),
                        float(coord[1]),
                        float(coord[2]),
                    )
                except Exception:
                    return False
                rid = request_id or str(uuid.uuid4())
                headers = {"X-Request-ID": rid}
                body = {
                    "coord": f"{c[0]},{c[1]},{c[2]}",
                    "payload": dict(payload),
                    "memory_type": str(
                        payload.get("memory_type") or payload.get("type") or "episodic"
                    ),
                }
                success, _ = self._store_http_sync(body, headers)
                if success:
                    return True
                return False

            key = (
                payload.get("task")
                or payload.get("headline")
                or payload.get("id")
                or f"autokey:{uuid.uuid4()}"
            )
            self.remember(str(key), payload, request_id=request_id)
            return True
        except Exception:
            return False

    def _remember_sync_persist(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float] | None:
        """Synchronous persistence implementation used by both sync callers and run_in_executor.

        This mirrors the original HTTP remember logic but centralizes retries and outbox alternative.
        """
        import uuid as _uuid

        if self._transport is None or self._transport.client is None:
            raise RuntimeError("HTTP memory service required for persistence")

        # Enrich payload and compute coord string once
        enriched, uni, compat_hdr = self._compat_enrich_payload(payload, coord_key)
        tenant, namespace = self._tenant_namespace()
        sc = _stable_coord(f"{uni}::{coord_key}")
        f"{sc[0]},{sc[1]},{sc[2]}"

        # Build request body conforming to the OpenAPI ``MemoryStoreRequest`` schema.
        # The service expects a ``coord`` string of three comma‑separated floats,
        # a ``payload`` object, and an optional ``memory_type``.  Previously the
        # client sent a legacy schema with tenant/namespace fields, causing a
        # 404/validation error.  We now construct the minimal, correct payload.
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        body: dict[str, Any] = {
            "coord": coord_str,
            "payload": dict(enriched),
            "memory_type": str(
                payload.get("memory_type") or payload.get("type") or "episodic"
            ),
        }

        rid = request_id or str(_uuid.uuid4())
        rid_hdr = {"X-Request-ID": rid}
        rid_hdr.update(compat_hdr)
        stored = False
        response_payload: Any = None
        try:
            stored, response_payload = self._store_http_sync(body, rid_hdr)
        except Exception:
            stored = False
        server_coord: Tuple[float, float, float] | None = None
        if stored and response_payload is not None:
            try:
                server_coord = _extract_memory_coord(
                    response_payload, idempotency_key=rid
                )
            except Exception:
                server_coord = None

        if not stored:
            raise RuntimeError("Memory service unavailable (remember persist failed)")
        return server_coord

    async def _aremember_background(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Async background persistence using the AsyncClient; used when remember is called from async contexts."""
        if self._transport is None or self._transport.async_client is None:
            # alternative: sync persist in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._remember_sync_persist, coord_key, payload, request_id
            )
            return

        rid = request_id
        rid_hdr = {"X-Request-ID": rid} if rid else {}
        enriched, uni, compat_hdr = self._compat_enrich_payload(payload, coord_key)
        rid_hdr.update(compat_hdr)
        tenant, namespace = self._tenant_namespace()
        body: dict[str, Any] = {
            "tenant": tenant,
            "namespace": namespace,
            "key": coord_key,
            "value": enriched,
            "universe": uni,
            "trace_id": payload.get("trace_id") if isinstance(payload, dict) else None,
        }
        for optional_key in (
            "meta",
            "ttl_seconds",
            "tags",
            "policy_tags",
            "attachments",
            "links",
            "signals",
            "importance",
            "novelty",
        ):
            if isinstance(payload, dict) and optional_key in payload:
                body[optional_key] = payload.get(optional_key)
        try:
            ok, response_data = await self._store_http_async(body, rid_hdr)
            if ok and response_data is not None:
                server_coord = _extract_memory_coord(response_data, idempotency_key=rid)
                if server_coord:
                    try:
                        payload["coordinate"] = server_coord
                    except Exception:
                        pass
        except Exception:
            logger.exception("Background memory persist failed")


# NOTE: MemoryClient already implements the required methods used by MemoryService.
# Adding a Protocol-based alias for type checkers helps during the refactor.
MemoryClientType: type = MemoryBackend
