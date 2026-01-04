"""Sleep Models

Django models for sleep state management.
"""

from django.db import models


class TenantSleepState(models.Model):
    """Sleep state for a tenant."""

    tenant_id = models.CharField(max_length=255, primary_key=True)
    current_state = models.CharField(max_length=50, default="active")
    target_state = models.CharField(max_length=50, default="active")
    last_transition = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    # TTL auto-wake support
    ttl = models.DateTimeField(null=True, blank=True)
    scheduled_wake = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Meta class implementation."""

        db_table = "tenant_sleep_states"
        app_label = "somabrain"

    def __str__(self):
        """Return string representation."""

        return f"{self.tenant_id}: {self.current_state}"
