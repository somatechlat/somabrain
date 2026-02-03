"""
AAAS Models - Webhooks and Notifications.

Webhook configuration and delivery tracking.
"""

from uuid import uuid4

from django.db import models


class Webhook(models.Model):
    """Webhook configuration for tenant event subscriptions."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="webhooks"
    )

    url = models.URLField(max_length=500)
    name = models.CharField(max_length=200, blank=True, null=True)
    event_types = models.JSONField(default=list)

    secret = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)
    failure_count = models.PositiveIntegerField(default=0)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration."""

        ordering = ["-created_at"]
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"

    def __str__(self):
        """Return string representation."""
        return f"{self.tenant.slug}: {self.url[:50]}"


class WebhookDelivery(models.Model):
    """Webhook delivery log entry."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    webhook = models.ForeignKey(
        Webhook, on_delete=models.CASCADE, related_name="deliveries"
    )

    event_type = models.CharField(max_length=100)
    payload = models.JSONField()

    status_code = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)

    attempt_number = models.PositiveIntegerField(default=1)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    delivered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta configuration."""

        ordering = ["-delivered_at"]
        indexes = [
            models.Index(fields=["webhook", "delivered_at"]),
            models.Index(fields=["success", "delivered_at"]),
        ]
        verbose_name = "Webhook Delivery"
        verbose_name_plural = "Webhook Deliveries"

    def __str__(self):
        """Return string representation."""
        return f"{self.webhook.id}:{self.event_type} - {'OK' if self.success else 'FAIL'}"


class Notification(models.Model):
    """In-app notification for tenant users."""

    class NotificationType(models.TextChoices):
        """Notification type choices."""

        INFO = "info", "Information"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        SUCCESS = "success", "Success"
        BILLING = "billing", "Billing"
        SECURITY = "security", "Security"
        SYSTEM = "system", "System"

    class NotificationPriority(models.TextChoices):
        """Notification priority choices."""

        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="notifications"
    )
    user_id = models.UUIDField(null=True, blank=True)

    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL,
    )

    action_url = models.URLField(max_length=500, blank=True, null=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta configuration."""

        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "user_id", "is_read"]),
            models.Index(fields=["tenant", "created_at"]),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        """Return string representation."""
        return f"{self.tenant.slug}: {self.title[:30]}"
