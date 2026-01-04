"""
SaaS Admin API Endpoints for SomaBrain.

Django Ninja endpoints for tenant management, API keys, billing.
Eye of God administrative interface backend.

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: RESTful design, versioned API
- Security: Permission checks, audit logging
- DevOps: Structured responses
- QA: Input validation
- Docs: OpenAPI docstrings
- DBA: Optimized queries
- SRE: Rate limiting, observability
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.saas.auth import APIKeyAuth, log_api_action, require_scope
from somabrain.saas.billing import get_lago_client
from somabrain.saas.models import (
    APIKey,
    AuditLog,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    Tenant,
    TenantStatus,
    TenantUser,
    UserRole,
)

logger = logging.getLogger(__name__)

# =============================================================================
# ROUTER
# =============================================================================

router = Router(tags=["SaaS Admin"])


# =============================================================================
# SCHEMAS
# =============================================================================

# --- Tenant Schemas ---

class TenantCreateSchema(Schema):
    """Create tenant request."""
    name: str
    slug: str
    tier_slug: str = "free"
    admin_email: str
    billing_email: Optional[str] = None
    config: Optional[dict] = None


class TenantUpdateSchema(Schema):
    """Update tenant request."""
    name: Optional[str] = None
    admin_email: Optional[str] = None
    billing_email: Optional[str] = None
    config: Optional[dict] = None
    quota_overrides: Optional[dict] = None


class TenantResponseSchema(Schema):
    """Tenant response."""
    id: UUID
    name: str
    slug: str
    status: str
    tier_name: str
    tier_slug: str
    admin_email: Optional[str]
    created_at: datetime


class TenantListSchema(Schema):
    """Paginated tenant list."""
    tenants: List[TenantResponseSchema]
    total: int
    page: int
    page_size: int


# --- API Key Schemas ---

class APIKeyCreateSchema(Schema):
    """Create API key request."""
    name: str
    scopes: List[str] = ["read:memory", "write:memory"]
    expires_days: Optional[int] = None
    is_test: bool = False


class APIKeyResponseSchema(Schema):
    """API key response (without full key)."""
    id: UUID
    name: str
    key_prefix: str
    scopes: list
    is_active: bool
    is_test: bool
    last_used_at: Optional[datetime]
    created_at: datetime


class APIKeyCreatedSchema(Schema):
    """Response when API key is created (includes full key ONCE)."""
    id: UUID
    name: str
    key: str  # Full key - only shown once!
    key_prefix: str
    scopes: list


# --- Subscription Tier Schemas ---

class SubscriptionTierCreateSchema(Schema):
    """Create subscription tier request."""
    name: str
    slug: str
    price_monthly: float
    price_yearly: Optional[float] = 0.0
    features: Optional[dict] = {}
    api_calls_limit: Optional[int] = 1000
    memory_ops_limit: Optional[int] = 500
    storage_limit_mb: Optional[int] = 100
    is_active: bool = True


class SubscriptionTierUpdateSchema(Schema):
    """Update subscription tier request."""
    name: Optional[str] = None
    price_monthly: Optional[float] = None
    features: Optional[dict] = None
    api_calls_limit: Optional[int] = None
    is_active: Optional[bool] = None


class SubscriptionTierResponseSchema(Schema):
    """Subscription tier details."""
    id: UUID
    name: str
    slug: str
    price_monthly: float
    features: dict
    is_active: bool
    created_at: datetime


# --- Subscription Schemas ---

class SubscriptionResponseSchema(Schema):
    """Subscription response."""
    id: UUID
    tier_name: str
    tier_slug: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]


class SubscriptionChangeSchema(Schema):
    """Change subscription tier."""
    tier_slug: str


# =============================================================================
# TENANT ENDPOINTS
# =============================================================================

@router.get("/tenants", response=TenantListSchema, auth=APIKeyAuth())
@require_scope("admin:tenants")
def list_tenants(
    request,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
):
    """
    List all tenants (paginated).
    
    Requires: admin:tenants scope
    """
    queryset = Tenant.objects.select_related("tier").all()
    
    if status:
        queryset = queryset.filter(status=status)
    
    total = queryset.count()
    offset = (page - 1) * page_size
    tenants = queryset[offset:offset + page_size]
    
    return {
        "tenants": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "status": t.status,
                "tier_name": t.tier.name if t.tier else "None",
                "tier_slug": t.tier.slug if t.tier else "none",
                "admin_email": t.admin_email,
                "created_at": t.created_at,
            }
            for t in tenants
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/tenants", response=TenantResponseSchema, auth=APIKeyAuth())
@require_scope("admin:tenants")
def create_tenant(request, data: TenantCreateSchema):
    """
    Create a new tenant.
    
    Requires: admin:tenants scope
    
    Automatically:
    - Creates Lago customer
    - Creates subscription
    - Logs to audit trail
    """
    # Get tier
    try:
        tier = SubscriptionTier.objects.get(slug=data.tier_slug, is_active=True)
    except SubscriptionTier.DoesNotExist:
        raise HttpError(400, f"Unknown tier: {data.tier_slug}")
    
    # Check slug uniqueness
    if Tenant.objects.filter(slug=data.slug).exists():
        raise HttpError(400, f"Slug already exists: {data.slug}")
    
    with transaction.atomic():
        # Create tenant
        tenant = Tenant.objects.create(
            name=data.name,
            slug=data.slug,
            tier=tier,
            status=TenantStatus.ACTIVE,
            admin_email=data.admin_email,
            billing_email=data.billing_email or data.admin_email,
            config=data.config or {},
            created_by=str(request.auth.get("api_key_id")),
        )
        
        # Create subscription
        Subscription.objects.create(
            tenant=tenant,
            tier=tier,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
        )
        
        # Log
        log_api_action(
            request,
            action="tenant.created",
            resource_type="tenant",
            resource_id=tenant.id,
            details={"name": data.name, "tier": data.tier_slug},
        )
    
    # Sync to Lago (async/background - don't block)
    try:
        lago = get_lago_client()
        lago.create_customer(tenant)
        lago.create_subscription(tenant, tier)
    except Exception as e:
        logger.warning(f"Lago sync failed for tenant {tenant.slug}: {e}")
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "tier_name": tier.name,
        "tier_slug": tier.slug,
        "admin_email": tenant.admin_email,
        "created_at": tenant.created_at,
    }


@router.get("/tenants/{tenant_id}", response=TenantResponseSchema, auth=APIKeyAuth())
@require_scope("admin:tenants")
def get_tenant(request, tenant_id: UUID):
    """Get tenant by ID."""
    tenant = get_object_or_404(Tenant.objects.select_related("tier"), id=tenant_id)
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "tier_name": tenant.tier.name if tenant.tier else "None",
        "tier_slug": tenant.tier.slug if tenant.tier else "none",
        "admin_email": tenant.admin_email,
        "created_at": tenant.created_at,
    }


@router.patch("/tenants/{tenant_id}", response=TenantResponseSchema, auth=APIKeyAuth())
@require_scope("admin:tenants")
def update_tenant(request, tenant_id: UUID, data: TenantUpdateSchema):
    """Update tenant details."""
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    if data.name:
        tenant.name = data.name
    if data.admin_email:
        tenant.admin_email = data.admin_email
    if data.billing_email:
        tenant.billing_email = data.billing_email
    if data.config:
        tenant.config.update(data.config)
    if data.quota_overrides:
        tenant.quota_overrides.update(data.quota_overrides)
    
    tenant.save()
    
    log_api_action(
        request,
        action="tenant.updated",
        resource_type="tenant",
        resource_id=tenant.id,
    )
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "tier_name": tenant.tier.name if tenant.tier else "None",
        "tier_slug": tenant.tier.slug if tenant.tier else "none",
        "admin_email": tenant.admin_email,
        "created_at": tenant.created_at,
    }


@router.post("/tenants/{tenant_id}/suspend", auth=APIKeyAuth())
@require_scope("admin:tenants")
def suspend_tenant(request, tenant_id: UUID, reason: str = "Administrative action"):
    """Suspend a tenant."""
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    tenant.suspend(reason=reason)
    
    log_api_action(
        request,
        action="tenant.suspended",
        resource_type="tenant",
        resource_id=tenant.id,
        details={"reason": reason},
    )
    
    return {"status": "suspended", "tenant_id": str(tenant_id)}


@router.post("/tenants/{tenant_id}/activate", auth=APIKeyAuth())
@require_scope("admin:tenants")
def activate_tenant(request, tenant_id: UUID):
    """Activate a suspended tenant."""
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    tenant.activate()
    
    log_api_action(
        request,
        action="tenant.activated",
        resource_type="tenant",
        resource_id=tenant.id,
    )
    
    return {"status": "active", "tenant_id": str(tenant_id)}


@router.delete("/tenants/{tenant_id}", auth=APIKeyAuth())
@require_scope("admin:tenants")
def delete_tenant(request, tenant_id: UUID, hard_delete: bool = False):
    """
    Delete a tenant.
    
    By default, soft delete (set status=DISABLED).
    Use hard_delete=true to permanently remove.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    if hard_delete:
        tenant_slug = tenant.slug
        tenant.delete()
        
        log_api_action(
            request,
            action="tenant.deleted.hard",
            resource_type="tenant",
            resource_id=tenant_id,
            details={"slug": tenant_slug},
        )
        
        return {"status": "deleted", "tenant_id": str(tenant_id)}
    else:
        tenant.status = TenantStatus.DISABLED
        tenant.save()
        
        log_api_action(
            request,
            action="tenant.deleted.soft",
            resource_type="tenant",
            resource_id=tenant_id,
        )
        
        return {"status": "disabled", "tenant_id": str(tenant_id)}


