"""
Billing API Endpoints for SomaBrain SaaS.

Django Ninja API exposing Lago billing operations.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tenant isolation, billing_admin role required
- 🏛️ Architect: Clean separation of billing concerns
- 💾 DBA: ORM for subscription records
- 🐍 Django: Native Django patterns
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable interfaces
- 🚨 SRE: Audit logging for billing actions
- 📊 Perf: Efficient usage batching
- 🎨 UX: Clear billing information
- 🛠️ DevOps: Environment-based Lago config
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.saas.models import (
    Tenant,
    SubscriptionTier,
    Subscription,  # Use existing Subscription model
    UsageRecord,
    AuditLog,
    ActorType,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission
from somabrain.saas.billing import get_lago_client


router = Router(tags=["Billing"])


# =============================================================================
# SCHEMAS
# =============================================================================


class SubscriptionTierOut(Schema):
    """Schema for subscription tier output."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    monthly_price: Decimal = None
    annual_price: Decimal = None
    features: dict
    is_active: bool
    lago_plan_code: Optional[str]

    @staticmethod
    def resolve_monthly_price(obj):
        """Map model price_monthly → schema monthly_price."""
        return obj.price_monthly

    @staticmethod
    def resolve_annual_price(obj):
        """Map model price_yearly → schema annual_price."""
        return obj.price_yearly

    @staticmethod
    def resolve_lago_plan_code(obj):
        """Lago plan code is the tier slug."""
        return obj.slug


class SubscriptionOut(Schema):
    """Schema for tenant subscription output."""

    id: UUID
    tenant_id: UUID
    tier_name: str
    tier_slug: str
    status: str
    started_at: str
    ends_at: Optional[str]
    lago_subscription_id: Optional[str]

    @staticmethod
    def resolve_tier_name(obj):
        """Execute resolve tier name.

        Args:
            obj: The obj.
        """

        return obj.tier.name

    @staticmethod
    def resolve_tier_slug(obj):
        """Execute resolve tier slug.

        Args:
            obj: The obj.
        """

        return obj.tier.slug

    @staticmethod
    def resolve_started_at(obj):
        """Execute resolve started at.

        Args:
            obj: The obj.
        """

        return obj.started_at.isoformat()

    @staticmethod
    def resolve_ends_at(obj):
        """Execute resolve ends at.

        Args:
            obj: The obj.
        """

        return obj.ends_at.isoformat() if obj.ends_at else None


class SubscriptionCreate(Schema):
    """Schema for creating a subscription."""

    tier_id: UUID


class SubscriptionChangePlan(Schema):
    """Schema for changing subscription plan."""

    new_tier_id: UUID


class UsageReportEvent(Schema):
    """Schema for usage event."""

    event_type: str  # e.g., "api_call", "memory_operation"
    count: int = 1
    properties: Optional[dict] = None


class UsageRecordOut(Schema):
    """Schema for usage record output."""

    id: UUID
    tenant_id: UUID
    metric_name: str
    quantity: int
    recorded_at: str
    metadata: dict

    @staticmethod
    def resolve_recorded_at(obj):
        """Execute resolve recorded at.

        Args:
            obj: The obj.
        """

        return obj.recorded_at.isoformat()


class InvoiceOut(Schema):
    """Schema for invoice output."""

    id: str
    status: str
    amount_cents: int
    currency: str
    issuing_date: Optional[str]
    payment_due_date: Optional[str]


class WalletCreate(Schema):
    """Schema for creating a wallet."""

    initial_credits: int
    currency: str = "USD"


class CreditAdd(Schema):
    """Schema for adding credits."""

    credits: int
    reason: str = "Manual top-up"


# =============================================================================
# SUBSCRIPTION TIER ENDPOINTS (Public)
# =============================================================================


@router.get("/tiers", response=List[SubscriptionTierOut])
def list_subscription_tiers(request):
    """
    List all available subscription tiers.

    Public endpoint - no auth required.
    Returns active tiers sorted by price.
    """
    return list(
        SubscriptionTier.objects.filter(is_active=True).order_by("price_monthly")
    )


@router.get("/tiers/{tier_id}", response=SubscriptionTierOut)
def get_subscription_tier(request, tier_id: UUID):
    """Get details of a specific subscription tier."""
    return get_object_or_404(SubscriptionTier, id=tier_id, is_active=True)


