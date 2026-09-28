"""
Admin schemas - Feature flags, Outbox, Quota operations.

Request/response schemas for admin endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlagsResponse(BaseModel):
    """Response model for the admin feature-flags status endpoint."""

    status: dict[str, Any]
    overrides: list[str]


class FeatureFlagsUpdateRequest(BaseModel):
    """Request model for updating feature-flag overrides."""

    disabled: list[str]


class FeatureFlagsUpdateResponse(BaseModel):
    """Response model after attempting to update feature-flag overrides."""

    overrides: list[str]
    started_at_ms: int | None = Field(
        None, description="Epoch ms when the run started"
    )
    mode: str | None = Field(
        None, description="Sleep mode executed, e.g. 'nrem' or 'rem'"
    )
    details: dict[str, Any] | None = Field(
        None, description="Optional additional runtime details"
    )


class OutboxEventModel(BaseModel):
    """Admin-facing view of an outbox event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    status: str
    tenant_id: str | None = None
    dedupe_key: str
    retries: int | None = None
    created_at: datetime | None = None
    last_error: str | None = None
    payload: dict[str, Any]


class OutboxListResponse(BaseModel):
    """List of outbox events."""

    events: list[OutboxEventModel]
    count: int


class OutboxReplayRequest(BaseModel):
    """Request to replay outbox events."""

    event_ids: list[int] = Field(..., min_length=1, max_length=1000)


class OutboxReplayResponse(BaseModel):
    """Response from outbox replay."""

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


class QuotaStatus(BaseModel):
    """Per-tenant quota status."""

    tenant_id: str
    daily_limit: int
    remaining: int | float
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
