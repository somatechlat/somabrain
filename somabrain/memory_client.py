"""Memory Client Module for SomaBrain.

The client speaks to the external HTTP memory service used by SomaBrain. When
the service is unavailable it mirrors writes locally and records them in an
outbox for replay. This module is the single gateway for storing, retrieving,
and linking memories; other packages must call into it rather than integrating
with the memory service directly.
"""

from __future__ import annotations

import asyncio

# Process-global in-memory mirror for recently stored payloads per-namespace.
# The previous implementation used a plain module-global dict which could
# become duplicated when the module is imported under different module
# objects (tests/run-time import shims). Use the interpreter's builtins to
# store a single shared dict accessible from any import context in the same
# process. Keep the name `_GLOBAL_PAYLOADS` for minimal diffs elsewhere.
import builtins as _builtins
import hashlib
import json
import logging
import math
import os  # added for environment handling
import random
import re
import time
import uuid
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Iterable, List, Tuple, cast

from .config import Config

_BUILTINS_KEY = "_SOMABRAIN_GLOBAL_PAYLOADS"
if not hasattr(_builtins, _BUILTINS_KEY):
    setattr(_builtins, _BUILTINS_KEY, {})

# Shared mapping: namespace -> list[payload]
_GLOBAL_PAYLOADS: Dict[str, List[dict]] = getattr(_builtins, _BUILTINS_KEY)

# Also keep a process-global links mirror so tests and duplicate import
# contexts can observe freshly created graph edges without requiring the
# exact same MemoryClient instance. Structure: namespace -> list[edge_dict]
# edge_dict: {"from": (x,y,z), "to": (x,y,z), "type": str, "weight": float}
_BUILTINS_LINKS_KEY = "_SOMABRAIN_GLOBAL_LINKS"
if not hasattr(_builtins, _BUILTINS_LINKS_KEY):
    setattr(_builtins, _BUILTINS_LINKS_KEY, {})

_GLOBAL_LINKS: Dict[str, List[dict]] = getattr(_builtins, _BUILTINS_LINKS_KEY)

# logger for diagnostic output during tests
logger = logging.getLogger(__name__)
if os.getenv("SOMABRAIN_DEBUG_MEMORY_CLIENT") == "1":
    # ensure a stderr handler exists for quick interactive debugging
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(h)
    logger.setLevel(logging.DEBUG)


def _stable_coord(key: str) -> Tuple[float, float, float]:
    """Derive a deterministic 3D coordinate in [-1,1]^3 from a string key."""
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=12).digest()
    a = int.from_bytes(h[0:4], "big") / 2**32
    b = int.from_bytes(h[4:8], "big") / 2**32
    c = int.from_bytes(h[8:12], "big") / 2**32
    # spread over [-1, 1]
    return (2 * a - 1, 2 * b - 1, 2 * c - 1)


def _parse_coord_string(s: str) -> Tuple[float, float, float] | None:
    try:
        parts = [float(x.strip()) for x in str(s).split(",")]
        if len(parts) >= 3:
            return (parts[0], parts[1], parts[2])
    except Exception:
        return None
    return None


def _refresh_builtins_globals() -> None:
    """Refresh module-level references to the builtins-backed global mirrors.

    Tests sometimes replace the builtins dict objects by assigning a new
    dict to the builtins key. That leaves module-level variables pointing to
    the old dict. Call this helper at method entry points to rebind the
    module-level names to the current builtins objects.
    """
    global _GLOBAL_PAYLOADS, _GLOBAL_LINKS
    try:
        _GLOBAL_PAYLOADS = getattr(_builtins, _BUILTINS_KEY)
    except Exception:
        _GLOBAL_PAYLOADS = getattr(_builtins, _BUILTINS_KEY, {})
    try:
        _GLOBAL_LINKS = getattr(_builtins, _BUILTINS_LINKS_KEY)
    except Exception:
        _GLOBAL_LINKS = getattr(_builtins, _BUILTINS_LINKS_KEY, {})


def _filter_payloads_by_keyword(payloads: Iterable[Any], keyword: str) -> List[dict]:
    """Return payloads that include *keyword* in common string fields.

    The filter is intentionally lightweight so it can run on every recall even
    when the backend service does not support lexical search. If no payloads
    match, the original list is returned to preserve behaviour.
    """

    items: List[dict] = [p for p in payloads if isinstance(p, dict)]
    key = str(keyword or "").strip().lower()
    if not key:
        return items

    filtered: List[dict] = []
    fields = ("what", "headline", "text", "content", "who", "task", "session")
    for entry in items:
        for field in fields:
            value = entry.get(field)
            if isinstance(value, str) and key in value.lower():
                filtered.append(entry)
                break
    return filtered or items


def _extract_memory_coord(
    resp: Any,
    idempotency_key: str | None = None,
) -> Tuple[float, float, float] | None:
    """Try common shapes to extract a 3‑tuple coord from a remember response.

    Known attempts (in order):
    - top‑level 'coord' or 'coordinate' as comma string or list
    - nested 'memory' object with 'coordinate' or 'id'
    - top‑level 'id' (opaque) -> map via stable hash
    - fallback: use idempotency_key (if provided) -> stable hash of 'idempotency:{key}'
    Returns a 3‑tuple floats or None.
    """
    try:
        if not resp:
            return None
        # if resp is a requests/HTTPX Response-like with .json(), prefer that
        try:
            if hasattr(resp, "json") and callable(resp.json):
                data = resp.json()
            else:
                data = resp
        except Exception:
            data = resp
        # top‑level coord/coordinate
        for k in ("coord", "coordinate"):
            v = data.get(k) if isinstance(data, dict) else None
            if isinstance(v, str):
                parsed = _parse_coord_string(v)
                if parsed:
                    return parsed
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                try:
                    return (float(v[0]), float(v[1]), float(v[2]))
                except Exception:
                    pass
        # nested memory
        if (
            isinstance(data, dict)
            and "memory" in data
            and isinstance(data["memory"], dict)
        ):
            mem = data["memory"]
            for k in ("coordinate", "coord", "location"):
                v = mem.get(k)
                if isinstance(v, str):
                    parsed = _parse_coord_string(v)
                    if parsed:
                        return parsed
                if isinstance(v, (list, tuple)) and len(v) >= 3:
                    try:
                        return (float(v[0]), float(v[1]), float(v[2]))
                    except Exception:
                        pass
            # try id field
            mid = mem.get("id") or mem.get("memory_id")
            if mid:
                try:
                    return _stable_coord(str(mid))
                except Exception:
                    pass
        # top‑level id
        if isinstance(data, dict) and (data.get("id") or data.get("memory_id")):
            mid = data.get("id") or data.get("memory_id")
            try:
                return _stable_coord(str(mid))
            except Exception:
                pass
        # fallback to idempotency
        if idempotency_key:
            try:
                return _stable_coord(f"idempotency:{idempotency_key}")
            except Exception:
                pass
    except Exception:
        return None
    return None


