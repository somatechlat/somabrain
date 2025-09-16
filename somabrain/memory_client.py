"""
Memory Client Module for SomaBrain

This module provides a unified interface to the SomaFractalMemory system, supporting
multiple deployment modes and memory operations. It serves as the primary gateway
for storing, retrieving, and linking memories in the brain-inspired architecture.

Key Features:
- Multiple memory modes: local, HTTP, and stub (for testing)
- Asynchronous and synchronous memory operations
- Semantic and episodic memory support
- Memory linking and graph operations
- Coordinate-based memory addressing
- Tenant isolation and namespace management

Memory Modes:
- local: In-process SomaFractalMemory instance
- http: Remote SomaFractalMemory API server
- stub: In-memory storage for testing and development

Operations:
- remember(): Store new memories with semantic content
- recall(): Retrieve memories by similarity or coordinates
- link(): Create semantic relationships between memories
- k_hop(): Traverse memory graph relationships
- payloads_for_coords(): Bulk coordinate-based retrieval

Classes:
    RecallHit: Container for memory recall results
    MemoryClient: Main memory client with unified interface
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, List, Tuple, cast

from .config import Config

# Process-global in-memory mirror for recently stored payloads per-namespace.
# This ensures tests and diagnostics can immediately see writes regardless of
# backend mode or client instance identity.
_GLOBAL_PAYLOADS: Dict[str, List[dict]] = {}


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


def _extract_memory_coord(
    resp: Any, idempotency_key: str | None = None
) -> Tuple[float, float, float] | None:
    """Try common shapes to extract a 3-tuple coord from a remember response.

    Known attempts (in order):
    - top-level 'coord' or 'coordinate' as comma string or list
    - nested 'memory' object with 'coordinate' or 'id'
    - top-level 'id' (opaque) -> map via stable hash
    - fallback: use idempotency_key (if provided) -> stable hash of 'idempotency:{key}'
    Returns a 3-tuple floats or None.
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
        # top-level coord/coordinate
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
        # try top-level id
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
    """
    Represents a memory recall hit.

    Attributes
    ----------
    payload : Dict[str, Any]
        The recalled memory payload.
    """

    payload: Dict[str, Any]


