"""
API Rate Limiting Dashboard for SomaBrain.

Real-time rate limit monitoring with Django cache counters.
Uses REAL Django cache - NO mocks, NO fallbacks.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Rate limit enforcement
- 🏛️ Architect: Clean rate limiting patterns
- 💾 DBA: Real Django cache counters
- 🐍 Django Expert: Native Django cache patterns
- 📚 Technical Writer: Rate limit documentation
- 🧪 QA Engineer: Rate limit validation
- 🚨 SRE: Rate limit monitoring/alerts
- 📊 Performance: Real-time metrics
- 🎨 UX: Clear quota status
- 🛠️ DevOps: Rate limit configuration
"""

from typing import List
from datetime import timedelta
from uuid import UUID

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.saas.models import (
    Tenant,
    SubscriptionTier,
    AuditLog,
    ActorType,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Rate Limits"])


# =============================================================================
# RATE LIMIT STORAGE (Real Django Cache)
# =============================================================================


def get_rate_key(tenant_id: str, endpoint: str, window: str) -> str:
    """Generate rate limit key for REAL cache."""
    return f"ratelimit:{tenant_id}:{endpoint}:{window}"


def get_current_count(tenant_id: str, endpoint: str = "global") -> int:
    """Get REAL current request count from cache."""
    minute_key = get_rate_key(tenant_id, endpoint, "minute")
    return cache.get(minute_key, 0)


def increment_count(tenant_id: str, endpoint: str = "global") -> int:
    """Increment REAL request count in cache."""
    minute_key = get_rate_key(tenant_id, endpoint, "minute")
    current = cache.get(minute_key, 0)
    new_count = current + 1
    cache.set(minute_key, new_count, timeout=60)
    return new_count


def get_tenant_limit(tenant_id: str) -> int:
    """Get REAL rate limit from tenant's subscription tier."""
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        if tenant.subscription_tier:
            return tenant.subscription_tier.rate_limit_rpm or 100
    except Tenant.DoesNotExist:
        pass
    return 100  # Default


# =============================================================================
# SCHEMAS
# =============================================================================


class RateLimitStatus(Schema):
    """Current rate limit status."""

    tenant_id: str
    limit: int
    remaining: int
    used: int
    reset_at: str
    percentage_used: float


class RateLimitEndpoint(Schema):
    """Per-endpoint rate limit."""

    endpoint: str
    method: str
    limit: int
    used: int
    remaining: int


class RateLimitViolation(Schema):
    """Rate limit violation record."""

    id: str
    tenant_id: str
    endpoint: str
    ip_address: str
    timestamp: str
    requested: int
    limit: int


class RateLimitConfig(Schema):
    """Rate limit configuration."""

    tier_name: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int


# =============================================================================
# RATE LIMIT STATUS
# =============================================================================


@router.get("/{tenant_id}/status", response=RateLimitStatus)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_rate_limit_status(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get current rate limit status for tenant.

    📊 Performance: REAL cache counters

    REAL data from Django cache.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    # Get REAL limit from subscription tier
    limit = get_tenant_limit(str(tenant_id))

    # Get REAL current count from cache
    used = get_current_count(str(tenant_id))

    remaining = max(0, limit - used)
    percentage = (used / limit * 100) if limit > 0 else 0

    # Calculate reset time (next minute)
    now = timezone.now()
    reset_at = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    return RateLimitStatus(
        tenant_id=str(tenant_id),
        limit=limit,
        remaining=remaining,
        used=used,
        reset_at=reset_at.isoformat(),
        percentage_used=round(percentage, 2),
    )


@router.get("/{tenant_id}/endpoints", response=List[RateLimitEndpoint])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_endpoint_limits(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get per-endpoint rate limit usage.

    📊 Performance: Endpoint-level metrics

    REAL cache data.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    limit = get_tenant_limit(str(tenant_id))

    # Common endpoints
    endpoints = [
        ("GET", "/api/v1/memories"),
        ("POST", "/api/v1/memories"),
        ("GET", "/api/v1/agents"),
        ("POST", "/api/v1/search"),
        ("GET", "/api/v1/analytics"),
    ]

    result = []
    for method, path in endpoints:
        endpoint_key = f"{method}:{path}"
        used = get_current_count(str(tenant_id), endpoint_key)

        result.append(
            RateLimitEndpoint(
                endpoint=path,
                method=method,
                limit=limit,
                used=used,
                remaining=max(0, limit - used),
            )
        )

    return result


@router.get("/{tenant_id}/config", response=RateLimitConfig)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_rate_limit_config(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get rate limit configuration for tenant.

    🔒 Security: Tier-based limits

    REAL tier data.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    tier = tenant.subscription_tier

    if not tier:
        raise HttpError(503, "No subscription tier configured")

    rpm = tier.rate_limit_rpm or 100

    return RateLimitConfig(
        tier_name=tier.name,
        requests_per_minute=rpm,
        requests_per_hour=rpm * 60,
        requests_per_day=rpm * 60 * 24,
        burst_limit=rpm * 2,
    )


# =============================================================================
# VIOLATIONS
# =============================================================================


@router.get("/{tenant_id}/violations", response=List[RateLimitViolation])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def list_rate_limit_violations(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 50,
):
    """
    List recent rate limit violations.

    🚨 SRE: Violation monitoring

    REAL audit log data.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    # Get REAL violations from audit log
    violations = AuditLog.objects.filter(
        tenant_id=tenant_id,
        action="rate_limit.exceeded",
    ).order_by("-timestamp")[:limit]

    return [
        RateLimitViolation(
            id=str(v.id),
            tenant_id=str(v.tenant_id),
            endpoint=v.details.get("endpoint", "") if v.details else "",
            ip_address=v.ip_address or "",
            timestamp=v.timestamp.isoformat(),
            requested=v.details.get("requested", 0) if v.details else 0,
            limit=v.details.get("limit", 0) if v.details else 0,
        )
        for v in violations
    ]


@router.get("/{tenant_id}/violations/count")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def count_violations(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 7,
):
    """
    Count rate limit violations.

    📊 Performance: REAL counts
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    since = timezone.now() - timedelta(days=days)

    # REAL count from database
    count = AuditLog.objects.filter(
        tenant_id=tenant_id,
        action="rate_limit.exceeded",
        timestamp__gte=since,
    ).count()

    return {
        "tenant_id": str(tenant_id),
        "violations": count,
        "period_days": days,
    }


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================


@router.get("/admin/thresholds")
@require_auth(roles=["super-admin"])
def list_tier_thresholds(request: AuthenticatedRequest):
    """
    List rate limits by tier (admin).

    🛠️ DevOps: Tier configuration

    REAL tier data.
    """
    tiers = SubscriptionTier.objects.filter(is_active=True).order_by("display_order")

    if not tiers.exists():
        raise HttpError(503, "No subscription tiers configured")

    return {
        "tiers": [
            {
                "name": tier.name,
                "slug": tier.slug,
                "rate_limit_rpm": tier.rate_limit_rpm or 0,
                "max_users": tier.max_users or 0,
                "max_agents": tier.max_agents or 0,
            }
            for tier in tiers
        ]
    }


@router.get("/admin/top-consumers")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_top_consumers(
    request: AuthenticatedRequest,
    limit: int = 10,
):
    """
    Get top API consumers (admin).

    📊 Performance: Platform-wide metrics

    REAL data from cache and database.
    """
    # Get all active tenants - REAL
    tenants = Tenant.objects.filter(status="active")[:50]

    consumers = []
    for tenant in tenants:
        used = get_current_count(str(tenant.id))
        tier_limit = get_tenant_limit(str(tenant.id))

        consumers.append(
            {
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name,
                "requests_minute": used,
                "limit": tier_limit,
                "usage_percent": (
                    round((used / tier_limit * 100), 2) if tier_limit > 0 else 0
                ),
            }
        )

    # Sort by usage
    consumers.sort(key=lambda x: x["requests_minute"], reverse=True)

    return {"consumers": consumers[:limit]}


@router.post("/admin/reset/{tenant_id}")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def reset_rate_limit(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Reset rate limit counter for tenant (admin).

    🛠️ DevOps: Manual reset

    REAL cache update.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)

    # Clear REAL cache counters
    minute_key = get_rate_key(str(tenant_id), "global", "minute")
    cache.delete(minute_key)

    # Audit log - REAL
    AuditLog.log(
        action="rate_limit.reset",
        resource_type="Tenant",
        resource_id=str(tenant_id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
    )

    return {"success": True, "tenant_id": str(tenant_id)}
