"""Cognitive and planning schemas for SomaBrain API.

This module contains Pydantic models for cognitive operations including
action execution, planning, and nano profile contracts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field, model_validator

from somabrain.schemas.memory import normalize_vector, _get_settings


# === Canonical Agent Brain Contracts (Nano Profile) ===


class Observation(BaseModel):
    """Observation schema for nano profile."""

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
        """Execute validate embeddings.
            """

        self.embeddings = normalize_vector(self.embeddings, dim=_get_settings().hrr_dim)
        return self


class Thought(BaseModel):
    """Thought schema for nano profile."""

    id: str
    causeIds: List[str] = []
    text: str
    vector: List[float]
    uncertainty: float = 0.0
    citations: List[str] = []
    policyState: Dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_vector(self):
        """Execute validate vector.
            """

        self.vector = normalize_vector(self.vector, dim=_get_settings().hrr_dim)
        return self


class Memory(BaseModel):
    """Memory schema for nano profile."""

    id: str
    type: str  # "episodic"|"semantic"|"procedural"
    vector: List[float]
    graphRefs: List[str] = []
    payload: Dict[str, Any] = {}
    strength: float = 1.0

    @model_validator(mode="after")
    def _validate_memory_vector(self):
        """Execute validate memory vector.
            """

        self.vector = normalize_vector(self.vector, dim=_get_settings().hrr_dim)
        return self


class ToolCall(BaseModel):
    """Tool call schema for nano profile."""

    toolId: str
    schemaVersion: str
    args: Dict[str, Any]
    budget: float = 0.0
    retry: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PlanStep(BaseModel):
    """Plan step schema for nano profile."""

    id: str
    preconds: List[str] = []
    action: str
    expected: Dict[str, Any] = {}
    deadline: Optional[str] = None  # ISO 8601
    risk: float = 0.0


class Action(BaseModel):
    """Action schema for nano profile."""

    channel: str
    toolId: str
    content: str
    args: Dict[str, Any] = {}
    constraints: Dict[str, Any] = {}
    outcome: Optional[Dict[str, Any]] = None


class Feedback(BaseModel):
    """Feedback schema for nano profile."""

    signal: str  # "success"|"fail"|"reward"
    reason: str
    metrics: Dict[str, Any] = {}

    class Observation(BaseModel):
        """Observation class implementation."""

        data: dict
        timestamp: float

    class Thought(BaseModel):
        """Thought class implementation."""

        query: str
        context: dict = {}

    class Memory(BaseModel):
        """Memory class implementation."""

        data: dict
        timestamp: float

        @classmethod
        def from_observation(cls, obs: Any):
            """Execute from observation.

                Args:
                    obs: The obs.
                """

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
            """Execute matches.

                Args:
                    thought: The thought.
                """

            from somabrain.math import cosine_similarity, normalize_vector as _norm

            if hasattr(thought, "vector"):
                query_vec = np.array(getattr(thought, "vector", []), dtype=np.float32)
            else:
                d = dict(thought) if not isinstance(thought, dict) else thought
                query_vec = np.array(
                    d.get("vector", d.get("context", {}).get("vector", [])),
                    dtype=np.float32,
                )
            query_vec = _norm(query_vec, dtype=np.float32)
            mem_vec = _norm(
                np.array(self.data.get("vector", []), dtype=np.float32),
                dtype=np.float32,
            )
            if query_vec.shape[0] != mem_vec.shape[0]:
                return False
            return cosine_similarity(query_vec, mem_vec) > 0.95


class Metric(BaseModel):
    """Metric schema for nano profile."""

    name: str
    value: float
    unit: str
    ts: str  # ISO 8601
    spanId: str


# === Action/Planning Schemas ===


class ActRequest(BaseModel):
    """Schema for action execution requests."""

    task: str
    top_k: int = 3
    universe: Optional[str] = None


class ActStepResult(BaseModel):
    """Schema for individual action step results."""

    step: str
    novelty: float
    pred_error: float
    salience: float
    stored: bool
    wm_hits: int
    memory_hits: int
    policy: Optional[dict] = None


class ActResponse(BaseModel):
    """Schema for action execution responses."""

    task: str
    results: List[ActStepResult]
    plan: Optional[List[str]] = None
    plan_universe: Optional[str] = None


class PlanSuggestRequest(BaseModel):
    """Request for plan suggestions."""

    task_key: str
    max_steps: Optional[int] = None
    rel_types: Optional[List[str]] = None
    universe: Optional[str] = None


class PlanSuggestResponse(BaseModel):
    """Response for plan suggestions."""

    plan: List[str]


# === Oak (ROAMDP) Schemas ===


class OakOptionCreateRequest(BaseModel):
    """Request body for creating a new Oak option."""

    option_id: Optional[str] = None
    payload: str = Field(..., description="Base64‑encoded option payload")


class OakPlanSuggestResponse(BaseModel):
    """Response model for Oak endpoints."""

    plan: List[str]


# === Neuromodulator/Personality Schemas ===


class NeuromodStateModel(BaseModel):
    """Schema for neuromodulator state representation."""

    dopamine: float = 0.4
    serotonin: float = 0.5
    noradrenaline: float = 0.0
    acetylcholine: float = 0.0


class PersonalityState(BaseModel):
    """Schema for personality trait states."""

    traits: Dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_traits(self):
        """Execute validate traits.
            """

        validated: Dict[str, float] = {}
        for k, v in (self.traits or {}).items():
            try:
                fv = float(v)
            except Exception as exc:
                raise ValueError(f"Trait '{k}' must be numeric") from exc
            if not 0.0 <= fv <= 1.0:
                raise ValueError(f"Trait '{k}' must be in [0,1]")
            validated[k] = fv
        object.__setattr__(self, "traits", validated)
        return self


class Persona(BaseModel):
    """Persona record schema."""

    id: str
    display_name: str | None = None
    properties: dict[str, Any] = {}
    fact: str = "persona"


__all__ = [
    # Nano Profile
    "Observation",
    "Thought",
    "Memory",
    "ToolCall",
    "PlanStep",
    "Action",
    "Feedback",
    "Metric",
    # Action/Planning
    "ActRequest",
    "ActStepResult",
    "ActResponse",
    "PlanSuggestRequest",
    "PlanSuggestResponse",
    # Oak
    "OakOptionCreateRequest",
    "OakPlanSuggestResponse",
    # Neuromod/Personality
    "NeuromodStateModel",
    "PersonalityState",
    "Persona",
]