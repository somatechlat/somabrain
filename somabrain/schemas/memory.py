"""
Memory schemas - Recall, Remember, Retrieval operations.

Request/response schemas for memory operations API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Union

from pydantic import BaseModel, Field, model_validator

from somabrain.datetime_utils import coerce_to_epoch_seconds

TimestampInput = Union[float, int, str, datetime]


class RecallRequest(BaseModel):
    """Schema for memory recall API requests."""

    query: str
    top_k: int = 3
    universe: str | None = None


class MemoryPayload(BaseModel):
    """Schema for episodic memory payloads."""

    task: str | None = None
    content: str | None = None
    phase: str | None = None
    quality_score: float | None = None
    domains: list[str] | str | None = None
    reasoning_chain: list[str] | str | None = None
    importance: float = 1.0
    memory_type: str = "episodic"
    timestamp: TimestampInput | None = None
    universe: str | None = None
    who: str | None = None
    did: str | None = None
    what: str | None = None
    where: str | None = None
    when: str | None = None
    why: str | None = None

    @model_validator(mode="after")
    def _normalize_timestamp(self):
        if self.timestamp is not None:
            try:
                self.timestamp = coerce_to_epoch_seconds(self.timestamp)
            except ValueError as exc:
                raise ValueError(f"Invalid timestamp format: {exc}")
        return self


class RememberRequest(BaseModel):
    """Schema for memory storage requests."""

    coord: str | None = Field(None, description="x,y,z; optional — auto if omitted")
    payload: MemoryPayload


class WMHit(BaseModel):
    """Working memory hit schema."""

    score: float
    payload: dict[str, Any]


class RecallResponse(BaseModel):
    """Response model for the /recall endpoint."""

    wm: list[WMHit]
    memory: list[dict[str, Any]]
    namespace: str
    trace_id: str
    deadline_ms: str | None = None
    idempotency_key: str | None = None
    reality: dict[str, Any] | None = None
    drift: dict[str, Any] | None = None
    hrr_cleanup: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []


class RetrievalRequest(BaseModel):
    """Advanced retrieval request schema."""

    query: str
    top_k: int = 10
    retrievers: list[str] = ["vector", "wm", "graph", "lexical"]
    rerank: str = "auto"
    persist: bool = True
    universe: str | None = None
    mode: str | None = None
    id: str | None = None
    key: str | None = None
    coord: str | None = None


class RetrievalCandidate(BaseModel):
    """Single retrieval candidate."""

    coord: str | None = None
    key: str | None = None
    score: float
    retriever: str
    payload: dict[str, Any]


class RetrievalResponse(BaseModel):
    """Response from retrieval operation."""

    candidates: list[RetrievalCandidate]
    session_coord: str | None = None
    namespace: str
    trace_id: str
    metrics: dict[str, Any] | None = None
    degraded: bool = False
    error: str | None = None


class RememberResponse(BaseModel):
    """Response model for the /remember endpoint."""

    ok: bool
    success: bool
    namespace: str
    trace_id: str
    deadline_ms: str | None = None
    idempotency_key: str | None = None


class LinkRequest(BaseModel):
    """Graph link creation request."""

    from_key: str | None = None
    to_key: str | None = None
    from_coord: str | None = None
    to_coord: str | None = None
    type: str | None = None
    weight: float | None = 1.0
    universe: str | None = None


class LinkResponse(BaseModel):
    """Graph link response."""

    ok: bool


class GraphLinksRequest(BaseModel):
    """Query graph links request."""

    from_key: str | None = None
    from_coord: str | None = None
    type: str | None = None
    limit: int | None = 50
    universe: str | None = None


class GraphLinksResponse(BaseModel):
    """Graph links query response."""

    edges: list[dict[str, Any]]
    universe: str | None = None


class DeleteRequest(BaseModel):
    """Delete memory request."""

    coordinate: list[float]


class DeleteResponse(BaseModel):
    """Delete memory response."""

    ok: bool = True
