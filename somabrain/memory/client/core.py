from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx
from django.conf import settings

from .graph_ops import GraphOpsMixin
from .read import ReadMixin
from .search import SearchMixin
from .serialization import _coord_to_str, _stable_coord
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
        tenant: Optional[str] = None,
    ):
        self.cfg = cfg if cfg is not None else settings
        self._scorer = scorer
        self._embedder = embedder
        if not namespace:
            raise ValueError(
                "MemoryClient: namespace is required (T-5 fail-closed, no default)"
            )
        self.namespace = namespace
        self.tenant = tenant or self.namespace
        self._mode = "http"
        self._http: Optional[Any] = None

        self._init_http()

    def coord_for_key(
        self, key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
        """Return a deterministic coordinate for *key* and optional *universe*."""
        uni = universe or "real"
        return _stable_coord(f"{uni}::{key}")

    def fetch_by_coord(
        self, coordinate: Any, universe: str | None = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch a stored memory payload by coordinate (``GET /memories/{coord}``).

        Fail-closed: raises when the transport is missing or the backend
        errors. Returns ``None`` when the coordinate is not present.
        """
        coord_str = _coord_to_str(coordinate)
        if not coord_str:
            raise ValueError(f"invalid coordinate for fetch: {coordinate!r}")
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED: HTTP memory backend not available (fetch_by_coord)."
            )
        headers = {}
        if universe:
            headers["X-Universe"] = str(universe)
        try:
            resp = self._http.get(f"/memories/{coord_str}", headers=headers)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"memory service unreachable (fetch): {exc}") from exc
        status = int(getattr(resp, "status_code", 0) or 0)
        if status == 404:
            return None
        if not (200 <= status < 300):
            raise RuntimeError(f"memory service fetch failed: HTTP {status}")
        data = self._response_json(resp)
        if isinstance(data, dict):
            mem = data.get("memory")
            if isinstance(mem, dict):
                return mem
            return data
        return None

    def _interpret_delete_response(self, resp: Any) -> bool:
        """Map a ``DELETE /memories/{coord}`` response to "was it removed".

        The SomaFractalMemory API answers HTTP 200 with ``{"deleted": true}``
        when it removed the row and ``{"deleted": false}`` when the coordinate
        was already absent; a missing coordinate is also reported as HTTP 404.
        The body's ``deleted`` flag is therefore authoritative — the status code
        alone cannot distinguish "removed" from "already gone", and reading only
        the status would report a no-op as a successful delete.
        """
        status = int(getattr(resp, "status_code", 0) or 0)
        if status == 404:
            return False
        if not (200 <= status < 300):
            raise RuntimeError(f"memory service delete failed: HTTP {status}")

        data = self._response_json(resp)
        if isinstance(data, dict) and isinstance(data.get("deleted"), bool):
            return bool(data["deleted"])
        # A 2xx without an explicit outcome must not be read as success.
        raise RuntimeError(
            f"memory service delete returned HTTP {status} without a 'deleted' flag: {data!r}"
        )

    def delete(self, coordinate: Any) -> bool:
        """Delete a memory by coordinate (``DELETE /memories/{coord}``).

        Returns True when the backend confirms removal and False when the
        coordinate was already absent. Any other backend outcome raises so a
        failed forget is never reported as success.
        """
        coord_str = _coord_to_str(coordinate)
        if not coord_str:
            raise ValueError(f"invalid coordinate for delete: {coordinate!r}")
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED: HTTP memory backend not available (delete)."
            )
        try:
            resp = self._http.delete(f"/memories/{coord_str}")
        except httpx.HTTPError as exc:
            raise RuntimeError(f"memory service unreachable (delete): {exc}") from exc
        return self._interpret_delete_response(resp)

    async def adelete(self, coordinate: Any) -> bool:
        """Async variant of :meth:`delete`."""
        coord_str = _coord_to_str(coordinate)
        if not coord_str:
            raise ValueError(f"invalid coordinate for delete: {coordinate!r}")
        if self._http_async is not None:
            try:
                resp = await self._http_async.delete(f"/memories/{coord_str}")
            except httpx.HTTPError as exc:
                raise RuntimeError(f"memory service unreachable (delete): {exc}") from exc
            return self._interpret_delete_response(resp)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete, coordinate)

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
        if not tenant:
            raise ValueError("store_with_coord: tenant is required (T-5 fail-closed)")
        enriched.setdefault("tenant", tenant)
        enriched.setdefault("namespace", self.namespace)
        # Scope the SFM universe to the tenant so the backend and our filters
        # both keep this memory separate from other tenants.
        enriched.setdefault("universe", tenant)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.store_from_payload, enriched)

    async def search(
        self, query: str, top_k: int = 5, tenant: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search memories and return raw result dicts (async wrapper).

        Search is scoped to the caller's tenant by reusing the tenant as the
        memory universe. Without this, the SFM backend returns memories from
        every tenant and the test/user sees cross-tenant leakage.
        """
        if not tenant:
            raise ValueError("search: tenant is required (T-5 fail-closed)")
        loop = asyncio.get_event_loop()
        hits = await loop.run_in_executor(
            None, self.recall, query, top_k, tenant
        )
        return [hit.raw if hit.raw is not None else hit.payload for hit in hits]
