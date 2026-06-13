from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

from .graph_ops import GraphOpsMixin
from .read import ReadMixin
from .search import SearchMixin
from .serialization import _stable_coord
from .transport import TransportMixin
from .write import WriteMixin


class MemoryClient(TransportMixin, WriteMixin, ReadMixin, SearchMixin, GraphOpsMixin):
    """Single gateway to the external memory service."""

    def __init__(
        self,
        cfg: Optional[Any] = None,
        scorer: Optional[Any] = None,
        embedder: Optional[Any] = None,
        namespace: Optional[str] = None,
    ):
        self.cfg = cfg if cfg is not None else settings
        self._scorer = scorer
        self._embedder = embedder
        self.namespace = namespace or "default"
        self._mode = "http"
        self._http: Optional[Any] = None
        self._http_async: Optional[Any] = None

        self._init_http()

    def coord_for_key(
        self, key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
        """Return a deterministic coordinate for *key* and optional *universe*."""
        uni = universe or "real"
        return _stable_coord(f"{uni}::{key}")

    async def store(
        self, coordinate: List[float], payload: Dict[str, Any], tenant: str = "default"
    ) -> bool:
        """Store a memory with an explicit coordinate (async wrapper).

        The caller-supplied ``tenant`` is persisted into the payload so that
        later searches can scope results to the same tenant. This is essential
        for multi-tenant isolation because SFM itself is not tenant-aware.
        """
        enriched = dict(payload)
        enriched.setdefault("coordinate", tuple(coordinate))
        enriched.setdefault("tenant", tenant)
        enriched.setdefault("namespace", self.namespace or "default")
        # Scope the SFM universe to the tenant so the backend and our filters
        # both keep this memory separate from other tenants.
        enriched.setdefault("universe", tenant)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.store_from_payload, enriched)

    async def search(
        self, query: str, top_k: int = 5, tenant: str = "default"
    ) -> List[Dict[str, Any]]:
        """Search memories and return raw result dicts (async wrapper).

        Search is scoped to the caller's tenant by reusing the tenant as the
        memory universe. Without this, the SFM backend returns memories from
        every tenant and the test/user sees cross-tenant leakage.
        """
        loop = asyncio.get_event_loop()
        hits = await loop.run_in_executor(
            None, self.recall, query, top_k, tenant
        )
        return [hit.raw if hit.raw is not None else hit.payload for hit in hits]
