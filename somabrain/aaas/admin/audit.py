"""
AAAS Admin - Audit, Webhooks, Notifications.

Admin classes for AuditLog, Webhook, WebhookDelivery, Notification.
"""

from django.contrib import admin
from django.utils.html import format_html

from ..models import AuditLog, Notification, Webhook, WebhookDelivery
from .filters import RecentlyCreatedFilter, WebhookDeliveryInline


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for audit logs (read-only, immutable)."""

    list_display = [
        "timestamp",
        "action",
        "actor_display",
        "resource_type",
        "resource_id",
        "tenant",
        "ip_address",
    ]
    list_filter = ["action", "resource_type", "actor_type", RecentlyCreatedFilter]
    search_fields = ["action", "actor_id", "resource_id", "tenant__name", "ip_address"]
    readonly_fields = [
        "id",
        "tenant",
        "actor_id",
        "actor_type",
        "actor_email",
        "action",
        "resource_type",
        "resource_id",
        "details",
        "ip_address",
        "user_agent",
        "request_id",
        "timestamp",
    ]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"

    fieldsets = (
        ("Event", {"fields": ("action", "resource_type", "resource_id", "timestamp")}),
        ("Actor", {"fields": ("actor_id", "actor_type", "actor_email")}),
        ("Context", {"fields": ("tenant", "ip_address", "user_agent", "request_id")}),
        ("Details", {"fields": ("details",), "classes": ("collapse",)}),
    )

    def actor_display(self, obj):
        """Display actor identifier."""
        return obj.actor_email or obj.actor_id[:8] + "..."

    actor_display.short_description = "Actor"

    def has_add_permission(self, request):
        """Prevent adding audit logs via admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent changing audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting audit logs."""
        return False


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    """Admin for webhooks."""

    list_display = [
        "name",
        "tenant",
        "url_truncated",
        "is_active",
        "failure_count",
        "last_triggered_at",
    ]
    list_filter = ["is_active", RecentlyCreatedFilter]
    search_fields = ["name", "url", "tenant__name"]
    readonly_fields = ["id", "secret", "created_at", "last_triggered_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant"]

    inlines = [WebhookDeliveryInline]

    fieldsets = (
        (None, {"fields": ("id", "tenant", "name", "url")}),
        ("Configuration", {"fields": ("event_types", "is_active")}),
        ("Status", {"fields": ("failure_count", "last_triggered_at", "created_at")}),
        ("Security", {"fields": ("secret",), "classes": ("collapse",)}),
    )

    def url_truncated(self, obj):
        """Display truncated URL."""
        return format_html('<code>{}</code>', obj.url[:40] + "..." if len(obj.url) > 40 else obj.url)

    url_truncated.short_description = "URL"


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    """Admin for webhook deliveries (read-only)."""

    list_display = [
        "webhook",
        "event_type",
        "status_code",
        "success_badge",
        "response_time_ms",
        "delivered_at",
    ]
    list_filter = ["success", "event_type", RecentlyCreatedFilter]
    search_fields = ["webhook__url", "event_type"]
    readonly_fields = [
        "id",
        "webhook",
        "event_type",
        "payload",
        "status_code",
        "success",
        "error_message",
        "response_time_ms",
        "attempt_number",
        "delivered_at",
    ]
    ordering = ["-delivered_at"]
    date_hierarchy = "delivered_at"

    def success_badge(self, obj):
        """Display success status badge."""
        color = "green" if obj.success else "red"
        text = "OK" if obj.success else "FAIL"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            text,
        )

    success_badge.short_description = "Status"

    def has_add_permission(self, request):
        """Prevent adding delivery logs via admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent changing delivery logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting delivery logs."""
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for notifications."""

    list_display = [
        "title_truncated",
        "tenant",
        "type",
        "priority",
        "is_read",
        "created_at",
    ]
    list_filter = ["type", "priority", "is_read", RecentlyCreatedFilter]
    search_fields = ["title", "message", "tenant__name"]
    readonly_fields = ["id", "created_at", "read_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant"]

    def title_truncated(self, obj):
        """Display truncated title."""
        return obj.title[:40] + "..." if len(obj.title) > 40 else obj.title

    title_truncated.short_description = "Title"
