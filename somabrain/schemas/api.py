"""
API schemas - Act, Health, Sleep, Plan operations.

Request/response schemas for general API endpoints.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActRequest(BaseModel):
    """Schema for action execution requests."""

    task: str
    top_k: int = 3
    universe: str | None = None


class ActStepResult(BaseModel):
    """Schema for individual action step results."""

    step: str
    novelty: float
    pred_error: float
    salience: float
    stored: bool
    wm_hits: int
    memory_hits: int
    policy: dict | None = None


class ActResponse(BaseModel):
    """Schema for action execution responses."""

    task: str
    results: list[ActStepResult]
    plan: list[str] | None = None
    plan_universe: str | None = None


class HealthResponse(BaseModel):
    """Schema for system health check responses."""

    ok: bool
    components: dict
    namespace: str | None = None
    trace_id: str | None = None
    deadline_ms: str | None = None
    idempotency_key: str | None = None
    constitution_version: str | None = None
    constitution_status: str | None = None
    minimal_public_api: bool | None = None
    external_backends_required: bool | None = None
    predictor_provider: str | None = None
    full_stack: bool | None = None
    embedder: dict[str, Any] | None = None
    component_counts: dict[str, int] | None = None
    ready: bool | None = None
    memory_items: int | None = None
    predictor_ok: bool | None = None
    memory_ok: bool | None = None
    embedder_ok: bool | None = None
    retrieval_ready: bool | None = None
    opa_ok: bool | None = None
    opa_required: bool | None = None
    kafka_ok: bool | None = None
    postgres_ok: bool | None = None
    metrics_ready: bool | None = None
    metrics_required: list[str] | None = None
    alerts: list[str] | None = None
    memory_circuit_open: bool | None = None
    fd_trace_norm_error: float | None = None
    fd_psd_ok: bool | None = None
    fd_capture_ratio: float | None = None
    scorer: dict[str, Any] | None = None


class PersonalityState(BaseModel):
    """Schema for personality trait states."""

    traits: dict[str, float] = Field(default_factory=dict)


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

    nrem: bool | None = True
    rem: bool | None = True


class SleepRunResponse(BaseModel):
    """Sleep run response schema."""

    ok: bool = Field(..., description="Whether the sleep run started successfully")
    run_id: str | None = Field(
        None, description="Identifier for the initiated sleep run"
    )


class SleepStatusResponse(BaseModel):
    """Sleep status response."""

    enabled: bool
    interval_seconds: int
    last: dict[str, float | None]


class SleepStatusAllResponse(BaseModel):
    """Sleep status for all tenants."""

    enabled: bool
    interval_seconds: int
    tenants: dict[str, dict[str, float | None]]


class PlanSuggestRequest(BaseModel):
    """Plan suggestion request."""

    task_key: str
    max_steps: int | None = Field(None, ge=1, le=50)
    rel_types: list[str] | None = None
    universe: str | None = None


class PlanSuggestResponse(BaseModel):
    """Plan suggestion response."""

    plan: list[str]


class ReflectResponse(BaseModel):
    """Reflect operation response."""

    created: int
    summaries: list[str]


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
