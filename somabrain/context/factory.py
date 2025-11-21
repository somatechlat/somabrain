"""Shared builders for context and planning."""

from __future__ import annotations

from functools import lru_cache
import os

from somabrain.context.builder import ContextBuilder, RetrievalWeights
from somabrain.context.planner import ContextPlanner
from somabrain.learning import UtilityWeights
from somabrain.runtime.working_memory import WorkingMemoryBuffer
# Unified configuration – use the central Settings instance
from common.config.settings import settings
from somabrain.embeddings import make_embedder
from somabrain.memory_client import MemoryClient


_embedder = None
try:
    # Use production embedder by default; allow tiny embedder only when explicitly enabled.
    if os.getenv("SOMABRAIN_ALLOW_TINY_EMBEDDER", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        from somabrain.embeddings import TinyDeterministicEmbedder

        _embedder = TinyDeterministicEmbedder(dim=256)
    else:
        _embedder = make_embedder(settings, quantum=None)
except Exception:
    from somabrain.embeddings import TinyDeterministicEmbedder

    _embedder = TinyDeterministicEmbedder(dim=256)
_working_memory = WorkingMemoryBuffer()
_retrieval_weights = RetrievalWeights()
_utility_weights = UtilityWeights()


@lru_cache(maxsize=1)
def get_context_builder() -> ContextBuilder:
    memory = MemoryClient(cfg=settings)
    return ContextBuilder(
        embed_fn=_embedder.embed,
        memory=memory,
        weights=_retrieval_weights,
        working_memory=_working_memory,
    )


@lru_cache(maxsize=1)
def get_context_planner() -> ContextPlanner:
    return ContextPlanner(utility_weights=_utility_weights)
