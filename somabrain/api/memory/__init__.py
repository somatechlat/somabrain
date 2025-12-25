"""Memory API Module for SomaBrain.

Submodules:
- models: Pydantic request/response models
- helpers: Helper functions for memory operations
- session: Session store for recall operations
- recall: Core recall implementation
"""

from somabrain.api.memory.models import (
    MemoryAttachment,
    MemoryLink,
    MemorySignalPayload,
    MemorySignalFeedback,
    MemoryWriteRequest,
    MemoryWriteResponse,
    MemoryRecallRequest,
    MemoryRecallItem,
    MemoryRecallResponse,
    MemoryMetricsResponse,
    MemoryBatchWriteItem,
    MemoryBatchWriteRequest,
    MemoryBatchWriteResult,
    MemoryBatchWriteResponse,
    MemoryRecallSessionResponse,
    OutboxEventSummary,
    OutboxReplayRequest,
    AnnRebuildRequest,
)

from somabrain.api.memory.helpers import (
    _get_runtime,
    _get_app_config,
    _get_embedder,
    _get_wm,
    _get_memory_pool,
    _resolve_namespace,
    _serialize_coord,
    _compose_memory_payload,
    _as_float_list,
    _map_retrieval_to_memory_items,
    _coerce_to_retrieval_request,
)

from somabrain.api.memory.session import (
    RecallSessionStore,
    get_recall_session_store,
)

__all__ = [
    # Models
    "MemoryAttachment",
    "MemoryLink",
    "MemorySignalPayload",
    "MemorySignalFeedback",
    "MemoryWriteRequest",
    "MemoryWriteResponse",
    "MemoryRecallRequest",
    "MemoryRecallItem",
    "MemoryRecallResponse",
    "MemoryMetricsResponse",
    "MemoryBatchWriteItem",
    "MemoryBatchWriteRequest",
    "MemoryBatchWriteResult",
    "MemoryBatchWriteResponse",
    "MemoryRecallSessionResponse",
    "OutboxEventSummary",
    "OutboxReplayRequest",
    "AnnRebuildRequest",
    # Helpers
    "_get_runtime",
    "_get_app_config",
    "_get_embedder",
    "_get_wm",
    "_get_memory_pool",
    "_resolve_namespace",
    "_serialize_coord",
    "_compose_memory_payload",
    "_as_float_list",
    "_map_retrieval_to_memory_items",
    "_coerce_to_retrieval_request",
    # Session
    "RecallSessionStore",
    "get_recall_session_store",
]