@dataclass
class RecallHit:
    """Represents a normalized memory recall hit from the SFM service."""

    payload: Dict[str, Any]
    score: float | None = None
    coordinate: Tuple[float, float, float] | None = None
    raw: Dict[str, Any] | None = None


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
        reasoning_chain  : list[str] | str (intermediate steps, RAG synthesis notes)

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
    - Strict mode correctness: If STRICT_REAL is enabled and neither HTTP nor
        deterministic local recall returns hits, recall() raises instead of silently
        falling back to a blind recent‑payload stub.

    Implementation Notes
    --------------------
    The weighting hook purposefully *post*‑multiplies cosine similarity; it does
    not change the embedding space and stays numerically stable (bounded factors
    in [~0, ~2]). We avoid injecting weighting into the embedding generation path
    to preserve determinism and test invariants.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        # Always operate as an HTTP-first Memory client. Local/redis modes
        # and in-process memory service imports are disabled by default to
        # avoid heavy top-level imports and environment coupling.
        # Keep a _mode attribute for compatibility but it is informational only.
        self._mode = "http"
        self._local = None
        self._http = None
        self._http_async = None
        self._stub_store: list[dict] = []
        self._graph: Dict[Any, Any] = {}
        self._lock = RLock()
        # New: path for outbox persistence (default within data dir)
        self._outbox_path = getattr(cfg, "outbox_path", "./data/somabrain/outbox.jsonl")
        # Ensure outbox file exists
        try:
            open(self._outbox_path, "a").close()
        except Exception:
            pass
        # NEW: Ensure the directory for the SQLite DB (if using local mode) exists.
        # MEMORY_DB_PATH is injected via docker‑compose; default to ./data/memory.db.
        db_path = os.getenv("MEMORY_DB_PATH", "./data/memory.db")
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        except Exception:
            pass
        # Store for potential future use (e.g., passing to the local backend)
        self._memory_db_path = db_path
        # Initialize HTTP client (primary runtime path). Local/redis
        # initialization is intentionally not attempted here.
        self._init_http()
        # Ensure outbox file exists (redundant safety)
        try:
            open(self._outbox_path, "a").close()
        except Exception:
            pass

    def _init_local(self) -> None:
        # Local in-process backend initialization has been removed. Running a
        # memory service must be done as a separate HTTP process.
        # If a developer needs an opt-in local backend, use an explicit
        # environment flag (e.g., `SOMABRAIN_ALLOW_LOCAL_MEMORY=1`) and implement that
        # code separately in a developer-only helper.
        return

    def _init_http(self) -> None:
        import httpx  # type: ignore

        # Default headers applied to all requests; per-request we add X-Request-ID
        headers = {}
        if self.cfg.http and self.cfg.http.token:
            headers["Authorization"] = f"Bearer {self.cfg.http.token}"

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
        try:
            max_conns = int(os.getenv("SOMABRAIN_HTTP_MAX_CONNS", "64"))
        except Exception:
            max_conns = 64
        try:
            keepalive = int(os.getenv("SOMABRAIN_HTTP_KEEPALIVE", "32"))
        except Exception:
            keepalive = 32
        try:
            retries = int(os.getenv("SOMABRAIN_HTTP_RETRIES", "1"))
        except Exception:
            retries = 1

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
        env_base = (
            os.getenv("SOMABRAIN_HTTP_ENDPOINT")
            or os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
            or os.getenv("MEMORY_SERVICE_URL")
        )
        if env_base:
            try:
                # Clean any surrounding whitespace/newlines that may be injected by tests
                env_base = str(env_base).strip()
                # If missing scheme, default to http://
                if "://" not in env_base and env_base.startswith('/'):
                    # likely a path; leave as‑is
                    pass
                elif "://" not in env_base:
                    env_base = f"http://{env_base}"
                # Strip trailing openapi.json if present
                if env_base.endswith('/openapi.json'):
                    env_base = env_base[:-len('/openapi.json')]
            except Exception:
                env_base = None
        base_url = str(getattr(self.cfg.http, "endpoint", "") or "")
        if not base_url and env_base:
            base_url = env_base
        # Hard requirement: if SOMABRAIN_REQUIRE_MEMORY unset or ==1 force default endpoint
        require_memory = os.getenv("SOMABRAIN_REQUIRE_MEMORY")
        if (
            require_memory is None or require_memory in ("1", "true", "True")
        ) and not base_url:
            base_url = "http://localhost:9595"
        # Final normalisation: ensure empty string remains empty
        base_url = base_url or ""
        if base_url:
            try:
                os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = base_url
            except Exception:
                pass
        # If running inside Docker and no endpoint provided, default to the
        # host gateway which is commonly reachable as host.docker.internal on
        # macOS/Windows. This helps tests running inside containers talk to
        # a memory service running on the host machine (port 9595 by default).
        try:
            in_docker = os.path.exists("/.dockerenv")
        except Exception:
            in_docker = False
        if not base_url and in_docker:
            try:
                base_url = (
                    os.getenv("SOMABRAIN_DOCKER_MEMORY_FALLBACK")
                    or "http://host.docker.internal:9595"
                )
                logger.debug(
                    "MemoryClient running in Docker, defaulting base_url to %r",
                    base_url,
                )
            except Exception:
                pass
        client_kwargs = {
            "base_url": base_url,
            "headers": headers,
            "timeout": 10.0,
        }
        # Diagnostic: record chosen endpoint for debugging in tests
        try:
            logger.debug("MemoryClient HTTP base_url=%r", base_url)
        except Exception:
            pass
        if limits is not None:
            client_kwargs["limits"] = limits

        # Create sync client
        try:
            self._http = httpx.Client(**client_kwargs)
        except Exception:
            self._http = None

        # Create async client with configurable transport retries
        try:
            transport = httpx.AsyncHTTPTransport(retries=retries)
            async_kwargs = dict(client_kwargs)
            async_kwargs["transport"] = transport
            self._http_async = httpx.AsyncClient(**async_kwargs)
        except Exception:
            try:
                self._http_async = httpx.AsyncClient(**client_kwargs)
            except Exception:
                self._http_async = None

        # If endpoint is empty, treat HTTP client as unavailable
        try:
            if not base_url:
                self._http = None
                self._http_async = None
        except Exception:
            pass
        # If memory is required and client not initialized, raise immediately to fail fast.
        if (require_memory is None or require_memory in ("1", "true", "True")) and (
            self._http is None
        ):
            raise RuntimeError(
                "SOMABRAIN_REQUIRE_MEMORY enforced but no memory service reachable or endpoint unset. Expected http://localhost:9595 or configured URL."
            )

    def _init_redis(self) -> None:
        # Redis mode removed. Redis-backed behavior should be exposed via the
        # HTTP memory service if required.
        return

    def health(self) -> dict:
        """Best-effort backend health signal for local or http mode."""
        try:
            if self._http:
                r = self._http.get("/health")
                return {"http": getattr(r, "status_code", 500) == 200}
        except Exception:
            return {"ok": False}
        return {"ok": True}

    def _record_outbox(self, op: str, payload: dict):
        """Append a failed HTTP operation to the outbox for later retry.
        The JSON line includes the operation name (remember, recall, link, alink) and the
        original payload needed to replay the request.
        """
        try:
            with open(self._outbox_path, "a") as f:
                json.dump({"op": op, "payload": payload}, f)
                f.write("\n")
        except Exception:
            pass

    # --- HTTP helpers ---------------------------------------------------------
    @staticmethod
    def _response_json(resp: Any) -> Any:
        try:
            if hasattr(resp, "json") and callable(resp.json):
                return resp.json()
        except Exception:
            return None
        return None

    def _http_post_with_retries_sync(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = 2,
    ) -> tuple[bool, int, Any]:
        if self._http is None:
            return False, 0, None
        status = 0
        data: Any = None
        for attempt in range(max_retries + 1):
            try:
                resp = self._http.post(endpoint, json=body, headers=headers)
            except Exception:
                if attempt < max_retries:
                    time.sleep(0.01 + random.random() * 0.02)
                continue
            status = int(getattr(resp, "status_code", 0) or 0)
            if status in (429, 503) and attempt < max_retries:
                time.sleep(0.01 + random.random() * 0.02)
                continue
            if status >= 500 and attempt < max_retries:
                time.sleep(0.05 + random.random() * 0.05)
                continue
            data = self._response_json(resp)
            return status < 300, status, data
        return False, status, data

    async def _http_post_with_retries_async(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = 2,
    ) -> tuple[bool, int, Any]:
        if self._http_async is None:
            return False, 0, None
        status = 0
        data: Any = None
        for attempt in range(max_retries + 1):
            try:
                resp = await self._http_async.post(endpoint, json=body, headers=headers)
            except Exception:
                if attempt < max_retries:
                    await asyncio.sleep(0.01 + random.random() * 0.02)
                continue
            status = int(getattr(resp, "status_code", 0) or 0)
            if status in (429, 503) and attempt < max_retries:
                await asyncio.sleep(0.01 + random.random() * 0.02)
                continue
            if status >= 500 and attempt < max_retries:
                await asyncio.sleep(0.05 + random.random() * 0.05)
                continue
            data = self._response_json(resp)
            return status < 300, status, data
        return False, status, data

    def _store_http_sync(
        self, body: dict, headers: dict
    ) -> tuple[bool, Any]:
        # Prefer /remember endpoint first; fall back to /store if /remember is unavailable.
        success, status, data = self._http_post_with_retries_sync("/remember", body, headers)
        if success:
            return True, data
        if status in (404, 405):
            # /remember not available – try /store as fallback.
            fallback_success, _, fallback_data = self._http_post_with_retries_sync(
                "/store", body, headers
            )
            if fallback_success:
                return True, fallback_data
        return False, data

    async def _store_http_async(
        self, body: dict, headers: dict
    ) -> tuple[bool, Any]:
        # Try /remember first; fall back to /store if /remember is unavailable.
        success, status, data = await self._http_post_with_retries_async(
            "/remember", body, headers
        )
        if success:
            return True, data
        if status in (404, 405):
            fallback_success, _, fallback_data = await self._http_post_with_retries_async(
                "/store", body, headers
            )
            if fallback_success:
                return True, fallback_data
        return False, data

    def _store_bulk_http_sync(
        self, items: List[dict], headers: dict
    ) -> tuple[bool, int, Any]:
        if self._http is None:
            return False, 0, None
        payload = {"items": items}
        success, status, data = self._http_post_with_retries_sync(
            "/store_bulk", payload, headers
        )
        return success, status, data

    async def _store_bulk_http_async(
        self, items: List[dict], headers: dict
    ) -> tuple[bool, int, Any]:
        if self._http_async is None:
            return False, 0, None
        payload = {"items": items}
        success, status, data = await self._http_post_with_retries_async(
            "/store_bulk", payload, headers
        )
        return success, status, data

    def _http_recall_sync(
        self,
        endpoint: str,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit] | None:
        if self._http is None:
            return None
        compat_payload, _, compat_hdr = self._compat_enrich_payload(
            {"query": query, "universe": universe or "real"}, query
        )
        headers = {"X-Request-ID": request_id}
        headers.update(compat_hdr)
        try:
            resp = self._http.post(
                endpoint,
                json={
                    "query": query,
                    "top_k": int(top_k),
                    "universe": compat_payload.get("universe", universe or "real"),
                },
                headers=headers,
            )
            try:
                code = getattr(resp, "status_code", 200)
                if code in (429, 503):
                    time.sleep(0.01 + random.random() * 0.02)
                    resp = self._http.post(
                        endpoint,
                        json={
                            "query": query,
                            "top_k": int(top_k),
                            "universe": compat_payload.get("universe", universe or "real"),
                        },
                        headers=headers,
                    )
            except Exception:
                pass
            data = self._response_json(resp)
            hits = self._normalize_recall_hits(data)
            if hits:
                hits = self._filter_hits_by_keyword(hits, str(query))
                if hits:
                    self._apply_weighting_to_hits(hits)
                    return hits
        except Exception:
            return None
        return None

    async def _http_recall_async(
        self,
        endpoint: str,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit] | None:
        if self._http_async is None:
            return None
        _, _, compat_hdr = self._compat_enrich_payload(
            {"query": query, "universe": universe or "real"}, query
        )
        headers = {"X-Request-ID": request_id}
        headers.update(compat_hdr)
        try:
            resp = await self._http_async.post(
                endpoint,
                json={
                    "query": query,
                    "top_k": int(top_k),
                    "universe": universe or "real",
                },
                headers=headers,
            )
            try:
                code = getattr(resp, "status_code", 200)
                if code in (429, 503):
                    await asyncio.sleep(0.01 + random.random() * 0.02)
                    resp = await self._http_async.post(
                        endpoint,
                        json={
                            "query": query,
                            "top_k": int(top_k),
                            "universe": universe or "real",
                        },
                        headers=headers,
                    )
            except Exception:
                pass
            data = self._response_json(resp)
            hits = self._normalize_recall_hits(data)
            if hits:
                hits = self._filter_hits_by_keyword(hits, str(query))
                if hits:
                    self._apply_weighting_to_hits(hits)
                    return hits
        except Exception:
            return None
        return None

    def _normalize_recall_hits(self, data: Any) -> List[RecallHit]:
        hits: List[RecallHit] = []
        if isinstance(data, dict):
            items = None
            for key in ("matches", "results", "items", "memories", "entries", "hits"):
                seq = data.get(key)
                if isinstance(seq, list):
                    items = seq
                    break
            if items is None and isinstance(data.get("data"), list):
                items = data.get("data")
            if items is not None:
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    payload = item.get("payload")
                    if not isinstance(payload, dict):
                        mem = item.get("memory")
                        if isinstance(mem, dict):
                            payload = mem.get("payload") or mem
                    if not isinstance(payload, dict):
                        payload = {
                            k: v
                            for k, v in item.items()
                            if k
                            not in (
                                "score",
                                "coord",
                                "coordinate",
                                "distance",
                                "vector",
                            )
                        }
                    payload = dict(payload or {})
                    score = None
                    try:
                        score_val = item.get("score")
                        if score_val is None:
                            score_val = item.get("similarity")
                        if score_val is None and isinstance(item.get("metadata"), dict):
                            score_val = item["metadata"].get("score")
                        if score_val is not None:
                            score = float(score_val)
                            payload.setdefault("_score", score)
                    except Exception:
                        score = None
                    coord = _extract_memory_coord(item)
                    if coord and "coordinate" not in payload:
                        payload["coordinate"] = coord
                    hits.append(
                        RecallHit(
                            payload=payload,
                            score=score,
                            coordinate=coord,
                            raw=item,
                        )
                    )
                return hits
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                payload = dict(item)
                coord = _extract_memory_coord(item)
                if coord and "coordinate" not in payload:
                    payload["coordinate"] = coord
                hits.append(
                    RecallHit(
                        payload=payload,
                        score=None,
                        coordinate=coord,
                        raw=item,
                    )
                )
        return hits

    def _keyword_terms(self, query: str) -> List[str]:
        q = str(query or "").strip()
        if not q:
            return []
        terms: List[str] = []
        seen: set[str] = set()
        for token in re.split(r"[^A-Za-z0-9]+", q):
            token = token.strip()
            if len(token) < 3:
                continue
            lower = token.lower()
            if not lower or lower in seen:
                continue
            seen.add(lower)
            terms.append(token)
        return terms

    def _hit_identity(self, hit: RecallHit) -> str:
        coord = hit.coordinate
        if coord is None:
            coord = _extract_memory_coord(hit.payload) or _extract_memory_coord(hit.raw)
        if coord:
            try:
                return "coord:{:.6f},{:.6f},{:.6f}".format(coord[0], coord[1], coord[2])
            except Exception:
                pass
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        if isinstance(payload, dict):
            for key in ("id", "memory_id", "key", "coord_key"):
                identifier = payload.get(key)
                if identifier:
                    return f"id:{identifier}"
            for field in ("task", "text", "content", "what", "fact", "headline"):
                value = payload.get(field)
                if isinstance(value, str) and value.strip():
                    return f"text:{value.strip().lower()}"
        try:
            raw = hit.raw or hit.payload
            serial = json.dumps(raw, sort_keys=True, default=str)
            digest = hashlib.blake2s(serial.encode("utf-8"), digest_size=16).hexdigest()
            return f"hash:{digest}"
        except Exception:
            return f"obj:{id(hit)}"

    def _deduplicate_hits(self, hits: List[RecallHit]) -> List[RecallHit]:
        deduped: List[RecallHit] = []
        seen: set[str] = set()
        for hit in hits:
            ident = self._hit_identity(hit)
            if ident in seen:
                continue
            seen.add(ident)
            deduped.append(hit)
        return deduped

    def _lexical_bonus(self, payload: dict, query: str) -> float:
        q = str(query or "").strip()
        if not q or not isinstance(payload, dict):
            return 0.0
        ql = q.lower()
        bonus = 0.0
        fields = ("task", "text", "content", "what", "fact", "headline", "summary")
        for field in fields:
            value = payload.get(field)
            if isinstance(value, str) and value:
                vl = value.lower()
                if vl == ql:
                    bonus = max(bonus, 1.5)
                elif ql in vl:
                    bonus = max(bonus, 1.0)
        token_matches = 0
        for token in re.split(r"[\s,;:/-]+", q):
            token = token.strip().lower()
            if len(token) < 3:
                continue
            for field in fields:
                value = payload.get(field)
                if isinstance(value, str) and token in value.lower():
                    token_matches += 1
                    break
        if token_matches:
            bonus += min(0.25 * token_matches, 1.0)
        return bonus

    def _rank_hits(self, hits: List[RecallHit], query: str) -> List[RecallHit]:
        ranked: List[tuple[float, float, float, int, RecallHit]] = []
        for idx, hit in enumerate(hits):
            payload = hit.payload if isinstance(hit.payload, dict) else {}
            lex_bonus = self._lexical_bonus(payload, query)
            base = 0.0
            if hit.score is not None:
                try:
                    base = float(hit.score)
                    if abs(base) > 1.0:
                        base = math.copysign(math.log1p(abs(base)), base)
                except Exception:
                    base = 0.0
            weight = 1.0
            if isinstance(payload, dict):
                try:
                    wf = payload.get("_weight_factor")
                    if isinstance(wf, (int, float)):
                        weight = float(wf)
                except Exception:
                    weight = 1.0
            final_score = (base * weight) + lex_bonus
            if hit.score is None and lex_bonus > 0:
                try:
                    hit.score = lex_bonus
                    payload.setdefault("_score", hit.score)
                except Exception:
                    pass
            ranked.append((final_score, lex_bonus, weight, -idx, hit))
        ranked.sort(key=lambda t: (t[0], t[1], t[2], t[3]), reverse=True)
        return [item[-1] for item in ranked]

    def _http_post_hits_sync(
        self,
        endpoint: str,
        body: dict,
        request_id: str,
        headers: dict,
        query: str,
    ) -> List[RecallHit]:
        if self._http is None:
            return []
        hdrs = {"X-Request-ID": f"{request_id}:{endpoint.strip('/').replace('/', '_') or 'root'}"}
        hdrs.update(headers or {})
        ok, status, data = self._http_post_with_retries_sync(endpoint, body, hdrs)
        if not ok:
            if status not in (404, 405):
                try:
                    logger.debug(
                        "MemoryClient HTTP %s returned status=%s body=%s", endpoint, status, data
                    )
                except Exception:
                    pass
            return []
        hits = self._normalize_recall_hits(data)
        for hit in hits:
            try:
                hit.payload.setdefault("_source_endpoint", endpoint)
            except Exception:
                pass
        return hits

    async def _http_post_hits_async(
        self,
        endpoint: str,
        body: dict,
        request_id: str,
        headers: dict,
        query: str,
    ) -> List[RecallHit]:
        if self._http_async is None:
            return []
        hdrs = {"X-Request-ID": f"{request_id}:{endpoint.strip('/').replace('/', '_') or 'root'}"}
        hdrs.update(headers or {})
        ok, status, data = await self._http_post_with_retries_async(endpoint, body, hdrs)
        if not ok:
            if status not in (404, 405):
                try:
                    logger.debug(
                        "MemoryClient HTTP %s returned status=%s body=%s", endpoint, status, data
                    )
                except Exception:
                    pass
            return []
        hits = self._normalize_recall_hits(data)
        for hit in hits:
            try:
                hit.payload.setdefault("_source_endpoint", endpoint)
            except Exception:
                pass
        return hits

    def _http_recall_aggregate_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        if self._http is None:
            return []
        _, compat_universe, compat_headers = self._compat_enrich_payload(
            {"query": query, "universe": universe or "real"}, query
        )
        universe = str(compat_universe or universe or "real")
        compat_headers = dict(compat_headers or {})
        fetch_limit = max(int(top_k) * 3, 10)
        aggregated: List[RecallHit] = []
        query_text = str(query or "")
        normalized_query = query_text.strip()

        primary_body = {
            "query": query_text,
            "top_k": fetch_limit,
            "universe": universe,
            "exact": False,
            "case_sensitive": False,
        }
        primary_hits = self._http_post_hits_sync(
            "/recall_with_scores", primary_body, request_id, compat_headers, query
        )
        aggregated.extend(primary_hits)
        if not primary_hits:
            fallback_body = {
                "query": query_text,
                "top_k": fetch_limit,
                "universe": universe,
                "hybrid": True,
            }
            aggregated.extend(
                self._http_post_hits_sync(
                    "/recall", fallback_body, request_id, compat_headers, query
                )
            )

        terms = self._keyword_terms(normalized_query or query_text)
        if normalized_query:
            hybrid_body = {
                "query": query_text,
                "terms": terms or None,
                "top_k": fetch_limit,
                "exact": False,
                "case_sensitive": False,
            }
            aggregated.extend(
                self._http_post_hits_sync(
                    "/hybrid_recall_with_scores",
                    hybrid_body,
                    request_id,
                    compat_headers,
                    query,
                )
            )

            keyword_body = {
                "term": normalized_query,
                "exact": False,
                "case_sensitive": False,
                "top_k": fetch_limit,
            }
            aggregated.extend(
                self._http_post_hits_sync(
                    "/keyword_search", keyword_body, request_id, compat_headers, query
                )
            )

        deduped = self._deduplicate_hits(aggregated)
        if not deduped:
            return []
        self._apply_weighting_to_hits(deduped)
        ranked = self._rank_hits(deduped, query)
        limit = max(1, int(top_k))
        return ranked[:limit]

    async def _http_recall_aggregate_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        if self._http_async is None:
            return []
        _, compat_universe, compat_headers = self._compat_enrich_payload(
            {"query": query, "universe": universe or "real"}, query
        )
        universe = str(compat_universe or universe or "real")
        compat_headers = dict(compat_headers or {})
        fetch_limit = max(int(top_k) * 3, 10)
        aggregated: List[RecallHit] = []
        query_text = str(query or "")
        normalized_query = query_text.strip()

        primary_body = {
            "query": query_text,
            "top_k": fetch_limit,
            "universe": universe,
            "exact": False,
            "case_sensitive": False,
        }
        primary_hits = await self._http_post_hits_async(
            "/recall_with_scores", primary_body, request_id, compat_headers, query
        )
        aggregated.extend(primary_hits)
        if not primary_hits:
            fallback_body = {
                "query": query_text,
                "top_k": fetch_limit,
                "universe": universe,
                "hybrid": True,
            }
            aggregated.extend(
                await self._http_post_hits_async(
                    "/recall", fallback_body, request_id, compat_headers, query
                )
            )

        terms = self._keyword_terms(normalized_query or query_text)
        if normalized_query:
            hybrid_body = {
                "query": query_text,
                "terms": terms or None,
                "top_k": fetch_limit,
                "exact": False,
                "case_sensitive": False,
            }
            aggregated.extend(
                await self._http_post_hits_async(
                    "/hybrid_recall_with_scores",
                    hybrid_body,
                    request_id,
                    compat_headers,
                    query,
                )
            )

            keyword_body = {
                "term": normalized_query,
                "exact": False,
                "case_sensitive": False,
                "top_k": fetch_limit,
            }
            aggregated.extend(
                await self._http_post_hits_async(
                    "/keyword_search", keyword_body, request_id, compat_headers, query
                )
            )

        deduped = self._deduplicate_hits(aggregated)
        if not deduped:
            return []
        self._apply_weighting_to_hits(deduped)
        ranked = self._rank_hits(deduped, query)
        limit = max(1, int(top_k))
        return ranked[:limit]

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

    def _apply_weighting_to_hits(self, hits: List[RecallHit]) -> None:
        if not hits:
            return
        if os.getenv("SOMABRAIN_MEMORY_ENABLE_WEIGHTING") not in (
            "1",
            "true",
            "True",
        ):
            return
        try:
            priors_env = os.getenv("SOMABRAIN_MEMORY_PHASE_PRIORS", "")
            qexp = float(os.getenv("SOMABRAIN_MEMORY_QUALITY_EXP", "1.0"))
            priors: dict[str, float] = {}
            if priors_env:
                for part in priors_env.split(","):
                    if not part.strip() or ":" not in part:
                        continue
                    k, v = part.split(":", 1)
                    try:
                        priors[k.strip().lower()] = float(v)
                    except Exception:
                        pass
            for hit in hits:
                payload = hit.payload
                phase_factor = 1.0
                quality_factor = 1.0
                try:
                    phase = payload.get("phase") if isinstance(payload, dict) else None
                    if phase and priors:
                        phase_factor = float(priors.get(str(phase).lower(), 1.0))
                except Exception:
                    phase_factor = 1.0
                try:
                    if isinstance(payload, dict) and "quality_score" in payload:
                        qs = float(payload.get("quality_score") or 0.0)
                        if qs < 0:
                            qs = 0.0
                        if qs > 1:
                            qs = 1.0
                        quality_factor = (qs**qexp) if qs > 0 else 0.0
                except Exception:
                    quality_factor = 1.0
                try:
                    payload.setdefault("_weight_factor", phase_factor * quality_factor)
                except Exception:
                    pass
        except Exception:
            return

    def _local_recall_hits(
        self, query: str, universe: str | None
    ) -> List[RecallHit]:
        try:
            uni = str(universe or "real")
            local: list[dict] = []
            with self._lock:
                local.extend(self._stub_store)
            try:
                ns = getattr(self.cfg, "namespace", None)
                if ns is not None:
                    local.extend(list(_GLOBAL_PAYLOADS.get(ns, [])))
            except Exception:
                pass
            needle = str(query or "").lower()
            out: list[dict] = []
            for p in local:
                try:
                    if universe is not None and str(p.get("universe") or "real") != uni:
                        continue
                    txt = None
                    if isinstance(p, dict):
                        for k in ("task", "text", "content", "what"):
                            v = p.get(k)
                            if isinstance(v, str) and v.strip():
                                txt = v
                                break
                    if not txt:
                        continue
                    if not needle or needle in txt.lower():
                        out.append(p)
                except Exception:
                    pass

            def _coord_from_payload(entry: dict) -> Tuple[float, float, float] | None:
                c = entry.get("coordinate")
                try:
                    if isinstance(c, (list, tuple)) and len(c) >= 3:
                        return (float(c[0]), float(c[1]), float(c[2]))
                    if isinstance(c, str):
                        parsed = _parse_coord_string(c)
                        if parsed:
                            return parsed
                except Exception:
                    return None
                return None

            return [
                RecallHit(payload=p, coordinate=_coord_from_payload(p)) for p in out
            ]
        except Exception:
            return []
    # --- HTTP compatibility helpers -------------------------------------------------
    def _compat_enrich_payload(
        self, payload: dict, coord_key: str
    ) -> tuple[dict, str, dict]:
        """Return an enriched (payload_copy, universe, extra_headers).

        Ensures downstream HTTP memory services receive common fields that many
        implementations index on: text/content/id/universe. Does not mutate input.
        """
        p = dict(payload or {})
        # Universe scoping
        universe = str(p.get("universe") or "real")
        # Choose canonical text for indexing: prefer 'task' then 'text' then 'content' then 'what/fact'
        text = None
        for k in ("task", "text", "content", "what", "fact", "headline", "description"):
            v = p.get(k)
            if isinstance(v, str) and v.strip():
                text = v.strip()
                break
        if not text:
            # last resort – coord_key as text anchor
            text = str(coord_key)
        # Mirror into common keys if absent
        p.setdefault("text", text)
        p.setdefault("content", text)
        # Provide a stable id if caller didn't specify one
        p.setdefault("id", p.get("memory_id") or p.get("key") or coord_key)
        # Provide a timestamp if missing
        p.setdefault("timestamp", time.time())
        # Ensure universe present
        p.setdefault("universe", universe)
        # Namespace (best-effort) – some services record this for tenancy
        try:
            ns = getattr(self.cfg, "namespace", None)
            if ns and not p.get("namespace"):
                p["namespace"] = ns
        except Exception:
            pass
        # Extra headers for HTTP calls
        headers = {"X-Universe": universe}
        return p, universe, headers

    def remember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Store a memory using a stable coordinate derived from coord_key.

        Ensures required structural keys, and normalizes optional metadata if
        present. Supported optional metadata (all pass‑through if already in
        correct shape): phase, quality_score, domains, reasoning_chain.
        - phase: coerced to lower‑case str.
        - quality_score: clamped into [0, 1].
        - domains: accepted as list[str] or comma/space separated string -> list[str].
        - reasoning_chain: list[str] or single string; stored verbatim.
        """
        # Refresh builtins-backed mirrors in case tests replaced them
        _refresh_builtins_globals()

        # include universe in coordinate hashing to avoid collisions across branches
        # and enrich payload for downstream compatibility
        enriched, universe, _hdr = self._compat_enrich_payload(payload, coord_key)
        coord = _stable_coord(f"{universe}::{coord_key}")

        # ensure we don't mutate caller's dict; copy and normalize metadata
        payload = dict(enriched)
        payload.setdefault("memory_type", "episodic")
        payload.setdefault("timestamp", time.time())
        payload.setdefault("universe", universe)

        # --- Normalize optional metadata fields (light-touch) ---
        try:
            # phase
            if "phase" in payload and isinstance(payload["phase"], str):
                payload["phase"] = payload["phase"].strip().lower() or None
            # quality_score
            if "quality_score" in payload:
                try:
                    qs = float(payload["quality_score"])  # type: ignore[arg-type]
                    if qs < 0:
                        qs = 0.0
                    if qs > 1:
                        qs = 1.0
                    payload["quality_score"] = qs
                except Exception:
                    payload.pop("quality_score", None)
            # domains
            if "domains" in payload:
                dval = payload["domains"]
                if isinstance(dval, str):
                    # split on comma or whitespace
                    parts = [
                        p.strip().lower()
                        for p in dval.replace(",", " ").split()
                        if p.strip()
                    ]
                    payload["domains"] = parts or []
                elif isinstance(dval, (list, tuple)):
                    cleaned = []
                    for x in dval:  # type: ignore[assignment]
                        if isinstance(x, str) and x.strip():
                            cleaned.append(x.strip().lower())
                    payload["domains"] = cleaned
                else:
                    payload.pop("domains", None)
            # reasoning_chain: accept list[str] or single string -> keep
            if "reasoning_chain" in payload and isinstance(
                payload["reasoning_chain"], str
            ):
                rc = payload["reasoning_chain"].strip()
                if rc:
                    payload["reasoning_chain"] = [rc]
                else:
                    payload.pop("reasoning_chain", None)
        except Exception:
            # Never fail store because of metadata normalization
            pass

        # Detect async context: if present, schedule background persistence
        try:
            loop = asyncio.get_running_loop()
            in_async = True
        except Exception:
            in_async = False

        p2: dict[str, Any] | None = None
        # Mirror locally for quick reads and visibility
        try:
            p2 = dict(payload)
            p2["coordinate"] = coord
            with self._lock:
                self._stub_store.append(p2)
            _GLOBAL_PAYLOADS.setdefault(self.cfg.namespace, []).append(p2)
        except Exception:
            p2 = None

        try:
            payload.setdefault("coordinate", coord)
        except Exception:
            pass

        import uuid

        rid = request_id or str(uuid.uuid4())

        # If we're in an async loop, schedule an async background persist (non-blocking)
        if in_async:
            try:
                loop = asyncio.get_running_loop()
                if self._http_async is not None:
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
        # fast-ack mode which writes to the local outbox and schedules background
        # persistence to improve client latency under load.
        fast_ack = os.getenv("SOMABRAIN_MEMORY_FAST_ACK", "0") in ("1", "true", "True")
        if fast_ack:
            # record to outbox immediately and schedule a background persist
            try:
                self._record_outbox(
                    "remember",
                    {"coord_key": coord_key, "payload": payload, "request_id": rid},
                )
            except Exception:
                pass
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
        server_coord: Tuple[float, float, float] | None = None
        try:
            server_coord = self._remember_sync_persist(coord_key, payload, rid)
        except Exception:
            server_coord = None
        if server_coord:
            coord = server_coord
            try:
                payload["coordinate"] = server_coord
            except Exception:
                pass
            if p2 is not None:
                try:
                    p2["coordinate"] = server_coord
                except Exception:
                    pass
        return coord

    def remember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Store multiple memories in a single HTTP round-trip when supported.

        Each element in *items* is a ``(coord_key, payload)`` pair. The method
        mirrors :meth:`remember` semantics: local mirrors are updated eagerly for
        read-your-writes guarantees, while the HTTP call happens best-effort. The
        return value is a list of coordinates (server-provided when available)
        aligned with the input order.
        """

        _refresh_builtins_globals()
        records = list(items)
        if not records:
            return []

        prepared: List[dict[str, Any]] = []
        local_payloads: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []

        for idx, (coord_key, payload) in enumerate(records):
            enriched, universe, _ = self._compat_enrich_payload(payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
            enriched_payload = dict(enriched)
            enriched_payload.setdefault("coordinate", coord)
            enriched_payload.setdefault("memory_type", "episodic")
            body = {
                "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                "payload": enriched_payload,
                "type": enriched_payload.get("memory_type", "episodic"),
            }
            # Local mirrors for read-your-writes
            local_copy = dict(enriched_payload)
            local_payloads.append(local_copy)
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "local_payload": local_copy,
                    "universe": universe,
                }
            )

        # Mirror into in-process stores before hitting HTTP for read-your-writes
        with self._lock:
            self._stub_store.extend(local_payloads)
        try:
            ns = getattr(self.cfg, "namespace", None)
            if ns is not None:
                bucket = _GLOBAL_PAYLOADS.setdefault(ns, [])
                bucket.extend(local_payloads)
        except Exception:
            pass

        if self._http is None:
            rid = request_id or str(uuid.uuid4())
            try:
                self._record_outbox(
                    "remember_bulk",
                    {
                        "request_id": rid,
                        "items": [
                            {
                                "coord_key": entry["coord_key"],
                                "payload": entry["body"]["payload"],
                                "coord": entry["body"]["coord"],
                            }
                            for entry in prepared
                        ],
                    },
                )
            except Exception:
                pass
            return coords

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        unique_universes = {u for u in universes if u}
        if len(unique_universes) == 1:
            headers["X-Universe"] = unique_universes.pop()

        success, status, response = self._store_bulk_http_sync(
            [entry["body"] for entry in prepared], headers
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
                    try:
                        prepared[idx]["local_payload"]["coordinate"] = server_coord
                    except Exception:
                        pass
            return coords

        if status in (404, 405):
            # Fallback to individual store calls
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
                        try:
                            entry["local_payload"]["coordinate"] = server_coord
                        except Exception:
                            pass
            return coords

        # HTTP request failed – record outbox for replay
        try:
            self._record_outbox(
                "remember_bulk",
                {
                    "request_id": rid,
                    "items": [
                        {
                            "coord_key": entry["coord_key"],
                            "payload": entry["body"]["payload"],
                            "coord": entry["body"]["coord"],
                        }
                        for entry in prepared
                    ],
                },
            )
        except Exception:
            pass
        return coords

    async def aremember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Async variant of remember for HTTP mode; falls back to thread executor.

        Returns the chosen 3‑tuple coord (server‑preferred if configured), or the
        locally computed coord. On failure, falls back to running the sync remember
        in a thread executor.
        """
        # Mirror locally first for read-your-writes semantics
        p2: dict[str, Any] | None = None
        try:
            _refresh_builtins_globals()
            enriched, universe, _hdr = self._compat_enrich_payload(payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
            p2 = dict(enriched)
            p2["coordinate"] = coord
            with self._lock:
                self._stub_store.append(p2)
            try:
                ns = getattr(self.cfg, "namespace", None)
                if ns is not None:
                    _GLOBAL_PAYLOADS.setdefault(ns, []).append(p2)
            except Exception:
                pass
        except Exception:
            pass
        if self._http_async is not None:
            try:
                enriched, universe, compat_hdr = self._compat_enrich_payload(
                    payload, coord_key
                )
                coord = _stable_coord(f"{universe}::{coord_key}")
                enriched = dict(enriched)
                enriched.setdefault("coordinate", coord)
                body = {
                    "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                    "payload": enriched,
                    "type": "episodic",
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
                        if getattr(
                            self.cfg, "prefer_server_coords_for_links", False
                        ):
                            return server_coord
                        return server_coord
                return coord
            except Exception:
                pass
        # Fallback: run the synchronous remember in a thread executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.remember, coord_key, payload)

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Async companion to :meth:`remember_bulk` using the async HTTP client."""

        _refresh_builtins_globals()
        records = list(items)
        if not records:
            return []

        prepared: List[dict[str, Any]] = []
        local_payloads: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []

        for idx, (coord_key, payload) in enumerate(records):
            enriched, universe, _ = self._compat_enrich_payload(payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
            enriched_payload = dict(enriched)
            enriched_payload.setdefault("coordinate", coord)
            enriched_payload.setdefault("memory_type", "episodic")
            body = {
                "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                "payload": enriched_payload,
                "type": enriched_payload.get("memory_type", "episodic"),
            }
            local_copy = dict(enriched_payload)
            local_payloads.append(local_copy)
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "local_payload": local_copy,
                    "universe": universe,
                }
            )

        with self._lock:
            self._stub_store.extend(local_payloads)
        try:
            ns = getattr(self.cfg, "namespace", None)
            if ns is not None:
                bucket = _GLOBAL_PAYLOADS.setdefault(ns, [])
                bucket.extend(local_payloads)
        except Exception:
            pass

        if self._http_async is None:
            return self.remember_bulk(records, request_id=request_id)

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        unique_universes = {u for u in universes if u}
        if len(unique_universes) == 1:
            headers["X-Universe"] = unique_universes.pop()

        success, status, response = await self._store_bulk_http_async(
            [entry["body"] for entry in prepared], headers
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
                    try:
                        prepared[idx]["local_payload"]["coordinate"] = server_coord
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
                        try:
                            entry["local_payload"]["coordinate"] = server_coord
                        except Exception:
                            pass
            return coords

        try:
            self._record_outbox(
                "remember_bulk",
                {
                    "request_id": rid,
                    "items": [
                        {
                            "coord_key": entry["coord_key"],
                            "payload": entry["body"]["payload"],
                            "coord": entry["body"]["coord"],
                        }
                        for entry in prepared
                    ],
                },
            )
        except Exception:
            pass
        return coords

    def recall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Retrieve memories relevant to the query. Stub returns recent payloads."""
        # Enforce memory requirement: do not allow fallback when required
        require_memory = os.getenv("SOMABRAIN_REQUIRE_MEMORY")
        memory_required = (require_memory is None) or (
            require_memory in ("1", "true", "True")
        )
        if memory_required and self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED: HTTP memory backend not available (expected on port 9595)."
            )
        # Prefer HTTP recall if available
        if self._http is not None:
            rid = request_id or str(uuid.uuid4())
            hits = self._http_recall_aggregate_sync(
                query, top_k, universe or "real", rid
            )
            if not hits:
                hits = self._http_recall_sync(
                    "/recall", query, top_k, universe or "real", rid
                )
            if hits:
                return hits
            return self._local_recall_hits(query, universe)
        # In-process deterministic recall only if memory not required or HTTP absent and allowed.
        from somabrain.stub_audit import (
            STRICT_REAL as __SR,
            record_stub as __record_stub,
        )

        # If memory required but we are here (HTTP failed mid-flight), escalate error.
        if memory_required:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED: HTTP recall path failed unexpectedly."
            )
        # Try real in-process recall if we have any payloads stored and memory not required.
        if self._stub_store:
            try:
                # Lazy import embedder from runtime to avoid heavy deps at import time
                from somabrain import runtime as _rt  # type: ignore

                embedder = getattr(_rt, "embedder", None)
                if embedder is not None and hasattr(embedder, "embed"):
                    import numpy as _np

                    qv = _np.array(embedder.embed(query), dtype=_np.float32)
                    if _np.linalg.norm(qv) > 0:
                        qv = qv / (float(_np.linalg.norm(qv)) + 1e-8)
                    scored: list[tuple[float, dict]] = []
                    uni = str(universe or "real")
                    for p in self._stub_store:
                        if universe is not None:
                            if str(p.get("universe") or "real") != uni:
                                continue
                        txt = None
                        if isinstance(p, dict):
                            for k in ("task", "content", "text", "description"):
                                v = p.get(k)
                                if isinstance(v, str) and v.strip():
                                    txt = v
                                    break
                        if not txt:
                            txt = str(p)
                        try:
                            pv = _np.array(embedder.embed(txt), dtype=_np.float32)
                            n = float(_np.linalg.norm(pv))
                            if n > 0:
                                pv = pv / (n + 1e-8)
                            sim = float(_np.dot(qv, pv))
                            # --- Optional weighting hook ---
                            # Controlled by env SOMABRAIN_MEMORY_ENABLE_WEIGHTING
                            # final_sim = sim * phase_factor * quality_factor
                            if os.getenv("SOMABRAIN_MEMORY_ENABLE_WEIGHTING") in (
                                "1",
                                "true",
                                "True",
                            ):
                                phase_factor = 1.0
                                quality_factor = 1.0
                                # Phase prior multiplier
                                try:
                                    phase = (
                                        p.get("phase") if isinstance(p, dict) else None
                                    )
                                    priors_env = os.getenv(
                                        "SOMABRAIN_MEMORY_PHASE_PRIORS", ""
                                    )
                                    if phase and priors_env:
                                        # parse once per recall? (cheap, small string) -> acceptable
                                        priors: dict[str, float] = {}
                                        for part in priors_env.split(","):
                                            if not part.strip():
                                                continue
                                            if ":" in part:
                                                k, val = part.split(":", 1)
                                                try:
                                                    priors[k.strip().lower()] = float(
                                                        val
                                                    )
                                                except Exception:
                                                    pass
                                        phase_factor = float(
                                            priors.get(str(phase).lower(), 1.0)
                                        )
                                except Exception:
                                    phase_factor = 1.0
                                # Quality score exponent weighting
                                try:
                                    if isinstance(p, dict) and "quality_score" in p:
                                        qs = float(p.get("quality_score") or 0.0)
                                        if qs < 0:
                                            qs = 0.0
                                        if qs > 1:
                                            qs = 1.0
                                        qexp = float(
                                            os.getenv(
                                                "SOMABRAIN_MEMORY_QUALITY_EXP", "1.0"
                                            )
                                        )
                                        quality_factor = (qs**qexp) if qs > 0 else 0.0
                                except Exception:
                                    quality_factor = 1.0
                                sim *= phase_factor * quality_factor
                        except Exception:
                            sim = 0.0
                        scored.append((sim, p))
                    scored.sort(key=lambda t: t[0], reverse=True)
                    hits = [
                        RecallHit(payload=p) for _, p in scored[: int(max(0, top_k))]
                    ]
                    if hits:
                        return hits
            except Exception:
                # fall through to stub path logic
                pass
        # If strict mode and no in-process path succeeded, raise instead of silent stub
        if __SR:
            raise RuntimeError(
                "STRICT REAL MODE: no HTTP memory backend and in-process recall yielded no results. Configure service or insert memories first."
            )
        # Non-strict: simple recent-payload fallback
        __record_stub("memory_client.recall.stub_fallback")
        return [RecallHit(payload=p) for p in self._stub_store[-int(max(0, top_k)) :]]

    def recall_with_scores(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Recall memories via the dedicated ``/recall_with_scores`` endpoint when available."""

        if self._http is not None:
            rid = request_id or str(uuid.uuid4())
            hits = self._http_recall_aggregate_sync(
                query, top_k, universe or "real", rid
            )
            if not hits:
                hits = self._http_recall_sync(
                    "/recall_with_scores", query, top_k, universe or "real", rid
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
        """Async recall for HTTP mode; falls back to sync for local/stub."""
        if self._http_async is not None:
            rid = request_id or str(uuid.uuid4())
            hits = await self._http_recall_aggregate_async(
                query, top_k, universe or "real", rid
            )
            if not hits:
                hits = await self._http_recall_async(
                    "/recall", query, top_k, universe or "real", rid
                )
            if hits:
                return hits
            return self._local_recall_hits(query, universe)
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

        if self._http_async is not None:
            rid = request_id or str(uuid.uuid4())
            hits = await self._http_recall_aggregate_async(
                query, top_k, universe or "real", rid
            )
            if not hits:
                hits = await self._http_recall_async(
                    "/recall_with_scores", query, top_k, universe or "real", rid
                )
            if hits:
                return hits
        return await self.arecall(query, top_k, universe, request_id)

    def link(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        """Create or strengthen a typed edge in the memory graph."""
        _refresh_builtins_globals()
        if self._http is not None:
            try:
                import uuid

                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                self._http.post(
                    "/link",
                    json={
                        "from_coord": f"{from_coord[0]},{from_coord[1]},{from_coord[2]}",
                        "to_coord": f"{to_coord[0]},{to_coord[1]},{to_coord[2]}",
                        "type": link_type,
                        "weight": weight,
                    },
                    headers=rid_hdr,
                )
            except Exception:
                pass
            self._mirror_link_locally(from_coord, to_coord, link_type, weight)
            return

        self._mirror_link_locally(from_coord, to_coord, link_type, weight)

    def _mirror_link_locally(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str,
        weight: float,
    ) -> None:
        key_from = cast(
            Tuple[float, float, float],
            (from_coord[0], from_coord[1], from_coord[2]),
        )
        key_to = cast(
            Tuple[float, float, float], (to_coord[0], to_coord[1], to_coord[2]))
        with self._lock:
            adj = self._graph.get(key_from)
            if adj is None:
                adj = {}
                self._graph[key_from] = adj
            prev = adj.get(key_to, {"type": str(link_type), "weight": 0.0})
            new_w = float(prev.get("weight", 0.0)) + float(weight)
            adj[key_to] = {"type": str(link_type), "weight": new_w}

        try:
            ns = getattr(self.cfg, "namespace", None)
            if ns is not None:
                GLOBAL_LINKS_KEY = "_SOMABRAIN_GLOBAL_LINKS"
                if not hasattr(_builtins, GLOBAL_LINKS_KEY):
                    setattr(_builtins, GLOBAL_LINKS_KEY, {})
                global_links: dict[str, list[dict]] = getattr(
                    _builtins, GLOBAL_LINKS_KEY
                )
                ns_links = global_links.setdefault(ns, [])
                ns_links.append(
                    {
                        "from": list(map(float, from_coord)),
                        "to": list(map(float, to_coord)),
                        "type": str(link_type),
                        "weight": float(weight),
                    }
                )
                try:
                    logger.debug(
                        "link(local): appended edge to _GLOBAL_LINKS ns=%r total=%d global_id=%r builtin_id=%r",
                        ns,
                        len(global_links.get(ns, [])),
                        id(global_links),
                        id(getattr(_builtins, GLOBAL_LINKS_KEY, None)),
                    )
                except Exception:
                    pass
        except Exception:
            pass

    async def alink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        """Async helper mirroring :meth:`link` behaviour."""

        _refresh_builtins_globals()
        if self._http_async is not None:
            try:
                import uuid

                rid = request_id or str(uuid.uuid4())
                headers = {"X-Request-ID": rid}
                await self._http_async.post(
                    "/link",
                    json={
                        "from_coord": f"{from_coord[0]},{from_coord[1]},{from_coord[2]}",
                        "to_coord": f"{to_coord[0]},{to_coord[1]},{to_coord[2]}",
                        "type": link_type,
                        "weight": weight,
                    },
                    headers=headers,
                )
            except Exception:
                pass
            self._mirror_link_locally(from_coord, to_coord, link_type, weight)
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self.link(
                from_coord,
                to_coord,
                link_type=link_type,
                weight=weight,
                request_id=request_id,
            ),
        )

    def links_from(
        self,
        start: Tuple[float, float, float],
        type_filter: str | None = None,
        limit: int = 50,
    ) -> List[dict]:
        """List outgoing edges with metadata.

        HTTP mode: call the memory service `/neighbors`. Local/stub: use the
        in-process adjacency mirror.
        """
        _refresh_builtins_globals()
        out: List[dict] = []
        # Interpret limit<=0 as unlimited
        unlimited = int(limit) <= 0
        max_items = None if unlimited else int(limit)

        # HTTP backend: ask remote neighbors endpoint if available
        if self._http is not None:
            try:
                body = {
                    "from_coord": [float(start[0]), float(start[1]), float(start[2])],
                    "type": str(type_filter) if type_filter else None,
                    "limit": int(limit),
                }
                r = self._http.post("/neighbors", json=body)
                data = r.json() if hasattr(r, "json") else None
                edges = (data or {}).get("edges", []) if isinstance(data, dict) else []
                # normalize
                for e in edges:
                    try:
                        out.append(
                            {
                                "from": tuple(e.get("from") or start),
                                "to": tuple(e.get("to") or start),
                                "type": e.get("type"),
                                "weight": float(e.get("weight", 1.0)),
                            }
                        )
                    except Exception:
                        pass
            except Exception:
                out.clear()
            if out:
                return out if unlimited else out[:max_items]

        # Local/stub: gather from in-memory adjacency
        key_from = cast(
            Tuple[float, float, float],
            (float(start[0]), float(start[1]), float(start[2])),
        )
        with self._lock:
            adj = self._graph.get(key_from, {})
            for to_coord, meta in list(adj.items()):
                try:
                    if type_filter and meta.get("type") != type_filter:
                        continue
                    out.append(
                        {
                            "from": key_from,
                            "to": to_coord,
                            "type": meta.get("type"),
                            "weight": float(meta.get("weight", 1.0)),
                        }
                    )
                    if not unlimited and len(out) >= max_items:
                        break
                except Exception:
                    pass

        # Also include mirrored global links for this namespace
        try:
            ns = getattr(self.cfg, "namespace", None)
            if ns is not None:
                ns_links = _GLOBAL_LINKS.get(ns, [])
                # Only include global links whose start coordinate matches the requested start
                eps = 1e-6

                def _close(
                    a: Tuple[float, float, float],
                    b: Tuple[float, float, float],
                    eps: float = eps,
                ) -> bool:
                    return (
                        abs(float(a[0]) - float(b[0])) <= eps
                        and abs(float(a[1]) - float(b[1])) <= eps
                        and abs(float(a[2]) - float(b[2])) <= eps
                    )

                for e in ns_links:
                    try:
                        if type_filter and e.get("type") != type_filter:
                            continue
                        ef = e.get("from")
                        if not isinstance(ef, (list, tuple)) or len(ef) != 3:
                            continue
                        ef_t = tuple(map(float, ef))
                        if not _close(ef_t, key_from):
                            continue
                        out.append(
                            {
                                "from": ef_t,
                                "to": tuple(map(float, e.get("to") or [])),
                                "type": e.get("type"),
                                "weight": float(e.get("weight", 1.0)),
                            }
                        )
                        if not unlimited and len(out) >= max_items:
                            break
                    except Exception:
                        pass
        except Exception:
            pass

        return out if unlimited else out[:max_items]

    def unlink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        """Remove a directed edge from the memory graph."""

        _refresh_builtins_globals()
        removed = False
        if self._http is not None:
            try:
                rid = request_id or str(uuid.uuid4())
                headers = {"X-Request-ID": rid}
                self._http.post(
                    "/unlink",
                    json={
                        "from_coord": [float(from_coord[0]), float(from_coord[1]), float(from_coord[2])],
                        "to_coord": [float(to_coord[0]), float(to_coord[1]), float(to_coord[2])],
                        "type": link_type,
                    },
                    headers=headers,
                )
            except Exception:
                pass

        key_from = cast(
            Tuple[float, float, float],
            (float(from_coord[0]), float(from_coord[1]), float(from_coord[2])),
        )
        key_to = cast(
            Tuple[float, float, float],
            (float(to_coord[0]), float(to_coord[1]), float(to_coord[2])),
        )
        with self._lock:
            adj = self._graph.get(key_from)
            if adj and key_to in adj:
                if link_type is None or adj[key_to].get("type") == link_type:
                    adj.pop(key_to, None)
                    removed = True
                    if not adj:
                        self._graph.pop(key_from, None)

        try:
            ns = getattr(self.cfg, "namespace", None)
            if ns is not None:
                eps = 1e-6

                def _close(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
                    return all(abs(a[i] - b[i]) <= eps for i in range(3))

                entries = _GLOBAL_LINKS.get(ns, [])
                retained: List[dict] = []
                for edge in entries:
                    frm = edge.get("from")
                    to = edge.get("to")
                    if not (isinstance(frm, (list, tuple)) and isinstance(to, (list, tuple))):
                        retained.append(edge)
                        continue
                    frm_t = tuple(map(float, frm[:3]))
                    to_t = tuple(map(float, to[:3]))
                    if _close(frm_t, key_from) and _close(to_t, key_to):
                        if link_type is not None and edge.get("type") != link_type:
                            retained.append(edge)
                            continue
                        removed = True
                        continue
                    retained.append(edge)
                _GLOBAL_LINKS[ns] = retained
        except Exception:
            pass
        return removed

    async def aunlink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        """Async variant of :meth:`unlink`."""

        if self._http_async is not None:
            try:
                rid = request_id or str(uuid.uuid4())
                headers = {"X-Request-ID": rid}
                await self._http_async.post(
                    "/unlink",
                    json={
                        "from_coord": [float(from_coord[0]), float(from_coord[1]), float(from_coord[2])],
                        "to_coord": [float(to_coord[0]), float(to_coord[1]), float(to_coord[2])],
                        "type": link_type,
                    },
                    headers=headers,
                )
            except Exception:
                pass
        return self.unlink(from_coord, to_coord, link_type=link_type, request_id=request_id)

    def prune_links(
        self,
        coord: tuple[float, float, float],
        *,
        weight_below: float | None = None,
        max_degree: int | None = None,
        type_filter: str | None = None,
        request_id: str | None = None,
    ) -> int:
        """Prune outgoing edges using lightweight heuristics.

        Returns the number of locally removed edges (or the remote-reported count
        when greater). ``weight_below`` removes edges with weights strictly below
        the threshold. ``max_degree`` keeps the highest-weight edges up to the
        limit. ``type_filter`` restricts pruning to matching edge types.
        """

        _refresh_builtins_globals()
        removed_remote = 0
        if self._http is not None:
            try:
                rid = request_id or str(uuid.uuid4())
                headers = {"X-Request-ID": rid}
                payload = {
                    "from_coord": [float(coord[0]), float(coord[1]), float(coord[2])],
                    "weight_below": weight_below,
                    "max_degree": max_degree,
                    "type": type_filter,
                }
                resp = self._http.post("/prune", json=payload, headers=headers)
                data = self._response_json(resp)
                if isinstance(data, dict) and "removed" in data:
                    try:
                        removed_remote = int(data.get("removed") or 0)
                    except Exception:
                        removed_remote = 0
            except Exception:
                removed_remote = 0

        key_from = cast(
            Tuple[float, float, float],
            (float(coord[0]), float(coord[1]), float(coord[2])),
        )

        removed_local = 0
        with self._lock:
            adj = self._graph.get(key_from)
            if adj:
                to_remove: List[Tuple[float, float, float]] = []
                if weight_below is not None:
                    for neighbor, meta in list(adj.items()):
                        if type_filter and meta.get("type") != type_filter:
                            continue
                        try:
                            if float(meta.get("weight", 0.0)) < float(weight_below):
                                to_remove.append(neighbor)
                        except Exception:
                            to_remove.append(neighbor)
                for nbr in to_remove:
                    if nbr in adj:
                        adj.pop(nbr, None)
                        removed_local += 1

                # Enforce max_degree by trimming lowest-weight edges
                if max_degree is not None and max_degree >= 0:
                    candidates = [
                        (nbr, float(meta.get("weight", 0.0)))
                        for nbr, meta in adj.items()
                        if not type_filter or meta.get("type") == type_filter
                    ]
                    if len(candidates) > max_degree:
                        candidates.sort(key=lambda x: x[1])
                        for nbr, _ in candidates[: len(candidates) - int(max_degree)]:
                            if nbr in adj:
                                adj.pop(nbr, None)
                                removed_local += 1

                if not adj:
                    self._graph.pop(key_from, None)

        try:
            ns = getattr(self.cfg, "namespace", None)
            if ns is not None:
                eps = 1e-6

                def _close(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
                    return all(abs(a[i] - b[i]) <= eps for i in range(3))

                edges = _GLOBAL_LINKS.get(ns, [])
                retained: List[dict] = []
                for edge in edges:
                    frm = edge.get("from")
                    to = edge.get("to")
                    if not (isinstance(frm, (list, tuple)) and isinstance(to, (list, tuple))):
                        retained.append(edge)
                        continue
                    frm_t = tuple(map(float, frm[:3]))
                    if not _close(frm_t, key_from):
                        retained.append(edge)
                        continue
                    if type_filter and edge.get("type") != type_filter:
                        retained.append(edge)
                        continue
                    weight_val = 0.0
                    try:
                        weight_val = float(edge.get("weight", 0.0))
                    except Exception:
                        weight_val = 0.0
                    if weight_below is not None and weight_val < float(weight_below):
                        removed_local += 1
                        continue
                    retained.append(edge)
                _GLOBAL_LINKS[ns] = retained
        except Exception:
            pass

        total_removed = removed_local
        if removed_remote and removed_remote > total_removed:
            total_removed = removed_remote
        return total_removed

    async def aprune_links(
        self,
        coord: tuple[float, float, float],
        *,
        weight_below: float | None = None,
        max_degree: int | None = None,
        type_filter: str | None = None,
        request_id: str | None = None,
    ) -> int:
        """Async helper matching :meth:`prune_links`."""

        if self._http_async is not None:
            try:
                rid = request_id or str(uuid.uuid4())
                headers = {"X-Request-ID": rid}
                await self._http_async.post(
                    "/prune",
                    json={
                        "from_coord": [float(coord[0]), float(coord[1]), float(coord[2])],
                        "weight_below": weight_below,
                        "max_degree": max_degree,
                        "type": type_filter,
                    },
                    headers=headers,
                )
            except Exception:
                pass
        return self.prune_links(
            coord,
            weight_below=weight_below,
            max_degree=max_degree,
            type_filter=type_filter,
            request_id=request_id,
        )

    # --- New Graph Analytics Helpers ---
    def degree(self, node: Tuple[float, float, float]) -> int:
        """Return the number of outgoing edges from *node*.
        This is a lightweight helper for quick degree queries used by
        analytics or monitoring tools. It mirrors the adjacency stored in
        ``self._graph`` and falls back to the global links mirror if the
        node is not present locally.
        """
        key = cast(Tuple[float, float, float], (node[0], node[1], node[2]))
        adj = self._graph.get(key)
        if adj is not None:
            return len(adj)
        # Fallback: count edges from the global mirror for the current namespace
        try:
            my_ns = getattr(self.cfg, "namespace", None)
            if my_ns is None:
                return 0
            count = 0
            global_links_map = getattr(_builtins, _BUILTINS_LINKS_KEY, {})
            for ns, edges in list(global_links_map.items()):
                if ns != my_ns:
                    continue
                for e in edges:
                    ef = e.get("from")
                    if isinstance(ef, (list, tuple)) and len(ef) == 3:
                        if all(
                            abs(float(ef[i]) - float(node[i])) <= 1e-6 for i in range(3)
                        ):
                            count += 1
            return count
        except Exception:
            return 0

    def centrality(self, node: Tuple[float, float, float]) -> float:
        """Return a simple degree‑centrality value for *node*.
        Centrality is defined as ``degree / (total_nodes - 1)`` where
        ``total_nodes`` is the number of distinct coordinates known in the
        current namespace (both local graph and global mirror). This provides
        a quick, interpretable metric without heavy computation.
        """
        try:
            deg = self.degree(node)
            # Gather all unique nodes in the namespace
            nodes: set[Tuple[float, float, float]] = set(self._graph.keys())
            # Include nodes from the global mirror
            my_ns = getattr(self.cfg, "namespace", None)
            if my_ns is not None:
                global_links_map = getattr(_builtins, _BUILTINS_LINKS_KEY, {})
                for ns, edges in list(global_links_map.items()):
                    if ns != my_ns:
                        continue
                    for e in edges:
                        f = e.get("from")
                        t = e.get("to")
                        if isinstance(f, (list, tuple)) and len(f) == 3:
                            nodes.add(tuple(map(float, f)))
                        if isinstance(t, (list, tuple)) and len(t) == 3:
                            nodes.add(tuple(map(float, t)))
            total = len(nodes)
            if total <= 1:
                return 0.0
            return deg / (total - 1)
        except Exception:
            return 0.0

    # --- Compatibility helper methods expected by migration and other code ---
    def coord_for_key(
        self, key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
        """Return a deterministic coordinate for *key* and optional *universe*.

        This is a lightweight compatibility shim used by migration scripts and
        higher-level services. It mirrors the stable hash used for remembered
        payloads.
        """
        # When universe is not provided, default to 'real' to match remember()
        # which uses payload.get('universe') or 'real'. Using the namespace here
        # would produce inconsistent coordinates and break tests that rely on
        # defaulting to the real universe.
        uni = universe or "real"
        return _stable_coord(f"{uni}::{key}")

    def k_hop(
        self,
        starts: List[Tuple[float, float, float]],
        depth: int = 1,
        limit: int = 50,
        type_filter: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Return a list of coordinates reachable from *starts* within *depth* hops.

        This is a lightweight BFS that uses :meth:`links_from` to enumerate
        neighbors. It is intentionally tolerant and works for stub/local/http
        modes by relying on the existing links_from fallbacks.
        """
        try:
            if not starts:
                return []
            seen: set[Tuple[float, float, float]] = set()
            frontier = [tuple(float(s[i]) for i in range(3)) for s in starts]
            out: list[Tuple[float, float, float]] = []
            for d in range(max(1, int(depth))):
                new_frontier: list[Tuple[float, float, float]] = []
                for node in frontier:
                    if node in seen:
                        continue
                    seen.add(node)
                    # gather neighbors
                    try:
                        neigh = self.links_from(
                            node, type_filter=type_filter, limit=limit
                        )
                    except Exception:
                        neigh = []
                    for e in neigh:
                        to_coord = e.get("to")
                        if isinstance(to_coord, (list, tuple)) and len(to_coord) >= 3:
                            t = (
                                float(to_coord[0]),
                                float(to_coord[1]),
                                float(to_coord[2]),
                            )
                            if t not in seen and t not in out:
                                out.append(t)
                                new_frontier.append(t)
                                if len(out) >= max(1, int(limit)):
                                    return out
                frontier = new_frontier
                if not frontier:
                    break
            return out
        except Exception:
            return []

    def payloads_for_coords(
        self, coords: List[Tuple[float, float, float]], universe: str | None = None
    ) -> List[dict]:
        """Bulk retrieval of payloads for the given coordinates.

        The method tries several fallbacks (in‑memory stub store, process-global
        mirror) to return payload dictionaries that include a `coordinate` field.
        It is intentionally tolerant of small floating point differences.
        """
        _refresh_builtins_globals()
        out: List[dict] = []
        try:
            ns = getattr(self.cfg, "namespace", None)
            # If an HTTP endpoint is configured, use the dedicated bulk endpoint.
            if self._http:
                # Convert each coordinate tuple to the string form expected by the API.
                coord_strs = [f"{c[0]},{c[1]},{c[2]}" for c in coords]
                try:
                    r = self._http.post("/payloads", json={"coords": coord_strs})
                    data = r.json() if hasattr(r, "json") else {}
                    payloads = (
                        data.get("payloads", []) if isinstance(data, dict) else []
                    )
                    for entry in payloads:
                        # The API returns each entry as {"payload": {...}, "coord": "x,y,z"}
                        pl = entry.get("payload", {})
                        coord_raw = entry.get("coord")
                        if coord_raw:
                            # Normalise to tuple of floats
                            parsed = _parse_coord_string(coord_raw)
                            if parsed:
                                pl["coordinate"] = parsed
                        out.append(pl)
                except Exception:
                    # On any error fall back to the stub mirrors.
                    pass
            # Gather candidates from stub store and global mirror.
            candidates: List[dict] = []
            try:
                candidates.extend(self._stub_store)
            except Exception:
                pass
            try:
                if ns is not None:
                    candidates.extend(_GLOBAL_PAYLOADS.get(ns, []))
            except Exception:
                pass
            eps = 1e-6
            for coord in coords:
                try:
                    target = (float(coord[0]), float(coord[1]), float(coord[2]))
                except Exception:
                    continue
                # Collect all matching candidates and choose the most recent by timestamp
                matches: List[dict] = []
                for p in candidates:
                    c = p.get("coordinate")
                    try:
                        if isinstance(c, (list, tuple)) and len(c) >= 3:
                            if all(
                                abs(float(c[i]) - target[i]) <= eps for i in range(3)
                            ):
                                matches.append(p)
                                continue
                        if isinstance(c, str):
                            parsed = _parse_coord_string(c)
                            if parsed and all(
                                abs(parsed[i] - target[i]) <= eps for i in range(3)
                            ):
                                matches.append(p)
                                continue
                    except Exception:
                        continue
                if matches:
                    # choose the payload with the largest timestamp (most recent)
                    def _ts(p: dict) -> float:
                        try:
                            return float(p.get("timestamp") or 0)
                        except Exception:
                            return 0.0

                    matches.sort(key=_ts, reverse=True)
                    out.append(matches[0])
            try:
                logger.debug(
                    "payloads_for_coords: coords=%d candidates=%d out=%d",
                    len(coords),
                    len(candidates),
                    len(out),
                )
            except Exception:
                pass
            return out
        except Exception:
            return out

    def store_from_payload(self, payload: dict, request_id: str | None = None) -> bool:
        """Compatibility helper: store a payload dict into the memory backend.

        Tests and migration scripts call this helper. If the payload contains a
        concrete ``coordinate`` value we mirror it into the in‑process stub and
        global mirrors. Otherwise we fall back to calling :meth:`remember` with
        a generated key based on the payload's task or a timestamp.
        """
        _refresh_builtins_globals()
        try:
            coord = payload.get("coordinate")
            if coord:
                # normalize coordinate to tuple
                try:
                    c = tuple(float(coord[i]) for i in range(3))
                except Exception:
                    c = None
                p2 = dict(payload)
                if c is not None:
                    p2["coordinate"] = c
                with self._lock:
                    try:
                        self._stub_store.append(p2)
                    except Exception:
                        pass
                try:
                    ns = getattr(self.cfg, "namespace", None)
                    if ns is not None:
                        _GLOBAL_PAYLOADS.setdefault(ns, []).append(p2)
                except Exception:
                    pass
                return True
            # No coordinate: fall back to remember with a stable key
            key = payload.get("task") or f"autokey:{int(time.time()*1000)}"
            try:
                self.remember(key, payload, request_id=request_id)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def _remember_sync_persist(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Synchronous persistence implementation used by both sync callers and run_in_executor.

        This mirrors the original HTTP remember logic but centralizes retries and outbox fallback.
        """
        import uuid as _uuid

        if self._http is None:
            try:
                self._record_outbox(
                    "remember",
                    {
                        "coord_key": coord_key,
                        "payload": payload,
                        "request_id": request_id,
                    },
                )
            except Exception:
                pass
            return

        # Enrich payload and compute coord string once
        enriched, uni, compat_hdr = self._compat_enrich_payload(payload, coord_key)
        sc = _stable_coord(f"{uni}::{coord_key}")
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        body = {"coord": coord_str, "payload": enriched, "type": "episodic"}

        rid = request_id or str(_uuid.uuid4())
        rid_hdr = {"X-Request-ID": rid}
        rid_hdr.update(compat_hdr)
        stored = False
        response_payload: Any = None
        if self._http is not None:
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
            try:
                self._record_outbox(
                    "remember",
                    {"coord_key": coord_key, "payload": payload, "request_id": rid},
                )
            except Exception:
                pass
        return server_coord

    async def _aremember_background(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Async background persistence using the AsyncClient; used when remember is called from async contexts."""
        if self._http_async is None:
            # fallback to sync persist in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._remember_sync_persist, coord_key, payload, request_id
            )
            return

        rid = request_id
        rid_hdr = {"X-Request-ID": rid} if rid else {}
        enriched, uni, compat_hdr = self._compat_enrich_payload(payload, coord_key)
        rid_hdr.update(compat_hdr)
        sc = _stable_coord(f"{uni}::{coord_key}")
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        body = {"coord": coord_str, "payload": enriched, "type": "episodic"}
        try:
            ok, response_data = await self._store_http_async(body, rid_hdr)
            if ok and response_data is not None:
                server_coord = _extract_memory_coord(
                    response_data, idempotency_key=rid
                )
                if server_coord:
                    try:
                        payload["coordinate"] = server_coord
                    except Exception:
                        pass
        except Exception:
            # record for later retry
            try:
                self._record_outbox(
                    "remember",
                    {"coord_key": coord_key, "payload": payload, "request_id": rid},
                )
            except Exception:
                pass
