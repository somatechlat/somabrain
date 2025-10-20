from __future__ import annotations

from collections import OrderedDict
from typing import Tuple
import numpy as np

from .context_hrr import HRRContext, HRRContextConfig
from .quantum import QuantumLayer


class MultiTenantHRRContext:
    def __init__(self, q: QuantumLayer, cfg: HRRContextConfig, max_tenants: int = 1000):
        self.q = q
        self.cfg = cfg
        self.max_tenants = int(max_tenants)
        self._ctxs: OrderedDict[str, HRRContext] = OrderedDict()

    def _ensure(self, tenant_id: str) -> HRRContext:
        ctx = self._ctxs.get(tenant_id)
        if ctx is None:
            ctx = HRRContext(self.q, self.cfg)
            self._ctxs[tenant_id] = ctx
        self._ctxs.move_to_end(tenant_id)
        while len(self._ctxs) > self.max_tenants:
            self._ctxs.popitem(last=False)
        return ctx

    def admit(self, tenant_id: str, anchor_id: str, vec: np.ndarray) -> None:
        self._ensure(tenant_id).admit(anchor_id, vec)

    def novelty(self, tenant_id: str, vec: np.ndarray) -> float:
        return self._ensure(tenant_id).novelty(vec)

    def cleanup(self, tenant_id: str, query: np.ndarray) -> Tuple[str, float]:
        return self._ensure(tenant_id).cleanup(query)

    def stats(self, tenant_id: str) -> tuple[int, int]:
        return self._ensure(tenant_id).stats()
