"""Health, admin, and operational schemas for SomaBrain API.

This module contains Pydantic models for health checks, sleep operations,
feature flags, migration, outbox management, and quota operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# === Health Schemas ===


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
    milvus_metrics: dict[str, Any] | None = None
    fd_trace_norm_error: float | None = None
    fd_psd_ok: bool | None = None
    fd_capture_ratio: float | None = None
    scorer: dict[str, Any] | None = None
    tau: float | None = None
    entropy_cap_enabled: bool | None = None
    entropy_cap: float | None = None
    retrieval_entropy: float | None = None


# === Sleep Schemas ===


class SleepRunRequest(BaseModel):
    """Request for sleep run operations."""

    nrem: bool | None = True
    rem: bool | None = True


class SleepRunResponse(BaseModel):
    """Response for sleep run operations."""

    ok: bool = Field(..., description="Whether the sleep run started successfully")
    run_id: str | None = Field(
        None, description="Identifier for the initiated sleep run"
    )


class SleepStatusResponse(BaseModel):
    """Response for sleep status query."""

    enabled: bool
    interval_seconds: int
    last: dict[str, float | None]


class SleepStatusAllResponse(BaseModel):
    """Response for all tenants sleep status."""

    enabled: bool
    interval_seconds: int
    tenants: dict[str, dict[str, float | None]]


# === Feature Flag Schemas ===


class FeatureFlagsResponse(BaseModel):
    """Response model for feature flags status."""

    status: dict[str, Any]
    overrides: list[str]


class FeatureFlagsUpdateRequest(BaseModel):
    """Request model for updating feature flag overrides."""

    disabled: list[str]


class FeatureFlagsUpdateResponse(BaseModel):
    """Response model after updating feature flag overrides."""

    overrides: list[str]
    started_at_ms: int | None = Field(
        None, description="Epoch ms when the run started"
    )
    mode: str | None = Field(None, description="Sleep mode executed")
    details: dict[str, Any] | None = Field(
        None, description="Optional additional runtime details"
    )


# === Migration Schemas ===


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
    """Response for import operations."""

    imported: int
    wm_warmed: int


class ReflectResponse(BaseModel):
    """Response for reflect operations."""

    created: int
    summaries: list[str]


# === Outbox/Admin Schemas ===


class OutboxEventModel(BaseModel):
    """Admin-facing view of an outbox event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    status: str
    tenant_id: str | None = None


class NeuromodAdjustRequest(BaseModel):
    """Request schema for adjusting neuromodulator levels."""

    dopamine: float | None = Field(None, ge=0.0, le=1.0)
    serotonin: float | None = Field(None, ge=0.0, le=1.0)
    noradrenaline: float | None = Field(None, ge=0.0, le=1.0)
    acetylcholine: float | None = Field(None, ge=0.0, le=1.0)


class ProxyRequest(BaseModel):
    """Request schema for proxying requests to external services."""

    service: str
    endpoint: str
    target_url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ConfigResponse(BaseModel):
    """Response schema for configuration endpoint."""

    tenant_id: str
    namespace: str
    features: dict[str, bool]
    limits: dict[str, Any]


class JournalReplayRequest(BaseModel):
    """Request to replay specific journal events."""

    event_ids: list[int] = Field(..., min_length=1, max_length=1000)
    tenant_id: str | None = None
    dedupe_key: str
    retries: int | None = None
    created_at: datetime | None = None
    last_error: str | None = None
    payload: dict[str, Any]


class OutboxListResponse(BaseModel):
    """Response for listing outbox events."""

    events: list[OutboxEventModel]
    count: int


class OutboxReplayRequest(BaseModel):
    """Request to replay outbox events."""

    event_ids: list[int] = Field(..., min_length=1, max_length=1000)


class OutboxReplayResponse(BaseModel):
    """Response for outbox replay."""

    replayed: int


class OutboxTenantReplayRequest(BaseModel):
    """Request to replay outbox events for a specific tenant."""

    tenant_id: str = Field(..., description="Tenant ID to replay events for")
    status: str = Field("failed", description="Status to filter: pending|failed|sent")
    topic_filter: str | None = Field(
        None, description="Optional topic pattern filter"
    )
    before_timestamp: datetime | None = Field(
        None, description="Only replay events before this time"
    )
    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of events to replay"
    )


class OutboxTenantReplayResponse(BaseModel):
    """Response from tenant-specific outbox replay."""

    tenant_id: str
    replayed: int
    status: str


class OutboxTenantListResponse(BaseModel):
    """Response for tenant-specific outbox event listing."""

    tenant_id: str
    events: list[OutboxEventModel]
    count: int
    status: str


class OutboxTenantSummary(BaseModel):
    """Summary statistics for a single tenant's outbox events."""

    tenant_id: str
    pending_count: int
    failed_count: int
    sent_count: int
    total_count: int


class OutboxSummaryResponse(BaseModel):
    """Summary statistics for outbox events across all tenants."""

    tenants: list[OutboxTenantSummary]
    total_tenants: int
    total_pending: int
    total_failed: int
    total_sent: int


# === Quota Schemas ===


class QuotaStatus(BaseModel):
    """Per-tenant quota status for admin monitoring."""

    tenant_id: str
    daily_limit: int
    remaining: int | float  # Allow float('inf') for exempt tenants
    used_today: int
    reset_at: datetime | None = None
    is_exempt: bool = False


class QuotaListResponse(BaseModel):
    """Response for listing all tenant quotas."""

    quotas: list[QuotaStatus]
    total_tenants: int


class QuotaResetRequest(BaseModel):
    """Request to reset a tenant's quota."""

    reason: str | None = Field(None, description="Reason for quota reset")


class QuotaResetResponse(BaseModel):
    """Response after quota reset."""

    tenant_id: str
    reset: bool
    new_remaining: int
    message: str


class QuotaAdjustRequest(BaseModel):
    """Request to adjust a tenant's quota limit."""

    new_limit: int = Field(..., gt=0, description="New daily quota limit")
    reason: str | None = Field(None, description="Reason for quota adjustment")


class QuotaAdjustResponse(BaseModel):
    """Response after quota adjustment."""

    tenant_id: str
    old_limit: int
    new_limit: int
    adjusted: bool
    message: str


__all__ = [
    # Health
    "HealthResponse",
    # Sleep
    "SleepRunRequest",
    "SleepRunResponse",
    "SleepStatusResponse",
    "SleepStatusAllResponse",
    # Feature Flags
    "FeatureFlagsResponse",
    "FeatureFlagsUpdateRequest",
    "FeatureFlagsUpdateResponse",
    # Migration
    "MigrateExportRequest",
    "MigrateExportResponse",
    "MigrateImportRequest",
    "MigrateImportResponse",
    "ReflectResponse",
    # Outbox
    "OutboxEventModel",
    "OutboxListResponse",
    "OutboxReplayRequest",
    "OutboxReplayResponse",
    "OutboxTenantReplayRequest",
    "OutboxTenantReplayResponse",
    "OutboxTenantListResponse",
    "OutboxTenantSummary",
    "OutboxSummaryResponse",
    # Quota
    "QuotaStatus",
    "QuotaListResponse",
    "QuotaResetRequest",
    "QuotaResetResponse",
    "QuotaAdjustRequest",
    "QuotaAdjustResponse",
]
