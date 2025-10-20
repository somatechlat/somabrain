from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import hashlib
import time
import asyncio

 

from .config import Config


def _stable_coord(key: str) -> Tuple[float, float, float]:
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=12).digest()
    a = int.from_bytes(h[0:4], "big") / 2**32
    b = int.from_bytes(h[4:8], "big") / 2**32
    c = int.from_bytes(h[8:12], "big") / 2**32
    # spread over [-1, 1]
    return (2 * a - 1, 2 * b - 1, 2 * c - 1)


@dataclass
class RecallHit:
    payload: Dict[str, Any]


class MemoryClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._mode = cfg.memory_mode
        self._local = None
        self._http = None
        self._http_async = None
        self._stub_store: list[dict] = []
        # in-process adjacency for simple graph reasoning in local/http modes
        # adjacency with metadata: from -> { to -> {type, weight} }
        self._graph: Dict[Tuple[float, float, float], Dict[Tuple[float, float, float], Dict[str, float | str]]] = {}
        if self._mode == "local":
            self._init_local()
        elif self._mode == "http":
            self._init_http()

    def _init_local(self) -> None:
        from somafractalmemory.factory import create_memory_system, MemoryMode  # type: ignore
        # Pass through indexing/quantization hints when available; the backend may ignore unknown keys.
        vec_cfg = {
            "backend": "inmemory",
            "profile": getattr(self.cfg, "index_profile", "balanced"),
            "pq": {
                "m": int(getattr(self.cfg, "pq_m", 16) or 16),
                "bits": int(getattr(self.cfg, "pq_bits", 8) or 8),
                "opq": bool(getattr(self.cfg, "opq_enabled", False) or False),
                "anisotropic": bool(getattr(self.cfg, "anisotropic_enabled", False) or False),
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
        self._local = create_memory_system(
            MemoryMode.ON_DEMAND,
            self.cfg.namespace,
            config={"redis": {"testing": True}, "vector": vec_cfg},
        )

    def _init_http(self) -> None:
        import httpx  # type: ignore
        headers = {}
        if self.cfg.http.token:
            headers["Authorization"] = f"Bearer {self.cfg.http.token}"
        self._http = httpx.Client(base_url=str(self.cfg.http.endpoint or ""), headers=headers, timeout=10.0)
        try:
            self._http_async = httpx.AsyncClient(base_url=str(self.cfg.http.endpoint or ""), headers=headers, timeout=10.0)
        except Exception:
            self._http_async = None

    def health(self) -> dict:
        try:
            if self._mode == "local" and self._local:
                return self._local.health_check()  # type: ignore
            if self._mode == "http" and self._http:
                r = self._http.get("/health")
                return {"http": r.status_code == 200}
        except Exception:
            return {"ok": False}
        return {"ok": True}

    def remember(self, coord_key: str, payload: dict) -> None:
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
            return
        if self._mode == "http" and self._http:
            body = {"coord": f"{coord[0]},{coord[1]},{coord[2]}", "payload": payload, "type": "episodic"}
            self._http.post("/store", json=body)
            return
        # stub: keep minimal in-process store
        payload = dict(payload)
        payload["coordinate"] = coord
        self._stub_store.append(payload)

    async def aremember(self, coord_key: str, payload: dict) -> None:
        if self._mode == "http" and self._http_async is not None:
            try:
                universe = str(payload.get("universe") or "real")
                coord = _stable_coord(f"{universe}::{coord_key}")
                body = {"coord": f"{coord[0]},{coord[1]},{coord[2]}", "payload": payload, "type": "episodic"}
                await self._http_async.post("/store", json=body)
                return
            except Exception:
                pass
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.remember, coord_key, payload)

    def recall(self, query: str, top_k: int = 3) -> List[RecallHit]:
        if self._mode == "local" and self._local:
            res = self._local.recall(query, top_k=top_k)  # type: ignore
            return [RecallHit(payload=r) for r in res]
        if self._mode == "http" and self._http:
            r = self._http.post("/recall", json={"query": query, "top_k": int(top_k)})
            try:
                data = r.json()
            except Exception:
                data = []
            return [RecallHit(payload=p) for p in (data or [])]
        # stub recall: return recent stubbed payloads
        return [RecallHit(payload=p) for p in self._stub_store[-int(max(0, top_k)):]]

    async def arecall(self, query: str, top_k: int = 3) -> List[RecallHit]:
        """Async recall for HTTP mode; falls back to sync for local/stub."""
        if self._mode == "http" and self._http_async is not None:
            try:
                r = await self._http_async.post("/recall", json={"query": query, "top_k": int(top_k)})
                data = r.json()
            except Exception:
                data = []
            return [RecallHit(payload=p) for p in (data or [])]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.recall, query, top_k)

    def link(self, from_coord: tuple[float, float, float], to_coord: tuple[float, float, float], link_type: str = "related", weight: float = 1.0) -> None:
        if self._mode == "local" and self._local:
            try:
                self._local.link_memories(from_coord, to_coord, link_type=link_type, weight=weight)  # type: ignore
            except Exception:
                pass
            # also record locally with metadata
            adj = self._graph.setdefault(tuple(from_coord), {})
            prev = adj.get(tuple(to_coord), {"type": str(link_type), "weight": 0.0})
            new_w = float(prev.get("weight", 0.0)) + float(weight)
            adj[tuple(to_coord)] = {"type": str(link_type), "weight": new_w}
            return
        if self._mode == "http" and self._http:
            try:
                self._http.post(
                    "/link",
                    json={
                        "from_coord": f"{from_coord[0]},{from_coord[1]},{from_coord[2]}",
                        "to_coord": f"{to_coord[0]},{to_coord[1]},{to_coord[2]}",
                        "type": link_type,
                        "weight": weight,
                    },
                )
            except Exception:
                pass
            # record locally for process augmentation
            adj = self._graph.setdefault(tuple(from_coord), {})
            prev = adj.get(tuple(to_coord), {"type": str(link_type), "weight": 0.0})
            new_w = float(prev.get("weight", 0.0)) + float(weight)
            adj[tuple(to_coord)] = {"type": str(link_type), "weight": new_w}
            return
        # stub: record in-process adjacency
        adj = self._graph.setdefault(tuple(from_coord), {})
        prev = adj.get(tuple(to_coord), {"type": str(link_type), "weight": 0.0})
        new_w = float(prev.get("weight", 0.0)) + float(weight)
        adj[tuple(to_coord)] = {"type": str(link_type), "weight": new_w}

    async def alink(self, from_coord: tuple[float, float, float], to_coord: tuple[float, float, float], link_type: str = "related", weight: float = 1.0) -> None:
        if self._mode == "http" and self._http_async is not None:
            try:
                await self._http_async.post(
                    "/link",
                    json={
                        "from_coord": f"{from_coord[0]},{from_coord[1]},{from_coord[2]}",
                        "to_coord": f"{to_coord[0]},{to_coord[1]},{to_coord[2]}",
                        "type": link_type,
                        "weight": weight,
                    },
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
        # stub returns in-process store
        return list(self._stub_store)

    def store_from_payload(self, payload: dict) -> bool:
        """Store a memory from an exported payload, requiring a coordinate in payload."""
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
    def coord_for_key(key: str, universe: str | None = None) -> Tuple[float, float, float]:
        u = str(universe or "real")
        return _stable_coord(f"{u}::{key}")

    def k_hop(self, starts: List[Tuple[float, float, float]], depth: int = 1, limit: int = 20, type_filter: str | None = None) -> List[Tuple[float, float, float]]:
        seen = set()
        frontier = list(starts)
        out: List[Tuple[float, float, float]] = []
        for _ in range(max(0, int(depth))):
            next_frontier: List[Tuple[float, float, float]] = []
            for u in frontier:
                adj = self._graph.get(tuple(u), {})
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

    def payloads_for_coords(self, coords: List[Tuple[float, float, float]], universe: str | None = None) -> List[dict]:
        if not coords:
            return []
        wanted = {tuple(c) for c in coords}
        results: List[dict] = []
        for p in self.all_memories():
            c = p.get("coordinate")
            if isinstance(c, (list, tuple)) and len(c) == 3 and tuple(c) in wanted:
                if universe is not None and str(p.get("universe") or "real") != str(universe):
                    continue
                results.append(p)
        return results

    def links_from(self, start: Tuple[float, float, float], type_filter: str | None = None, limit: int = 50) -> List[dict]:
        adj = self._graph.get(tuple(start), {})
        out: List[dict] = []
        for v, meta in adj.items():
            if type_filter and str(meta.get("type")) != str(type_filter):
                continue
            out.append({"from": start, "to": v, "type": meta.get("type"), "weight": meta.get("weight", 1.0)})
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
