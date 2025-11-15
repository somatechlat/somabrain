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
import threading
import logging

from .wm import WorkingMemory
# Import metrics for working‑memory instrumentation. The metrics module defines
# counters such as ``WM_ADMIT``, ``WM_HITS``, ``WM_MISSES`` and ``WM_EVICTIONS``.
from . import metrics as M


@dataclass
class MTWMConfig:
    per_tenant_capacity: int = 128
    max_tenants: int = 1000
    recency_time_scale: float = 60.0
    recency_max_steps: float = 4096.0


class MultiTenantWM:
    def __init__(self, dim: int, cfg: MTWMConfig | None = None, scorer=None):
        self.dim = int(dim)
        self.cfg = cfg or MTWMConfig()
        self._wms: OrderedDict[str, WorkingMemory] = OrderedDict()
        self._scorer = scorer
        # Re‑entrant lock to guarantee thread‑safety for all public operations.
        self._lock = threading.RLock()

    def _ensure(self, tenant_id: str) -> WorkingMemory:
        """Return the ``WorkingMemory`` instance for *tenant_id*.

        The method is protected by ``self._lock`` to ensure that creation,
        LRU‑promotion and eviction are atomic. When a tenant is evicted we emit the
        ``WM_EVICTIONS`` metric and update the overall utilization gauge.
        """
        with self._lock:
            wm = self._wms.get(tenant_id)
            if wm is None:
                wm = WorkingMemory(
                    capacity=self.cfg.per_tenant_capacity,
                    dim=self.dim,
                    scorer=self._scorer,
                    recency_time_scale=self.cfg.recency_time_scale,
                    recency_max_steps=self.cfg.recency_max_steps,
                )
                self._wms[tenant_id] = wm
            # LRU update – move the accessed tenant to the end (most‑recent)
            self._wms.move_to_end(tenant_id)
            # Evict oldest tenants if we exceed the configured limit
            while len(self._wms) > self.cfg.max_tenants:
                evicted_id, _ = self._wms.popitem(last=False)
                try:
                    M.WM_EVICTIONS.inc()
                except Exception:
                    pass
                logger = logging.getLogger(__name__)
                logger.debug(
                    "Evicted tenant %s from MultiTenantWM (max_tenants=%s)",
                    evicted_id,
                    self.cfg.max_tenants,
                )
            # Update utilization after any creation or eviction
            try:
                total_items = sum(len(w._items) for w in self._wms.values())
                total_capacity = self.cfg.max_tenants * self.cfg.per_tenant_capacity
                M.WM_UTILIZATION.set(total_items / total_capacity if total_capacity else 0.0)
            except Exception:
                pass
            return wm

    def admit(
        self,
        tenant_id: str,
        vec: np.ndarray,
        payload: dict,
        *,
        cleanup_overlap: float | None = None,
    ) -> None:
        """Store a vector/payload for *tenant_id* and increment ``WM_ADMIT``.

        The metric uses a ``source`` label that contains the tenant identifier
        (truncated to avoid high‑cardinality). The underlying ``WorkingMemory``
        performs the actual admission.
        """
        with self._lock:
            self._ensure(tenant_id).admit(vec, payload, cleanup_overlap=cleanup_overlap)
        try:
            M.WM_ADMIT.labels(source=tenant_id[:50]).inc()
        except Exception:
            pass

    def recall(
        self, tenant_id: str, vec: np.ndarray, top_k: int = 3
    ) -> List[Tuple[float, dict]]:
        """Retrieve up to *top_k* items for *tenant_id*.

        ``WM_HITS`` is incremented when the call returns at least one result;
        otherwise ``WM_MISSES`` is incremented.
        """
        with self._lock:
            results = self._ensure(tenant_id).recall(vec, top_k)
        try:
            if results:
                M.WM_HITS.inc()
            else:
                M.WM_MISSES.inc()
        except Exception:
            pass
        return results

    def novelty(self, tenant_id: str, vec: np.ndarray) -> float:
        with self._lock:
            return self._ensure(tenant_id).novelty(vec)

    def items(self, tenant_id: str, limit: int | None = None) -> List[dict]:
        with self._lock:
            wm = self._ensure(tenant_id)
            data = [it.payload for it in wm._items]  # internal list for introspection
        if limit is not None and limit > 0:
            return data[-limit:]
        return data

    def tenants(self) -> List[str]:
        with self._lock:
            return list(self._wms.keys())
