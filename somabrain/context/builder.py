"""Context bundle construction for SomaBrain.

Builds multi-view retrieval results (semantic, graph, temporal) and produces
structured bundles that the agent can feed into its SLM.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np

from brain.adapters.memstore_adapter import MemstoreAdapter


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
        memstore: Optional[MemstoreAdapter] = None,
        weights: Optional[RetrievalWeights] = None,
        working_memory: Optional["WorkingMemoryBuffer"] = None,
    ) -> None:
        self._embed_fn = embed_fn
        self._memstore = memstore or MemstoreAdapter()
        self._weights = weights or RetrievalWeights()
        self._working_memory = working_memory

    def build(  # noqa: PLR0914
        self,
        query: str,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> ContextBundle:
        embedding = self._embed(query)
        results = self._search(embedding, top_k)
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

    def _search(self, embedding: List[float], top_k: int) -> List[Dict]:
        try:
            return self._memstore.search(embedding, top_k=top_k)
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
            combined = alpha * cos + beta * g_score + gamma * age_penalty
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

    @staticmethod
    def _temporal_decay(ts: float) -> float:
        if ts <= 0:
            return 0.0
        age = max(time.time() - ts, 0.0)
        # Exponential decay with 24h half-life
        half_life = 86400.0
        return math.exp(-age / half_life)


try:  # circular import guard
    from somabrain.runtime.working_memory import WorkingMemoryBuffer
except Exception:  # pragma: no cover - runtime optional during static analysis
    WorkingMemoryBuffer = None  # type: ignore
