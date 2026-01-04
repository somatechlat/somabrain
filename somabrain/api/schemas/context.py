"""Pydantic schemas for Evaluate/Feedback APIs."""

from __future__ import annotations

from typing import Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    BaseModel = object

    def Field(*a, **k):
        """Execute Field.
            """

        return None


class EvaluateRequest(BaseModel):
    """Data model for EvaluateRequest."""

    session_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    tenant_id: Optional[str] = None


class MemoryItem(BaseModel):
    """Memoryitem class implementation."""

    id: str
    score: float
    metadata: Dict
    embedding: Optional[List[float]] = None


class EvaluateResponse(BaseModel):
    """Data model for EvaluateResponse."""

    query: str
    prompt: str
    tenant_id: str
    memories: List[MemoryItem]
    weights: List[float]
    residual_vector: List[float]
    working_memory: List[Dict]
    constitution_checksum: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Data model for FeedbackRequest."""

    session_id: str
    query: str
    prompt: str
    response_text: str
    utility: float
    reward: Optional[float] = None
    metadata: Optional[Dict] = None
    tenant_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Data model for FeedbackResponse."""

    accepted: bool
    adaptation_applied: bool


class RetrievalWeightsState(BaseModel):
    """Retrievalweightsstate class implementation."""

    alpha: float
    beta: float
    gamma: float
    tau: float


class UtilityWeightsState(BaseModel):
    """Utilityweightsstate class implementation."""

    lambda_: float
    mu: float
    nu: float


class AdaptationGainsState(BaseModel):
    """Adaptationgainsstate class implementation."""

    alpha: float
    gamma: float
    lambda_: float
    mu: float
    nu: float


class AdaptationConstraintsState(BaseModel):
    """Adaptationconstraintsstate class implementation."""

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


class AdaptationStateResponse(BaseModel):
    """Data model for AdaptationStateResponse."""

    retrieval: RetrievalWeightsState
    utility: UtilityWeightsState
    history_len: int
    learning_rate: float
    gains: AdaptationGainsState
    constraints: AdaptationConstraintsState