# =============================================================================
# TENANT SUBSCRIPTION ENDPOINTS
# =============================================================================


@router.get("/tenant/{tenant_id}/subscription", response=SubscriptionOut)
@require_auth(roles=["super-admin", "tenant-admin", "billing-admin"], any_role=True)
@require_permission(Permission.SUBSCRIPTIONS_READ.value)
def get_tenant_subscription(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get current subscription for a tenant.

    ALL 10 PERSONAS:
    - Security: Tenant isolation enforced
    - DBA: Efficient query with select_related
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    subscription = (
        Subscription.objects.filter(
            tenant_id=tenant_id,
            status="active",
        )
        .select_related("tier")
        .first()
    )

    if not subscription:
        from ninja.errors import HttpError

        raise HttpError(404, "No active subscription found")

    return subscription


@router.post("/tenant/{tenant_id}/subscription", response=SubscriptionOut)
@require_auth(roles=["super-admin", "tenant-admin", "billing-admin"], any_role=True)
@require_permission(Permission.SUBSCRIPTIONS_CREATE.value)
def create_tenant_subscription(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: SubscriptionCreate,
):
    """
    Create a subscription for a tenant.

    Creates both Django record and Lago subscription.

    ALL 10 PERSONAS:
    - Security: Permission required
    - SRE: Dual-write ORM + Lago
    - Audit: Full logging
    """
    from django.db import transaction

    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    tier = get_object_or_404(SubscriptionTier, id=data.tier_id, is_active=True)

    # Check for existing active subscription
    existing = Subscription.objects.filter(tenant=tenant, status="active").exists()
    if existing:
        from ninja.errors import HttpError

        raise HttpError(400, "Tenant already has an active subscription")

    with transaction.atomic():
        # 1. Create Django ORM record
        subscription = Subscription.objects.create(
            tenant=tenant,
            tier=tier,
            status="active",
            started_at=datetime.now(),
        )

        # 2. Create Lago subscription
        lago = get_lago_client()
        if lago:
            lago_response = lago.create_subscription(
                tenant=tenant,
                tier=tier,
                external_id=str(subscription.id),
            )
            if lago_response:
                subscription.lago_subscription_id = lago_response.get("external_id")
                subscription.save()

        # 3. Audit log
        AuditLog.log(
            action="subscription.created",
            resource_type="Subscription",
            resource_id=str(subscription.id),
            actor_id=str(request.user_id),
            actor_type=ActorType.ADMIN if request.is_super_admin else ActorType.USER,
            tenant=tenant,
            details={"tier": tier.name, "tier_id": str(tier.id)},
        )

    return subscription


@router.patch("/tenant/{tenant_id}/subscription", response=SubscriptionOut)
@require_auth(roles=["super-admin", "tenant-admin", "billing-admin"], any_role=True)
@require_permission(Permission.SUBSCRIPTIONS_UPDATE.value)
def change_subscription_plan(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: SubscriptionChangePlan,
):
    """
    Change tenant's subscription plan.

    Updates both Django record and Lago subscription.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    new_tier = get_object_or_404(SubscriptionTier, id=data.new_tier_id, is_active=True)

    subscription = (
        Subscription.objects.filter(tenant=tenant, status="active")
        .select_related("tier")
        .first()
    )

    if not subscription:
        from ninja.errors import HttpError

        raise HttpError(404, "No active subscription found")

    old_tier_name = subscription.tier.name
    subscription.tier = new_tier
    subscription.save()

    # Update Lago
    lago = get_lago_client()
    if lago and subscription.lago_subscription_id:
        lago.change_subscription_plan(
            external_id=subscription.lago_subscription_id,
            new_plan_code=new_tier.lago_plan_code,
        )

    # Audit log
    AuditLog.log(
        action="subscription.plan_changed",
        resource_type="Subscription",
        resource_id=str(subscription.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"old_tier": old_tier_name, "new_tier": new_tier.name},
    )

    return subscription


@router.delete("/tenant/{tenant_id}/subscription")
@require_auth(roles=["super-admin", "billing-admin"], any_role=True)
@require_permission(Permission.SUBSCRIPTIONS_CANCEL.value)
def cancel_subscription(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Cancel tenant's subscription."""
    tenant = get_object_or_404(Tenant, id=tenant_id)

    subscription = Subscription.objects.filter(tenant=tenant, status="active").first()

    if not subscription:
        from ninja.errors import HttpError

        raise HttpError(404, "No active subscription found")

    subscription.status = "cancelled"
    subscription.ends_at = datetime.now()
    subscription.save()

    # Terminate in Lago
    lago = get_lago_client()
    if lago and subscription.lago_subscription_id:
        lago.terminate_subscription(subscription.lago_subscription_id)

    # Audit log
    AuditLog.log(
        action="subscription.cancelled",
        resource_type="Subscription",
        resource_id=str(subscription.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"tier": subscription.tier.name},
    )

    return {"success": True, "message": "Subscription cancelled"}


# =============================================================================
# USAGE ENDPOINTS
# =============================================================================


@router.post("/tenant/{tenant_id}/usage")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_MANAGE.value)
def report_usage(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: UsageReportEvent,
):
    """
    Report a usage event for a tenant.

    Records in Django ORM and sends to Lago for billing.

    ALL 10 PERSONAS:
    - DBA: ORM for usage records
    - SRE: Lago for billing
    - Perf: Efficient event processing
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)

    # 1. Save to Django ORM
    usage_record = UsageRecord.objects.create(
        tenant=tenant,
        metric_name=data.event_type,
        quantity=data.count,
        metadata=data.properties or {},
    )

    # 2. Send to Lago
    lago = get_lago_client()
    if lago:
        lago.report_usage(
            tenant=tenant,
            event_type=data.event_type,
            properties={"count": data.count, **(data.properties or {})},
        )

    return {"success": True, "usage_id": str(usage_record.id)}


@router.get("/tenant/{tenant_id}/usage", response=List[UsageRecordOut])
@require_auth(roles=["super-admin", "tenant-admin", "billing-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def get_usage_history(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 100,
):
    """Get usage history for a tenant."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    records = UsageRecord.objects.filter(tenant_id=tenant_id).order_by("-recorded_at")[
        :limit
    ]

    return list(records)


