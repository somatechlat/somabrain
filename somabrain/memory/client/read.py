from __future__ import annotations
import uuid
import asyncio
from typing import List, Tuple, Any
from .types import RecallHit
from .serialization import _response_json, _parse_coord_string

class ReadMixin:
    """Handles high-level recall operations."""

    def recall(
        self,
        query: str,
        top_k: int = 3,
        universe: str | None = None,
        request_id: str | None = None,
    ) -> List[RecallHit]:
        """Retrieve memories relevant to the query using the HTTP memory service."""
        # Strict mode: memory service is ALWAYS required
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED: HTTP memory backend not available."
            )
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

    def payloads_for_coords(
        self, coords: List[Tuple[float, float, float]], universe: str | None = None
    ) -> List[dict]:
        """Bulk retrieval of payloads for the given coordinates."""
        if not coords:
            return []

        if self._http is None:
            # Check strict mode setting if needed, but for now just return empty if no HTTP
            try:
                if getattr(self.cfg, "require_memory", False):
                    raise RuntimeError(
                        "MEMORY SERVICE UNAVAILABLE: payloads_for_coords requires an HTTP memory backend."
                    )
            except Exception:
                pass
            return []

        coord_strs = [f"{c[0]},{c[1]},{c[2]}" for c in coords]
        body: dict[str, Any] = {"coords": coord_strs}
        if universe:
            body["universe"] = universe

        try:
            resp = self._http.post("/payloads", json=body)
            data = _response_json(resp)
        except Exception:
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
