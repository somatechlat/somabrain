"""
 Multi-Tenant HRR Context Module for SomaBrain

This module provides multi-tenant Hyperdimensional Representation (HRR) context
management. It maintains separate HRR contexts for different tenants with LRU
eviction, enabling efficient context tracking and novelty detection.

Key Features:
- Tenant-isolated HRR contexts
- LRU-based context eviction for memory efficiency
- Superposition-based context accumulation
- Novelty detection via context similarity
- Anchor-based cleanup for robust retrieval
- Statistical tracking of context usage

HRR Operations:
- Admit: Add vectors to context via superposition
- Novelty: Compute novelty as 1 - context similarity
- Cleanup: Find nearest anchors using cosine similarity
- Stats: Track anchor counts and capacity usage

Classes:
    MultiTenantHRRContext: Main multi-tenant context manager

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Tuple

import numpy as np
from django.conf import settings

from .context_hrr import CleanupResult, HRRContext, HRRContextConfig
from .quantum import QuantumLayer


class MultiTenantHRRContext:
    """Multitenanthrrcontext class implementation."""

    def __init__(
        self, q: QuantumLayer, cfg: HRRContextConfig, max_tenants: int | None = None
    ):
        """Initialize the instance."""

        self.q = q
        self.cfg = cfg
        self.max_tenants = int(
            settings.SOMABRAIN_MTWM_MAX_TENANTS if max_tenants is None else max_tenants
        )
        self._ctxs: OrderedDict[str, HRRContext] = OrderedDict()

    def _ensure(self, tenant_id: str) -> HRRContext:
        """Execute ensure.

        Args:
            tenant_id: The tenant_id.
        """

        ctx = self._ctxs.get(tenant_id)
        if ctx is None:
            ctx = HRRContext(self.q, self.cfg, context_id=tenant_id)
            self._ctxs[tenant_id] = ctx
        self._ctxs.move_to_end(tenant_id)
        while len(self._ctxs) > self.max_tenants:
            self._ctxs.popitem(last=False)
        return ctx

    def admit(self, tenant_id: str, anchor_id: str, vec: np.ndarray) -> None:
        """Execute admit.

        Args:
            tenant_id: The tenant_id.
            anchor_id: The anchor_id.
            vec: The vec.
        """

        self._ensure(tenant_id).admit(anchor_id, vec)

    def novelty(self, tenant_id: str, vec: np.ndarray) -> float:
        """Execute novelty.

        Args:
            tenant_id: The tenant_id.
            vec: The vec.
        """

        return self._ensure(tenant_id).novelty(vec)

    def cleanup(self, tenant_id: str, query: np.ndarray) -> Tuple[str, float]:
        """Execute cleanup.

        Args:
            tenant_id: The tenant_id.
            query: The query.
        """

        return self._ensure(tenant_id).cleanup(query)

    def analyze(self, tenant_id: str, query: np.ndarray) -> CleanupResult:
        """Return cleanup scores (best, second, margin) without thresholding."""
        return self._ensure(tenant_id).analyze(query)

    def stats(self, tenant_id: str) -> tuple[int, int]:
        """Execute stats.

        Args:
            tenant_id: The tenant_id.
        """

        return self._ensure(tenant_id).stats()
