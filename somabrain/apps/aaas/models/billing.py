"""
AAAS Models - Billing and Subscriptions.

Subscription tiers, subscriptions, and usage tracking.
"""

from uuid import uuid4

from django.db import models

from .enums import SubscriptionStatus


class SubscriptionTier(models.Model):
    """AAAS subscription tier definition (Free, Starter, Pro, Enterprise)."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    slug = models.CharField(max_length=50, unique=True, db_index=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    api_calls_limit = models.IntegerField(default=1000, help_text="API calls per month")
    memory_ops_limit = models.IntegerField(
        default=500, help_text="Memory operations per month"
    )
    storage_limit_mb = models.IntegerField(default=100, help_text="Storage in MB")

    rate_limit_rps = models.IntegerField(default=10, help_text="Requests per second")
    rate_limit_burst = models.IntegerField(default=20, help_text="Burst limit")

    features = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_subscription_tiers"
        ordering = ["display_order", "price_monthly"]
        verbose_name = "Subscription Tier"
        verbose_name_plural = "Subscription Tiers"

    def __str__(self):
        """Return string representation."""
        return f"{self.name} (${self.price_monthly}/mo)"


class Subscription(models.Model):
    """Tenant subscription record."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.OneToOneField(
        "Tenant", on_delete=models.CASCADE, related_name="subscription"
    )
    tier = models.ForeignKey(
        SubscriptionTier, on_delete=models.PROTECT, related_name="subscriptions"
    )

    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
    )

    lago_subscription_id = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )

    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_subscriptions"
        ordering = ["-created_at"]
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        """Return string representation."""
        return f"{self.tenant.name} - {self.tier.name}"


class TenantSubscription(models.Model):
    """Tenant's active subscription with Lago integration."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="tenant_subscriptions"
    )
    tier = models.ForeignKey(
        "SubscriptionTier", on_delete=models.PROTECT, related_name="tier_subscriptions"
    )

    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    lago_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    lago_customer_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration."""

        ordering = ["-created_at"]
        verbose_name = "Tenant Subscription"
        verbose_name_plural = "Tenant Subscriptions"

    def __str__(self):
        """Return string representation."""
        return f"{self.tenant.name} - {self.tier.name} ({self.status})"


class UsageRecord(models.Model):
    """Usage event for billing metering."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="usage_records"
    )

    metric_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)

    metadata = models.JSONField(default=dict)

    lago_event_id = models.CharField(max_length=255, blank=True, null=True)
    synced_to_lago = models.BooleanField(default=False)

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta configuration."""

        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["tenant", "recorded_at"]),
            models.Index(fields=["metric_name", "recorded_at"]),
        ]
        verbose_name = "Usage Record"
        verbose_name_plural = "Usage Records"

    def __str__(self):
        """Return string representation."""
        return f"{self.tenant.slug}:{self.metric_name}={self.quantity}"
