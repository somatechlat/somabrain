"""Pydantic Models for Memory API.

This module contains all Pydantic request/response models used by the Memory API.
Extracted from somabrain/api/memory_api.py for better organization.

CANONICAL MEMORY CONTRACT (the seam)
------------------------------------
``POST /api/memory/remember``  (alias ``/memory/remember``)
``POST /api/memory/recall``    (alias ``/memory/recall``)
``POST /api/memory/forget``    (alias ``/memory/forget``)

``MemoryWriteRequest`` accepts BOTH the rich write shape
(``tenant/namespace/key/value``) and the seam ``MemoryWrite`` shape
(``text/kind/tenant_id/session_id/coord/embedding/salience/source``), plus the
dialect aliases ``content`` and ``memory_type``. There is a single write path;
the aliases are folded in by ``MemoryWriteRequest._normalize_seam_fields``.

Recall hits are returned as ``MemoryHit`` items
(``text/coord/score/store/created_at``) with the legacy
``content/layer/coordinate`` keys retained as aliases.

Models:
- MemoryAttachment: Attachment descriptor for memory entries
- MemoryLink: Link descriptor for memory relationships
- MemorySignalPayload: Agent-provided signals for storage priorities
- MemorySignalFeedback: Feedback on signal processing
- MemoryWriteRequest/Response: Single memory write operations
- MemoryRecallRequest/Response: Memory recall operations
- MemoryRecallItem: Individual recall result item (MemoryHit shape)
- ForgetRequest/Response: Memory delete operations
- MemoryBatchWriteRequest/Response: Batch memory write operations
- MemoryMetricsResponse: Memory metrics response
- MemoryRecallSessionResponse: Recall session response
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class MemoryAttachment(BaseModel):
    """Attachment descriptor for memory entries."""

    kind: str = Field(..., description="Attachment type identifier")
    uri: str | None = Field(None, description="External location reference")
    content_type: str | None = Field(
        None, description="MIME type for the attachment"
    )
    checksum: str | None = Field(
        None, description="Integrity checksum for validation"
    )
    data: str | None = Field(
        None,
        description="Inline base64-encoded payload; use sparingly for small blobs",
    )
    meta: dict[str, Any] | None = Field(
        None, description="Attachment metadata annotations"
    )


class MemoryLink(BaseModel):
    """Link descriptor for memory relationships."""

    rel: str = Field(..., description="Relationship descriptor (e.g. causes, follows)")
    target: str = Field(..., description="Target memory key or URI")
    weight: float | None = Field(None, ge=0.0, description="Optional link strength")
    meta: dict[str, Any] | None = Field(None, description="Additional link metadata")


class MemorySignalPayload(BaseModel):
    """Agent-provided signals guiding storage priorities."""

    importance: float | None = Field(
        None, ge=0.0, description="Relative importance weight"
    )
    novelty: float | None = Field(
        None, ge=0.0, description="Novelty score from agent"
    )
    ttl_seconds: int | None = Field(
        None, ge=0, description="Soft time-to-live for cleanup"
    )
    reinforcement: str | None = Field(
        None, description="Working-memory reinforcement hint (e.g. boost, suppress)"
    )
    recall_bias: str | None = Field(
        None, description="Preferred recall strategy (explore, exploit, balanced, etc.)"
    )


class MemorySignalFeedback(BaseModel):
    """Feedback on signal processing results."""

    importance: float | None = None
    novelty: float | None = None
    ttl_seconds: int | None = Field(None, ge=0, description="Applied ttl in seconds")
    reinforcement: str | None = None
    recall_bias: str | None = None
    promoted_to_wm: bool | None = None
    persisted_to_ltm: bool | None = None


class MemoryWriteRequest(BaseModel):
    """Request model for single memory write operations.

    Accepts the rich write shape and the seam ``MemoryWrite`` shape:

    .. code-block:: json

        {"text": "...", "kind": "episodic", "tenant_id": "...",
         "session_id": null, "coord": "x,y,z", "embedding": [..],
         "salience": 0.5, "source": "agent-chat"}
    """

    # --- seam fields (THE SEAM contract) ---
    text: str | None = Field(
        None, description="Primary memory text (seam). Alias: content"
    )
    content: str | None = Field(
        None, description="Dialect alias for text (BrainBridge / legacy proofs)"
    )
    kind: str | None = Field(
        None,
        description="Memory kind: episodic | semantic | belief (seam). Omitted "
        "means the caller did not set it: a kind already carried in ``value`` "
        "wins, and only then the seam default 'episodic'. Defaulting this "
        "field here would clobber an explicit ``value.kind`` on every write.",
    )
    memory_type: str | None = Field(
        None, description="Dialect alias for kind (legacy value.memory_type)"
    )
    tenant_id: str | None = Field(
        None, description="Tenant identifier (seam). Alias for tenant"
    )
    session_id: str | None = Field(
        None, description="Optional session scope for this memory"
    )
    coord: str | list[float] | None = Field(
        None,
        description="Explicit coordinate identity, either 'x,y,z' or [x,y,z]. "
        "When provided it is the single storage identity.",
    )
    embedding: list[float] | None = Field(
        None,
        description="Optional precomputed embedding vector stored with the memory",
    )
    salience: float | None = Field(
        None, ge=0.0, le=1.0, description="Salience weight in [0,1] (seam)"
    )
    source: str | None = Field(
        None,
        description="Write provenance (seam). Omitted means the caller did not "
        "set it: a source already carried in ``value`` wins, and only then the "
        "seam default 'agent-chat'. Defaulting this field here would clobber "
        "an explicit ``value.source`` on every write.",
    )

    # --- rich write shape (still canonical) ---
    tenant: str = Field(
        default="",
        description="Tenant identifier. May be omitted here and supplied as the "
        "X-Tenant-ID header; the handler resolves and requires one of the two.",
    )
    namespace: str = Field(
        ..., min_length=1, description="Logical namespace (e.g. wm, ltm). No default (Rule 91)."
    )
    key: str = Field(
        ...,
        min_length=1,
        description="Stable key used to derive coordinates when coord is absent",
    )
    value: dict[str, Any] = Field(..., description="Payload stored in memory")
    meta: dict[str, Any] | None = Field(
        None, description="Optional metadata blended into the stored payload"
    )
    universe: str | None = Field(
        None, description="Universe scope forwarded to the memory backend"
    )
    ttl_seconds: int | None = Field(
        None, ge=0, description="Desired time-to-live hint for automatic cleanup"
    )
    tags: list[str] = Field(
        default_factory=list, description="Arbitrary agent-supplied tags"
    )
    policy_tags: list[str] = Field(
        default_factory=list, description="Policy or governance tags for this memory"
    )
    attachments: list[MemoryAttachment] = Field(
        default_factory=list, description="Optional attachment descriptors"
    )
    links: list[MemoryLink] = Field(
        default_factory=list, description="Optional outbound links to existing memories"
    )
    signals: MemorySignalPayload | None = Field(
        None, description="Agent-provided signals guiding storage priorities"
    )
    importance: float | None = Field(
        None, ge=0.0, description="Shortcut for signals.importance"
    )
    novelty: float | None = Field(
        None, ge=0.0, description="Shortcut for signals.novelty"
    )
    trace_id: str | None = Field(
        None, description="Agent correlation identifier for downstream observability"
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_seam_fields(cls, data: Any) -> Any:
        """Fold the seam/dialect field names into the canonical write shape.

        Runs before field validation so the rich required fields
        (``tenant``/``key``/``value``) are present once aliases are resolved.
        """
        if not isinstance(data, dict):
            return data
        d = dict(data)

        # tenant scoping: tenant_id (seam) == tenant (rich)
        tenant = d.get("tenant") or d.get("tenant_id") or ""
        if isinstance(tenant, str):
            tenant = tenant.strip()
        else:
            tenant = str(tenant or "").strip()
        d["tenant"] = tenant
        d["tenant_id"] = str(d.get("tenant_id") or tenant).strip() or tenant

        # meta alias used by the BrainBridge proof scripts
        if d.get("meta") is None and d.get("metadata") is not None:
            d["meta"] = d["metadata"]

        # namespace: required, never invented (Rule 91). A memory without a
        # namespace is a memory that cannot be partitioned.
        ns = d.get("namespace")
        if not isinstance(ns, str) or not ns.strip():
            from somabrain.settings.resolve import require_namespace

            d["namespace"] = require_namespace(ns)
        else:
            d["namespace"] = ns.strip()

        # value: tolerate absent/dict/scalar, and dict-valued `content`
        value = d.get("value")
        content = d.get("content")
        if isinstance(content, dict) and not isinstance(value, dict):
            value = dict(content)
            content = None
        if not isinstance(value, dict):
            value = {} if value is None else {"text": value}
        d["value"] = value

        # primary text: text | content | value.text | value.task
        text = d.get("text")
        if not isinstance(text, str) or not text.strip():
            if isinstance(content, str) and content.strip():
                text = content
            else:
                text = (
                    value.get("text")
                    or value.get("content")
                    or value.get("task")
                    or value.get("what")
                )
        if isinstance(text, str) and text.strip():
            d["text"] = text.strip()
            value.setdefault("text", d["text"])
        else:
            d["text"] = None

        # kind: kind | memory_type | value.memory_type
        kind = d.get("kind") or d.get("memory_type") or value.get("memory_type")
        kind = str(kind or "episodic").strip().lower() or "episodic"
        d["kind"] = kind
        d["memory_type"] = kind
        value.setdefault("memory_type", kind)

        # salience / source / session_id ride into the stored value
        if d.get("session_id"):
            value.setdefault("session_id", str(d["session_id"]))
        if d.get("salience") is not None:
            value.setdefault("salience", float(d["salience"]))
        if d.get("source"):
            value.setdefault("source", str(d["source"]))
        if d.get("embedding") is not None:
            value.setdefault("embedding", list(d["embedding"]))

        # key: required for deterministic identity when coord is absent
        key = d.get("key")
        if not isinstance(key, str) or not key.strip():
            coord = d.get("coord")
            if isinstance(coord, str) and coord.strip():
                key = coord.strip()
            elif isinstance(coord, (list, tuple)) and len(coord) >= 3:
                try:
                    key = f"{float(coord[0])},{float(coord[1])},{float(coord[2])}"
                except (TypeError, ValueError):
                    key = None
            if not key:
                key = d.get("text") or value.get("task") or ""
            key = str(key).strip()
        if not key:
            raise ValueError(
                "one of 'key', 'coord' or 'text' is required to identify the memory"
            )
        d["key"] = key

        if not value:
            raise ValueError("one of 'value', 'text' or 'content' is required")
        return d


class MemoryWriteResponse(BaseModel):
    """Response model for single memory write operations.

    Superset of the seam ``MemoryAck``: ``coord`` (canonical ``x,y,z`` string),
    ``store``, ``ok`` and ``error`` are always present alongside the legacy
    ``coordinate`` float list.
    """

    ok: bool
    tenant: str
    namespace: str
    key: str | None = None
    coord: str | None = Field(
        None, description="Canonical coordinate string 'x,y,z' (seam MemoryAck.coord)"
    )
    coordinate: list[float] | None = None
    store: str = Field("somafractalmemory", description="Store that acked the write")
    kind: str | None = None
    error: str | None = None
    promoted_to_wm: bool = False
    persisted_to_ltm: bool = False
    queued_for_ltm: bool = False
    deduplicated: bool = False
    importance: float | None = None
    novelty: float | None = None
    ttl_applied: int | None = None
    trace_id: str | None = None
    request_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    signals: MemorySignalFeedback | None = None


class MemoryRecallRequest(BaseModel):
    """Request model for memory recall operations."""

    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(3, ge=1, le=50)
    layer: str | None = Field(
        None, description="Set to 'wm', 'ltm', or omit for both"
    )
    universe: str | None = None
    tags: list[str] = Field(
        default_factory=list, description="Filter hits containing these tags"
    )
    min_score: float | None = Field(
        None, ge=0.0, description="Drop hits with score below this threshold"
    )
    max_age_seconds: int | None = Field(
        None,
        ge=0,
        description="Exclude hits older than the specified age when payload timestamps exist",
    )
    scoring_mode: str | None = Field(
        None,
        description="Preferred scoring strategy (explore, exploit, blended, recency, etc.)",
    )
    session_id: str | None = Field(
        None, description="Attach to existing recall session to accumulate context"
    )
    conversation_id: str | None = Field(
        None, description="Agent-provided conversation identifier"
    )
    pin_results: bool = Field(
        False,
        description="If true, persist results in the session registry for follow-up queries",
    )
    chunk_size: int | None = Field(
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


# Moved to somabrain.datetime_utils so the gRPC transport can share it
# without importing this module (and with it Django/ninja).
from somabrain.datetime_utils import iso_created_at as _iso_created_at  # noqa: E402


class MemoryRecallItem(BaseModel):
    """Individual recall result item (seam ``MemoryHit`` shape).

    ``text``, ``coord``, ``score``, ``store`` and ``created_at`` are the
    canonical hit fields; ``content``, ``layer``, ``payload`` and
    ``coordinate`` are retained as legacy aliases.
    """

    # --- seam MemoryHit fields ---
    text: str = ""
    coord: str | None = Field(
        None, description="Canonical coordinate string 'x,y,z' (MemoryHit.coord)"
    )
    score: float | None = None
    store: str = Field(
        "somafractalmemory",
        description="Originating store: somabrain | somafractalmemory",
    )
    created_at: str = Field(
        "", description="ISO-8601 creation timestamp of the stored memory"
    )

    # --- legacy aliases ---
    layer: str
    payload: dict[str, Any]
    coordinate: list[float] | None = None
    source: str
    confidence: float | None = Field(
        None, description="Confidence score derived from backend metrics"
    )
    novelty: float | None = Field(
        None, description="Novelty indicator relative to session history"
    )
    affinity: float | None = Field(
        None, description="Affinity to current conversation or goal state"
    )


class MemoryRecallResponse(BaseModel):
    """Response model for memory recall operations."""

    tenant: str
    namespace: str
    results: list[MemoryRecallItem]
    wm_hits: int
    ltm_hits: int
    duration_ms: float
    session_id: str
    scoring_mode: str | None = None
    chunk_index: int = 0
    has_more: bool = False
    total_results: int
    chunk_size: int | None = None
    conversation_id: str | None = None
    degraded: bool = False


class ForgetRequest(BaseModel):
    """Request model for forgetting (deleting) a memory by coordinate."""

    coord: str | list[float] = Field(
        ..., description="Coordinate identity: 'x,y,z' or [x,y,z]"
    )
    tenant: str | None = Field(None, description="Tenant identifier (rich name)")
    tenant_id: str | None = Field(None, description="Tenant identifier (seam name)")


class ForgetResponse(BaseModel):
    """Response model for forget operations (seam ``MemoryAck`` shape)."""

    ok: bool
    coord: str
    store: str = "somafractalmemory"
    tenant: str = ""
    error: str | None = None


class MemoryMetricsResponse(BaseModel):
    """Response model for memory metrics."""

    tenant: str
    namespace: str
    wm_items: int
    circuit_open: bool


class MemoryBatchWriteItem(BaseModel):
    """Individual item in a batch write request."""

    key: str = Field(..., min_length=1)
    value: dict[str, Any] = Field(..., description="Payload stored in memory")
    meta: dict[str, Any] | None = Field(None, description="Optional metadata")
    ttl_seconds: int | None = Field(
        None, ge=0, description="TTL override for this item"
    )
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    policy_tags: list[str] = Field(default_factory=list, description="Policy tags")
    attachments: list[MemoryAttachment] = Field(default_factory=list)
    links: list[MemoryLink] = Field(default_factory=list)
    signals: MemorySignalPayload | None = None
    importance: float | None = Field(None, ge=0.0)
    novelty: float | None = Field(None, ge=0.0)
    trace_id: str | None = None
    universe: str | None = None


class MemoryBatchWriteRequest(BaseModel):
    """Request model for batch memory write operations."""

    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    items: list[MemoryBatchWriteItem] = Field(
        ..., min_length=1, description="Batch of memories to persist"
    )
    universe: str | None = Field(
        None,
        description="Default universe applied when items omit universe; item value wins",
    )


class MemoryBatchWriteResult(BaseModel):
    """Individual result in a batch write response."""

    key: str
    coordinate: list[float] | None = None
    promoted_to_wm: bool = False
    persisted_to_ltm: bool = False
    deduplicated: bool = False
    importance: float | None = None
    novelty: float | None = None
    ttl_applied: int | None = None
    trace_id: str | None = None
    request_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    signals: MemorySignalFeedback | None = None


class MemoryBatchWriteResponse(BaseModel):
    """Response model for batch memory write operations."""

    ok: bool
    tenant: str
    namespace: str
    results: list[MemoryBatchWriteResult]


class MemoryRecallSessionResponse(BaseModel):
    """Response model for recall session creation."""

    session_id: str
    tenant: str


__all__ = [
    "ForgetRequest",
    "ForgetResponse",
    "MemoryAttachment",
    "MemoryBatchWriteItem",
    "MemoryBatchWriteRequest",
    "MemoryBatchWriteResponse",
    "MemoryBatchWriteResult",
    "MemoryLink",
    "MemoryMetricsResponse",
    "MemoryRecallItem",
    "MemoryRecallRequest",
    "MemoryRecallResponse",
    "MemoryRecallSessionResponse",
    "MemorySignalFeedback",
    "MemorySignalPayload",
    "MemoryWriteRequest",
    "MemoryWriteResponse",
    "_iso_created_at",
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
    last_error: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class OutboxReplayRequest(BaseModel):
    """Request to replay specific outbox events."""

    ids: list[int] = Field(..., min_length=1, description="Event IDs to replay")


class AnnRebuildRequest(BaseModel):
    """Request to rebuild ANN indexes."""

    tenant: str
    namespace: str | None = None


# Update __all__ to include new models
__all__.extend(
    [
        "AnnRebuildRequest",
        "OutboxEventSummary",
        "OutboxReplayRequest",
    ]
)
