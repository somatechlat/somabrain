"""
AAAS Admin - Billing and API Keys.

Admin classes for Subscription, APIKey, UsageRecord.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from ..models import APIKey, Subscription, UsageRecord
from .filters import ActiveStatusFilter, RecentlyCreatedFilter


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin for subscriptions."""

    list_display = [
        "tenant",
        "tier",
        "status_badge",
        "current_period_end",
        "created_at",
    ]
    list_filter = ["status", "tier", RecentlyCreatedFilter]
    search_fields = ["tenant__name", "lago_subscription_id"]
    readonly_fields = ["id", "created_at", "updated_at", "cancelled_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant", "tier"]

    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            "active": "green",
            "trialing": "blue",
            "past_due": "orange",
            "cancelled": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.status,
        )

    status_badge.short_description = "Status"


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin for API keys."""

    list_display = [
        "name",
        "tenant_link",
        "key_prefix_display",
        "is_active",
        "is_test",
        "last_used_at",
        "usage_count",
    ]
    list_filter = ["is_active", "is_test", ActiveStatusFilter, RecentlyCreatedFilter]
    search_fields = ["name", "tenant__name", "key_prefix"]
    readonly_fields = [
        "id",
        "key_prefix",
        "key_hash",
        "created_at",
        "last_used_at",
        "usage_count",
        "revoked_at",
    ]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant"]

    def tenant_link(self, obj):
        """Link to tenant."""
        from django.urls import reverse

        url = reverse("admin:aaas_tenant_change", args=[obj.tenant_id])
        return format_html('<a href="{}">{}</a>', url, obj.tenant.name)

    tenant_link.short_description = "Tenant"

    def key_prefix_display(self, obj):
        """Display key prefix with color."""
        color = "green" if obj.is_active else "red"
        return format_html(
            '<code style="color: {}; background: #f0f0f0; padding: 2px 6px; '
            'border-radius: 3px;">{}</code>',
            color,
            f"{obj.key_prefix}...",
        )

    key_prefix_display.short_description = "Key"

    actions = ["revoke_keys", "activate_keys"]

    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request, queryset):
        """Revoke selected API keys."""
        queryset.update(is_active=False, revoked_at=timezone.now())
        self.message_user(request, f"Revoked {queryset.count()} API keys.")

    @admin.action(description="Reactivate selected API keys")
    def activate_keys(self, request, queryset):
        """Reactivate selected API keys."""
        queryset.update(is_active=True, revoked_at=None)


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    """Admin for usage records (read-only)."""

    list_display = [
        "tenant",
        "metric_name",
        "quantity",
        "recorded_at",
        "synced_to_lago",
    ]
    list_filter = ["metric_name", "synced_to_lago", RecentlyCreatedFilter]
    search_fields = ["tenant__name", "metric_name"]
    readonly_fields = ["id", "recorded_at", "synced_to_lago", "lago_event_id"]
    ordering = ["-recorded_at"]
    date_hierarchy = "recorded_at"
    autocomplete_fields = ["tenant"]

    def has_change_permission(self, request, obj=None):
        """Prevent changes to usage records."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of usage records."""
        return False