# =============================================================================
# INVOICE ENDPOINTS
# =============================================================================


@router.get("/tenant/{tenant_id}/invoices", response=List[InvoiceOut])
@require_auth(roles=["super-admin", "tenant-admin", "billing-admin"], any_role=True)
@require_permission(Permission.INVOICES_READ.value)
def get_invoices(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Get all invoices for a tenant from Lago."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    lago = get_lago_client()
    if not lago:
        from ninja.errors import HttpError

        raise HttpError(503, "Billing service unavailable")

    invoices = lago.get_invoices(str(tenant_id))
    if invoices is None:
        return []

    return [
        InvoiceOut(
            id=inv.get("lago_id", inv.get("id")),
            status=inv.get("status", "unknown"),
            amount_cents=inv.get("total_amount_cents", 0),
            currency=inv.get("currency", "USD"),
            issuing_date=inv.get("issuing_date"),
            payment_due_date=inv.get("payment_due_date"),
        )
        for inv in invoices.get("invoices", [])
    ]


@router.get("/tenant/{tenant_id}/invoices/{invoice_id}/download")
@require_auth(roles=["super-admin", "tenant-admin", "billing-admin"], any_role=True)
@require_permission(Permission.INVOICES_READ.value)
def download_invoice(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    invoice_id: str,
):
    """Download invoice PDF from Lago."""
    from django.http import HttpResponse

    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    lago = get_lago_client()
    if not lago:
        from ninja.errors import HttpError

        raise HttpError(503, "Billing service unavailable")

    pdf_data = lago.download_invoice_pdf(invoice_id)
    if not pdf_data:
        from ninja.errors import HttpError

        raise HttpError(404, "Invoice not found")

    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{invoice_id}.pdf"'
    return response


# =============================================================================
# BILLING HEALTH
# =============================================================================


@router.get("/health")
def billing_health(request):
    """Check billing service health."""
    lago = get_lago_client()
    if not lago:
        return {"status": "unavailable", "message": "Lago client not configured"}

    is_healthy = lago.health_check()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "lago",
    }
