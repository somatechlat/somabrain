"""High-fidelity HRR context handling for SomaBrain.

This module manages tenant-scoped HRR contexts with mathematically grounded
recency weighting, cleanup gating, and observability. It preserves truthful
hyperdimensional behaviour by:

* Maintaining anchor vectors under an exponential decay model
* Enforcing configurable confidence thresholds during cleanup
* Exposing capacity/SNR/cosine-margin metrics for supervisory control loops

The implementation is deliberately free of mocks or shortcuts; every update
applies the exact decay specified by :class:`HRRContextConfig.decay_lambda`
and updates Prometheus-backed metrics for downstream verification.
"""

from __future__ import annotations

import math
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Tuple

import numpy as np

from .quantum import QuantumLayer
from somabrain.metrics_extra.context_metrics import ContextMetrics


@dataclass
class CleanupResult:
    """Outcome of an HRR cleanup sweep with margin data."""

    best_id: str
    best_score: float
    second_score: float

        yield self.best_id
        yield self.best_score

    @property
    def margin(self) -> float:
        return max(0.0, float(self.best_score) - float(self.second_score))


@dataclass
class HRRContextConfig:
    """Configuration for an HRR context."""

    max_anchors: int = 10000
    decay_lambda: float = 0.0
    min_confidence: float = 0.0


class HRRContext:
    """Tenant-scoped HRR working context: superposed context vector + cleanup anchors.

    - context: superposition of admitted item vectors
    - anchors: limited-size dict of id->vector for cleanup/nearest neighbor
    """

    def __init__(
        self,
        q: QuantumLayer,
        cfg: HRRContextConfig,
        *,
        context_id: str | None = None,
        now_fn: Callable[[], float] | None = None,
    ):
        self.q = q
        self.cfg = cfg
        self.context = np.zeros((q.cfg.dim,), dtype="float32")
        self._anchors: OrderedDict[str, np.ndarray] = OrderedDict()
        self._anchor_times: OrderedDict[str, float] = OrderedDict()
        self._now = now_fn or time.time
        self._decay_lambda = max(0.0, float(cfg.decay_lambda))
        self._min_confidence = float(cfg.min_confidence)
        self._context_timestamp = self._now()
        self._context_id = context_id or "global"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _apply_decay(self, target_time: float) -> None:
        """Bring the context forward in time under exponential decay."""

        if self._decay_lambda <= 0.0:
            self._context_timestamp = target_time
            return

        delta = float(target_time - self._context_timestamp)
        if delta <= 0.0:
            return

        decay = math.exp(-self._decay_lambda * delta)
        self.context = (self.context * decay).astype("float32", copy=False)
        self._context_timestamp = target_time

    def _record_state_metrics(self) -> None:
        anchor_count = len(self._anchors)
        capacity = (
            0.0
            if self.cfg.max_anchors <= 0
            else anchor_count / float(self.cfg.max_anchors)
        )

        if anchor_count == 0:
            snr_db = 0.0
        else:
            signal = float(np.linalg.norm(self.context))
            noise = math.sqrt(anchor_count / max(1, self.q.cfg.dim))
            if noise <= 1e-12 or signal <= 1e-12:
                snr_db = 0.0
            else:
                snr_ratio = max(signal / noise, 1e-12)
                snr_db = 20.0 * math.log10(snr_ratio)

        ContextMetrics.observe_state(self._context_id, anchor_count, capacity, snr_db)

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(vec))
        if norm <= 1e-12:
            return np.zeros_like(vec)
        return (vec / norm).astype("float32", copy=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def admit(
        self, anchor_id: str, vec: np.ndarray, *, timestamp: float | None = None
    ) -> None:
        """Admit a new anchor vector and update the context state."""

        ts = float(timestamp) if timestamp is not None else self._now()
        self._apply_decay(ts)

        updated = self.context + vec.astype("float32", copy=False)
        self.context = self._normalize(updated)
        self._context_timestamp = ts

        # maintain anchors as LRU capped by max_anchors
        self._anchors[anchor_id] = vec
        self._anchors.move_to_end(anchor_id)
        self._anchor_times[anchor_id] = ts
        self._anchor_times.move_to_end(anchor_id)
        while len(self._anchors) > self.cfg.max_anchors:
            old_id, _ = self._anchors.popitem(last=False)
            self._anchor_times.pop(old_id, None)

        self._record_state_metrics()

    def novelty(self, vec: np.ndarray) -> float:
        self._apply_decay(self._now())
        return max(0.0, 1.0 - self.q.cosine(vec, self.context))

    def _evaluate_cleanup(self, query_vec: np.ndarray, now: float) -> CleanupResult:
        best_id = ""
        best_score = -1.0
        second_score = -1.0

        for key, vec in self._anchors.items():
            candidate = vec.astype("float32", copy=False)
            base = self.q.cosine(query_vec, candidate)
            if self._decay_lambda > 0.0:
                age = now - self._anchor_times.get(key, now)
                weight = math.exp(-self._decay_lambda * max(0.0, age))
            else:
                weight = 1.0
            score = base * weight

            if score > best_score:
                second_score = best_score
                best_score = score
                best_id = key
            elif score > second_score:
                second_score = score

        if best_score < 0.0:
            best_score = 0.0
        if second_score < 0.0:
            second_score = 0.0
        return CleanupResult(best_id, float(best_score), float(second_score))

    def analyze(self, query: np.ndarray) -> CleanupResult:
        now = self._now()
        self._apply_decay(now)
        query_vec = query.astype("float32", copy=False)
        result = self._evaluate_cleanup(query_vec, now)
        ContextMetrics.record_cleanup(
            self._context_id,
            result.best_score,
            result.second_score,
            self._min_confidence,
        )
        return result

    def cleanup(self, query: np.ndarray) -> Tuple[str, float]:
        result = self.analyze(query)
        if result.best_score < self._min_confidence:
            return CleanupResult("", 0.0, result.second_score)
        return result

    def stats(self) -> tuple[int, int]:
        """Return (anchor_count, max_anchors)."""
        self._apply_decay(self._now())
        self._record_state_metrics()
        return (len(self._anchors), int(self.cfg.max_anchors))
