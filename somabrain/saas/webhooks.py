"""
Lago Webhook Receiver for SomaBrain SaaS.

Handles billing events from Lago:
- invoice.created
- invoice.paid
- subscription.started
- subscription.terminated
- customer.payment_overdue

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: Clean event handling
- Security: Webhook signature verification
- DevOps: Structured logging
- QA: Testable handlers
- Docs: Event documentation
- DBA: Atomic updates
- SRE: Error tracking
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Callable

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from somabrain.saas.models import (
    AuditLog,
    SubscriptionStatus,
    Tenant,
    TenantStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# WEBHOOK SIGNATURE VERIFICATION
# =============================================================================


def verify_lago_signature(request: HttpRequest) -> bool:
    """
    Verify Lago webhook signature.

    Security: Uses HMAC-SHA256 to verify webhook authenticity.
    """
    webhook_secret = getattr(settings, "LAGO_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.warning("LAGO_WEBHOOK_SECRET not configured - skipping verification")
        return True  # Allow in development

    signature = request.headers.get("X-Lago-Signature", "")
    if not signature:
        logger.warning("Missing X-Lago-Signature header")
        return False

    # Compute expected signature
    body = request.body
    expected = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(signature, expected)


# =============================================================================
# EVENT HANDLERS
# =============================================================================


def handle_invoice_created(data: dict) -> None:
    """Handle invoice.created event."""
    invoice = data.get("invoice", {})
    customer_id = invoice.get("customer", {}).get("external_id")
    amount = invoice.get("total_amount_cents", 0) / 100

    logger.info(f"Invoice created for customer {customer_id}: ${amount}")

    if customer_id:
        try:
            tenant = Tenant.objects.get(id=customer_id)
            AuditLog.log(
                action="invoice.created",
                resource_type="invoice",
                resource_id=invoice.get("lago_id", "unknown"),
                actor_id="lago_webhook",
                actor_type="system",
                tenant=tenant,
                details={"amount": amount, "status": invoice.get("status")},
            )
        except Tenant.DoesNotExist:
            logger.warning(f"Tenant not found for invoice: {customer_id}")


def handle_invoice_paid(data: dict) -> None:
    """Handle invoice.paid event."""
    invoice = data.get("invoice", {})
    customer_id = invoice.get("customer", {}).get("external_id")

    logger.info(f"Invoice paid for customer {customer_id}")

    if customer_id:
        try:
            tenant = Tenant.objects.get(id=customer_id)

            # Ensure subscription is active
            if hasattr(tenant, "subscription"):
                sub = tenant.subscription
                if sub.status == SubscriptionStatus.PAST_DUE:
                    sub.status = SubscriptionStatus.ACTIVE
                    sub.save()

            AuditLog.log(
                action="invoice.paid",
                resource_type="invoice",
                resource_id=invoice.get("lago_id", "unknown"),
                actor_id="lago_webhook",
                actor_type="system",
                tenant=tenant,
            )
        except Tenant.DoesNotExist:
            logger.warning(f"Tenant not found: {customer_id}")


def handle_subscription_started(data: dict) -> None:
    """Handle subscription.started event."""
    subscription = data.get("subscription", {})
    customer_id = subscription.get("external_customer_id")
    plan_code = subscription.get("plan_code")

    logger.info(f"Subscription started for {customer_id}: {plan_code}")

    if customer_id:
        try:
            tenant = Tenant.objects.get(id=customer_id)

            with transaction.atomic():
                if hasattr(tenant, "subscription"):
                    sub = tenant.subscription
                    sub.status = SubscriptionStatus.ACTIVE
                    sub.lago_subscription_id = subscription.get("lago_id")
                    sub.current_period_start = datetime.now(timezone.utc)
                    sub.save()

                # Ensure tenant is active
                if tenant.status == TenantStatus.PENDING:
                    tenant.status = TenantStatus.ACTIVE
                    tenant.save()

            AuditLog.log(
                action="subscription.started",
                resource_type="subscription",
                resource_id=subscription.get("lago_id", "unknown"),
                actor_id="lago_webhook",
                actor_type="system",
                tenant=tenant,
                details={"plan": plan_code},
            )
        except Tenant.DoesNotExist:
            logger.warning(f"Tenant not found: {customer_id}")


def handle_subscription_terminated(data: dict) -> None:
    """Handle subscription.terminated event."""
    subscription = data.get("subscription", {})
    customer_id = subscription.get("external_customer_id")

    logger.info(f"Subscription terminated for {customer_id}")

    if customer_id:
        try:
            tenant = Tenant.objects.get(id=customer_id)

            with transaction.atomic():
                if hasattr(tenant, "subscription"):
                    sub = tenant.subscription
                    sub.status = SubscriptionStatus.CANCELLED
                    sub.cancelled_at = datetime.now(timezone.utc)
                    sub.save()

            AuditLog.log(
                action="subscription.terminated",
                resource_type="subscription",
                resource_id=subscription.get("lago_id", "unknown"),
                actor_id="lago_webhook",
                actor_type="system",
                tenant=tenant,
            )
        except Tenant.DoesNotExist:
            logger.warning(f"Tenant not found: {customer_id}")


def handle_payment_overdue(data: dict) -> None:
    """Handle customer.payment_overdue event."""
    customer = data.get("customer", {})
    customer_id = customer.get("external_id")

    logger.warning(f"Payment overdue for customer {customer_id}")

    if customer_id:
        try:
            tenant = Tenant.objects.get(id=customer_id)

            with transaction.atomic():
                if hasattr(tenant, "subscription"):
                    sub = tenant.subscription
                    sub.status = SubscriptionStatus.PAST_DUE
                    sub.save()

            AuditLog.log(
                action="payment.overdue",
                resource_type="customer",
                resource_id=customer_id,
                actor_id="lago_webhook",
                actor_type="system",
                tenant=tenant,
            )
        except Tenant.DoesNotExist:
            logger.warning(f"Tenant not found: {customer_id}")


# =============================================================================
# EVENT ROUTER
# =============================================================================

EVENT_HANDLERS: dict[str, Callable[[dict], None]] = {
    "invoice.created": handle_invoice_created,
    "invoice.paid": handle_invoice_paid,
    "subscription.started": handle_subscription_started,
    "subscription.terminated": handle_subscription_terminated,
    "customer.payment_overdue": handle_payment_overdue,
}


# =============================================================================
# WEBHOOK VIEW
# =============================================================================


@csrf_exempt
@require_POST
def lago_webhook(request: HttpRequest) -> JsonResponse:
    """
    Lago webhook endpoint.

    POST /webhooks/lago/

    Receives and processes billing events from Lago.
    """
    # Verify signature
    if not verify_lago_signature(request):
        logger.error("Invalid Lago webhook signature")
        return JsonResponse({"error": "Invalid signature"}, status=401)

    # Parse body
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Extract event type
    event_type = payload.get("webhook_type")
    if not event_type:
        logger.error("Missing webhook_type in payload")
        return JsonResponse({"error": "Missing webhook_type"}, status=400)

    logger.info(f"Received Lago webhook: {event_type}")

    # Route to handler
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        try:
            handler(payload)
            return JsonResponse({"status": "processed", "event": event_type})
        except Exception as e:
            logger.exception(f"Error processing {event_type}: {e}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        logger.info(f"Unhandled event type: {event_type}")
        return JsonResponse({"status": "ignored", "event": event_type})
