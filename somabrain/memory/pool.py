"""Multi-tenant memory pool for SomaBrain.

The pool hands out one `MemoryClient` instance per namespace. There is no
local journal replay or local mirror. All operations are HTTP-first via the
external memory service.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Use the unified Settings singleton for configuration.
from django.conf import settings as Config

from somabrain.memory.client import MemoryClient


class MultiTenantMemory:
    """Multitenantmemory class implementation."""

    def __init__(
        self,
        cfg: Config,
        scorer: Optional[Any] = None,
        embedder: Optional[Any] = None,
    ):
        """Initialize the instance."""

        self.cfg = cfg
        self._pool: Dict[str, MemoryClient] = {}
        self._scorer = scorer
        self._embedder = embedder

    def for_namespace(self, namespace: str) -> MemoryClient:
        """Execute for namespace.

        Args:
            namespace: The namespace.
        """

        ns = str(namespace)
        if ns not in self._pool:
            # clone config with namespace override
            # ``self.cfg`` is usually the Django shared settings or a similar object.
            # Use the ``namespace`` argument to override the tenant scope.
            # This keeps the original settings object immutable for other tenants.
            # ALWAYS use the external HTTP MemoryClient. Fallback to a local in‑process
            # memory store has been removed to enforce a single source of truth for
            # memory operations. This ensures consistency across tenants and aligns
            # with the roadmap's Phase 0 goal of eliminating any fallback behavior.
            client = MemoryClient(
                self.cfg, scorer=self._scorer, embedder=self._embedder, namespace=ns
            )
            self._pool[ns] = client

        return self._pool[ns]