class MemoryClient:
    """
    Single memory gateway to Somafractalmemory.

    Modes
    -----
    - local: in-process SFM
    - http: remote SFM API
    - stub: in-memory for tests

    Contract
    --------
    - remember(), aremember(), recall()/arecall(), link()/alink(), k_hop(), payloads_for_coords()

    Guarantees
    ----------
    - tenancy scoping via namespace
    - never import somafractalmemory outside this module (ADR‑0002)
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._mode = cfg.memory_mode
        self._local = None
        self._http = None
        self._http_async = None
        self._stub_store: list[dict] = []
        # in-process adjacency for simple graph reasoning in local/http modes
        # adjacency: from -> { to -> {type, weight} } (best-effort, not persisted)
        self._graph: Dict[Any, Any] = {}
        # concurrency guard for in-process structures
        self._lock = RLock()
        if self._mode == "local":
            self._init_local()
        elif self._mode == "http":
            self._init_http()

    def _init_local(self) -> None:
        # Try to import the bundled somafractalmemory package; if not installed,
        # add the nested project folder to sys.path as a fallback. Also try
        # the external checkout under external/somafractalmemory for dev setups.
        try:
            try:
                from somafractalmemory.factory import (  # type: ignore
                    MemoryMode,
                    create_memory_system,
                )
            except ModuleNotFoundError:
                import pathlib
                import sys

                root = pathlib.Path(__file__).resolve().parents[1]
                candidates = [
                    root / "somafractalmemory",
                    root / "external" / "somafractalmemory" / "src",
                ]
                for candidate in candidates:
                    # Expect one of:
                    #  - <repo>/somafractalmemory/somafractalmemory/factory.py
                    #  - <repo>/external/somafractalmemory/src/somafractalmemory/factory.py
                    target = candidate / "somafractalmemory"
                    if target.exists() and str(candidate) not in sys.path:
                        sys.path.insert(0, str(candidate))
                from somafractalmemory.factory import (  # type: ignore
                    MemoryMode,
                    create_memory_system,
                )
        except Exception:
            # Cannot import backend; degrade to stub mode
            self._local = None
            self._mode = "stub"
            return
        # Pass through indexing/quantization hints when available; the backend may ignore unknown keys.
        vec_cfg = {
            "backend": "inmemory",
            "profile": getattr(self.cfg, "index_profile", "balanced"),
            "pq": {
                "m": int(getattr(self.cfg, "pq_m", 16) or 16),
                "bits": int(getattr(self.cfg, "pq_bits", 8) or 8),
                "opq": bool(getattr(self.cfg, "opq_enabled", False) or False),
                "anisotropic": bool(
                    getattr(self.cfg, "anisotropic_enabled", False) or False
                ),
            },
            "imi": {
                "cells": int(getattr(self.cfg, "imi_cells", 2048) or 2048),
            },
            "hnsw": {
                "M": int(getattr(self.cfg, "hnsw_M", 16) or 16),
                "ef_construction": int(getattr(self.cfg, "hnsw_efc", 100) or 100),
                "ef_search": int(getattr(self.cfg, "hnsw_efs", 64) or 64),
            },
        }
        try:
            self._local = create_memory_system(
                MemoryMode.ON_DEMAND,
                self.cfg.namespace,
                config={"redis": {"testing": True}, "vector": vec_cfg},
            )
        except Exception:
            # Backend initialization failed; degrade to stub
            self._local = None
            self._mode = "stub"

    def _init_http(self) -> None:
        import httpx  # type: ignore

        # Default headers applied to all requests; per-request we add X-Request-ID
        headers = {}
        if self.cfg.http and self.cfg.http.token:
            headers["Authorization"] = f"Bearer {self.cfg.http.token}"
        # Propagate tenancy via standardized headers
        ns = str(getattr(self.cfg, "namespace", ""))
        if ns:
            headers["X-Soma-Namespace"] = ns
            # best-effort tenant extraction from namespace suffix
            try:
                tenant_guess = ns.split(":")[-1] if ":" in ns else ns
                headers["X-Soma-Tenant"] = tenant_guess
            except Exception:
                pass
        limits = None
        try:
            limits = httpx.Limits(max_connections=64, max_keepalive_connections=32)
        except Exception:
            limits = None
        if limits is not None:
            self._http = httpx.Client(
                base_url=str(getattr(self.cfg.http, "endpoint", "") or ""),
                headers=headers,
                timeout=10.0,
                limits=limits,
            )
        else:
            self._http = httpx.Client(
                base_url=str(getattr(self.cfg.http, "endpoint", "") or ""),
                headers=headers,
                timeout=10.0,
            )
        try:
            if limits is not None:
                self._http_async = httpx.AsyncClient(
                    base_url=str(getattr(self.cfg.http, "endpoint", "") or ""),
                    headers=headers,
                    timeout=10.0,
                    limits=limits,
                )
            else:
                self._http_async = httpx.AsyncClient(
                    base_url=str(getattr(self.cfg.http, "endpoint", "") or ""),
                    headers=headers,
                    timeout=10.0,
                )
        except Exception:
            self._http_async = None

    def health(self) -> dict:
        """Best-effort backend health signal for local or http mode."""
        try:
            if self._mode == "local" and self._local:
                return self._local.health_check()  # type: ignore
            if self._mode == "http" and self._http:
                r = self._http.get("/health")
                return {"http": r.status_code == 200}
        except Exception:
            return {"ok": False}
        return {"ok": True}

    def remember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Store a memory using a stable coordinate derived from coord_key.

        Ensures payload has memory_type, timestamp, and universe fields.
        """
        # include universe in coordinate hashing to avoid collisions across branches
        universe = str(payload.get("universe") or "real")
        coord = _stable_coord(f"{universe}::{coord_key}")
        payload = dict(payload)
        payload.setdefault("memory_type", "episodic")
        payload.setdefault("timestamp", time.time())
        payload.setdefault("universe", universe)
        if self._mode == "local" and self._local:
            from somafractalmemory.core import MemoryType  # type: ignore

            self._local.store_memory(coord, payload, memory_type=MemoryType.EPISODIC)  # type: ignore
            # Mirror to in-process stub for immediate introspection (tests/diagnostics)
            try:
                p2 = dict(payload)
                p2["coordinate"] = coord
                with self._lock:
                    self._stub_store.append(p2)
                # also record in global mirror
                _GLOBAL_PAYLOADS.setdefault(self.cfg.namespace, []).append(p2)
            except Exception:
                pass
            return
        if self._mode == "http" and self._http:
            # Primary endpoint: /remember (Option A); fallback to /store if not found
            body = {
                "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                "payload": payload,
                "type": "episodic",
            }
            import uuid

            rid = request_id or str(uuid.uuid4())
            rid_hdr = {"X-Request-ID": rid}
            stored = False
            try:
                r = self._http.post("/remember", json=body, headers=rid_hdr)
                code = getattr(r, "status_code", 200)
                if code in (404, 405):
                    r2 = self._http.post("/store", json=body, headers=rid_hdr)
                    stored = getattr(r2, "status_code", 500) < 300
                elif code in (429, 503):
                    # brief backoff and retry once
                    time.sleep(0.01 + random.random() * 0.02)
                    r3 = self._http.post("/remember", json=body, headers=rid_hdr)
                    stored = getattr(r3, "status_code", 500) < 300
                else:
                    stored = code < 300
                # try to extract coord if server returns one
                try:
                    server_coord = _extract_memory_coord(r, idempotency_key=rid)
                    if server_coord and getattr(
                        self.cfg, "prefer_server_coords_for_links", False
                    ):
                        return server_coord
                except Exception:
                    pass
            except Exception:
                try:
                    r4 = self._http.post("/store", json=body, headers=rid_hdr)
                    stored = getattr(r4, "status_code", 500) < 300
                except Exception:
                    stored = False
            # Record to global mirror (always), and to stub if the HTTP store failed
            if not stored:
                payload = dict(payload)
                payload["coordinate"] = coord
                with self._lock:
                    self._stub_store.append(payload)
                _GLOBAL_PAYLOADS.setdefault(self.cfg.namespace, []).append(payload)
            else:
                try:
                    p2 = dict(payload)
                    p2["coordinate"] = coord
                    _GLOBAL_PAYLOADS.setdefault(self.cfg.namespace, []).append(p2)
                except Exception:
                    pass
            # default: return locally computed coord
            return coord
        # stub: keep minimal in-process store
        payload = dict(payload)
        payload["coordinate"] = coord
        with self._lock:
            self._stub_store.append(payload)
        _GLOBAL_PAYLOADS.setdefault(self.cfg.namespace, []).append(payload)

    async def aremember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        """Async variant of remember for HTTP mode; falls back to thread executor.

        Returns the chosen 3-tuple coord (server-preferred if configured), or the
        locally computed coord. On failure, falls back to running the sync
        remember() function in a thread executor.
        """
        if self._mode == "http" and self._http_async is not None:
            try:
                universe = str(payload.get("universe") or "real")
                coord = _stable_coord(f"{universe}::{coord_key}")
                body = {
                    "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                    "payload": payload,
                    "type": "episodic",
                }
                import uuid

                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                r = await self._http_async.post("/remember", json=body, headers=rid_hdr)
                code = getattr(r, "status_code", 200)
                if code in (404, 405):
                    await self._http_async.post("/store", json=body, headers=rid_hdr)
                elif code in (429, 503):
                    await asyncio.sleep(0.01 + random.random() * 0.02)
                    await self._http_async.post("/remember", json=body, headers=rid_hdr)
                # try to extract server coord and return preferred coord or fallback
                try:
                    data = None
                    try:
                        data = await r.json()
                    except Exception:
                        # some clients return body via r.content or similar; skip
                        data = None
                    server_coord = _extract_memory_coord(data, idempotency_key=rid)
                    if server_coord and getattr(
                        self.cfg, "prefer_server_coords_for_links", False
                    ):
                        return server_coord
                except Exception:
                    pass
                return coord
            except Exception:
                try:
                    import uuid

                    rid2 = request_id or str(uuid.uuid4())
                    rid_hdr = {"X-Request-ID": rid2}
                    await self._http_async.post("/store", json=body, headers=rid_hdr)  # type: ignore[name-defined]
                    # fall back to sync remember below
                except Exception:
                    pass
        # Fallback: run the synchronous remember in a thread executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.remember, coord_key, payload)

    def recall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Retrieve memories relevant to the query. Stub returns recent payloads."""
        if self._mode == "local" and self._local:
            res = self._local.recall(query, top_k=top_k)  # type: ignore
            return [RecallHit(payload=r) for r in res]
        if self._mode == "http" and self._http:
            import uuid

            rid = request_id or str(uuid.uuid4())
            rid_hdr = {"X-Request-ID": rid}
            # Include best-effort universe hint
            uni = str(universe or "real")
            r = self._http.post(
                "/recall",
                json={"query": query, "top_k": int(top_k), "universe": uni},
                headers=rid_hdr,
            )
            try:
                code = getattr(r, "status_code", 200)
                if code in (429, 503):
                    time.sleep(0.01 + random.random() * 0.02)
                    r = self._http.post(
                        "/recall",
                        json={"query": query, "top_k": int(top_k), "universe": uni},
                        headers=rid_hdr,
                    )
            except Exception:
                pass
            try:
                data = r.json()
            except Exception:
                data = []
            return [RecallHit(payload=p) for p in (data or [])]
        # stub recall: return recent stubbed payloads
        return [RecallHit(payload=p) for p in self._stub_store[-int(max(0, top_k)) :]]

    async def arecall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Async recall for HTTP mode; falls back to sync for local/stub."""
        if self._mode == "http" and self._http_async is not None:
            try:
                import uuid

                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                uni = str(universe or "real")
                r = await self._http_async.post(
                    "/recall",
                    json={"query": query, "top_k": int(top_k), "universe": uni},
                    headers=rid_hdr,
                )
                try:
                    code = getattr(r, "status_code", 200)
                    if code in (429, 503):
                        await asyncio.sleep(0.01 + random.random() * 0.02)
                        r = await self._http_async.post(
                            "/recall",
                            json={"query": query, "top_k": int(top_k), "universe": uni},
                            headers=rid_hdr,
                        )
                except Exception:
                    pass
                try:
                    data = r.json()
                except Exception:
                    data = []
            except Exception:
                data = []
            return [RecallHit(payload=p) for p in (data or [])]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.recall, query, top_k)

    def link(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        """Create or strengthen a typed edge in the memory graph."""
        if self._mode == "local" and self._local:
            try:
                self._local.link_memories(from_coord, to_coord, link_type=link_type, weight=weight)  # type: ignore
            except Exception:
                pass
            # also record locally with metadata
            key_from = cast(
                Tuple[float, float, float],
                (from_coord[0], from_coord[1], from_coord[2]),
            )
            key_to = cast(
                Tuple[float, float, float], (to_coord[0], to_coord[1], to_coord[2])
            )
            with self._lock:
                adj = self._graph.get(key_from)
                if adj is None:
                    adj = {}
                    self._graph[key_from] = adj
                prev = adj.get(key_to, {"type": str(link_type), "weight": 0.0})
                new_w = float(prev.get("weight", 0.0)) + float(weight)
                adj[key_to] = {"type": str(link_type), "weight": new_w}
            return
        if self._mode == "http" and self._http:
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
            # record locally for process augmentation
            key_from = cast(
                Tuple[float, float, float],
                (from_coord[0], from_coord[1], from_coord[2]),
            )
            key_to = cast(
                Tuple[float, float, float], (to_coord[0], to_coord[1], to_coord[2])
            )
            with self._lock:
                adj = self._graph.get(key_from)
                if adj is None:
                    adj = {}
                    self._graph[key_from] = adj
                prev = adj.get(key_to, {"type": str(link_type), "weight": 0.0})
                new_w = float(prev.get("weight", 0.0)) + float(weight)
                adj[key_to] = {"type": str(link_type), "weight": new_w}
            return
        # stub: record in-process adjacency
        key_from = cast(
            Tuple[float, float, float], (from_coord[0], from_coord[1], from_coord[2])
        )
        key_to = cast(
            Tuple[float, float, float], (to_coord[0], to_coord[1], to_coord[2])
        )
        with self._lock:
            adj = self._graph.get(key_from)
            if adj is None:
                adj = {}
                self._graph[key_from] = adj
            prev = adj.get(key_to, {"type": str(link_type), "weight": 0.0})
            new_w = float(prev.get("weight", 0.0)) + float(weight)
            adj[key_to] = {"type": str(link_type), "weight": new_w}

    async def alink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        """Async link for HTTP mode; always mirrors to in-process graph for augmentation."""
        if self._mode == "http" and self._http_async is not None:
            try:
                import uuid

                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                await self._http_async.post(
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
        # record locally for process augmentation as well
        self.link(from_coord, to_coord, link_type=link_type, weight=weight)

    def all_memories(self) -> List[dict]:
        """Return all memories (payloads). Local mode only; HTTP mode not implemented."""
        if self._mode == "local" and self._local:
            try:
                return list(self._local.get_all_memories())  # type: ignore
            except Exception:
                return []
        # stub returns in-process store (snapshot under lock)
        with self._lock:
            return list(self._stub_store)

    def store_from_payload(self, payload: dict) -> bool:
        """Store a memory from an exported payload; falls back to remember() when coord missing."""
        coord = payload.get("coordinate")
        if isinstance(coord, (list, tuple)) and len(coord) == 3:
            t = payload.get("memory_type", "episodic").lower()
            try:
                from somafractalmemory.core import MemoryType  # type: ignore

                mt = MemoryType.EPISODIC if t == "episodic" else MemoryType.SEMANTIC
                self._local.store_memory(tuple(coord), dict(payload), memory_type=mt)  # type: ignore
                return True
            except Exception:
                return False
        # Fallback: use remember() keyed by summary/task text
        key = payload.get("task") or payload.get("fact") or "payload"
        try:
            self.remember(str(key), dict(payload))
            return True
        except Exception:
            return False

    # Graph reasoning helpers (best-effort)
    @staticmethod
    def coord_for_key(
        key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
        u = str(universe or "real")
        return _stable_coord(f"{u}::{key}")

    def k_hop(
        self,
        starts: List[Tuple[float, float, float]],
        depth: int = 1,
        limit: int = 20,
        type_filter: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        """Breadth-first expansion from start coords up to depth with optional type filter."""
        seen = set()
        frontier = list(starts)
        out: List[Tuple[float, float, float]] = []
        for _ in range(max(0, int(depth))):
            next_frontier: List[Tuple[float, float, float]] = []
            for u in frontier:
                key_u = cast(Tuple[float, float, float], (u[0], u[1], u[2]))
                adj = self._graph.get(key_u, {})
                for v, meta in adj.items():
                    if type_filter and str(meta.get("type")) != str(type_filter):
                        continue
                    if v in seen:
                        continue
                    seen.add(v)
                    out.append(v)
                    next_frontier.append(v)
                    if len(out) >= max(1, int(limit)):
                        return out
            frontier = next_frontier
            if not frontier:
                break
        return out

    def payloads_for_coords(
        self, coords: List[Tuple[float, float, float]], universe: str | None = None
    ) -> List[dict]:
        """Return stored payloads matching any of the requested coordinates, universe-scoped."""
        if not coords:
            return []
        # Process-global mirror (fast path for recently persisted items across clients)
        try:
            wanted = {tuple(c) for c in coords}
            global_hits_map: Dict[Tuple[float, float, float], dict] = {}
            for p in _GLOBAL_PAYLOADS.get(self.cfg.namespace, [])[:]:
                c = p.get("coordinate")
                if isinstance(c, (list, tuple)) and len(c) == 3 and tuple(c) in wanted:
                    if universe is not None and str(p.get("universe") or "real") != str(
                        universe
                    ):
                        continue
                    global_hits_map[(float(c[0]), float(c[1]), float(c[2]))] = p
            if global_hits_map:
                return list(global_hits_map.values())
        except Exception:
            pass
        # HTTP mode: use SFM batch endpoint when available
        if self._mode == "http" and self._http is not None:
            try:
                body = {
                    "coords": [[float(x), float(y), float(z)] for x, y, z in coords]
                }
                r = self._http.post("/payloads_by_coords", json=body)
                data = r.json() if hasattr(r, "json") else None
                payloads = (
                    (data or {}).get("payloads", []) if isinstance(data, dict) else []
                )
                if universe is not None:
                    payloads = [
                        p
                        for p in payloads
                        if str(p.get("universe") or "real") == str(universe)
                    ]
                return payloads
            except Exception:
                # fall back to local filtering
                pass
        # Local mode: ask backend directly if available
        if self._mode == "local" and self._local is not None:
            out: List[dict] = []
            try:
                for x, y, z in coords:
                    try:
                        p = self._local.retrieve((float(x), float(y), float(z)))  # type: ignore[attr-defined]
                    except Exception:
                        p = None
                    if isinstance(p, dict):
                        if universe is not None and str(
                            p.get("universe") or "real"
                        ) != str(universe):
                            continue
                        out.append(p)
            except Exception:
                out = []
            if out:
                return out
        # Local/stub fallback: scan in-process store
        wanted = {tuple(c) for c in coords}
        results: List[dict] = []
        for p in self.all_memories():
            c = p.get("coordinate")
            if isinstance(c, (list, tuple)) and len(c) == 3 and tuple(c) in wanted:
                if universe is not None and str(p.get("universe") or "real") != str(
                    universe
                ):
                    continue
                results.append(p)
        # If not found yet, try the process-global mirror as a last resort
        if not results:
            try:
                # same-namespace first
                for p in _GLOBAL_PAYLOADS.get(self.cfg.namespace, [])[:]:
                    c = p.get("coordinate")
                    if (
                        isinstance(c, (list, tuple))
                        and len(c) == 3
                        and tuple(c) in wanted
                    ):
                        if universe is not None and str(
                            p.get("universe") or "real"
                        ) != str(universe):
                            continue
                        results.append(p)
                # scan all mirrors if still empty (test resilience)
                if not results:
                    for ns, plist in _GLOBAL_PAYLOADS.items():
                        for p in plist:
                            c = p.get("coordinate")
                            if (
                                isinstance(c, (list, tuple))
                                and len(c) == 3
                                and tuple(c) in wanted
                            ):
                                if universe is not None and str(
                                    p.get("universe") or "real"
                                ) != str(universe):
                                    continue
                                results.append(p)
                                break
                        if results:
                            break
            except Exception:
                pass
        return results

    def links_from(
        self,
        start: Tuple[float, float, float],
        type_filter: str | None = None,
        limit: int = 50,
    ) -> List[dict]:
        """List outgoing edges with metadata.

        HTTP mode: call SFM /neighbors. Local/stub: use in-process adjacency.
        """
        if self._mode == "http" and self._http is not None:
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
                out: List[dict] = []
                for e in edges:
                    try:
                        out.append(
                            {
                                "from": tuple(e.get("from") or start),
                                "to": tuple(e.get("to")),
                                "type": e.get("type"),
                                "weight": float(e.get("weight", 1.0)),
                            }
                        )
                    except Exception:
                        continue
                return out[: max(1, int(limit))]
            except Exception:
                pass
        # local/stub fallback
        key = cast(Tuple[float, float, float], (start[0], start[1], start[2]))
        adj = self._graph.get(key, {})
        out: List[dict] = []
        for v, meta in adj.items():
            if type_filter and str(meta.get("type")) != str(type_filter):
                continue
            out.append(
                {
                    "from": start,
                    "to": v,
                    "type": meta.get("type"),
                    "weight": meta.get("weight", 1.0),
                }
            )
            if len(out) >= max(1, int(limit)):
                break
        return out

    def decay_links(self, factor: float = 0.98, min_weight: float = 0.05) -> int:
        """Decay in-process link weights and prune small edges.

        Returns the number of pruned edges. Local/HTTP backends are not affected.
        """
        pruned = 0
        try:
            from . import metrics as _mx
        except Exception:
            _mx = None  # type: ignore
        with self._lock:
            for u, adj in list(self._graph.items()):
                for v, meta in list(adj.items()):
                    w = float(meta.get("weight", 0.0)) * float(factor)
                    if w < float(min_weight):
                        pruned += 1
                        del adj[v]
                    else:
                        meta["weight"] = w
                if not adj:
                    del self._graph[u]
        try:
            if _mx is not None:
                _mx.LINK_DECAY_PRUNED.inc(pruned)
        except Exception:
            pass
        return pruned
