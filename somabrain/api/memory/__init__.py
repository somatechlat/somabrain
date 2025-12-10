"""Memory API Module for SomaBrain.

This module provides the Memory API endpoints and related models.

Submodules:
- models: Pydantic request/response models
- helpers: Helper functions for memory operations (future)

For backward compatibility, all models are re-exported from this module.
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
]
