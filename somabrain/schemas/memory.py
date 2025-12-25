"""Memory-related schemas for SomaBrain API.

This module contains Pydantic models for memory operations including
recall, remember, retrieval, and delete operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import numpy as np
from pydantic import BaseModel, Field, model_validator

from somabrain.datetime_utils import coerce_to_epoch_seconds


def _get_settings():
    """Lazy settings access to avoid circular imports."""
    from django.conf import settings

    return settings


def normalize_vector(vec_like, dim: int = None):
    """
    Convert an input sequence/array to a unit-norm float32 list of length `dim`.
    Raises ValueError on invalid inputs.
    """
    from somabrain.math import normalize_vector as _canonical_normalize

    s = _get_settings()
    if dim is None:
        dim = s.hrr_dim
    hrr_dtype = s.hrr_dtype

    arr = np.asarray(vec_like, dtype=hrr_dtype)
    if arr.ndim != 1:
        arr = arr.reshape(-1)
    if arr.size < dim:
        padded = np.zeros((dim,), dtype=hrr_dtype)
        padded[: arr.size] = arr
        arr = padded
    elif arr.size > dim:
        arr = arr[:dim]

    normed = _canonical_normalize(arr, dtype=np.dtype(hrr_dtype))
    return normed.tolist()


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
    """Working memory hit result."""

    score: float
    payload: Dict[str, Any]


class RecallResponse(BaseModel):
    """Canonical response model for the /recall endpoint."""

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
    degraded: Optional[bool] = None


class RememberResponse(BaseModel):
    """Canonical response model for the /remember endpoint."""

    ok: bool
    success: bool
    namespace: str
    trace_id: str
    deadline_ms: Optional[str] = None
    idempotency_key: Optional[str] = None


class RetrievalRequest(BaseModel):
    """Request model for retrieval operations."""

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
    layer: Optional[str] = None


class RetrievalCandidate(BaseModel):
    """Single retrieval candidate."""

    coord: Optional[str] = None
    key: Optional[str] = None
    score: float
    retriever: str
    payload: Dict[str, Any]


class RetrievalResponse(BaseModel):
    """Response model for retrieval operations."""

    candidates: List[RetrievalCandidate]
    session_coord: Optional[str] = None
    namespace: str
    trace_id: str
    metrics: Optional[Dict[str, Any]] = None


class DeleteRequest(BaseModel):
    """Schema for delete memory requests."""

    coordinate: List[float]


class DeleteResponse(BaseModel):
    """Simple response indicating delete success."""

    ok: bool = True


class LinkRequest(BaseModel):
    """Request for creating memory links."""

    from_key: Optional[str] = None
    to_key: Optional[str] = None
    from_coord: Optional[str] = None
    to_coord: Optional[str] = None
    type: Optional[str] = None
    weight: Optional[float] = 1.0
    universe: Optional[str] = None


class GraphLinksRequest(BaseModel):
    """Request for querying graph links."""

    from_key: Optional[str] = None
    from_coord: Optional[str] = None
    type: Optional[str] = None
    limit: Optional[int] = 50
    universe: Optional[str] = None


class GraphLinksResponse(BaseModel):
    """Response for graph links query."""

    edges: List[Dict[str, Any]]
    universe: Optional[str] = None


class LinkResponse(BaseModel):
    """Response for link operations."""

    ok: bool


__all__ = [
    "RecallRequest",
    "MemoryPayload",
    "RememberRequest",
    "WMHit",
    "RecallResponse",
    "RememberResponse",
    "RetrievalRequest",
    "RetrievalCandidate",
    "RetrievalResponse",
    "DeleteRequest",
    "DeleteResponse",
    "LinkRequest",
    "GraphLinksRequest",
    "GraphLinksResponse",
    "LinkResponse",
    "TimestampInput",
    "normalize_vector",
    "_get_settings",
]
