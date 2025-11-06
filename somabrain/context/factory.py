"""Shared builders for context and planning."""

from __future__ import annotations

from functools import lru_cache
import os

from somabrain.context.memory_shim import MemoryRecallClient
from somabrain.context.builder import ContextBuilder, RetrievalWeights
from somabrain.context.planner import ContextPlanner
from somabrain.learning import UtilityWeights
from somabrain.runtime.working_memory import WorkingMemoryBuffer
from somabrain.config import get_config
from somabrain.embeddings import make_embedder


_embedder = None
try:
    # Use production embedder by default; allow tiny embedder only when explicitly enabled.
    if (os.getenv("SOMABRAIN_ALLOW_TINY_EMBEDDER", "").strip().lower() in ("1","true","yes","on")):
        from somabrain.embeddings import TinyDeterministicEmbedder
        _embedder = TinyDeterministicEmbedder(dim=256)
    else:
        _embedder = make_embedder(get_config(), quantum=None)
except Exception:
    from somabrain.embeddings import TinyDeterministicEmbedder
    _embedder = TinyDeterministicEmbedder(dim=256)
_working_memory = WorkingMemoryBuffer()
_retrieval_weights = RetrievalWeights()
_utility_weights = UtilityWeights()


@lru_cache(maxsize=1)
def get_context_builder() -> ContextBuilder:
    memory = MemoryRecallClient()
    return ContextBuilder(
        embed_fn=_embedder.embed,
        memory=memory,
        weights=_retrieval_weights,
        working_memory=_working_memory,
    )


@lru_cache(maxsize=1)
def get_context_planner() -> ContextPlanner:
    return ContextPlanner(utility_weights=_utility_weights)
