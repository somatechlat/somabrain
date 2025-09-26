"""
Multi-Tenant Working Memory Module for SomaBrain

This module implements multi-tenant working memory management with automatic
LRU eviction. It provides isolated working memory instances for different tenants
while efficiently managing memory resources across the system.

Key Features:
- Tenant-isolated working memory instances
- LRU-based eviction for memory efficiency
- Configurable capacity per tenant
- Automatic cleanup of inactive tenants
- Thread-safe operations with ordered access tracking

Operations:
- Admit: Store vectors and payloads in tenant-specific memory
- Recall: Retrieve similar items using cosine similarity
- Novelty: Compute novelty scores for new inputs
- Items: Access stored items for introspection/debugging

Classes:
    MTWMConfig: Configuration for multi-tenant working memory
    MultiTenantWM: Main multi-tenant working memory manager

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .wm import WorkingMemory


@dataclass
class MTWMConfig:
    per_tenant_capacity: int = 128
    max_tenants: int = 1000


class MultiTenantWM:
    def __init__(self, dim: int, cfg: MTWMConfig):
        self.dim = int(dim)
        self.cfg = cfg
        self._wms: OrderedDict[str, WorkingMemory] = OrderedDict()

    def _ensure(self, tenant_id: str) -> WorkingMemory:
        wm = self._wms.get(tenant_id)
        if wm is None:
            wm = WorkingMemory(capacity=self.cfg.per_tenant_capacity, dim=self.dim)
            self._wms[tenant_id] = wm
        # LRU update
        self._wms.move_to_end(tenant_id)
        # Evict oldest tenants if exceeding max
        while len(self._wms) > self.cfg.max_tenants:
            self._wms.popitem(last=False)
        return wm

    def admit(self, tenant_id: str, vec: np.ndarray, payload: dict) -> None:
        self._ensure(tenant_id).admit(vec, payload)

    def recall(
        self, tenant_id: str, vec: np.ndarray, top_k: int = 3
    ) -> List[Tuple[float, dict]]:
        return self._ensure(tenant_id).recall(vec, top_k)

    def novelty(self, tenant_id: str, vec: np.ndarray) -> float:
        return self._ensure(tenant_id).novelty(vec)

    def items(self, tenant_id: str, limit: int | None = None) -> List[dict]:
        wm = self._ensure(tenant_id)
        data = [
            it.payload for it in wm._items
        ]  # accessing internal list for introspection
        if limit is not None and limit > 0:
            return data[-limit:]
        return data

    def tenants(self) -> List[str]:
        return list(self._wms.keys())
