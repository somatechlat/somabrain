"""Context bundle construction for SomaBrain.

Builds multi-view retrieval results (semantic, graph, temporal) and produces
structured bundles that the agent can feed into its SLM.
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np

from somabrain.context.memory_shim import MemoryRecallClient

try:  # optional import; falls back to defaults during lightweight tests
    from somabrain.config import get_config as _get_config
except (
    Exception
):  # pragma: no cover - config module may not be loaded in some unit tests
    _get_config = None


@dataclass
class RetrievalWeights:
    alpha: float = 1.0
    beta: float = 0.2
    gamma: float = 0.1
    tau: float = 0.7


@dataclass
class MemoryRecord:
    id: str
    score: float
    metadata: Dict
    embedding: Optional[List[float]] = None


@dataclass
class ContextBundle:
    query: str
    prompt: str
    memories: List[MemoryRecord]
    weights: List[float]
    residual_vector: List[float]
    working_memory_snapshot: List[Dict]


class ContextBuilder:
    """Construct multi-view context bundles for agent requests."""

    def __init__(
        self,
        embed_fn: Callable[[str], Iterable[float]],
        memory: Optional[object] = None,
        weights: Optional[RetrievalWeights] = None,
        working_memory: Optional["WorkingMemoryBuffer"] = None,
    ) -> None:
        self._embed_fn = embed_fn
        self._memory = memory or MemoryRecallClient()
        self._weights = weights or RetrievalWeights()
        self._working_memory = working_memory
        # Tenant identifier for per‑tenant metrics (default placeholder)
        self._tenant_id: str = "default"
        # Align temporal decay and density penalties with runtime configuration when available
        self._recency_half_life = 60.0
        self._recency_sharpness = 1.2
        self._recency_floor = 0.05
        self._density_target = 0.2
        self._density_floor = 0.6
        self._density_weight = 0.35
        self._tau_min = 0.4
        self._tau_max = 1.2
        self._tau_increment_up = 0.1
        self._tau_increment_down = 0.05
        self._dup_ratio_threshold = 0.5
        try:
            cfg = _get_config() if _get_config else None
            if cfg is not None:
                self._recency_half_life = float(
                    getattr(cfg, "recall_recency_time_scale", self._recency_half_life)
                )
                self._recency_sharpness = float(
                    getattr(cfg, "recall_recency_sharpness", self._recency_sharpness)
                )
                self._recency_floor = float(
                    getattr(cfg, "recall_recency_floor", self._recency_floor)
                )
                self._density_target = float(
                    getattr(cfg, "recall_density_margin_target", self._density_target)
                )
                self._density_floor = float(
                    getattr(cfg, "recall_density_margin_floor", self._density_floor)
                )
                self._density_weight = float(
                    getattr(cfg, "recall_density_margin_weight", self._density_weight)
                )
                self._tau_min = float(
                    getattr(cfg, "recall_tau_min", self._tau_min)
                )
                self._tau_max = float(
                    getattr(cfg, "recall_tau_max", self._tau_max)
                )
                self._tau_increment_up = float(
                    getattr(
                        cfg, "recall_tau_increment_up", self._tau_increment_up
                    )
                )
                self._tau_increment_down = float(
                    getattr(
                        cfg, "recall_tau_increment_down", self._tau_increment_down
                    )
                )
                self._dup_ratio_threshold = float(
                    getattr(
                        cfg,
                        "recall_tau_dup_ratio_threshold",
                        self._dup_ratio_threshold,
                    )
                )
        except Exception:
            # Fallback to defaults when configuration cannot be loaded
            pass
        def _env_float(name: str, current: float) -> float:
            value = os.getenv(name)
            if value is None:
                return current
            try:
                return float(value)
            except Exception:
                return current

        # Environment overrides for tau tuning
        self._tau_min = _env_float("SOMABRAIN_RECALL_TAU_MIN", self._tau_min)
        self._tau_max = _env_float("SOMABRAIN_RECALL_TAU_MAX", self._tau_max)
        self._tau_increment_up = _env_float(
            "SOMABRAIN_RECALL_TAU_INCREMENT_UP", self._tau_increment_up
        )
        self._tau_increment_down = _env_float(
            "SOMABRAIN_RECALL_TAU_INCREMENT_DOWN", self._tau_increment_down
        )
        self._dup_ratio_threshold = _env_float(
            "SOMABRAIN_RECALL_TAU_DUP_RATIO_THRESHOLD",
            self._dup_ratio_threshold,
        )
        # Clamp derived parameters into safe ranges to avoid pathological curves
        if not math.isfinite(self._recency_half_life) or self._recency_half_life <= 0:
            self._recency_half_life = 60.0
        if not math.isfinite(self._recency_sharpness) or self._recency_sharpness <= 0:
            self._recency_sharpness = 1.2
        if not math.isfinite(self._recency_floor) or self._recency_floor < 0:
            self._recency_floor = 0.05
        self._recency_floor = min(self._recency_floor, 0.99)
        if not math.isfinite(self._density_target) or self._density_target <= 0:
            self._density_target = 0.2
        if not math.isfinite(self._density_floor) or self._density_floor < 0:
            self._density_floor = 0.6
        self._density_floor = min(self._density_floor, 1.0)
        if not math.isfinite(self._density_weight) or self._density_weight < 0:
            self._density_weight = 0.35
        if not math.isfinite(self._tau_min):
            self._tau_min = 0.4
        if not math.isfinite(self._tau_max) or self._tau_max <= 0:
            self._tau_max = 1.2
        if self._tau_max < self._tau_min:
            self._tau_max = max(self._tau_min, 1.2)
        if not math.isfinite(self._tau_increment_up):
            self._tau_increment_up = 0.1
        if not math.isfinite(self._tau_increment_down):
            self._tau_increment_down = 0.05
        if not math.isfinite(self._dup_ratio_threshold):
            self._dup_ratio_threshold = 0.5
        self._dup_ratio_threshold = min(max(self._dup_ratio_threshold, 0.0), 1.0)

    # New method to set the tenant for the current request
    def set_tenant(self, tenant_id: str) -> None:
        """Store the tenant ID so weight updates can be attributed correctly."""
        if tenant_id:
            self._tenant_id = tenant_id

    def build(  # noqa: PLR0914
        self,
        query: str,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> ContextBundle:
        embedding = self._embed(query)
        results = self._search(query, embedding, top_k)
        memories: List[MemoryRecord] = [
            MemoryRecord(
                id=r.get("id", ""),
                score=float(r.get("score", 0.0)),
                metadata=r.get("metadata", {}) or {},
                embedding=r.get("embedding"),
            )
            for r in results
        ]
        weights = self._compute_weights(embedding, memories)
        prompt = self._build_prompt(query, memories)
        residual = self._build_residual(weights, memories)
        wm_snapshot: List[Dict] = []
        if self._working_memory and session_id:
            item = {
                "ts": time.time(),
                "query": query,
                "prompt": prompt,
                "memory_ids": [m.id for m in memories],
            }
            self._working_memory.record(session_id, item)
            wm_snapshot = self._working_memory.snapshot(session_id)
        return ContextBundle(
            query=query,
            prompt=prompt,
            memories=memories,
            weights=weights,
            residual_vector=residual,
            working_memory_snapshot=wm_snapshot,
        )

    @property
    def weights(self) -> RetrievalWeights:
        return self._weights

    # ------------------------------------------------------------------
    def _embed(self, text: str) -> List[float]:
        raw = list(self._embed_fn(text))
        if not raw:
            raise RuntimeError("embedding function returned empty vector")
        return [float(v) for v in raw]

    def _search(self, query_text: str, embedding: List[float], top_k: int) -> List[Dict]:
        # Prefer text search on the live memory service when possible, with tenant scoping
        try:
            filters = {"tenant": self._tenant_id} if getattr(self, "_tenant_id", None) else None
            results = self._memory.search_text(query_text, top_k=top_k, filters=filters)
            if results:
                return results
        except Exception:
            pass
        # Fallback to legacy vector search path
        try:
            return self._memory.search(embedding, top_k=top_k)
        except Exception:
            return []

    def _compute_weights(
        self,
        query_vec: List[float],
        memories: List[MemoryRecord],
    ) -> List[float]:
        alpha, beta, gamma, tau = (
            self._weights.alpha,
            self._weights.beta,
            self._weights.gamma,
            self._weights.tau,
        )
        query = np.array(query_vec, dtype="float32")
        if np.linalg.norm(query) == 0:
            query = np.ones_like(query)
        raw_scores: List[float] = []
        for mem in memories:
            vec = np.array(mem.embedding or [], dtype="float32")
            cos = self._cosine(query, vec)
            g_score = float(mem.metadata.get("graph_score", 0.0))
            ts = float(mem.metadata.get("timestamp", 0.0))
            age_penalty = self._temporal_decay(ts)
            density_factor = self._density_factor(mem.metadata)
            combined = (
                alpha * cos + beta * g_score + gamma * age_penalty
            ) * density_factor
            if density_factor != 1.0:
                try:
                    mem.metadata.setdefault("_density_factor", density_factor)
                except Exception:
                    pass
            raw_scores.append(combined)
        if not raw_scores:
            return []
        scores = np.array(raw_scores, dtype="float32")
        scores = scores - scores.max()
        weights = np.exp(scores / max(tau, 1e-6))
        weights_sum = weights.sum()
        if weights_sum == 0:
            return [1.0 / len(weights)] * len(weights)
        normalized = weights / weights_sum

        # ==== Tau adaptation for diversity ====
        # Simple heuristic: increase tau when many duplicate memory IDs are returned.
        # This encourages a higher temperature (more exploration) when diversity is low.
        try:
            ids = [m.id for m in memories]
            unique = len(set(ids))
            dup_ratio = 1.0 - (unique / max(len(ids), 1))
        except Exception:
            dup_ratio = 0.0
        # Adjust tau within the configured range.
        if dup_ratio > self._dup_ratio_threshold:
            excess = dup_ratio - self._dup_ratio_threshold
            step = max(self._tau_increment_up, 0.0) * excess
            new_tau = min(self._weights.tau + step, self._tau_max)
        else:
            deficit = self._dup_ratio_threshold - dup_ratio
            step = max(self._tau_increment_down, 0.0) * deficit
            new_tau = max(self._weights.tau - step, self._tau_min)
        self._weights.tau = new_tau
        # Emit metric for the current tenant (import inside to respect monkeypatch)
        from somabrain.metrics import (
            update_learning_retrieval_weights as _update_metric,
        )

        _update_metric(
            tenant_id=self._tenant_id,
            alpha=self._weights.alpha,
            beta=self._weights.beta,
            gamma=self._weights.gamma,
            tau=self._weights.tau,
        )
        return normalized.tolist()

    def _build_prompt(self, query: str, memories: List[MemoryRecord]) -> str:
        context_blocks: List[str] = []
        for mem in memories:
            meta = mem.metadata or {}
            text = meta.get("text") or meta.get("content")
            if text:
                header = meta.get("title") or mem.id
                context_blocks.append(f"[{header}]\n{text}")
        if context_blocks:
            context_section = "\n\n".join(context_blocks)
            return f"Context:\n{context_section}\n\nQuery:\n{query}"
        return query

    def _build_residual(
        self,
        weights: List[float],
        memories: List[MemoryRecord],
    ) -> List[float]:
        if not weights or not memories:
            return []
        dim = len(memories[0].embedding or [])
        if dim == 0:
            return []
        accum = np.zeros(dim, dtype="float32")
        for w, mem in zip(weights, memories, strict=False):
            vec = np.array(mem.embedding or np.zeros(dim), dtype="float32")
            accum += w * vec
        norm = np.linalg.norm(accum)
        if norm > 0:
            accum /= norm
        return accum.tolist()

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        if b.size == 0:
            return 0.0
        if a.shape != b.shape:
            min_dim = min(a.size, b.size)
            if min_dim == 0:
                return 0.0
            a = a[:min_dim]
            b = b[:min_dim]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def _temporal_decay(self, ts: float) -> float:
        if ts <= 0:
            return max(self._recency_floor, 0.0)
        age = max(time.time() - ts, 0.0)
        half_life = max(self._recency_half_life, 1e-6)
        try:
            normalised = age / half_life
            if normalised <= 0:
                return 1.0
            damp = math.exp(-(normalised ** max(self._recency_sharpness, 1e-3)))
        except Exception:
            damp = 0.0
        return float(max(self._recency_floor, min(1.0, damp)))

    def _density_factor(self, metadata: Dict) -> float:
        if not isinstance(metadata, dict):
            return 1.0
        margin = metadata.get("_cleanup_margin")
        if margin is None:
            margin = metadata.get("cleanup_margin")
        try:
            margin_val = float(margin)
        except Exception:
            return 1.0
        if not math.isfinite(margin_val) or margin_val < 0:
            return 1.0
        target = max(self._density_target, 1e-6)
        if margin_val >= target:
            return 1.0
        floor = max(0.0, min(self._density_floor, 1.0))
        weight = max(self._density_weight, 0.0)
        deficit = (target - margin_val) / target
        penalty = 1.0 - (weight * deficit)
        return float(max(floor, min(1.0, penalty)))


try:  # circular import guard
    from somabrain.runtime.working_memory import WorkingMemoryBuffer
except Exception:  # pragma: no cover - runtime optional during static analysis
    WorkingMemoryBuffer = None  # type: ignore
