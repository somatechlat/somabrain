"""
AAAS Models - Tenant and User Models.

Core tenant and user models for multi-tenancy.
"""

from uuid import uuid4

from django.db import models
from django.utils import timezone

from .enums import TenantStatus, TenantTier, UserRole


class Tenant(models.Model):
    """
    Multi-tenant organization.

    Each tenant has isolated data, users, and API keys.
    Integrates with Keycloak for SSO and Lago for billing.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=100, unique=True, db_index=True)

    status = models.CharField(
        max_length=20,
        choices=TenantStatus.choices,
        default=TenantStatus.PENDING,
        db_index=True,
    )
    tier = models.CharField(
        max_length=20,
        choices=TenantTier.choices,
        default=TenantTier.FREE,
    )

    keycloak_realm = models.CharField(max_length=255, null=True, blank=True)
    keycloak_client_id = models.CharField(max_length=255, null=True, blank=True)
    lago_customer_id = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )
    lago_subscription_id = models.CharField(max_length=255, null=True, blank=True)

    config = models.JSONField(default=dict, blank=True)
    quota_overrides = models.JSONField(default=dict, blank=True)

    admin_email = models.EmailField(null=True, blank=True)
    billing_email = models.EmailField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_tenants"
        ordering = ["-created_at"]
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        """Return string representation."""
        return f"{self.name} ({self.slug})"

    def suspend(self, reason: str = None):
        """Suspend the tenant."""
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = timezone.now()
        if reason:
            self.config["suspension_reason"] = reason
        self.save()

    def activate(self):
        """Activate the tenant."""
        self.status = TenantStatus.ACTIVE
        self.suspended_at = None
        self.config.pop("suspension_reason", None)
        self.save()

    @property
    def is_active(self):
        """Check if active."""
        return self.status == TenantStatus.ACTIVE

    @property
    def is_trial(self):
        """Check if trial."""
        return self.status == TenantStatus.TRIAL


class TenantUser(models.Model):
    """
    User within a tenant.

    Linked to Keycloak user ID for SSO authentication.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="users")

    email = models.EmailField(db_index=True)
    keycloak_user_id = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )

    role = models.CharField(
        max_length=20, choices=UserRole.choices, default=UserRole.VIEWER
    )

    display_name = models.CharField(max_length=255, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(
        default=False, help_text="Primary admin for tenant"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_tenant_users"
        ordering = ["-created_at"]
        verbose_name = "Tenant User"
        verbose_name_plural = "Tenant Users"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"], name="uq_tenant_user_email"
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        """Return string representation."""
        return f"{self.email} ({self.tenant.slug})"