# =============================================================================
# API KEY ENDPOINTS
# =============================================================================

@router.get("/tenants/{tenant_id}/api-keys", response=List[APIKeyResponseSchema], auth=APIKeyAuth())
@require_scope("admin:tenants")
def list_api_keys(request, tenant_id: UUID):
    """List API keys for a tenant."""
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    keys = APIKey.objects.filter(tenant=tenant).order_by("-created_at")
    
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "is_active": k.is_active,
            "is_test": k.is_test,
            "last_used_at": k.last_used_at,
            "created_at": k.created_at,
        }
        for k in keys
    ]


@router.post("/tenants/{tenant_id}/api-keys", response=APIKeyCreatedSchema, auth=APIKeyAuth())
@require_scope("admin:tenants")
def create_api_key(request, tenant_id: UUID, data: APIKeyCreateSchema):
    """
    Create a new API key for a tenant.
    
    ⚠️ The full key is only returned ONCE in this response!
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    # Generate key
    full_key, prefix, key_hash = APIKey.generate_key(is_test=data.is_test)
    
    # Calculate expiration
    expires_at = None
    if data.expires_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)
    
    # Create key
    api_key = APIKey.objects.create(
        tenant=tenant,
        name=data.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=data.scopes,
        is_test=data.is_test,
        expires_at=expires_at,
    )
    
    log_api_action(
        request,
        action="api_key.created",
        resource_type="api_key",
        resource_id=api_key.id,
        tenant=tenant,
        details={"name": data.name, "scopes": data.scopes},
    )
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": full_key,  # Only shown once!
        "key_prefix": prefix,
        "scopes": api_key.scopes,
    }


@router.delete("/tenants/{tenant_id}/api-keys/{key_id}", auth=APIKeyAuth())
@require_scope("admin:tenants")
def revoke_api_key(request, tenant_id: UUID, key_id: UUID):
    """Revoke an API key."""
    api_key = get_object_or_404(APIKey, id=key_id, tenant_id=tenant_id)
    
    api_key.revoke()
    
    log_api_action(
        request,
        action="api_key.revoked",
        resource_type="api_key",
        resource_id=key_id,
        tenant=api_key.tenant,
    )
    
    return {"status": "revoked", "key_id": str(key_id)}


# =============================================================================
# SUBSCRIPTION ENDPOINTS
# =============================================================================

@router.get("/tenants/{tenant_id}/subscription", response=SubscriptionResponseSchema, auth=APIKeyAuth())
@require_scope("admin:tenants")
def get_subscription(request, tenant_id: UUID):
    """Get tenant subscription."""
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    try:
        sub = tenant.subscription
        return {
            "id": sub.id,
            "tier_name": sub.tier.name,
            "tier_slug": sub.tier.slug,
            "status": sub.status,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
        }
    except Subscription.DoesNotExist:
        raise HttpError(404, "No subscription found")


@router.post("/tenants/{tenant_id}/subscription/change", response=SubscriptionResponseSchema, auth=APIKeyAuth())
@require_scope("admin:tenants")
def change_subscription(request, tenant_id: UUID, data: SubscriptionChangeSchema):
    """Change tenant subscription tier."""
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    new_tier = get_object_or_404(SubscriptionTier, slug=data.tier_slug, is_active=True)
    
    try:
        sub = tenant.subscription
        old_tier = sub.tier.slug
        sub.tier = new_tier
        sub.save()
        
        # Update tenant tier reference
        tenant.tier = new_tier
        tenant.save()
        
        # Sync to Lago
        lago = get_lago_client()
        lago.change_subscription_plan(str(tenant.id), new_tier.slug)
        
        log_api_action(
            request,
            action="subscription.changed",
            resource_type="subscription",
            resource_id=sub.id,
            tenant=tenant,
            details={"from": old_tier, "to": data.tier_slug},
        )
        
        return {
            "id": sub.id,
            "tier_name": sub.tier.name,
            "tier_slug": sub.tier.slug,
            "status": sub.status,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
        }
    except Subscription.DoesNotExist:
        raise HttpError(404, "No subscription found")


# =============================================================================
# SUBSCRIPTION TIER ENDPOINTS (Public)
# =============================================================================

# =============================================================================
# SUBSCRIPTION TIER ENDPOINTS (Mixed Access)
# =============================================================================

@router.get("/tiers", response=List[SubscriptionTierResponseSchema])
def list_tiers(request):
    """List available subscription tiers (public)."""
    tiers = SubscriptionTier.objects.filter(is_active=True).order_by("display_order")
    return [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "price_monthly": float(t.price_monthly),
            "features": t.features,
            "is_active": t.is_active,
            "created_at": t.created_at,
        }
        for t in tiers
    ]


@router.post("/tiers", response=SubscriptionTierResponseSchema, auth=APIKeyAuth())
@require_scope("admin:billing")
def create_tier(request, data: SubscriptionTierCreateSchema):
    """Create a new subscription tier."""
    if SubscriptionTier.objects.filter(slug=data.slug).exists():
        raise HttpError(400, f"Tier slug already exists: {data.slug}")

    tier = SubscriptionTier.objects.create(
        name=data.name,
        slug=data.slug,
        price_monthly=data.price_monthly,
        price_yearly=data.price_yearly or 0,
        features=data.features or {},
        api_calls_limit=data.api_calls_limit or 1000,
        memory_ops_limit=data.memory_ops_limit or 500,
        storage_limit_mb=data.storage_limit_mb or 100,
        is_active=data.is_active,
    )
    
    log_api_action(request, "tier.created", "tier", tier.id, details={"slug": tier.slug})
    
    return {
        "id": tier.id,
        "name": tier.name,
        "slug": tier.slug,
        "price_monthly": float(tier.price_monthly),
        "features": tier.features,
        "is_active": tier.is_active,
        "created_at": tier.created_at,
    }


@router.get("/tiers/{tier_id}", response=SubscriptionTierResponseSchema, auth=APIKeyAuth())
@require_scope("admin:billing")
def get_tier(request, tier_id: UUID):
    """Get subscription tier details."""
    tier = get_object_or_404(SubscriptionTier, id=tier_id)
    return {
        "id": tier.id,
        "name": tier.name,
        "slug": tier.slug,
        "price_monthly": float(tier.price_monthly),
        "features": tier.features,
        "is_active": tier.is_active,
        "created_at": tier.created_at,
    }


@router.patch("/tiers/{tier_id}", response=SubscriptionTierResponseSchema, auth=APIKeyAuth())
@require_scope("admin:billing")
def update_tier(request, tier_id: UUID, data: SubscriptionTierUpdateSchema):
    """Update subscription tier."""
    tier = get_object_or_404(SubscriptionTier, id=tier_id)
    
    if data.name: tier.name = data.name
    if data.price_monthly is not None: tier.price_monthly = data.price_monthly
    if data.features is not None: tier.features = data.features
    if data.api_calls_limit is not None: tier.api_calls_limit = data.api_calls_limit
    if data.is_active is not None: tier.is_active = data.is_active
    
    tier.save()
    log_api_action(request, "tier.updated", "tier", tier.id)
    
    return {
        "id": tier.id,
        "name": tier.name,
        "slug": tier.slug,
        "price_monthly": float(tier.price_monthly),
        "features": tier.features,
        "is_active": tier.is_active,
        "created_at": tier.created_at,
    }


# =============================================================================
# USAGE REPORT ENDPOINT (For SFM Integration)
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
    events: List[UsageEventSchema]


@router.post("/usage/report", auth=APIKeyAuth())
@require_scope("admin:billing")
def report_usage(request, data: UsageReportSchema):
    """
    Receive usage report from SomaFractalMemory.
    
    Forwards events to Lago for billing.
    """
    try:
        tenant = Tenant.objects.get(id=data.tenant_id)
    except Tenant.DoesNotExist:
        raise HttpError(404, f"Tenant not found: {data.tenant_id}")
    
    # Forward to Lago
    lago = get_lago_client()
    success_count = 0
    
    for event in data.events:
        if lago.report_usage(
            tenant=tenant,
            event_type=f"{data.source}_{event.code}",
            properties=event.properties,
        ):
            success_count += 1
    
    log_api_action(
        request,
        action="usage.reported",
        resource_type="usage",
        resource_id=data.tenant_id,
        tenant=tenant,
        details={
            "source": data.source,
            "events_count": len(data.events),
            "success_count": success_count,
        },
    )
    
    return {
        "status": "processed",
        "tenant_id": data.tenant_id,
        "events_received": len(data.events),
        "events_forwarded": success_count,
    }
