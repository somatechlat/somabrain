"""Pydantic Models for Memory API.

This module contains all Pydantic request/response models used by the Memory API.
Extracted from somabrain/api/memory_api.py for better organization.

Models:
- MemoryAttachment: Attachment descriptor for memory entries
- MemoryLink: Link descriptor for memory relationships
- MemorySignalPayload: Agent-provided signals for storage priorities
- MemorySignalFeedback: Feedback on signal processing
- MemoryWriteRequest/Response: Single memory write operations
- MemoryRecallRequest/Response: Memory recall operations
- MemoryRecallItem: Individual recall result item
- MemoryBatchWriteRequest/Response: Batch memory write operations
- MemoryMetricsResponse: Memory metrics response
- MemoryRecallSessionResponse: Recall session response
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryAttachment(BaseModel):
    """Attachment descriptor for memory entries."""

    kind: str = Field(..., description="Attachment type identifier")
    uri: Optional[str] = Field(None, description="External location reference")
    content_type: Optional[str] = Field(None, description="MIME type for the attachment")
    checksum: Optional[str] = Field(None, description="Integrity checksum for validation")
    data: Optional[str] = Field(
        None,
        description="Inline base64-encoded payload; use sparingly for small blobs",
    )
    meta: Optional[Dict[str, Any]] = Field(None, description="Attachment metadata annotations")


class MemoryLink(BaseModel):
    """Link descriptor for memory relationships."""

    rel: str = Field(..., description="Relationship descriptor (e.g. causes, follows)")
    target: str = Field(..., description="Target memory key or URI")
    weight: Optional[float] = Field(None, ge=0.0, description="Optional link strength")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional link metadata")


class MemorySignalPayload(BaseModel):
    """Agent-provided signals guiding storage priorities."""

    importance: Optional[float] = Field(None, ge=0.0, description="Relative importance weight")
    novelty: Optional[float] = Field(None, ge=0.0, description="Novelty score from agent")
    ttl_seconds: Optional[int] = Field(None, ge=0, description="Soft time-to-live for cleanup")
    reinforcement: Optional[str] = Field(
        None, description="Working-memory reinforcement hint (e.g. boost, suppress)"
    )
    recall_bias: Optional[str] = Field(
        None, description="Preferred recall strategy (explore, exploit, balanced, etc.)"
    )


class MemorySignalFeedback(BaseModel):
    """Feedback on signal processing results."""

    importance: Optional[float] = None
    novelty: Optional[float] = None
    ttl_seconds: Optional[int] = Field(None, ge=0, description="Applied ttl in seconds")
    reinforcement: Optional[str] = None
    recall_bias: Optional[str] = None
    promoted_to_wm: Optional[bool] = None
    persisted_to_ltm: Optional[bool] = None


class MemoryWriteRequest(BaseModel):
    """Request model for single memory write operations."""

    tenant: str = Field(..., min_length=1, description="Tenant identifier")
    namespace: str = Field(..., min_length=1, description="Logical namespace (e.g. wm, ltm)")
    key: str = Field(..., min_length=1, description="Stable key used to derive coordinates")
    value: Dict[str, Any] = Field(..., description="Payload stored in memory")
    meta: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata blended into the stored payload"
    )
    universe: Optional[str] = Field(
        None, description="Universe scope forwarded to the memory backend"
    )
    ttl_seconds: Optional[int] = Field(
        None, ge=0, description="Desired time-to-live hint for automatic cleanup"
    )
    tags: List[str] = Field(default_factory=list, description="Arbitrary agent-supplied tags")
    policy_tags: List[str] = Field(
        default_factory=list, description="Policy or governance tags for this memory"
    )
    attachments: List[MemoryAttachment] = Field(
        default_factory=list, description="Optional attachment descriptors"
    )
    links: List[MemoryLink] = Field(
        default_factory=list, description="Optional outbound links to existing memories"
    )
    signals: Optional[MemorySignalPayload] = Field(
        None, description="Agent-provided signals guiding storage priorities"
    )
    importance: Optional[float] = Field(None, ge=0.0, description="Shortcut for signals.importance")
    novelty: Optional[float] = Field(None, ge=0.0, description="Shortcut for signals.novelty")
    trace_id: Optional[str] = Field(
        None, description="Agent correlation identifier for downstream observability"
    )


class MemoryWriteResponse(BaseModel):
    """Response model for single memory write operations."""

    ok: bool
    tenant: str
    namespace: str
    coordinate: Optional[List[float]] = None
    promoted_to_wm: bool = False
    persisted_to_ltm: bool = False
    deduplicated: bool = False
    importance: Optional[float] = None
    novelty: Optional[float] = None
    ttl_applied: Optional[int] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    signals: Optional[MemorySignalFeedback] = None


class MemoryRecallRequest(BaseModel):
    """Request model for memory recall operations."""

    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(3, ge=1, le=50)
    layer: Optional[str] = Field(None, description="Set to 'wm', 'ltm', or omit for both")
    universe: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="Filter hits containing these tags")
    min_score: Optional[float] = Field(
        None, ge=0.0, description="Drop hits with score below this threshold"
    )
    max_age_seconds: Optional[int] = Field(
        None,
        ge=0,
        description="Exclude hits older than the specified age when payload timestamps exist",
    )
    scoring_mode: Optional[str] = Field(
        None,
        description="Preferred scoring strategy (explore, exploit, blended, recency, etc.)",
    )
    session_id: Optional[str] = Field(
        None, description="Attach to existing recall session to accumulate context"
    )
    conversation_id: Optional[str] = Field(
        None, description="Agent-provided conversation identifier"
    )
    pin_results: bool = Field(
        False,
        description="If true, persist results in the session registry for follow-up queries",
    )
    chunk_size: Optional[int] = Field(
        None,
        ge=1,
        le=50,
        description="Limit number of hits returned per call for streaming",
    )
    chunk_index: int = Field(
        0,
        ge=0,
        description="Chunk index when requesting paged/streamed recall segments",
    )


class MemoryRecallItem(BaseModel):
    """Individual recall result item."""

    layer: str
    score: Optional[float] = None
    payload: Dict[str, Any]
    coordinate: Optional[List[float]] = None
    source: str
    confidence: Optional[float] = Field(
        None, description="Confidence score derived from backend metrics"
    )
    novelty: Optional[float] = Field(
        None, description="Novelty indicator relative to session history"
    )
    affinity: Optional[float] = Field(
        None, description="Affinity to current conversation or goal state"
    )


class MemoryRecallResponse(BaseModel):
    """Response model for memory recall operations."""

    tenant: str
    namespace: str
    results: List[MemoryRecallItem]
    wm_hits: int
    ltm_hits: int
    duration_ms: float
    session_id: str
    scoring_mode: Optional[str] = None
    chunk_index: int = 0
    has_more: bool = False
    total_results: int
    chunk_size: Optional[int] = None
    conversation_id: Optional[str] = None
    degraded: bool = False


class MemoryMetricsResponse(BaseModel):
    """Response model for memory metrics."""

    tenant: str
    namespace: str
    wm_items: int
    circuit_open: bool


class MemoryBatchWriteItem(BaseModel):
    """Individual item in a batch write request."""

    key: str = Field(..., min_length=1)
    value: Dict[str, Any] = Field(..., description="Payload stored in memory")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    ttl_seconds: Optional[int] = Field(None, ge=0, description="TTL override for this item")
    tags: List[str] = Field(default_factory=list, description="Optional tags")
    policy_tags: List[str] = Field(default_factory=list, description="Policy tags")
    attachments: List[MemoryAttachment] = Field(default_factory=list)
    links: List[MemoryLink] = Field(default_factory=list)
    signals: Optional[MemorySignalPayload] = None
    importance: Optional[float] = Field(None, ge=0.0)
    novelty: Optional[float] = Field(None, ge=0.0)
    trace_id: Optional[str] = None
    universe: Optional[str] = None


class MemoryBatchWriteRequest(BaseModel):
    """Request model for batch memory write operations."""

    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    items: List[MemoryBatchWriteItem] = Field(
        ..., min_length=1, description="Batch of memories to persist"
    )
    universe: Optional[str] = Field(
        None,
        description="Default universe applied when items omit universe; item value wins",
    )


class MemoryBatchWriteResult(BaseModel):
    """Individual result in a batch write response."""

    key: str
    coordinate: Optional[List[float]] = None
    promoted_to_wm: bool = False
    persisted_to_ltm: bool = False
    deduplicated: bool = False
    importance: Optional[float] = None
    novelty: Optional[float] = None
    ttl_applied: Optional[int] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    signals: Optional[MemorySignalFeedback] = None


class MemoryBatchWriteResponse(BaseModel):
    """Response model for batch memory write operations."""

    ok: bool
    tenant: str
    namespace: str
    results: List[MemoryBatchWriteResult]


class MemoryRecallSessionResponse(BaseModel):
    """Response model for recall session creation."""

    session_id: str
    tenant: str


__all__ = [
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
]


# Admin/Outbox models


class OutboxEventSummary(BaseModel):
    """Summary of an outbox event for admin listing."""

    id: int
    tenant_id: str
    topic: str
    status: str
    retries: int
    created_at: float
    dedupe_key: str
    last_error: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class OutboxReplayRequest(BaseModel):
    """Request to replay specific outbox events."""

    ids: List[int] = Field(..., min_length=1, description="Event IDs to replay")


class AnnRebuildRequest(BaseModel):
    """Request to rebuild ANN indexes."""

    tenant: str
    namespace: Optional[str] = None


# Update __all__ to include new models
__all__.extend(
    [
        "OutboxEventSummary",
        "OutboxReplayRequest",
        "AnnRebuildRequest",
    ]
)
