from __future__ import annotations
import asyncio
import os
from typing import Optional, Any, Tuple, List, Dict
from django.conf import settings
from .transport import TransportMixin
from .write import WriteMixin
from .read import ReadMixin
from .search import SearchMixin
from .serialization import _stable_coord


class MemoryClient(TransportMixin, WriteMixin, ReadMixin, SearchMixin):
    """Single gateway to the external memory service."""

    def __init__(
        self,
        cfg: Optional[Any] = None,
        scorer: Optional[Any] = None,
        embedder: Optional[Any] = None,
    ):
        self.cfg = cfg if cfg is not None else settings
        self._scorer = scorer
        self._embedder = embedder
        self._mode = "http"
        self._http: Optional[Any] = None
        self._http_async: Optional[Any] = None

        # Ensure DB path exists (legacy/fallback)
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
        self._memory_db_path = db_path

        self._init_http()

    def coord_for_key(
        self, key: str, universe: str | None = None
    ) -> Tuple[float, float, float]:
        """Return a deterministic coordinate for *key* and optional *universe*."""
        uni = universe or "real"
        return _stable_coord(f"{uni}::{key}")

    def _init_local(self) -> None:
        """Deprecated: Local memory backend is no longer supported in-process."""
        return

    async def store(
        self, coordinate: List[float], payload: Dict[str, Any], tenant: str = "default"
    ) -> bool:
        """Store a memory with an explicit coordinate (async wrapper)."""
        try:
            enriched = dict(payload)
            enriched.setdefault("coordinate", tuple(coordinate))
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.store_from_payload, enriched)
        except Exception:
            return False

    async def search(
        self, query: str, top_k: int = 5, tenant: str = "default"
    ) -> List[Dict[str, Any]]:
        """Search memories and return raw result dicts (async wrapper)."""
        try:
            loop = asyncio.get_event_loop()
            hits = await loop.run_in_executor(None, self.recall, query, top_k)
            return [hit.raw if hit.raw is not None else hit.payload for hit in hits]
        except Exception:
            return []
