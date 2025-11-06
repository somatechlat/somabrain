"""Multi-tenant memory pool for SomaBrain.

The pool hands out one `MemoryClient` instance per namespace. Journal replay is
no longer performed here (handled by the MemorySyncWorker/migration helpers).
All operations are HTTP-first via the external memory service; no local/stub
mirrors are used.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .config import Config
from .memory_client import MemoryClient


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
            from dataclasses import replace

            cfg2 = replace(self.cfg)
            cfg2.namespace = ns

            # V3: The pool no longer replays the journal. This is now the sole
            # responsibility of the MemorySyncWorker.
            client = MemoryClient(cfg2, scorer=self._scorer, embedder=self._embedder)
            self._pool[ns] = client

        return self._pool[ns]
