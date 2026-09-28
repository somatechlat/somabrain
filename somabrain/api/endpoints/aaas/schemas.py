"""
AAAS Admin Schemas for Django Ninja endpoints.

Pydantic Schema models for tenant, API key, subscription operations.
"""

from datetime import datetime
from uuid import UUID

from ninja import Schema

# =============================================================================
# TENANT SCHEMAS
# =============================================================================


class TenantCreateSchema(Schema):
    """Create tenant request."""

    name: str
    slug: str
    tier_slug: str = "free"
    admin_email: str
    billing_email: str | None = None
    config: dict | None = None


class TenantUpdateSchema(Schema):
    """Update tenant request."""

    name: str | None = None
    admin_email: str | None = None
    billing_email: str | None = None
    config: dict | None = None
    quota_overrides: dict | None = None


class TenantResponseSchema(Schema):
    """Tenant response."""

    id: UUID
    name: str
    slug: str
    status: str
    tier_name: str
    tier_slug: str
    admin_email: str | None
    created_at: datetime


class TenantListSchema(Schema):
    """Paginated tenant list."""

    tenants: list[TenantResponseSchema]
    total: int
    page: int
    page_size: int


# =============================================================================
# API KEY SCHEMAS
# =============================================================================


class APIKeyCreateSchema(Schema):
    """Create API key request."""

    name: str
    scopes: list[str] = ["read:memory", "write:memory"]
    expires_days: int | None = None
    is_test: bool = False


class APIKeyResponseSchema(Schema):
    """API key response (without full key)."""

    id: UUID
    name: str
    key_prefix: str
    scopes: list
    is_active: bool
    is_test: bool
    last_used_at: datetime | None
    created_at: datetime


class APIKeyCreatedSchema(Schema):
    """Response when API key is created (includes full key ONCE)."""

    id: UUID
    name: str
    key: str  # Full key - only shown once!
    key_prefix: str
    scopes: list


# =============================================================================
# SUBSCRIPTION TIER SCHEMAS
# =============================================================================


class SubscriptionTierCreateSchema(Schema):
    """Create subscription tier request."""

    name: str
    slug: str
    price_monthly: float
    price_yearly: float | None = 0.0
    features: dict | None = {}
    api_calls_limit: int | None = 1000
    memory_ops_limit: int | None = 500
    storage_limit_mb: int | None = 100
    is_active: bool = True


class SubscriptionTierUpdateSchema(Schema):
    """Update subscription tier request."""

    name: str | None = None
    price_monthly: float | None = None
    features: dict | None = None
    api_calls_limit: int | None = None
    is_active: bool | None = None


class SubscriptionTierResponseSchema(Schema):
    """Subscription tier details."""

    id: UUID
    name: str
    slug: str
    price_monthly: float
    features: dict
    is_active: bool
    created_at: datetime


# =============================================================================
# SUBSCRIPTION SCHEMAS
# =============================================================================


class SubscriptionResponseSchema(Schema):
    """Subscription response."""

    id: UUID
    tier_name: str
    tier_slug: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None


class SubscriptionChangeSchema(Schema):
    """Change subscription tier."""

    tier_slug: str


# =============================================================================
# USAGE SCHEMAS
# =============================================================================


class UsageEventSchema(Schema):
    """Single usage event."""

    code: str
    properties: dict
    timestamp: str


class UsageReportSchema(Schema):
    """Usage report from external service."""

    tenant_id: str
    source: str
    events: list[UsageEventSchema]
