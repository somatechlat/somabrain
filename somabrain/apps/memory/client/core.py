from __future__ import annotations
import os
from typing import Optional, Any, Tuple
from django.conf import settings
from .transport import TransportMixin
from .write import WriteMixin
from .read import ReadMixin
from .search import SearchMixin
from .graph import GraphMixin
from .serialization import _stable_coord

class MemoryClient(TransportMixin, WriteMixin, ReadMixin, SearchMixin, GraphMixin):
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
