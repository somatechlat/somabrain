"""
AAAS Admin - Filters and Inlines.

Reusable filters and inline admin classes.
"""

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone

from ..models import APIKey, Subscription, TenantUser, Webhook, WebhookDelivery


class ActiveStatusFilter(SimpleListFilter):
    """Filter by active status."""

    title = "Active Status"
    parameter_name = "is_active"

    def lookups(self, request, model_admin):
        """Return filter options."""
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )

    def queryset(self, request, queryset):
        """Filter queryset by active status."""
        if self.value() == "yes":
            return queryset.filter(is_active=True)
        if self.value() == "no":
            return queryset.filter(is_active=False)


class RecentlyCreatedFilter(SimpleListFilter):
    """Filter by creation date."""

    title = "Created"
    parameter_name = "created_recently"

    def lookups(self, request, model_admin):
        """Return filter options."""
        return (
            ("today", "Today"),
            ("week", "This Week"),
            ("month", "This Month"),
        )

    def queryset(self, request, queryset):
        """Filter queryset by creation date."""
        now = timezone.now()
        if self.value() == "today":
            return queryset.filter(created_at__date=now.date())
        if self.value() == "week":
            return queryset.filter(created_at__gte=now - timezone.timedelta(days=7))
        if self.value() == "month":
            return queryset.filter(created_at__gte=now - timezone.timedelta(days=30))


class TenantUserInline(admin.TabularInline):
    """Inline for tenant users."""

    model = TenantUser
    extra = 0
    readonly_fields = ["id", "last_login_at"]
    fields = ["email", "display_name", "role", "is_active", "is_primary"]


class APIKeyInline(admin.TabularInline):
    """Inline for API keys."""

    model = APIKey
    extra = 0
    readonly_fields = ["key_prefix", "created_at", "last_used_at", "usage_count"]
    fields = ["name", "key_prefix", "is_active", "is_test", "last_used_at"]


class SubscriptionInline(admin.TabularInline):
    """Inline for subscriptions."""

    model = Subscription
    extra = 0
    readonly_fields = ["created_at", "lago_subscription_id"]
    fields = ["tier", "status", "current_period_start", "current_period_end"]


class WebhookInline(admin.TabularInline):
    """Inline for webhooks."""

    model = Webhook
    extra = 0
    readonly_fields = ["created_at", "last_triggered_at"]
    fields = ["name", "url", "is_active", "failure_count"]


class WebhookDeliveryInline(admin.TabularInline):
    """Inline for webhook deliveries."""

    model = WebhookDelivery
    extra = 0
    readonly_fields = ["event_type", "status_code", "success", "delivered_at"]
    fields = ["event_type", "status_code", "success", "delivered_at"]
    max_num = 10
    can_delete = False
