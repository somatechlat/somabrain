"""Multi-tenant memory pool for SomaBrain.

The pool hands out one `MemoryClient` instance per namespace. There is no
local journal replay or stub mirror. All operations are HTTP-first via the
external memory service.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Use the unified Settings singleton for configuration.
from common.config.settings import Settings as Config
from typing import Tuple

from .memory_client import MemoryClient, _stable_coord


class LocalMemoryClient:
    """Opt-in, functional in-process memory backend for tests/offline dev."""

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self._store: dict[str, dict] = {}

    # ---------------- Memory API ----------------
    def remember(self, key: str, payload: dict):
        self._store[key] = payload
        return {"ok": True, "key": key, "namespace": self.namespace}

    async def aremember(self, key: str, payload: dict):
        return self.remember(key, payload)

    def recall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ):
        q_lower = (query or "").lower()
        hits = []
        for k, v in self._store.items():
            text = str(v.get("task") or v.get("content") or k).lower()
            # Score: exact key 1.0, substring 0.8, else 0
            if q_lower == k.lower():
                score = 1.0
            elif q_lower and q_lower in text:
                score = 0.8
            else:
                continue
            hits.append({"id": k, "score": score, "payload": v})
        # Stable ordering: highest score then key
        hits.sort(key=lambda h: (-h["score"], h["id"]))
        return hits[: max(1, top_k or 3)]

    async def arecall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ):
        return self.recall(query, top_k, universe, request_id)

    def coord_for_key(
        self, key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
        uni = universe or "real"
        return _stable_coord(f"{uni}::{key}")


class MultiTenantMemory:
    def __init__(
        self,
        cfg: Config,
        scorer: Optional[Any] = None,
        embedder: Optional[Any] = None,
    ):
        self.cfg = cfg
        self._pool: Dict[str, MemoryClient] = {}
        self._scorer = scorer
        self._embedder = embedder

    def for_namespace(self, namespace: str) -> MemoryClient:
        ns = str(namespace)
        if ns not in self._pool:
            # clone config with namespace override
            # ``self.cfg`` is a Pydantic ``BaseSettings`` instance, not a dataclass.
            # Use the built‑in ``copy`` method to create a shallow clone with the
            # overridden ``namespace``. This avoids the ``replace()`` TypeError
            # and keeps the original settings object immutable for other tenants.
            cfg2 = self.cfg.copy(update={"namespace": ns})

            # ALWAYS use the external HTTP MemoryClient. Fallback to a local in‑process
            # memory store has been removed to enforce a single source of truth for
            # memory operations. This ensures consistency across tenants and aligns
            # with the roadmap's Phase 0 goal of eliminating stub/fallback behavior.
            client = MemoryClient(cfg2, scorer=self._scorer, embedder=self._embedder)
            self._pool[ns] = client

        return self._pool[ns]
