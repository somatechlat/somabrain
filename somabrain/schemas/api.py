"""
API schemas - Act, Health, Sleep, Plan operations.

Request/response schemas for general API endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class HealthResponse(BaseModel):
    """Schema for system health check responses."""

    ok: bool
    components: dict
    namespace: Optional[str] = None
    trace_id: Optional[str] = None
    deadline_ms: Optional[str] = None
    idempotency_key: Optional[str] = None
    constitution_version: Optional[str] = None
    constitution_status: Optional[str] = None
    minimal_public_api: Optional[bool] = None
    external_backends_required: Optional[bool] = None
    predictor_provider: Optional[str] = None
    full_stack: Optional[bool] = None
    embedder: Optional[Dict[str, Any]] = None
    stub_counts: Optional[Dict[str, int]] = None
    ready: Optional[bool] = None
    memory_items: Optional[int] = None
    predictor_ok: Optional[bool] = None
    memory_ok: Optional[bool] = None
    embedder_ok: Optional[bool] = None
    retrieval_ready: Optional[bool] = None
    opa_ok: Optional[bool] = None
    opa_required: Optional[bool] = None
    kafka_ok: Optional[bool] = None
    postgres_ok: Optional[bool] = None
    metrics_ready: Optional[bool] = None
    metrics_required: Optional[list[str]] = None
    alerts: Optional[list[str]] = None
    memory_circuit_open: Optional[bool] = None
    fd_trace_norm_error: Optional[float] = None
    fd_psd_ok: Optional[bool] = None
    fd_capture_ratio: Optional[float] = None
    scorer: Optional[Dict[str, Any]] = None


class PersonalityState(BaseModel):
    """Schema for personality trait states."""

    traits: Dict[str, float] = Field(default_factory=dict)


class Persona(BaseModel):
    """Persona record schema."""

    id: str
    display_name: str | None = None
    properties: dict[str, Any] = {}
    fact: str = "persona"


class NeuromodStateModel(BaseModel):
    """Schema for neuromodulator state representation."""

    dopamine: float = 0.4
    serotonin: float = 0.5
    noradrenaline: float = 0.0
    acetylcholine: float = 0.0


class SleepRunRequest(BaseModel):
    """Sleep run request schema."""

    nrem: Optional[bool] = True
    rem: Optional[bool] = True


class SleepRunResponse(BaseModel):
    """Sleep run response schema."""

    ok: bool = Field(..., description="Whether the sleep run started successfully")
    run_id: Optional[str] = Field(None, description="Identifier for the initiated sleep run")


class SleepStatusResponse(BaseModel):
    """Sleep status response."""

    enabled: bool
    interval_seconds: int
    last: Dict[str, Optional[float]]


class SleepStatusAllResponse(BaseModel):
    """Sleep status for all tenants."""

    enabled: bool
    interval_seconds: int
    tenants: Dict[str, Dict[str, Optional[float]]]


class PlanSuggestRequest(BaseModel):
    """Plan suggestion request."""

    task_key: str
    max_steps: Optional[int] = None
    rel_types: Optional[List[str]] = None
    universe: Optional[str] = None


class PlanSuggestResponse(BaseModel):
    """Plan suggestion response."""

    plan: List[str]


class ReflectResponse(BaseModel):
    """Reflect operation response."""

    created: int
    summaries: List[str]


class MigrateExportRequest(BaseModel):
    """Schema for data export requests."""

    include_wm: bool = True
    wm_limit: int = 128


class MigrateExportResponse(BaseModel):
    """Schema for export operation responses."""

    manifest: dict
    memories: list[dict]
    wm: list[dict] = []


class MigrateImportRequest(BaseModel):
    """Schema for data import requests."""

    manifest: dict
    memories: list[dict]
    wm: list[dict] = []
    replace: bool = False


class MigrateImportResponse(BaseModel):
    """Import operation response."""

    imported: int
    wm_warmed: int
