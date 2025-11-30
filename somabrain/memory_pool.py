from __future__ import annotations
from typing import Any, Dict, Optional
from common.config.settings import Settings as Config
from .memory_client import MemoryClient

"""Multi-tenant memory pool for SomaBrain.

The pool hands out one `MemoryClient` instance per namespace. There is no
local journal replay or stub mirror. All operations are HTTP-first via the
external memory service.
"""



# Use the unified Settings singleton for configuration.



class MultiTenantMemory:
    pass
def __init__(
        self,
        cfg: Config,
        scorer: Optional[Any] = None,
        embedder: Optional[Any] = None, ):
            pass
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
