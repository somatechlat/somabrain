"""Shared builders for context and planning."""

from __future__ import annotations

from functools import lru_cache

from somabrain.context.builder import ContextBuilder, RetrievalWeights
from somabrain.context.planner import ContextPlanner
from somabrain.learning import UtilityWeights
from somabrain.cognitive.working_memory_buffer import WorkingMemoryBuffer

# Unified configuration – use the central Settings instance
from django.conf import settings
from somabrain.embeddings import make_embedder
from somabrain.memory_pool import MultiTenantMemory


_embedder = None
try:
    # Use production embedder by default; allow tiny embedder only when explicitly enabled.
    # Use Settings attribute "allow_tiny_embedder" (bool) instead of getenv.
    if getattr(settings, "allow_tiny_embedder", False):
        from somabrain.embeddings import TinyDeterministicEmbedder

        _embedder = TinyDeterministicEmbedder(dim=256)
    else:
        _embedder = make_embedder(settings, quantum=None)
except Exception:
    from somabrain.embeddings import TinyDeterministicEmbedder

    _embedder = TinyDeterministicEmbedder(dim=256)
_working_memory = WorkingMemoryBuffer()
_retrieval_weights = RetrievalWeights(
    alpha=float(getattr(settings, "retrieval_alpha", 1.0)),
    beta=float(getattr(settings, "retrieval_beta", 0.3)),
    gamma=float(getattr(settings, "retrieval_gamma", 0.1)),
    tau=float(getattr(settings, "retrieval_tau", 0.8)),
)
_utility_weights = UtilityWeights()
_memory_backend = MultiTenantMemory(cfg=settings)


@lru_cache(maxsize=1)
def get_context_builder() -> ContextBuilder:
    """Retrieve context builder."""

    return ContextBuilder(
        embed_fn=_embedder.embed,
        memory_backend=_memory_backend,
        weights=_retrieval_weights,
        working_memory=_working_memory,
    )


@lru_cache(maxsize=1)
def get_context_planner() -> ContextPlanner:
    """Retrieve context planner."""

    return ContextPlanner(utility_weights=_utility_weights)
