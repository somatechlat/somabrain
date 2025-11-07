"""Memory Client Module for SomaBrain.

The client speaks to the external HTTP memory service used by SomaBrain. When
the service is unavailable it mirrors writes locally and records them in an
outbox for replay. This module is the single gateway for storing, retrieving,
and linking memories; other packages must call into it rather than integrating
with the memory service directly.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import hashlib
import json
import logging
import math
import os
import random
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import Config

try:  # optional dependency, older deployments may not ship shared settings yet
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - legacy layout
    shared_settings = None  # type: ignore

try:  # Import the settings object under a distinct name for strict-mode checks.
    from common.config.settings import settings as _shared_settings
except Exception:  # pragma: no cover - not always available in local runs
    _shared_settings = None  # type: ignore

from somabrain.infrastructure import get_memory_http_endpoint
from somabrain.interfaces.memory import MemoryBackend

# logger for diagnostic output during tests
logger = logging.getLogger(__name__)
debug_memory_client = False
if shared_settings is not None:
    try:
        debug_memory_client = bool(
            getattr(shared_settings, "debug_memory_client", False)
        )
    except Exception:
        debug_memory_client = False
else:
    debug_memory_client = os.getenv("SOMABRAIN_DEBUG_MEMORY_CLIENT") == "1"
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


def _require_memory_enabled() -> bool:
    if shared_settings is not None:
        try:
            return bool(getattr(shared_settings, "require_memory", True))
        except Exception:
            return True
    env_flag = os.getenv("SOMABRAIN_REQUIRE_MEMORY")
    if env_flag is not None:
        try:
            return env_flag.strip().lower() in _TRUE_VALUES
        except Exception:
            return True
    return True


def _http_setting(attr: str, fallback: int) -> int:
    """Fetch HTTP client tuning knobs from shared settings with sane fallback."""

    if shared_settings is not None:
        try:
            value = getattr(shared_settings, attr)
            if value is None:
                raise ValueError("empty")
            return int(value)
        except Exception:
            pass
    return fallback


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
    """Try to derive a coordinate tuple from the memory-service response."""

    if not resp:
        return None

    data = resp
    json_attr = getattr(resp, "json", None)
    if callable(json_attr):
        try:
            data = json_attr()
        except (ValueError, TypeError):
            data = resp

    data_dict = data if isinstance(data, dict) else None

    if data_dict is not None:
        for key in ("coord", "coordinate"):
            value = data_dict.get(key)
            parsed: Optional[Tuple[float, float, float]] = None
            if isinstance(value, str):
                parsed = _parse_coord_string(value)
            elif isinstance(value, (list, tuple)) and len(value) >= 3:
                try:
                    parsed = (float(value[0]), float(value[1]), float(value[2]))
                except (TypeError, ValueError):
                    parsed = None
            if parsed:
                return parsed

        mem_section = data_dict.get("memory")
        if isinstance(mem_section, dict):
            for key in ("coordinate", "coord", "location"):
                value = mem_section.get(key)
                parsed = None
                if isinstance(value, str):
                    parsed = _parse_coord_string(value)
                elif isinstance(value, (list, tuple)) and len(value) >= 3:
                    try:
                        parsed = (float(value[0]), float(value[1]), float(value[2]))
                    except (TypeError, ValueError):
                        parsed = None
                if parsed:
                    return parsed

            mid = mem_section.get("id") or mem_section.get("memory_id")
            if mid is not None:
                try:
                    return _stable_coord(str(mid))
                except (TypeError, ValueError):
                    pass

        mid = data_dict.get("id") or data_dict.get("memory_id")
        if mid is not None:
            try:
                return _stable_coord(str(mid))
            except (TypeError, ValueError):
                pass

    if idempotency_key:
        try:
            return _stable_coord(f"idempotency:{idempotency_key}")
        except (TypeError, ValueError):
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
    - Backend enforcement: If SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS is enabled and neither HTTP nor
        deterministic local recall returns hits, recall() raises instead of silently
        falling back to a blind recent‑payload stub.

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
        # Keep a _mode attribute for compatibility but it is informational only.
        self._mode = "http"
        self._local = None
        # Annotate http clients to help static checkers; actual httpx types
        # are imported locally inside _init_http to avoid heavy top-level
        # imports in some runtime contexts.
        self._http: Optional[Any] = None
        self._http_async: Optional[Any] = None
        # New: path for outbox persistence (default within data dir)
        self._outbox_path = getattr(cfg, "outbox_path", "./data/somabrain/outbox.jsonl")
        # Ensure outbox file exists
        try:
            open(self._outbox_path, "a").close()
        except Exception:
            pass
        # NEW: Ensure the directory for the SQLite DB (if using local mode) exists.
        # MEMORY_DB_PATH is injected via docker‑compose; default to ./data/memory.db.
        if shared_settings is not None:
            try:
                db_path = str(
                    getattr(shared_settings, "memory_db_path", "./data/memory.db")
                )
            except Exception:
                db_path = "./data/memory.db"
        else:
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
        token_value = None
        if self.cfg.http and getattr(self.cfg.http, "token", None):
            token_value = self.cfg.http.token
            # Prefer standard Bearer auth, but include common alternatives for dev services
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
            max_conns = int(os.getenv("SOMABRAIN_HTTP_MAX_CONNS", str(default_max)))
        except Exception:
            max_conns = default_max
        default_keepalive = _http_setting("http_keepalive_connections", 32)
        try:
            keepalive = int(
                os.getenv("SOMABRAIN_HTTP_KEEPALIVE", str(default_keepalive))
            )
        except Exception:
            keepalive = default_keepalive
        default_retries = _http_setting("http_retries", 1)
        try:
            retries = int(os.getenv("SOMABRAIN_HTTP_RETRIES", str(default_retries)))
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
        candidate_base = get_memory_http_endpoint()
        env_base = os.getenv("SOMABRAIN_HTTP_ENDPOINT") or os.getenv(
            "MEMORY_SERVICE_URL"
        )
        if not env_base:
            env_base = candidate_base
        if env_base:
            try:
                env_base = str(env_base).strip()
                if "://" not in env_base and env_base.startswith("/"):
                    pass
                elif "://" not in env_base:
                    env_base = f"http://{env_base}"
                if env_base.endswith("/openapi.json"):
                    env_base = env_base[: -len("/openapi.json")]
            except Exception:
                env_base = None
        base_url = str(getattr(self.cfg.http, "endpoint", "") or "")
        if not base_url and env_base:
            base_url = env_base
        # Hard requirement: if memory is required ensure an endpoint exists.
        require_memory_enabled = _require_memory_enabled()
        if require_memory_enabled and not base_url:
            base_url = get_memory_http_endpoint() or ""
        # Final normalisation: ensure empty string remains empty
        base_url = base_url or ""
        if base_url:
            try:
                os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = base_url
            except Exception:
                pass
        # Fail-fast: do not auto-default inside Docker; require explicit endpoint
        client_kwargs: dict[str, Any] = {
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
        if require_memory_enabled and (self._http is None):
            raise RuntimeError(
                "SOMABRAIN_REQUIRE_MEMORY enforced but no memory service reachable or endpoint unset. Set SOMABRAIN_MEMORY_HTTP_ENDPOINT in the environment."
            )
        # Enforce token presence by mode policy
        mem_auth_required = True
        if shared_settings is not None:
            try:
                mem_auth_required = bool(
                    getattr(shared_settings, "mode_memory_auth_required", True)
                )
            except Exception:
                mem_auth_required = True
        if self._http is not None and mem_auth_required and not token_value:
            # If memory is required, treat missing token as fatal; otherwise warn.
            message = (
                "MEMORY AUTH REQUIRED: missing SOMABRAIN_MEMORY_HTTP_TOKEN for HTTP memory backend. "
                "Set a valid dev/staging/prod token to enable /memories and /memories/search."
            )
            if require_memory_enabled:
                raise RuntimeError(message)
            else:
                try:
                    logger.warning(message)
                except Exception:
                    pass

    def _init_redis(self) -> None:
        # Redis mode removed. Redis-backed behavior should be exposed via the
        # HTTP memory service if required.
        return

    def health(self) -> dict:
        """Best-effort backend health signal for local or http mode."""
        try:
            if self._http:
                # Try common health endpoints in order of preference.
                for path in ("/health", "/healthz", "/readyz"):
                    try:
                        r = self._http.get(path)
                        if int(getattr(r, "status_code", 0) or 0) == 200:
                            return {"http": True}
                    except Exception:
                        # Try next path
                        continue
                return {"http": False}
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

    def _store_http_sync(self, body: dict, headers: dict) -> tuple[bool, Any]:
        if self._http is None:
            return False, None

        coord = str(body.get("coord") or "")
        payload = body.get("payload") or {}
        memory_type = str(body.get("memory_type") or body.get("type") or "episodic")

        payload = {
            "coord": coord,
            "payload": payload,
            "memory_type": memory_type,
        }

        success, _, data = self._http_post_with_retries_sync(
            "/memories", payload, headers
        )
        if success:
            return True, data

        return False, data

    async def _store_http_async(self, body: dict, headers: dict) -> tuple[bool, Any]:
        if self._http_async is None:
            return False, None

        coord = str(body.get("coord") or "")
        payload = body.get("payload") or {}
        memory_type = str(body.get("memory_type") or body.get("type") or "episodic")

        payload = {
            "coord": coord,
            "payload": payload,
            "memory_type": memory_type,
        }

        success, _, data = await self._http_post_with_retries_async(
            "/memories", payload, headers
        )
        if success:
            return True, data

        return False, data

    def _store_bulk_http_sync(
        self, items: List[dict], headers: dict
    ) -> tuple[bool, int, Any]:
        if self._http is None:
            return False, 0, None
        all_ok = True
        responses: List[Any] = []
        for item in items:
            ok, resp = self._store_http_sync(item, headers)
            all_ok = all_ok and ok
            responses.append(resp)
        return all_ok, 200 if all_ok else 207, responses

    async def _store_bulk_http_async(
        self, items: List[dict], headers: dict
    ) -> tuple[bool, int, Any]:
        if self._http_async is None:
            return False, 0, None
        all_ok = True
        responses: List[Any] = []
        for item in items:
            ok, resp = await self._store_http_async(item, headers)
            all_ok = all_ok and ok
            responses.append(resp)
        return all_ok, 200 if all_ok else 207, responses

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

    def _hit_score(self, hit: RecallHit) -> float | None:
        score = hit.score
        if isinstance(score, (int, float)) and not math.isnan(score):
            return float(score)
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        if isinstance(payload, dict):
            alt = payload.get("_score")
            if isinstance(alt, (int, float)) and not math.isnan(alt):
                return float(alt)
        return None

    def _coerce_timestamp_value(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            try:
                if math.isnan(float(value)):
                    return None
            except Exception:
                return None
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                # ISO8601 handling; account for trailing Z
                if text.endswith("Z"):
                    dt = datetime.fromisoformat(text[:-1] + "+00:00")
                else:
                    dt = datetime.fromisoformat(text)
                return dt.timestamp()
            except Exception:
                try:
                    return float(text)
                except Exception:
                    return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.timestamp()
        return None

    def _hit_timestamp(self, hit: RecallHit) -> float | None:
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        candidate_keys = (
            "timestamp",
            "created_at",
            "updated_at",
            "ts",
            "time",
        )
        if isinstance(payload, dict):
            for key in candidate_keys:
                value = payload.get(key)
                ts = self._coerce_timestamp_value(value)
                if ts is not None:
                    return ts
        raw = hit.raw
        if isinstance(raw, dict):
            meta = raw.get("metadata")
            if isinstance(meta, dict):
                for key in candidate_keys:
                    ts = self._coerce_timestamp_value(meta.get(key))
                    if ts is not None:
                        return ts
        return None

    def _prefer_candidate_hit(self, current: RecallHit, candidate: RecallHit) -> bool:
        curr_score = self._hit_score(current)
        cand_score = self._hit_score(candidate)
        if cand_score is not None or curr_score is not None:
            curr_metric = curr_score if curr_score is not None else float("-inf")
            cand_metric = cand_score if cand_score is not None else float("-inf")
            if cand_metric > curr_metric + 1e-9:
                return True
            if cand_metric < curr_metric - 1e-9:
                return False
        curr_ts = self._hit_timestamp(current)
        cand_ts = self._hit_timestamp(candidate)
        if cand_ts is not None and curr_ts is not None:
            if cand_ts > curr_ts + 1e-6:
                return True
            if cand_ts < curr_ts - 1e-6:
                return False
        elif cand_ts is not None:
            return True
        return False

    def _deduplicate_hits(self, hits: List[RecallHit]) -> List[RecallHit]:
        winners: dict[str, RecallHit] = {}
        order: List[str] = []
        for hit in hits:
            ident = self._hit_identity(hit)
            existing = winners.get(ident)
            if existing is None:
                winners[ident] = hit
                order.append(ident)
                continue
            if self._prefer_candidate_hit(existing, hit):
                winners[ident] = hit
        return [winners[idx] for idx in order]

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

    def _memories_search_sync(
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
        universe_value = str(compat_universe or universe or "real")
        headers = {"X-Request-ID": request_id}
        headers.update(compat_headers)

        fetch_limit = max(int(top_k) * 3, 10)
        query_text = str(query or "")
        body = {
            "query": query_text,
            "top_k": fetch_limit,
        }

        success, status, data = self._http_post_with_retries_sync(
            "/memories/search", body, headers
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
        if self._http_async is None:
            return []

        _, compat_universe, compat_headers = self._compat_enrich_payload(
            {"query": query, "universe": universe or "real"}, query
        )
        universe_value = str(compat_universe or universe or "real")
        headers = {"X-Request-ID": request_id}
        headers.update(compat_headers)

        fetch_limit = max(int(top_k) * 3, 10)
        query_text = str(query or "")
        body = {
            "query": query_text,
            "top_k": fetch_limit,
        }

        success, status, data = await self._http_post_with_retries_async(
            "/memories/search", body, headers
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

    def _recency_normalisation(self) -> tuple[float, float]:
        scale = getattr(self.cfg, "recall_recency_time_scale", 60.0)
        if (
            not isinstance(scale, (int, float))
            or not math.isfinite(scale)
            or scale <= 0
        ):
            scale = 60.0
        cap = getattr(self.cfg, "recall_recency_max_steps", 4096.0)
        if not isinstance(cap, (int, float)) or not math.isfinite(cap) or cap <= 0:
            cap = 4096.0
        return float(scale), float(cap)

    def _recency_profile(self) -> tuple[float, float, float, float]:
        scale, cap = self._recency_normalisation()
        sharpness = getattr(self.cfg, "recall_recency_sharpness", 1.2)
        try:
            sharpness = float(sharpness)
        except Exception:
            sharpness = 1.2
        if not math.isfinite(sharpness) or sharpness <= 0:
            sharpness = 1.0
        floor = getattr(self.cfg, "recall_recency_floor", 0.05)
        try:
            floor = float(floor)
        except Exception:
            floor = 0.05
        if not math.isfinite(floor) or floor < 0:
            floor = 0.0
        if floor >= 1.0:
            floor = 0.99
        return scale, cap, sharpness, floor

    def _recency_features(
        self, ts_epoch: float | None, now_ts: float
    ) -> tuple[float | None, float]:
        if ts_epoch is None:
            return None, 1.0
        scale, cap, sharpness, floor = self._recency_profile()
        age_seconds = max(0.0, now_ts - ts_epoch)
        if age_seconds <= 0:
            return 0.0, 1.0
        normalised = age_seconds / max(scale, 1e-6)
        damp_steps = math.log1p(normalised) * sharpness
        recency_steps = min(damp_steps, cap)
        try:
            damp = math.exp(-(normalised**sharpness))
        except Exception:
            damp = 0.0
        boost = max(floor, min(1.0, damp))
        return recency_steps, boost

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except Exception:
            return None
        if not math.isfinite(numeric):
            return None
        return numeric

    @staticmethod
    def _parse_payload_timestamp(raw: Any) -> float | None:
        if raw is None:
            return None
        try:
            if isinstance(raw, (int, float)):
                value = float(raw)
            elif isinstance(raw, str):
                txt = raw.strip()
                if not txt:
                    return None
                try:
                    value = float(txt)
                except ValueError:
                    try:
                        txt_norm = (
                            txt.replace("Z", "+00:00") if txt.endswith("Z") else txt
                        )
                        dt = datetime.fromisoformat(txt_norm)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)
                        return float(dt.timestamp())
                    except Exception:
                        return None
            else:
                return None
        except Exception:
            return None
        if not math.isfinite(value):
            return None
        # Accept millisecond epoch values transparently
        if value > 1e12:
            value /= 1000.0
        return value

    def _extract_cleanup_margin(self, hit: RecallHit) -> float | None:
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        margin = None
        if isinstance(payload, dict):
            margin = payload.get("_cleanup_margin")
            if margin is None:
                margin = payload.get("cleanup_margin")
        if margin is None and isinstance(hit.raw, dict):
            metadata = hit.raw.get("metadata")
            if isinstance(metadata, dict):
                margin = metadata.get("cleanup_margin")
        return self._coerce_float(margin)

    def _density_factor(self, margin: float | None) -> float:
        if margin is None:
            return 1.0
        target = getattr(self.cfg, "recall_density_margin_target", 0.2)
        floor = getattr(self.cfg, "recall_density_margin_floor", 0.6)
        weight = getattr(self.cfg, "recall_density_margin_weight", 0.35)
        try:
            target = float(target)
        except Exception:
            target = 0.2
        if not math.isfinite(target) or target <= 0:
            target = 0.2
        try:
            floor = float(floor)
        except Exception:
            floor = 0.6
        if not math.isfinite(floor) or floor < 0:
            floor = 0.0
        if floor > 1.0:
            floor = 1.0
        try:
            weight = float(weight)
        except Exception:
            weight = 0.35
        if not math.isfinite(weight) or weight < 0:
            weight = 0.0
        if margin >= target:
            return 1.0
        deficit = (target - margin) / target
        penalty = 1.0 - (weight * deficit)
        return max(floor, min(1.0, penalty))

    def _rescore_and_rank_hits(
        self, hits: List[RecallHit], query: str
    ) -> List[RecallHit]:
        if not self._scorer or not self._embedder:
            # Fallback to old logic if scorer is not available
            self._apply_weighting_to_hits(hits)
            return self._rank_hits(hits, query)

        query_vec = self._embedder.embed(query)
        now_ts = datetime.now(timezone.utc).timestamp()

        def _text_of(p: dict) -> str:
            return str(p.get("task") or p.get("fact") or p.get("content") or "").strip()

        scored_hits = []
        for hit in hits:
            payload = hit.payload or {}
            text = _text_of(payload)
            if not text:
                # Cannot score without text to embed, assign a low score
                new_score = 0.0
            else:
                candidate_vec = self._embedder.embed(text)

                # Calculate recency_steps from timestamp
                recency_steps: float | None = None
                recency_boost = 1.0
                ts_epoch = None
                for key in ("timestamp", "ts", "created_at"):
                    if key in payload:
                        ts_epoch = self._parse_payload_timestamp(payload.get(key))
                        if ts_epoch is not None:
                            break
                if ts_epoch is not None:
                    recency_steps, recency_boost = self._recency_features(
                        ts_epoch, now_ts
                    )

                new_score = self._scorer.score(
                    query_vec,
                    candidate_vec,
                    recency_steps=recency_steps,
                    cosine=hit.score,  # Pass original score as cosine hint
                )
                new_score *= recency_boost
                try:
                    payload.setdefault("_recency_steps", recency_steps)
                    payload.setdefault("_recency_boost", recency_boost)
                except Exception:
                    pass

            margin = self._extract_cleanup_margin(hit)
            density_factor = self._density_factor(margin)
            new_score *= density_factor
            if density_factor != 1.0:
                try:
                    payload.setdefault("_density_factor", density_factor)
                except Exception:
                    pass
            new_score = max(0.0, min(1.0, float(new_score)))

            hit.score = new_score
            scored_hits.append(hit)

        # Sort by the new score in descending order
        scored_hits.sort(key=lambda h: h.score or 0.0, reverse=True)
        return scored_hits

    def _apply_weighting_to_hits(self, hits: List[RecallHit]) -> None:
        if not hits:
            return
        weighting_enabled = False
        priors_env = ""
        quality_exp = 1.0
        if shared_settings is not None:
            try:
                weighting_enabled = bool(
                    getattr(shared_settings, "memory_enable_weighting", False)
                )
                priors_env = getattr(shared_settings, "memory_phase_priors", "") or ""
                quality_exp = float(
                    getattr(shared_settings, "memory_quality_exp", 1.0) or 1.0
                )
            except Exception:
                weighting_enabled = False
        else:
            env_toggle = os.getenv("SOMABRAIN_MEMORY_ENABLE_WEIGHTING")
            if env_toggle is not None and env_toggle.lower() in ("1", "true", "yes"):
                weighting_enabled = True
                priors_env = os.getenv("SOMABRAIN_MEMORY_PHASE_PRIORS", "")
                try:
                    quality_exp = float(
                        os.getenv("SOMABRAIN_MEMORY_QUALITY_EXP", "1.0")
                    )
                except Exception:
                    quality_exp = 1.0
        if not weighting_enabled:
            return
        try:
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
                        quality_factor = (qs**quality_exp) if qs > 0 else 0.0
                except Exception:
                    quality_factor = 1.0
                try:
                    payload.setdefault("_weight_factor", phase_factor * quality_factor)
                except Exception:
                    pass
        except Exception:
            return

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
    ) -> Tuple[float, float, float]:
        """Store a memory using a stable coordinate derived from coord_key.

        Ensures required structural keys, and normalizes optional metadata if
        present. Supported optional metadata (all pass‑through if already in
        correct shape): phase, quality_score, domains, reasoning_chain.
        - phase: coerced to lower‑case str.
        - quality_score: clamped into [0, 1].
        - domains: accepted as list[str] or comma/space separated string -> list[str].
        - reasoning_chain: list[str] or single string; stored verbatim.
        """
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
        if shared_settings is not None:
            try:
                fast_ack = bool(getattr(shared_settings, "memory_fast_ack", False))
            except Exception:
                fast_ack = False
        else:
            fast_ack = os.getenv("SOMABRAIN_MEMORY_FAST_ACK", "0") in (
                "1",
                "true",
                "True",
            )
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

        records = list(items)
        if not records:
            return []

        prepared: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []

        for coord_key, payload in records:
            enriched, universe, _ = self._compat_enrich_payload(payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
            enriched_payload = dict(enriched)
            enriched_payload.setdefault("coordinate", coord)
            enriched_payload.setdefault("memory_type", "episodic")
            memory_type = str(
                enriched_payload.get("memory_type")
                or enriched_payload.get("type")
                or "episodic"
            )
            body = {
                "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                "payload": enriched_payload,
                "memory_type": memory_type,
                "type": memory_type,
            }
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "universe": universe,
                }
            )

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
    ) -> Tuple[float, float, float]:
        """Async variant of remember for HTTP mode; falls back to thread executor.

        Returns the chosen 3‑tuple coord (server‑preferred if configured), or the
        locally computed coord. On failure, falls back to running the sync remember
        in a thread executor.
        """
        # Mirror locally first for read-your-writes semantics (optional)
        # Strict real mode: no local mirroring, only HTTP service
        p2: dict[str, Any] | None = None
        if self._http_async is not None:
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
        # Fallback: run the synchronous remember in a thread executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.remember, coord_key, payload)

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Async companion to :meth:`remember_bulk` using the async HTTP client."""

        records = list(items)
        if not records:
            return []

        prepared: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []

        for coord_key, payload in records:
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
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "universe": universe,
                }
            )

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
        """Retrieve memories relevant to the query using the HTTP memory service."""
        # Enforce memory requirement: do not allow fallback when required
        memory_required = _require_memory_enabled()
        if memory_required and self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED: HTTP memory backend not available (set SOMABRAIN_MEMORY_HTTP_ENDPOINT)."
            )
        # Prefer HTTP recall if available
        if self._http is not None:
            rid = request_id or str(uuid.uuid4())
            return self._http_recall_aggregate_sync(
                query, top_k, universe or "real", rid
            )
        if memory_required:
            raise RuntimeError(
                "MEMORY SERVICE UNAVAILABLE: No HTTP backend configured and stub fallback disabled."
            )
        return []

    def recall_with_scores(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Recall memories including similarity scores via the `/memories/search` endpoint."""

        if self._http is not None:
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
        if self._http_async is not None:
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

        if self._http_async is not None:
            rid = request_id or str(uuid.uuid4())
            hits = await self._http_recall_aggregate_async(
                query, top_k, universe or "real", rid
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
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE UNAVAILABLE: link requires an HTTP memory backend."
            )
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
        except Exception as exc:
            logger.debug("link request failed: %r", exc)

    async def alink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        """Async helper mirroring :meth:`link` behaviour."""
        if self._http_async is not None:
            rid = request_id or str(uuid.uuid4())
            headers = {"X-Request-ID": rid}
            try:
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
                return
            except Exception as exc:
                logger.debug("async link request failed: %r", exc)

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
        """List outgoing edges with metadata from the memory service."""

        if self._http is None:
            if _require_memory_enabled():
                raise RuntimeError(
                    "MEMORY SERVICE UNAVAILABLE: links_from requires an HTTP memory backend."
                )
            return []

        unlimited = int(limit) <= 0
        max_items = None if unlimited else int(limit)
        out: List[dict] = []
        try:
            body = {
                "from_coord": [float(start[0]), float(start[1]), float(start[2])],
                "type": str(type_filter) if type_filter else None,
                "limit": int(limit),
            }
            resp = self._http.post("/neighbors", json=body)
            data = self._response_json(resp)
            if isinstance(data, dict):
                edges = data.get("edges") or data.get("results") or []
            else:
                edges = []
            for edge in edges:
                try:
                    raw_from = edge.get("from") or start
                    raw_to = edge.get("to") or start
                    if isinstance(raw_from, (list, tuple)) and len(raw_from) >= 3:
                        from_vec = (
                            float(raw_from[0]),
                            float(raw_from[1]),
                            float(raw_from[2]),
                        )
                    else:
                        from_vec = (
                            float(start[0]),
                            float(start[1]),
                            float(start[2]),
                        )
                    if isinstance(raw_to, (list, tuple)) and len(raw_to) >= 3:
                        to_vec = (
                            float(raw_to[0]),
                            float(raw_to[1]),
                            float(raw_to[2]),
                        )
                    else:
                        to_vec = (
                            float(start[0]),
                            float(start[1]),
                            float(start[2]),
                        )
                    if type_filter and edge.get("type") != type_filter:
                        continue
                    out.append(
                        {
                            "from": from_vec,
                            "to": to_vec,
                            "type": edge.get("type"),
                            "weight": float(edge.get("weight", 1.0)),
                        }
                    )
                    if (
                        not unlimited
                        and max_items is not None
                        and len(out) >= max_items
                    ):
                        break
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("links_from request failed: %r", exc)
            return []

        return out if unlimited else out[:max_items]

    def unlink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        """Remove a directed edge from the memory graph."""

        if self._http is None:
            if _require_memory_enabled():
                raise RuntimeError(
                    "MEMORY SERVICE UNAVAILABLE: unlink requires an HTTP memory backend."
                )
            return False

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        body = {
            "from_coord": [
                float(from_coord[0]),
                float(from_coord[1]),
                float(from_coord[2]),
            ],
            "to_coord": [
                float(to_coord[0]),
                float(to_coord[1]),
                float(to_coord[2]),
            ],
            "type": link_type,
        }

        success, _, _ = self._http_post_with_retries_sync("/unlink", body, headers)
        if success:
            return True

        try:
            self._record_outbox(
                "unlink",
                {
                    "from_coord": body["from_coord"],
                    "to_coord": body["to_coord"],
                    "type": link_type,
                    "request_id": rid,
                },
            )
        except Exception:
            pass
        return False

    async def aunlink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        """Async companion to :meth:`unlink`."""

        if self._http_async is not None:
            rid = request_id or str(uuid.uuid4())
            headers = {"X-Request-ID": rid}
            body = {
                "from_coord": [
                    float(from_coord[0]),
                    float(from_coord[1]),
                    float(from_coord[2]),
                ],
                "to_coord": [
                    float(to_coord[0]),
                    float(to_coord[1]),
                    float(to_coord[2]),
                ],
                "type": link_type,
            }
            success, _, _ = await self._http_post_with_retries_async(
                "/unlink", body, headers
            )
            if success:
                return True

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.unlink(
                from_coord,
                to_coord,
                link_type=link_type,
                request_id=request_id,
            ),
        )

    def prune_links(
        self,
        coord: tuple[float, float, float],
        *,
        weight_below: float | None = None,
        max_degree: int | None = None,
        type_filter: str | None = None,
        request_id: str | None = None,
    ) -> int:
        """Prune outgoing edges using the remote memory service."""

        if self._http is None:
            if _require_memory_enabled():
                raise RuntimeError(
                    "MEMORY SERVICE UNAVAILABLE: prune_links requires an HTTP memory backend."
                )
            return 0

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        body = {
            "from_coord": [float(coord[0]), float(coord[1]), float(coord[2])],
            "weight_below": weight_below,
            "max_degree": max_degree,
            "type": type_filter,
        }
        success, _, data = self._http_post_with_retries_sync("/prune", body, headers)
        if success and isinstance(data, dict):
            try:
                removed = int(data.get("removed") or data.get("count") or 0)
            except Exception:
                removed = 0
            return removed

        try:
            self._record_outbox(
                "prune_links",
                {
                    "from_coord": body["from_coord"],
                    "weight_below": weight_below,
                    "max_degree": max_degree,
                    "type": type_filter,
                    "request_id": rid,
                },
            )
        except Exception:
            pass
        return 0

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
            rid = request_id or str(uuid.uuid4())
            headers = {"X-Request-ID": rid}
            body = {
                "from_coord": [float(coord[0]), float(coord[1]), float(coord[2])],
                "weight_below": weight_below,
                "max_degree": max_degree,
                "type": type_filter,
            }
            success, _, data = await self._http_post_with_retries_async(
                "/prune", body, headers
            )
            if success and isinstance(data, dict):
                try:
                    return int(data.get("removed") or data.get("count") or 0)
                except Exception:
                    return 0

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.prune_links(
                coord,
                weight_below=weight_below,
                max_degree=max_degree,
                type_filter=type_filter,
                request_id=request_id,
            ),
        )

    # --- Graph Analytics Helpers ---
    def degree(self, node: Tuple[float, float, float]) -> int:
        """Return the number of outgoing edges from *node* via the remote service."""

        try:
            neighbors = self.links_from(node, limit=1024)
            return len(neighbors)
        except Exception:
            return 0

    def centrality(self, node: Tuple[float, float, float]) -> float:
        """Approximate degree centrality using remote neighbors only."""

        try:
            neighbors = self.links_from(node, limit=1024)
            if not neighbors:
                return 0.0
            deg = float(len(neighbors))
            unique_nodes: set[Tuple[float, float, float]] = {
                (float(node[0]), float(node[1]), float(node[2]))
            }
            for edge in neighbors:
                to_coord = edge.get("to")
                if isinstance(to_coord, (list, tuple)) and len(to_coord) >= 3:
                    unique_nodes.add(
                        (
                            float(to_coord[0]),
                            float(to_coord[1]),
                            float(to_coord[2]),
                        )
                    )
            total = len(unique_nodes)
            if total <= 1:
                return 0.0
            return deg / float(total - 1)
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
        """Return a list of coordinates reachable from *starts* within *depth* hops."""
        try:
            if not starts:
                return []
            seen: set[Tuple[float, float, float]] = set()
            # build explicit 3-tuples for static typing
            frontier = [(float(s[0]), float(s[1]), float(s[2])) for s in starts]
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

        The method performs a best-effort call to the remote ``/payloads`` endpoint.
        It returns payload dictionaries that include a ``coordinate`` field when
        available. When the memory service is unavailable the function returns an
        empty list (or raises in strict mode).
        """

        if not coords:
            return []

        if self._http is None:
            if _require_memory_enabled():
                raise RuntimeError(
                    "MEMORY SERVICE UNAVAILABLE: payloads_for_coords requires an HTTP memory backend."
                )
            return []

        coord_strs = [f"{c[0]},{c[1]},{c[2]}" for c in coords]
        body: dict[str, Any] = {"coords": coord_strs}
        if universe:
            body["universe"] = universe

        try:
            resp = self._http.post("/payloads", json=body)
            data = self._response_json(resp)
        except Exception as exc:
            logger.debug("payloads_for_coords request failed: %r", exc)
            return []

        out: List[dict] = []
        if isinstance(data, dict):
            entries = data.get("payloads") or data.get("results") or []
            if isinstance(entries, list):
                for entry in entries:
                    payload = entry.get("payload") if isinstance(entry, dict) else entry
                    if not isinstance(payload, dict):
                        continue
                    coord_value = None
                    if isinstance(entry, dict):
                        coord_value = entry.get("coord") or entry.get("coordinate")
                    if coord_value is None:
                        coord_value = payload.get("coordinate")
                    parsed_coord: Tuple[float, float, float] | None = None
                    if isinstance(coord_value, str):
                        parsed_coord = _parse_coord_string(coord_value)
                    elif (
                        isinstance(coord_value, (list, tuple)) and len(coord_value) >= 3
                    ):
                        try:
                            parsed_coord = (
                                float(coord_value[0]),
                                float(coord_value[1]),
                                float(coord_value[2]),
                            )
                        except Exception:
                            parsed_coord = None
                    if parsed_coord is not None:
                        payload["coordinate"] = parsed_coord
                    out.append(payload)
        return out

    def store_from_payload(self, payload: dict, request_id: str | None = None) -> bool:
        """Compatibility helper: store a payload dict into the memory backend.

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
                try:
                    self._record_outbox(
                        "store_from_payload",
                        {
                            "coord": body["coord"],
                            "payload": payload,
                            "request_id": rid,
                        },
                    )
                except Exception:
                    pass
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
            return None

        # Enrich payload and compute coord string once
        enriched, uni, compat_hdr = self._compat_enrich_payload(payload, coord_key)
        sc = _stable_coord(f"{uni}::{coord_key}")
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        memory_type = str(
            enriched.get("memory_type") or enriched.get("type") or "episodic"
        )
        body = {
            "coord": coord_str,
            "payload": enriched,
            "memory_type": memory_type,
            "type": memory_type,
        }

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
        memory_type = str(
            enriched.get("memory_type") or enriched.get("type") or "episodic"
        )
        body = {
            "coord": coord_str,
            "payload": enriched,
            "memory_type": memory_type,
            "type": memory_type,
        }
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
            # record for later retry
            try:
                self._record_outbox(
                    "remember",
                    {"coord_key": coord_key, "payload": payload, "request_id": rid},
                )
            except Exception:
                pass


# NOTE: MemoryClient already implements the required methods used by MemoryService.
# Adding a Protocol-based alias for type checkers helps during the refactor.
MemoryClientType: type = MemoryBackend  # type: ignore[misc]
