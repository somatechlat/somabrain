"""Pydantic schemas for Evaluate/Feedback APIs."""

from __future__ import annotations

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    BaseModel = object

    def Field(*a, **k):
        """Execute Field."""

        return


class EvaluateRequest(BaseModel):
    """Data model for EvaluateRequest."""

    session_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    tenant_id: str | None = None


class MemoryItem(BaseModel):
    """Memoryitem class implementation."""

    id: str
    score: float
    metadata: dict
    embedding: list[float] | None = None


class EvaluateResponse(BaseModel):
    """Data model for EvaluateResponse."""

    query: str
    prompt: str
    tenant_id: str
    memories: list[MemoryItem]
    weights: list[float]
    residual_vector: list[float]
    working_memory: list[dict]
    constitution_checksum: str | None = None


class FeedbackRequest(BaseModel):
    """Data model for FeedbackRequest."""

    session_id: str
    query: str
    prompt: str
    response_text: str
    utility: float
    reward: float | None = None
    metadata: dict | None = None
    tenant_id: str | None = None


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
