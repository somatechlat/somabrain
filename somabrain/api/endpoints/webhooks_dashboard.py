"""
Webhooks Dashboard API for SomaBrain.

Webhook delivery tracking with real Django cache.
Uses REAL Django cache - NO mocks, NO fallbacks.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Webhook signature verification
- 🏛️ Architect: Clean webhook patterns
- 💾 DBA: Real Django cache for deliveries
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Webhook documentation
- 🧪 QA Engineer: Delivery validation
- 🚨 SRE: Delivery monitoring
- 📊 Performance: Real-time metrics
- 🎨 UX: Clear delivery status
- 🛠️ DevOps: Webhook configuration
"""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
import hashlib

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.saas.models import (
    Tenant,
    AuditLog,
    ActorType,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Webhooks Dashboard"])


# =============================================================================
# WEBHOOK STATUS
# =============================================================================


class DeliveryStatus(str, Enum):
    """Deliverystatus class implementation."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


# =============================================================================
# CACHE KEYS (Real Django Cache)
# =============================================================================


def get_webhook_config_key(tenant_id: str) -> str:
    """Retrieve webhook config key.

    Args:
        tenant_id: The tenant_id.
    """

    return f"webhook:config:{tenant_id}"


def get_deliveries_key(tenant_id: str) -> str:
    """Retrieve deliveries key.

    Args:
        tenant_id: The tenant_id.
    """

    return f"webhook:deliveries:{tenant_id}"


def get_delivery_key(delivery_id: str) -> str:
    """Retrieve delivery key.

    Args:
        delivery_id: The delivery_id.
    """

    return f"webhook:delivery:{delivery_id}"


# =============================================================================
# SCHEMAS
# =============================================================================


class WebhookConfig(Schema):
    """Webhook configuration."""

    id: str
    url: str
    events: List[str]
    is_active: bool
    secret_masked: str
    created_at: str


class WebhookDelivery(Schema):
    """Webhook delivery record."""

    id: str
    event: str
    url: str
    status: str
    status_code: Optional[int]
    attempt: int
    max_attempts: int
    created_at: str
    delivered_at: Optional[str]
    response_time_ms: Optional[int]


class WebhookStats(Schema):
    """Webhook statistics."""

    total_deliveries: int
    successful: int
    failed: int
    pending: int
    success_rate: float
    avg_response_time_ms: float


class WebhookEvent(Schema):
    """Available webhook event."""

    name: str
    description: str
    sample_payload: Dict[str, Any]


# =============================================================================
# WEBHOOK CONFIGURATION
# =============================================================================


@router.get("/{tenant_id}/config", response=List[WebhookConfig])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def list_webhook_configs(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    List webhook configurations.

    🛠️ DevOps: Webhook management

    REAL data from Django cache.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    configs = cache.get(get_webhook_config_key(str(tenant_id)), [])

    return [
        WebhookConfig(
            id=c["id"],
            url=c.get("url", ""),
            events=c.get("events", []),
            is_active=c.get("is_active", True),
            secret_masked=(
                "****" + c.get("secret", "")[-4:] if c.get("secret") else "****"
            ),
            created_at=c.get("created_at", ""),
        )
        for c in configs
    ]


@router.post("/{tenant_id}/config")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def create_webhook_config(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    url: str,
    events: List[str],
):
    """
    Create webhook configuration.

    🔒 Security: Generate secure secret

    REAL cache storage.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    config_id = str(uuid4())
    secret = hashlib.sha256(
        f"{config_id}:{timezone.now().isoformat()}".encode()
    ).hexdigest()[:32]

    config = {
        "id": config_id,
        "url": url,
        "events": events,
        "secret": secret,
        "is_active": True,
        "created_at": timezone.now().isoformat(),
    }

    # Store in REAL cache
    configs = cache.get(get_webhook_config_key(str(tenant_id)), [])
    configs.append(config)
    cache.set(get_webhook_config_key(str(tenant_id)), configs, timeout=86400 * 30)

    # Audit log - REAL
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="webhook.config_created",
        resource_type="WebhookConfig",
        resource_id=config_id,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"url": url, "events": events},
    )

    return {
        "success": True,
        "config_id": config_id,
        "secret": secret,  # Return secret ONLY on creation
    }


@router.delete("/{tenant_id}/config/{config_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def delete_webhook_config(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    config_id: str,
):
    """Delete webhook configuration."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    configs = cache.get(get_webhook_config_key(str(tenant_id)), [])
    configs = [c for c in configs if c["id"] != config_id]
    cache.set(get_webhook_config_key(str(tenant_id)), configs, timeout=86400 * 30)

    return {"deleted": True}


# =============================================================================
# WEBHOOK DELIVERIES
# =============================================================================


@router.get("/{tenant_id}/deliveries", response=List[WebhookDelivery])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def list_deliveries(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    status: Optional[str] = None,
    limit: int = 50,
):
    """
    List webhook deliveries.

    🚨 SRE: Delivery monitoring

    REAL delivery data from cache.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    delivery_ids = cache.get(get_deliveries_key(str(tenant_id)), [])
    deliveries = []

    for did in delivery_ids[:limit]:
        delivery = cache.get(get_delivery_key(did))
        if delivery:
            if status and delivery.get("status") != status:
                continue
            deliveries.append(
                WebhookDelivery(
                    id=delivery["id"],
                    event=delivery.get("event", ""),
                    url=delivery.get("url", ""),
                    status=delivery.get("status", "pending"),
                    status_code=delivery.get("status_code"),
                    attempt=delivery.get("attempt", 1),
                    max_attempts=delivery.get("max_attempts", 3),
                    created_at=delivery.get("created_at", ""),
                    delivered_at=delivery.get("delivered_at"),
                    response_time_ms=delivery.get("response_time_ms"),
                )
            )

    return deliveries


