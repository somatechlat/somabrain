"""Hierarchical working/long-term memory coordination.

Implements the tiered memory behaviours described in the v3.0 roadmap. The
primary entry point is :class:`TieredMemory`, which wraps two
:class:`~somabrain.memory.superposed_trace.SuperposedTrace` instances—one for
Working Memory (WM) and one for Long-Term Memory (LTM)—and exposes a hierarchical
recall path with optional promotion hooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from .superposed_trace import SuperposedTrace, TraceConfig


@dataclass(frozen=True)
class LayerPolicy:
    """Policy parameters for a memory layer."""

    threshold: float = 0.65  # minimum cleanup score required to accept the hit
    promote_margin: float = 0.1  # margin requirement to promote into the next tier

    def validate(self) -> "LayerPolicy":
        thr = float(self.threshold)
        if not 0.0 <= thr <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        margin = float(self.promote_margin)
        if margin < 0.0:
            raise ValueError("promote_margin must be non-negative")
        return LayerPolicy(threshold=thr, promote_margin=margin)


@dataclass
class RecallContext:
    """Result of a hierarchical recall attempt."""

    layer: str
    anchor_id: str
    score: float
    second_score: float
    raw: np.ndarray

    @property
    def margin(self) -> float:
        return max(0.0, float(self.score) - float(self.second_score))


class TieredMemory:
    """Coordinates WM and LTM layers for governed recall."""

    def __init__(
        self,
        wm_cfg: TraceConfig,
        ltm_cfg: TraceConfig,
        *,
        wm_policy: LayerPolicy | None = None,
        ltm_policy: LayerPolicy | None = None,
        promotion_callback: Optional[Callable[[RecallContext], bool]] = None,
    ) -> None:
        self.wm = SuperposedTrace(wm_cfg)
        self.ltm = SuperposedTrace(ltm_cfg)
        self._wm_policy = (wm_policy or LayerPolicy()).validate()
        self._ltm_policy = (ltm_policy or LayerPolicy(threshold=0.55, promote_margin=0.05)).validate()
        self._promotion_callback = promotion_callback

    # ------------------------------------------------------------------
    # Memory operations
    # ------------------------------------------------------------------
    def remember(self, anchor_id: str, key: np.ndarray, value: np.ndarray) -> None:
        """Store an item in working memory, optionally promoting to LTM."""

        key_vec = self._ensure_vector(key, self.wm.cfg.dim, "key")
        value_vec = self._ensure_vector(value, self.wm.cfg.dim, "value")

        self.wm.register_anchor(anchor_id, value_vec)
        self.wm.upsert(anchor_id, key_vec, value_vec)

        wm_result = self._recall_internal(self.wm, key_vec, layer="wm")

        if self._should_promote(wm_result):
            # Ensure value matches LTM dimensionality if different
            value_ltm = self._ensure_vector(value, self.ltm.cfg.dim, "value_ltm")
            key_ltm = self._ensure_vector(key, self.ltm.cfg.dim, "key_ltm")
            self.ltm.register_anchor(anchor_id, value_ltm)
            self.ltm.upsert(anchor_id, key_ltm, value_ltm)

    def recall(self, key: np.ndarray) -> RecallContext:
        """Recall via WM, falling back to LTM when necessary."""

        key_wm = self._ensure_vector(key, self.wm.cfg.dim, "key_wm")
        wm_hit = self._recall_internal(self.wm, key_wm, layer="wm")
        if wm_hit.score >= self._wm_policy.threshold:
            return wm_hit

        key_ltm = self._ensure_vector(key, self.ltm.cfg.dim, "key_ltm")
        ltm_hit = self._recall_internal(self.ltm, key_ltm, layer="ltm")
        if ltm_hit.score >= self._ltm_policy.threshold:
            return ltm_hit

        # Neither layer passes threshold; return best WM hit for diagnostics
        return wm_hit

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _recall_internal(self, trace: SuperposedTrace, key: np.ndarray, *, layer: str) -> RecallContext:
        raw, (anchor_id, best, second) = trace.recall(key)
        return RecallContext(layer=layer, anchor_id=anchor_id, score=best, second_score=second, raw=raw)

    def _should_promote(self, result: RecallContext) -> bool:
        if result.score < self._wm_policy.threshold:
            return False
        if result.margin < self._wm_policy.promote_margin:
            return False
        if self._promotion_callback is not None:
            return bool(self._promotion_callback(result))
        return True

    @staticmethod
    def _ensure_vector(vec: np.ndarray, dim: int, name: str) -> np.ndarray:
        if not isinstance(vec, np.ndarray):
            raise TypeError(f"{name} must be a numpy.ndarray")
        arr = vec.astype(np.float32, copy=False)
        if arr.ndim != 1:
            raise ValueError(f"{name} must be a 1-D vector")
        if arr.shape[0] < dim:
            pad = np.zeros((dim - arr.shape[0],), dtype=np.float32)
            arr = np.concatenate([arr, pad])
        elif arr.shape[0] > dim:
            arr = arr[:dim]
        norm = float(np.linalg.norm(arr))
        if norm <= 0.0:
            raise ValueError(f"{name} must have non-zero norm")
        return arr / norm


__all__ = ["LayerPolicy", "RecallContext", "TieredMemory"]
