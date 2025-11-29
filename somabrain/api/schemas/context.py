"""Pydantic schemas for Evaluate/Feedback APIs."""

from __future__ import annotations

from typing import Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except Exception as exc: raise  # pragma: no cover
    BaseModel = object  # type: ignore

    def Field(*a, **k):  # type: ignore
        return None


class EvaluateRequest(BaseModel):  # type: ignore[misc]
    session_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    tenant_id: Optional[str] = None


class MemoryItem(BaseModel):  # type: ignore[misc]
    id: str
    score: float
    metadata: Dict
    embedding: Optional[List[float]] = None


class EvaluateResponse(BaseModel):  # type: ignore[misc]
    query: str
    prompt: str
    tenant_id: str
    memories: List[MemoryItem]
    weights: List[float]
    residual_vector: List[float]
    working_memory: List[Dict]
    constitution_checksum: Optional[str] = None


class FeedbackRequest(BaseModel):  # type: ignore[misc]
    session_id: str
    query: str
    prompt: str
    response_text: str
    utility: float
    reward: Optional[float] = None
    metadata: Optional[Dict] = None
    tenant_id: Optional[str] = None


class FeedbackResponse(BaseModel):  # type: ignore[misc]
    accepted: bool
    adaptation_applied: bool


class RetrievalWeightsState(BaseModel):  # type: ignore[misc]
    alpha: float
    beta: float
    gamma: float
    tau: float


class UtilityWeightsState(BaseModel):  # type: ignore[misc]
    lambda_: float
    mu: float
    nu: float


class AdaptationGainsState(BaseModel):  # type: ignore[misc]
    alpha: float
    gamma: float
    lambda_: float
    mu: float
    nu: float


class AdaptationConstraintsState(BaseModel):  # type: ignore[misc]
    alpha_min: float
    alpha_max: float
    gamma_min: float
    gamma_max: float
    lambda_min: float
    lambda_max: float
    mu_min: float
    mu_max: float
    nu_min: float
    nu_max: float


class AdaptationStateResponse(BaseModel):  # type: ignore[misc]
    retrieval: RetrievalWeightsState
    utility: UtilityWeightsState
    history_len: int
    learning_rate: float
    gains: AdaptationGainsState
    constraints: AdaptationConstraintsState
