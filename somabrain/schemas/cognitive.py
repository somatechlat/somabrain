"""
Cognitive schemas - Nano Profile contracts.

Agent brain observation, thought, memory, action, and feedback schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, model_validator

from somabrain.nano_profile import HRR_DIM
from .common import normalize_vector


class Observation(BaseModel):
    """Agent observation schema."""

    who: str
    where: str
    when: str  # ISO 8601
    channel: str
    content: str
    embeddings: List[float]
    tags: List[str] = []
    traceId: str

    @model_validator(mode="after")
    def _validate_embeddings(self):
        self.embeddings = normalize_vector(self.embeddings, dim=HRR_DIM)
        return self


class Thought(BaseModel):
    """Agent thought schema."""

    id: str
    causeIds: List[str] = []
    text: str
    vector: List[float]
    uncertainty: float = 0.0
    citations: List[str] = []
    policyState: Dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_vector(self):
        self.vector = normalize_vector(self.vector, dim=HRR_DIM)
        return self


class Memory(BaseModel):
    """Agent memory schema."""

    id: str
    type: str  # "episodic"|"semantic"|"procedural"
    vector: List[float]
    graphRefs: List[str] = []
    payload: Dict[str, Any] = {}
    strength: float = 1.0

    @model_validator(mode="after")
    def _validate_memory_vector(self):
        self.vector = normalize_vector(self.vector, dim=HRR_DIM)
        return self


class ToolCall(BaseModel):
    """Tool invocation schema."""

    toolId: str
    schemaVersion: str
    args: Dict[str, Any]
    budget: float = 0.0
    retry: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PlanStep(BaseModel):
    """Planning step schema."""

    id: str
    preconds: List[str] = []
    action: str
    expected: Dict[str, Any] = {}
    deadline: Optional[str] = None  # ISO 8601
    risk: float = 0.0


class Action(BaseModel):
    """Agent action schema."""

    channel: str
    toolId: str
    content: str
    args: Dict[str, Any] = {}
    constraints: Dict[str, Any] = {}
    outcome: Optional[Dict[str, Any]] = None


class Feedback(BaseModel):
    """Agent feedback schema."""

    signal: str  # "success"|"fail"|"reward"
    reason: str
    metrics: Dict[str, Any] = {}

    class Observation(BaseModel):
        """Nested observation for feedback."""
        data: dict
        timestamp: float

    class Thought(BaseModel):
        """Nested thought for feedback."""
        query: str
        context: dict = {}

    class Memory(BaseModel):
        """Nested memory for feedback."""
        data: dict
        timestamp: float

        @classmethod
        def from_observation(cls, obs: Any):
            """Create memory from observation."""
            if hasattr(obs, "embeddings"):
                vec = getattr(obs, "embeddings", [])
                ts = float(getattr(obs, "when", 0.0)) if hasattr(obs, "when") else 0.0
            elif hasattr(obs, "data"):
                vec = getattr(obs, "data", {}).get("vector", [])
                ts = float(getattr(obs, "timestamp", 0.0))
            else:
                d = dict(obs) if not isinstance(obs, dict) else obs
                vec = d.get("vector", d.get("embeddings", []))
                ts = float(d.get("timestamp", 0.0))
            normalized = normalize_vector(vec)
            return cls(data={"vector": normalized}, timestamp=ts)

        def matches(self, thought: Any) -> bool:
            """Check if memory matches thought."""
            if hasattr(thought, "vector"):
                query_vec = np.array(getattr(thought, "vector", []), dtype=np.float32)
            else:
                d = dict(thought) if not isinstance(thought, dict) else thought
                query_vec = np.array(
                    d.get("vector", d.get("context", {}).get("vector", [])),
                    dtype=np.float32,
                )
            query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-8)
            mem_vec = np.array(self.data.get("vector", []), dtype=np.float32)
            mem_vec = mem_vec / (np.linalg.norm(mem_vec) + 1e-8)
            if query_vec.shape[0] != mem_vec.shape[0]:
                return False
            return float(np.dot(query_vec, mem_vec)) > 0.95


class Metric(BaseModel):
    """System metric schema."""

    name: str
    value: float
    unit: str
    ts: str  # ISO 8601
    spanId: str
