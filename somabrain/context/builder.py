"""Context bundle construction for SomaBrain.

Builds multi-view retrieval results (semantic, graph, temporal) and produces
structured bundles that the agent can feed into its SLM.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional

import numpy as np
from cachetools import TTLCache

# Unified configuration – use the central Settings instance
from django.conf import settings

from somabrain.math import cosine_similarity
from somabrain.apps.memory.client import RecallHit
from somabrain.apps.memory.pool import MultiTenantMemory
from somabrain.services.memory_service import MemoryService

# VIBE Compliance: Use TYPE_CHECKING for forward references to avoid circular imports
if TYPE_CHECKING:
    from somabrain.cognitive.working_memory_buffer import WorkingMemoryBuffer


@dataclass
class RetrievalWeights:
    """Retrievalweights class implementation."""

    alpha: float
    beta: float
    gamma: float
    tau: float


@dataclass
class MemoryRecord:
    """Memoryrecord class implementation."""

    id: str
    score: float
    metadata: Dict
    embedding: Optional[List[float]] = None


@dataclass
class ContextBundle:
    """Contextbundle class implementation."""

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
        memory_backend: Optional[MultiTenantMemory] = None,
        weights: Optional[RetrievalWeights] = None,
        working_memory: Optional["WorkingMemoryBuffer"] = None,
    ) -> None:
        """Initialize the instance."""

        self._embed_fn = embed_fn
        self._memory = memory
        self._memory_backend = memory_backend
        self._memory_service: Optional[MemoryService] = None
        if self._memory is None and self._memory_backend is None:
            self._memory_backend = MultiTenantMemory(cfg=settings)
        self._weights = weights or RetrievalWeights(
            settings.SOMABRAIN_RETRIEVAL_ALPHA,
            settings.SOMABRAIN_RETRIEVAL_BETA,
            settings.SOMABRAIN_RETRIEVAL_GAMMA,
            settings.SOMABRAIN_RETRIEVAL_TAU,
        )
        self._working_memory = working_memory
        # Tenant identifier for per‑tenant metrics (default value)
        self._tenant_id: str = getattr(settings, "SOMABRAIN_DEFAULT_TENANT", "public")
        # Align temporal decay and density penalties with runtime configuration when available
        self._recency_half_life = settings.retrieval_recency_half_life
        self._recency_sharpness = settings.retrieval_recency_sharpness
        self._recency_floor = settings.retrieval_recency_floor
        self._density_target = settings.retrieval_density_target
        self._density_floor = settings.retrieval_density_floor
        self._density_weight = settings.retrieval_density_weight
        self._tau_min = settings.SOMABRAIN_RETRIEVAL_TAU_min
        self._tau_max = settings.SOMABRAIN_RETRIEVAL_TAU_max
        self._tau_increment_up = settings.SOMABRAIN_RETRIEVAL_TAU_increment_up
        self._tau_increment_down = settings.SOMABRAIN_RETRIEVAL_TAU_increment_down
        self._dup_ratio_threshold = settings.retrieval_dup_ratio_threshold
        # Per-tenant overrides cache (learning.tenants.yaml)
        # Uses somabrain.context.tenant_overrides for loading
        # Bounded TTLCache: max 1000 tenants, 5 minute TTL for config reload
        self._tenant_overrides_cache: TTLCache[str, Dict] = TTLCache(
            maxsize=1000, ttl=300
        )

        def _env_float(name: str, current: float) -> float:
            # Use Settings attribute if available; fall back to None.
            # Environment variable names are uppercase; Settings uses snake_case.
            """Execute env float.

            Args:
                name: The name.
                current: The current.
            """

            attr_name = name.lower()
            value = getattr(settings, attr_name, None)
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
        if self._memory is None and self._memory_backend is not None:
            namespace = self._namespace_for_tenant(self._tenant_id)
            self._memory_service = MemoryService(self._memory_backend, namespace)

    def build(  # noqa: PLR0914
        self,
        query: str,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> ContextBundle:
        """Execute build.

        Args:
            query: The query.
            top_k: The top_k.
            session_id: The session_id.
        """

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
        """Execute weights."""

        return self._weights

    # ------------------------------------------------------------------
    def _embed(self, text: str) -> List[float]:
        """Execute embed.

        Args:
            text: The text.
        """

        raw = list(self._embed_fn(text))
        if not raw:
            raise RuntimeError("embedding function returned empty vector")
        return [float(v) for v in raw]

    def _namespace_for_tenant(self, tenant_id: str) -> str:
        """Execute namespace for tenant.

        Args:
            tenant_id: The tenant_id.
        """

        base = getattr(settings, "SOMABRAIN_NAMESPACE", "public") or "public"
        tid = str(tenant_id or getattr(settings, "SOMABRAIN_DEFAULT_TENANT", "public"))
        return f"{base}:{tid}"

    def _memory_component(self) -> object:
        """Execute memory component."""

        if self._memory is not None:
            return self._memory
        if self._memory_backend is None:
            self._memory_backend = MultiTenantMemory(cfg=settings)
        if self._memory_service is None:
            namespace = self._namespace_for_tenant(self._tenant_id)
            self._memory_service = MemoryService(self._memory_backend, namespace)
        return self._memory_service

    def _search(
        self, query_text: str, embedding: List[float], top_k: int
    ) -> List[Dict[str, Any]]:
        """Execute search.

        Args:
            query_text: The query_text.
            embedding: The embedding.
            top_k: The top_k.
        """

        memory_component = self._memory_component()
        try:
            if hasattr(memory_component, "recall_with_scores"):
                hits = memory_component.recall_with_scores(query_text, top_k=top_k)
            else:
                hits = memory_component.recall(query_text, top_k=top_k)
            return self._hits_to_results(hits)
        except Exception:
            return []

    def _hits_to_results(self, hits: Iterable[RecallHit]) -> List[Dict[str, Any]]:
        """Execute hits to results.

        Args:
            hits: The hits.
        """

        tenant = getattr(self, "_tenant_id", None) or None
        results: List[Dict[str, Any]] = []
        for idx, hit in enumerate(hits):
            payload = hit.payload if isinstance(hit.payload, dict) else {}
            if tenant and payload.get("tenant") not in (tenant, None):
                continue
            score = hit.score if isinstance(hit.score, (int, float)) else 0.0
            coord = payload.get("coordinate") or payload.get("coord") or None
            results.append(
                {
                    "id": coord or f"mem-{idx}",
                    "score": float(score),
                    "metadata": payload,
                    "embedding": None,
                }
            )
        return results

    def _compute_weights(
        self,
        query_vec: List[float],
        memories: List[MemoryRecord],
    ) -> List[float]:
        """Execute compute weights.

        Args:
            query_vec: The query_vec.
            memories: The memories.
        """

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
            cos = cosine_similarity(query, vec)
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

        # ==== Apply per-tenant entropy cap on retrieval parameter vector (alpha,beta,gamma,tau) ====
        try:
            cap = self._get_entropy_cap_for_tenant(self._tenant_id)
        except Exception:
            cap = None
        entropy_exceeded = False
        if isinstance(cap, (int, float)) and cap > 0.0:
            try:
                import math as _m

                vec = [
                    max(1e-9, float(self._weights.alpha)),
                    max(1e-9, float(self._weights.beta)),
                    max(1e-9, float(self._weights.gamma)),
                    max(1e-9, float(self._weights.tau)),
                ]
                s = sum(vec)
                probs = [v / s for v in vec]
                H = -sum(p * _m.log(p) for p in probs)
                if H > float(cap):
                    entropy_exceeded = True
                    # Iteratively sharpen non-max components while preserving max component
                    largest_idx = max(range(len(vec)), key=lambda i: vec[i])
                    attempts = 0
                    entropy = H
                    while entropy > float(cap) and attempts < 10:
                        overflow = entropy - float(cap)
                        scale = min(0.99, max(0.2, overflow / (float(cap) + 1e-9)))
                        for i in range(len(vec)):
                            if i != largest_idx:
                                vec[i] *= 1.0 - scale
                        s2 = sum(vec)
                        if s2 > 0:
                            vec = [v / s2 for v in vec]
                        probs = [v / sum(vec) for v in vec]
                        entropy = -sum(p * _m.log(p) for p in probs)
                        attempts += 1
                    if entropy > float(cap):
                        # Final strong sharpen if still resistant
                        for i in range(len(vec)):
                            if i != largest_idx:
                                vec[i] *= 0.05
                        s2 = sum(vec)
                        if s2 > 0:
                            vec = [v / s2 for v in vec]
                    (
                        self._weights.alpha,
                        self._weights.beta,
                        self._weights.gamma,
                        self._weights.tau,
                    ) = (
                        float(vec[0]),
                        float(vec[1]),
                        float(vec[2]),
                        float(vec[3]),
                    )
            except Exception:
                pass
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
        try:
            from somabrain.metrics import LEARNING_ENTROPY_CAP_HITS, LEARNING_TAU

            if hasattr(LEARNING_TAU, "labels"):
                LEARNING_TAU.labels(tenant_id=self._tenant_id).set(self._weights.tau)
            else:
                LEARNING_TAU.set(self._weights.tau)
            if entropy_exceeded:
                LEARNING_ENTROPY_CAP_HITS.labels(tenant_id=self._tenant_id).inc()
        except Exception:
            pass
        return normalized.tolist()

    # ---------------- Tenant overrides helpers ----------------
    def _get_entropy_cap_for_tenant(self, tenant_id: str) -> Optional[float]:
        """Read entropy_cap from SOMABRAIN_LEARNING_TENANTS_FILE or env overrides."""
        from somabrain.context.tenant_overrides import get_entropy_cap_for_tenant

        return get_entropy_cap_for_tenant(tenant_id, self._tenant_overrides_cache)

    def _build_prompt(self, query: str, memories: List[MemoryRecord]) -> str:
        """Execute build prompt.

        Args:
            query: The query.
            memories: The memories.
        """

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
        """Execute build residual.

        Args:
            weights: The weights.
            memories: The memories.
        """

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

    def _temporal_decay(self, ts: float) -> float:
        """Execute temporal decay.

        Args:
            ts: The ts.
        """

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
        """Execute density factor.

        Args:
            metadata: The metadata.
        """

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
