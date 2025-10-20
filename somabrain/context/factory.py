"""Shared builders for context and planning."""

from __future__ import annotations

import os
from functools import lru_cache

from somabrain.context.memory_shim import MemoryRecallClient
from somabrain.context.builder import ContextBuilder, RetrievalWeights
from somabrain.context.planner import ContextPlanner
from somabrain.embeddings import TinyDeterministicEmbedder
from somabrain.learning import UtilityWeights
from somabrain.runtime.working_memory import WorkingMemoryBuffer


_embedder = TinyDeterministicEmbedder(dim=256)
_working_memory = WorkingMemoryBuffer()
_retrieval_weights = RetrievalWeights()
_utility_weights = UtilityWeights()


@lru_cache(maxsize=1)
def get_context_builder() -> ContextBuilder:
    memstore = MemoryRecallClient()
    return ContextBuilder(
        embed_fn=_embedder.embed,
        memstore=memstore,
        weights=_retrieval_weights,
        working_memory=_working_memory,
    )


@lru_cache(maxsize=1)
def get_context_planner() -> ContextPlanner:
    return ContextPlanner(utility_weights=_utility_weights)
