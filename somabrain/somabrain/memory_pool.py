from __future__ import annotations

from typing import Dict

from .config import Config
from .memory_client import MemoryClient


class MultiTenantMemory:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._pool: Dict[str, MemoryClient] = {}

    def for_namespace(self, namespace: str) -> MemoryClient:
        ns = str(namespace)
        if ns not in self._pool:
            # clone config with namespace override
            from dataclasses import replace
            cfg2 = replace(self.cfg)
            cfg2.namespace = ns
            self._pool[ns] = MemoryClient(cfg2)
        return self._pool[ns]
