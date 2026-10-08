"""Shared builders for context and planning."""

from __future__ import annotations

from functools import lru_cache

# Unified configuration – use the central Settings instance
from django.conf import settings

from somabrain.admin.core.embeddings import make_embedder
from somabrain.embed_dim import resolve_embed_dim
from somabrain.admin.cognitive.working_memory_buffer import WorkingMemoryBuffer
from somabrain.context.builder import ContextBuilder, RetrievalWeights
from somabrain.context.planner import ContextPlanner
from somabrain.learning import UtilityWeights
from somabrain.memory.pool import MultiTenantMemory

_embedder = None
try:
    # HRR/QuantumLayer is the DEFAULT brain path (Operator: always on).
    # Tiny embed is only a fallback when HRR is explicitly disabled or init fails.
    from somabrain.bootstrap.singletons import make_quantum_layer

    _quantum = make_quantum_layer(settings)
    if _quantum is not None:
        _embedder = make_embedder(settings, quantum=_quantum)
    else:
        # Explicit disable or HRR init failure — last-resort tiny (FAIL HONEST).
        import logging

        logging.getLogger(__name__).error(
            "HRR/QuantumLayer UNAVAILABLE — falling back to TinyDeterministicEmbedder. "
            "Operator law: HRR is default. Investigate immediately."
        )
        from somabrain.admin.core.embeddings import TinyDeterministicEmbedder

        _embedder = TinyDeterministicEmbedder(dim=resolve_embed_dim())
except Exception:
    import logging

    logging.getLogger(__name__).exception(
        "HRR/QuantumLayer init FAILED — TinyDeterministicEmbedder fallback (NOT silent)."
    )
    from somabrain.admin.core.embeddings import TinyDeterministicEmbedder

    _embedder = TinyDeterministicEmbedder(dim=resolve_embed_dim())
_working_memory = WorkingMemoryBuffer()
_retrieval_weights = RetrievalWeights(
    alpha=float(getattr(settings, "SOMABRAIN_RETRIEVAL_ALPHA")),
    beta=float(getattr(settings, "SOMABRAIN_RETRIEVAL_BETA")),
    gamma=float(getattr(settings, "SOMABRAIN_RETRIEVAL_GAMMA")),
    tau=float(getattr(settings, "SOMABRAIN_RETRIEVAL_TAU")),
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
