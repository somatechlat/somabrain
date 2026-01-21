"""Health, admin, and operational schemas for SomaBrain API.

This module contains Pydantic models for health checks, sleep operations,
feature flags, migration, outbox management, and quota operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# === Health Schemas ===


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
    milvus_metrics: Optional[Dict[str, Any]] = None
    fd_trace_norm_error: Optional[float] = None
    fd_psd_ok: Optional[bool] = None
    fd_capture_ratio: Optional[float] = None
    scorer: Optional[Dict[str, Any]] = None
    tau: Optional[float] = None
    entropy_cap_enabled: Optional[bool] = None
    entropy_cap: Optional[float] = None
    retrieval_entropy: Optional[float] = None


# === Sleep Schemas ===


class SleepRunRequest(BaseModel):
    """Request for sleep run operations."""

    nrem: Optional[bool] = True
    rem: Optional[bool] = True


class SleepRunResponse(BaseModel):
    """Response for sleep run operations."""

    ok: bool = Field(..., description="Whether the sleep run started successfully")
    run_id: Optional[str] = Field(
        None, description="Identifier for the initiated sleep run"
    )


class SleepStatusResponse(BaseModel):
    """Response for sleep status query."""

    enabled: bool
    interval_seconds: int
    last: Dict[str, Optional[float]]


class SleepStatusAllResponse(BaseModel):
    """Response for all tenants sleep status."""

    enabled: bool
    interval_seconds: int
    tenants: Dict[str, Dict[str, Optional[float]]]


# === Feature Flag Schemas ===


class FeatureFlagsResponse(BaseModel):
    """Response model for feature flags status."""

    status: Dict[str, Any]
    overrides: List[str]


class FeatureFlagsUpdateRequest(BaseModel):
    """Request model for updating feature flag overrides."""

    disabled: List[str]


class FeatureFlagsUpdateResponse(BaseModel):
    """Response model after updating feature flag overrides."""

    overrides: List[str]
    started_at_ms: Optional[int] = Field(
        None, description="Epoch ms when the run started"
    )
    mode: Optional[str] = Field(None, description="Sleep mode executed")
    details: Optional[Dict[str, Any]] = Field(
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
    summaries: List[str]


# === Outbox/Admin Schemas ===


class OutboxEventModel(BaseModel):
    """Admin-facing view of an outbox event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    status: str
    tenant_id: Optional[str] = None


class NeuromodAdjustRequest(BaseModel):
    """Request schema for adjusting neuromodulator levels."""

    dopamine: Optional[float] = Field(None, ge=0.0, le=1.0)
    serotonin: Optional[float] = Field(None, ge=0.0, le=1.0)
    noradrenaline: Optional[float] = Field(None, ge=0.0, le=1.0)
    acetylcholine: Optional[float] = Field(None, ge=0.0, le=1.0)


class ProxyRequest(BaseModel):
    """Request schema for proxying requests to external services."""

    service: str
    endpoint: str
    target_url: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ConfigResponse(BaseModel):
    """Response schema for configuration endpoint."""

    tenant_id: str
    namespace: str
    features: Dict[str, bool]
    limits: Dict[str, Any]


class JournalReplayRequest(BaseModel):
    """Request to replay specific journal events."""

    event_ids: List[int] = Field(..., min_length=1, max_length=1000)
    tenant_id: Optional[str] = None
    dedupe_key: str
    retries: Optional[int] = None
    created_at: Optional[datetime] = None
    last_error: Optional[str] = None
    payload: Dict[str, Any]


class OutboxListResponse(BaseModel):
    """Response for listing outbox events."""

    events: List[OutboxEventModel]
    count: int


class OutboxReplayRequest(BaseModel):
    """Request to replay outbox events."""

    event_ids: List[int] = Field(..., min_length=1, max_length=1000)


class OutboxReplayResponse(BaseModel):
    """Response for outbox replay."""

    replayed: int


class OutboxTenantReplayRequest(BaseModel):
    """Request to replay outbox events for a specific tenant."""

    tenant_id: str = Field(..., description="Tenant ID to replay events for")
    status: str = Field("failed", description="Status to filter: pending|failed|sent")
    topic_filter: Optional[str] = Field(
        None, description="Optional topic pattern filter"
    )
    before_timestamp: Optional[datetime] = Field(
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
    events: List[OutboxEventModel]
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

    tenants: List[OutboxTenantSummary]
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
    reset_at: Optional[datetime] = None
    is_exempt: bool = False


class QuotaListResponse(BaseModel):
    """Response for listing all tenant quotas."""

    quotas: List[QuotaStatus]
    total_tenants: int


class QuotaResetRequest(BaseModel):
    """Request to reset a tenant's quota."""

    reason: Optional[str] = Field(None, description="Reason for quota reset")


class QuotaResetResponse(BaseModel):
    """Response after quota reset."""

    tenant_id: str
    reset: bool
    new_remaining: int
    message: str


class QuotaAdjustRequest(BaseModel):
    """Request to adjust a tenant's quota limit."""

    new_limit: int = Field(..., gt=0, description="New daily quota limit")
    reason: Optional[str] = Field(None, description="Reason for quota adjustment")


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