@router.get("/{tenant_id}/deliveries/{delivery_id}", response=WebhookDelivery)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_delivery(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    delivery_id: str,
):
    """Get delivery details."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    delivery = cache.get(get_delivery_key(delivery_id))
    if not delivery:
        raise HttpError(404, "Delivery not found")

    return WebhookDelivery(
        id=delivery["id"],
        event=delivery.get("event", ""),
        url=delivery.get("url", ""),
        status=delivery.get("status", "pending"),
        status_code=delivery.get("status_code"),
        attempt=delivery.get("attempt", 1),
        max_attempts=delivery.get("max_attempts", 3),
        created_at=delivery.get("created_at", ""),
        delivered_at=delivery.get("delivered_at"),
        response_time_ms=delivery.get("response_time_ms"),
    )


@router.post("/{tenant_id}/deliveries/{delivery_id}/retry")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def retry_delivery(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    delivery_id: str,
):
    """
    Retry a failed delivery.

    🛠️ DevOps: Manual retry

    REAL cache update.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    delivery = cache.get(get_delivery_key(delivery_id))
    if not delivery:
        raise HttpError(404, "Delivery not found")

    # Update status for retry
    delivery["status"] = "retrying"
    delivery["attempt"] = delivery.get("attempt", 1) + 1
    cache.set(get_delivery_key(delivery_id), delivery, timeout=86400 * 7)

    return {"success": True, "new_attempt": delivery["attempt"]}


# =============================================================================
# WEBHOOK STATISTICS
# =============================================================================


@router.get("/{tenant_id}/stats", response=WebhookStats)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_webhook_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get webhook statistics.

    📊 Performance: REAL aggregated stats
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    delivery_ids = cache.get(get_deliveries_key(str(tenant_id)), [])

    total = 0
    successful = 0
    failed = 0
    pending = 0
    total_response_time = 0

    for did in delivery_ids[:500]:  # Analyze up to 500
        delivery = cache.get(get_delivery_key(did))
        if delivery:
            total += 1
            status = delivery.get("status", "pending")
            if status == "delivered":
                successful += 1
                if delivery.get("response_time_ms"):
                    total_response_time += delivery["response_time_ms"]
            elif status == "failed":
                failed += 1
            else:
                pending += 1

    success_rate = (successful / total * 100) if total > 0 else 0
    avg_response = (total_response_time / successful) if successful > 0 else 0

    return WebhookStats(
        total_deliveries=total,
        successful=successful,
        failed=failed,
        pending=pending,
        success_rate=round(success_rate, 2),
        avg_response_time_ms=round(avg_response, 2),
    )


# =============================================================================
# WEBHOOK EVENTS
# =============================================================================


@router.get("/events", response=List[WebhookEvent])
def list_available_events():
    """
    List available webhook events.

    📚 Docs: Event documentation
    """
    events = [
        WebhookEvent(
            name="tenant.created",
            description="Fired when a new tenant is created",
            sample_payload={"tenant_id": "uuid", "name": "Tenant Name"},
        ),
        WebhookEvent(
            name="user.created",
            description="Fired when a user is added to a tenant",
            sample_payload={"user_id": "uuid", "email": "user@example.com"},
        ),
        WebhookEvent(
            name="subscription.changed",
            description="Fired when subscription tier changes",
            sample_payload={"tenant_id": "uuid", "old_tier": "free", "new_tier": "pro"},
        ),
        WebhookEvent(
            name="memory.created",
            description="Fired when a memory is created",
            sample_payload={"memory_id": "uuid", "agent_id": "uuid"},
        ),
        WebhookEvent(
            name="quota.exceeded",
            description="Fired when a quota limit is reached",
            sample_payload={"tenant_id": "uuid", "resource": "users", "limit": 10},
        ),
    ]
    return events


@router.post("/{tenant_id}/test")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def test_webhook(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    config_id: str,
):
    """
    Test webhook configuration.

    🧪 QA: Webhook testing

    Creates a test delivery record.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    configs = cache.get(get_webhook_config_key(str(tenant_id)), [])
    config = next((c for c in configs if c["id"] == config_id), None)

    if not config:
        raise HttpError(404, "Config not found")

    # Create test delivery
    delivery_id = str(uuid4())
    delivery = {
        "id": delivery_id,
        "event": "test.ping",
        "url": config["url"],
        "status": "pending",
        "attempt": 1,
        "max_attempts": 1,
        "created_at": timezone.now().isoformat(),
        "is_test": True,
    }

    cache.set(get_delivery_key(delivery_id), delivery, timeout=86400)

    # Add to deliveries list
    delivery_ids = cache.get(get_deliveries_key(str(tenant_id)), [])
    delivery_ids.insert(0, delivery_id)
    cache.set(get_deliveries_key(str(tenant_id)), delivery_ids[:100], timeout=86400 * 7)

    return {"success": True, "delivery_id": delivery_id}
