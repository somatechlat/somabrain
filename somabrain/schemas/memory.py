"""
Memory schemas - Recall, Remember, Retrieval operations.

Request/response schemas for memory operations API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator

from somabrain.datetime_utils import coerce_to_epoch_seconds

TimestampInput = Union[float, int, str, datetime]


class RecallRequest(BaseModel):
    """Schema for memory recall API requests."""

    query: str
    top_k: int = 3
    universe: Optional[str] = None


class MemoryPayload(BaseModel):
    """Schema for episodic memory payloads."""

    task: Optional[str] = None
    content: Optional[str] = None
    phase: Optional[str] = None
    quality_score: Optional[float] = None
    domains: Optional[Union[List[str], str]] = None
    reasoning_chain: Optional[Union[List[str], str]] = None
    importance: float = 1.0
    memory_type: str = "episodic"
    timestamp: Optional[TimestampInput] = None
    universe: Optional[str] = None
    who: Optional[str] = None
    did: Optional[str] = None
    what: Optional[str] = None
    where: Optional[str] = None
    when: Optional[str] = None
    why: Optional[str] = None

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

    coord: Optional[str] = Field(None, description="x,y,z; optional — auto if omitted")
    payload: MemoryPayload


class WMHit(BaseModel):
    """Working memory hit schema."""

    score: float
    payload: Dict[str, Any]


class RecallResponse(BaseModel):
    """Response model for the /recall endpoint."""

    wm: List[WMHit]
    memory: List[Dict[str, Any]]
    namespace: str
    trace_id: str
    deadline_ms: Optional[str] = None
    idempotency_key: Optional[str] = None
    reality: Optional[Dict[str, Any]] = None
    drift: Optional[Dict[str, Any]] = None
    hrr_cleanup: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = []


class RetrievalRequest(BaseModel):
    """Advanced retrieval request schema."""

    query: str
    top_k: int = 10
    retrievers: List[str] = ["vector", "wm", "graph", "lexical"]
    rerank: str = "auto"
    persist: bool = True
    universe: Optional[str] = None
    mode: Optional[str] = None
    id: Optional[str] = None
    key: Optional[str] = None
    coord: Optional[str] = None


class RetrievalCandidate(BaseModel):
    """Single retrieval candidate."""

    coord: Optional[str] = None
    key: Optional[str] = None
    score: float
    retriever: str
    payload: Dict[str, Any]


class RetrievalResponse(BaseModel):
    """Response from retrieval operation."""

    candidates: List[RetrievalCandidate]
    session_coord: Optional[str] = None
    namespace: str
    trace_id: str
    metrics: Optional[Dict[str, Any]] = None


class RememberResponse(BaseModel):
    """Response model for the /remember endpoint."""

    ok: bool
    success: bool
    namespace: str
    trace_id: str
    deadline_ms: Optional[str] = None
    idempotency_key: Optional[str] = None


class LinkRequest(BaseModel):
    """Graph link creation request."""

    from_key: Optional[str] = None
    to_key: Optional[str] = None
    from_coord: Optional[str] = None
    to_coord: Optional[str] = None
    type: Optional[str] = None
    weight: Optional[float] = 1.0
    universe: Optional[str] = None


class LinkResponse(BaseModel):
    """Graph link response."""

    ok: bool


class GraphLinksRequest(BaseModel):
    """Query graph links request."""

    from_key: Optional[str] = None
    from_coord: Optional[str] = None
    type: Optional[str] = None
    limit: Optional[int] = 50
    universe: Optional[str] = None


class GraphLinksResponse(BaseModel):
    """Graph links query response."""

    edges: List[Dict[str, Any]]
    universe: Optional[str] = None


class DeleteRequest(BaseModel):
    """Delete memory request."""

    coordinate: List[float]


class DeleteResponse(BaseModel):
    """Delete memory response."""

    ok: bool = True
