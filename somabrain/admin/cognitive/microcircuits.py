"""
Microcircuits Module for SomaBrain

This module implements microcircuit-based working memory with multiple columns
and vote aggregation. It provides distributed working memory that shards data
across multiple columns for improved capacity and retrieval performance.

Key Features:
- Multi-column working memory architecture
- Load distribution via hash-based routing
- Vote aggregation for recall operations
- Tenant isolation with LRU eviction
- Cosine similarity-based retrieval
- Novelty detection across all columns

Architecture:
- Items are routed to columns based on hash of content
- Recall aggregates results from all columns using weighted voting
- Novelty is computed as 1 - max similarity across columns
- Entropy-based metrics for column performance monitoring

Classes:
    MCConfig: Configuration for microcircuit parameters
    MultiColumnWM: Main multi-column working memory implementation

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

import logging
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

import numpy as np
from django.conf import settings

from .metrics import MICRO_COLUMN_ADMIT, MICRO_COLUMN_BEST, MICRO_VOTE_ENTROPY
from .wm import WorkingMemory


@dataclass
class MCConfig:
    """Mcconfig class implementation."""

    columns: int = field(
        default_factory=lambda: max(1, int(settings.SOMABRAIN_MICRO_CIRCUITS))
    )
    per_col_capacity: int = field(
        default_factory=lambda: max(
            int(settings.SOMABRAIN_WM_PER_COL_MIN_CAPACITY),
            int(settings.SOMABRAIN_WM_SIZE),
        )
    )
    vote_temperature: float = field(
        default_factory=lambda: float(settings.SOMABRAIN_MICRO_VOTE_TEMPERATURE)
    )
    max_tenants: int = field(
        default_factory=lambda: int(settings.SOMABRAIN_MICRO_MAX_TENANTS)
    )
    recency_time_scale: float = field(
        default_factory=lambda: float(settings.SOMABRAIN_WM_RECENCY_TIME_SCALE)
    )
    recency_max_steps: float = field(
        default_factory=lambda: float(settings.SOMABRAIN_WM_RECENCY_MAX_STEPS)
    )


class MultiColumnWM:
    """Tenant-scoped working memory sharded into K columns with vote aggregation.

    - Admit: route items to a column by hash of task/fact text, distributing load.
    - Recall: per-column top-k with cosine similarity, then aggregate using softmax
      weights derived from each column's best score.
    - Novelty: 1 - max cosine across all columns.
    """

    def __init__(self, dim: int, cfg: MCConfig, scorer=None):
        """Initialize the instance."""

        self.dim = int(dim)
        self.cfg = cfg
        self._tenants: OrderedDict[str, List[WorkingMemory]] = OrderedDict()
        self._scorer = scorer

    def _ensure(self, tenant_id: str) -> List[WorkingMemory]:
        """Execute ensure.

        Args:
            tenant_id: The tenant_id.
        """

        cols = self._tenants.get(tenant_id)
        if cols is None:
            cols = [
                WorkingMemory(
                    capacity=self.cfg.per_col_capacity,
                    dim=self.dim,
                    scorer=self._scorer,
                    recency_time_scale=self.cfg.recency_time_scale,
                    recency_max_steps=self.cfg.recency_max_steps,
                )
                for _ in range(max(1, int(self.cfg.columns)))
            ]
            self._tenants[tenant_id] = cols
        self._tenants.move_to_end(tenant_id)
        while len(self._tenants) > self.cfg.max_tenants:
            self._tenants.popitem(last=False)
        return cols

    @staticmethod
    def _choose_column(payload: dict, columns: int) -> int:
        """Route payload to a column using FNV-1a hash.

        Uses FNV-1a (Fowler-Noll-Vo) hash algorithm constants:
        - FNV_OFFSET_BASIS: 1469598103934665603 (64-bit)
        - FNV_PRIME: 1099511628211 (64-bit)

        These are mathematical constants from the FNV hash specification,
        not configuration values.
        """
        key = str(payload.get("task") or payload.get("fact") or "")
        if not key:
            return 0
        # FNV-1a hash constants (64-bit)
        FNV_OFFSET_BASIS = 1469598103934665603
        FNV_PRIME = 1099511628211
        h = FNV_OFFSET_BASIS
        for ch in key.encode("utf-8"):
            h ^= ch
            h *= FNV_PRIME
            h &= (1 << 64) - 1
        return int(h % max(1, columns))

    def admit(
        self,
        tenant_id: str,
        vec: np.ndarray,
        payload: dict,
        *,
        cleanup_overlap: float | None = None,
    ) -> None:
        """Execute admit.

        Args:
            tenant_id: The tenant_id.
            vec: The vec.
            payload: The payload.
        """

        cols = self._ensure(tenant_id)
        idx = self._choose_column(payload, len(cols))
        cols[idx].admit(vec, dict(payload), cleanup_overlap=cleanup_overlap)
        try:
            MICRO_COLUMN_ADMIT.labels(column=str(idx)).inc()
        except Exception as metric_exc:
            logger.debug("Failed to record micro_column_admit metric: %s", metric_exc)

    def recall(
        self, tenant_id: str, vec: np.ndarray, top_k: int = 3
    ) -> List[Tuple[float, dict]]:
        """Execute recall.

        Args:
            tenant_id: The tenant_id.
            vec: The vec.
            top_k: The top_k.
        """

        cols = self._ensure(tenant_id)
        per_col: List[List[Tuple[float, dict]]] = []
        bests: List[float] = []
        for wm in cols:
            hits = wm.recall(vec, top_k=top_k)
            per_col.append(hits)
            bests.append(hits[0][0] if hits else 0.0)
        try:
            # increment the column with highest best score
            if bests:
                best_idx = int(max(range(len(bests)), key=lambda i: bests[i]))
                MICRO_COLUMN_BEST.labels(column=str(best_idx)).inc()
        except Exception as metric_exc:
            logger.debug("Failed to record micro_column_best metric: %s", metric_exc)
        # softmax weights over best scores
        T = max(
            settings.SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR, float(self.cfg.vote_temperature)
        )
        xs = [b / T for b in bests]
        m = max(xs) if xs else 0.0
        exps = [math.exp(x - m) for x in xs]
        Z = sum(exps) or 1.0
        weights = [e / Z for e in exps]
        # record entropy of vote distribution
        eps = settings.SOMABRAIN_WM_VOTE_ENTROPY_EPS or 1e-9
        ent = -sum(w * math.log(max(eps, w)) for w in weights if w > 0.0)
        MICRO_VOTE_ENTROPY.observe(max(0.0, float(ent)))
        # aggregate
        combined: List[Tuple[float, dict]] = []
        for w, hits in zip(weights, per_col):
            for s, p in hits:
                combined.append((float(w) * float(s), p))
        combined.sort(key=lambda t: t[0], reverse=True)
        return combined[: max(0, int(top_k))]

    def novelty(self, tenant_id: str, vec: np.ndarray) -> float:
        """Execute novelty.

        Args:
            tenant_id: The tenant_id.
            vec: The vec.
        """

        cols = self._ensure(tenant_id)
        best = 0.0
        for wm in cols:
            best = max(
                best, 1.0 - wm.novelty(vec)
            )  # wm.novelty returns 1 - best_cosine
        return max(0.0, 1.0 - best)

    def items(self, tenant_id: str, limit: int | None = None) -> List[dict]:
        """Execute items.

        Args:
            tenant_id: The tenant_id.
            limit: The limit.
        """

        cols = self._ensure(tenant_id)
        data: List[dict] = []
        for wm in cols:
            data.extend([it.payload for it in wm._items])
        if limit is not None and limit > 0:
            return data[-limit:]
        return data

    def stats(self, tenant_id: str) -> Dict[str, int]:
        """Execute stats.

        Args:
            tenant_id: The tenant_id.
        """

        cols = self._ensure(tenant_id)
        return {f"col_{i}": len(wm._items) for i, wm in enumerate(cols)}
