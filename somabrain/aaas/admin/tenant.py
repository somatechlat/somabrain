"""
AAAS Admin - Tenant and User Admin.

Admin classes for Tenant, TenantUser, and SubscriptionTier.
"""

import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from ..models import Tenant, TenantStatus, TenantUser, SubscriptionTier
from .filters import (
    APIKeyInline,
    RecentlyCreatedFilter,
    SubscriptionInline,
    TenantUserInline,
    WebhookInline,
)


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    """Admin for subscription tiers."""

    list_display = [
        "name",
        "slug",
        "price_monthly",
        "api_calls_limit",
        "memory_ops_limit",
        "is_active",
        "is_default",
        "tenant_count",
    ]
    list_filter = ["is_active", "is_default"]
    search_fields = ["name", "slug"]
    ordering = ["display_order", "price_monthly"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def tenant_count(self, obj):
        """Count tenants on this tier."""
        return Tenant.objects.filter(tier=obj.slug).count()

    tenant_count.short_description = "Tenants"

    actions = ["make_active", "make_inactive"]

    @admin.action(description="Mark selected tiers as active")
    def make_active(self, request, queryset):
        """Activate selected tiers."""
        queryset.update(is_active=True)

    @admin.action(description="Mark selected tiers as inactive")
    def make_inactive(self, request, queryset):
        """Deactivate selected tiers."""
        queryset.update(is_active=False)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin for tenants with full capabilities."""

    list_display = [
        "name",
        "slug",
        "status_badge",
        "tier",
        "admin_email",
        "users_count",
        "api_keys_count",
        "created_at",
    ]
    list_filter = ["status", "tier", RecentlyCreatedFilter]
    search_fields = ["name", "slug", "admin_email", "billing_email"]
    readonly_fields = ["id", "created_at", "updated_at", "suspended_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    inlines = [TenantUserInline, APIKeyInline, SubscriptionInline, WebhookInline]

    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "status", "tier")}),
        ("Contact Information", {"fields": ("admin_email", "billing_email")}),
        (
            "External Integrations",
            {
                "fields": (
                    "keycloak_realm",
                    "keycloak_client_id",
                    "lago_customer_id",
                    "lago_subscription_id",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Configuration",
            {"fields": ("config", "quota_overrides"), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "suspended_at",
                    "trial_ends_at",
                    "created_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            TenantStatus.ACTIVE: "green",
            TenantStatus.TRIAL: "blue",
            TenantStatus.SUSPENDED: "orange",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.status,
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def users_count(self, obj):
        """Count users in tenant."""
        return obj.users.count()

    users_count.short_description = "Users"

    def api_keys_count(self, obj):
        """Count API keys in tenant."""
        return obj.api_keys.count()

    api_keys_count.short_description = "API Keys"

    def get_queryset(self, request):
        """Optimize with prefetch."""
        return super().get_queryset(request).prefetch_related("users", "api_keys")

    actions = ["suspend_tenants", "activate_tenants", "export_as_csv"]

    @admin.action(description="Suspend selected tenants")
    def suspend_tenants(self, request, queryset):
        """Suspend selected tenants."""
        queryset.update(status=TenantStatus.SUSPENDED, suspended_at=timezone.now())
        self.message_user(request, f"Suspended {queryset.count()} tenants.")

    @admin.action(description="Activate selected tenants")
    def activate_tenants(self, request, queryset):
        """Activate selected tenants."""
        queryset.update(status=TenantStatus.ACTIVE, suspended_at=None)
        self.message_user(request, f"Activated {queryset.count()} tenants.")

    @admin.action(description="Export selected as CSV")
    def export_as_csv(self, request, queryset):
        """Export tenants to CSV."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=tenants.csv"
        writer = csv.writer(response)
        writer.writerow(
            ["ID", "Name", "Slug", "Status", "Tier", "Admin Email", "Created"]
        )
        for t in queryset:
            writer.writerow(
                [t.id, t.name, t.slug, t.status, t.tier, t.admin_email, t.created_at.isoformat()]
            )
        return response


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    """Admin for tenant users."""

    list_display = [
        "email",
        "tenant_link",
        "role",
        "is_active",
        "is_primary",
        "last_login_at",
    ]
    list_filter = ["role", "is_active", "is_primary", RecentlyCreatedFilter]
    search_fields = ["email", "display_name", "tenant__name"]
    readonly_fields = ["id", "created_at", "updated_at", "last_login_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant"]

    def tenant_link(self, obj):
        """Link to tenant."""
        from django.urls import reverse

        url = reverse("admin:aaas_tenant_change", args=[obj.tenant_id])
        return format_html('<a href="{}">{}</a>', url, obj.tenant.name)

    tenant_link.short_description = "Tenant"

    actions = ["deactivate_users", "activate_users"]

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        queryset.update(is_active=False)

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        """Activate selected users."""
        queryset.update(is_active=True)
