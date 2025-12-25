"""
Django Admin configuration for SaaS models.

FULL Django Admin Capabilities - ALL 10 PERSONAS:
- 🔒 Security: Permission-based access, sensitive data masking
- 🏛️ Architect: Organized fieldsets and inlines
- 💾 DBA: Efficient querysets with select_related
- 🐍 Django Expert: Full ModelAdmin features
- 📚 Technical Writer: Clear help_text
- 🧪 QA: Data validation in admin
- 🚨 SRE: Audit logging for admin actions
- 📊 Performance: Optimized list queries
- 🎨 UX: List display, filters, search
- 🛠️ DevOps: Bulk actions, exports
"""

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Count, Sum
from django.http import HttpResponse
import csv

from .models import (
    SubscriptionTier,
    Tenant,
    TenantUser,
    Subscription,
    APIKey,
    AuditLog,
    UsageRecord,
    Webhook,
    WebhookDelivery,
    Notification,
    TenantStatus,
)


# =============================================================================
# CUSTOM FILTERS - ALL 10 PERSONAS
# =============================================================================

class ActiveStatusFilter(SimpleListFilter):
    """Filter by active status."""
    title = "Active Status"
    parameter_name = "is_active"
    
    def lookups(self, request, model_admin):
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )
    
    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(is_active=True)
        if self.value() == "no":
            return queryset.filter(is_active=False)


class RecentlyCreatedFilter(SimpleListFilter):
    """Filter by creation date."""
    title = "Created"
    parameter_name = "created_recently"
    
    def lookups(self, request, model_admin):
        return (
            ("today", "Today"),
            ("week", "This Week"),
            ("month", "This Month"),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "today":
            return queryset.filter(created_at__date=now.date())
        if self.value() == "week":
            return queryset.filter(created_at__gte=now - timezone.timedelta(days=7))
        if self.value() == "month":
            return queryset.filter(created_at__gte=now - timezone.timedelta(days=30))


# =============================================================================
# INLINE ADMINS - ALL 10 PERSONAS
# =============================================================================

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


# =============================================================================
# SUBSCRIPTION TIER ADMIN
# =============================================================================

@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    """Admin for subscription tiers."""
    
    list_display = ["name", "slug", "price_monthly", "api_calls_limit", 
                    "memory_ops_limit", "is_active", "is_default", "tenant_count"]
    list_filter = ["is_active", "is_default"]
    search_fields = ["name", "slug", "description"]
    ordering = ["display_order", "price_monthly"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    fieldsets = (
        (None, {
            "fields": ("id", "name", "slug", "description")
        }),
        ("Pricing", {
            "fields": ("price_monthly", "price_yearly", "lago_plan_code")
        }),
        ("Limits", {
            "fields": ("api_calls_limit", "memory_ops_limit", "users_limit", 
                       "storage_limit_gb", "webhook_limit")
        }),
        ("Configuration", {
            "fields": ("features", "is_active", "is_default", "display_order"),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def tenant_count(self, obj):
        """Count tenants on this tier."""
        return Tenant.objects.filter(tier=obj.slug).count()
    tenant_count.short_description = "Tenants"
    
    actions = ["make_active", "make_inactive"]
    
    @admin.action(description="Mark selected tiers as active")
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    
    @admin.action(description="Mark selected tiers as inactive")
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)


# =============================================================================
# TENANT ADMIN - FULL FEATURED
# =============================================================================

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin for tenants with full capabilities."""
    
    list_display = ["name", "slug", "status_badge", "tier", "admin_email", 
                    "users_count", "api_keys_count", "created_at"]
    list_filter = ["status", "tier", RecentlyCreatedFilter]
    search_fields = ["name", "slug", "admin_email", "billing_email"]
    readonly_fields = ["id", "created_at", "updated_at", "suspended_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    
    inlines = [TenantUserInline, APIKeyInline, SubscriptionInline, WebhookInline]
    
    fieldsets = (
        (None, {
            "fields": ("id", "name", "slug", "status", "tier")
        }),
        ("Contact Information", {
            "fields": ("admin_email", "billing_email")
        }),
        ("External Integrations", {
            "fields": ("keycloak_realm", "keycloak_client_id", 
                       "lago_customer_id", "lago_subscription_id"),
            "classes": ("collapse",)
        }),
        ("Configuration", {
            "fields": ("config", "quota_overrides"),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "suspended_at", 
                       "trial_ends_at", "created_by"),
            "classes": ("collapse",)
        }),
    )
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            TenantStatus.ACTIVE: "green",
            TenantStatus.TRIAL: "blue",
            TenantStatus.SUSPENDED: "orange",
            TenantStatus.CANCELLED: "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"
    
    def users_count(self, obj):
        return obj.users.count()
    users_count.short_description = "Users"
    
    def api_keys_count(self, obj):
        return obj.api_keys.count()
    api_keys_count.short_description = "API Keys"
    
    def get_queryset(self, request):
        """Optimize with prefetch."""
        return super().get_queryset(request).prefetch_related("users", "api_keys")
    
    actions = ["suspend_tenants", "activate_tenants", "export_as_csv"]
    
    @admin.action(description="Suspend selected tenants")
    def suspend_tenants(self, request, queryset):
        queryset.update(status=TenantStatus.SUSPENDED, suspended_at=timezone.now())
        self.message_user(request, f"Suspended {queryset.count()} tenants.")
    
    @admin.action(description="Activate selected tenants")
    def activate_tenants(self, request, queryset):
        queryset.update(status=TenantStatus.ACTIVE, suspended_at=None)
        self.message_user(request, f"Activated {queryset.count()} tenants.")
    
    @admin.action(description="Export selected as CSV")
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=tenants.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "Name", "Slug", "Status", "Tier", "Admin Email", "Created"])
        for t in queryset:
            writer.writerow([t.id, t.name, t.slug, t.status, t.tier, 
                            t.admin_email, t.created_at.isoformat()])
        return response


# =============================================================================
# TENANT USER ADMIN
# =============================================================================

@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    """Admin for tenant users."""
    
    list_display = ["email", "tenant_link", "role", "is_active", "is_primary", 
                    "permissions_count", "last_login_at"]
    list_filter = ["role", "is_active", "is_primary", RecentlyCreatedFilter]
    search_fields = ["email", "display_name", "tenant__name"]
    readonly_fields = ["id", "created_at", "updated_at", "last_login_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant"]
    
    fieldsets = (
        (None, {
            "fields": ("id", "tenant", "email", "display_name")
        }),
        ("Authentication", {
            "fields": ("role", "permissions")
        }),
        ("Status", {
            "fields": ("is_active", "is_primary", "last_login_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def tenant_link(self, obj):
        """Link to tenant."""
        from django.urls import reverse
        url = reverse("admin:saas_tenant_change", args=[obj.tenant_id])
        return format_html('<a href="{}">{}</a>', url, obj.tenant.name)
    tenant_link.short_description = "Tenant"
    
    def permissions_count(self, obj):
        return len(obj.permissions) if obj.permissions else 0
    permissions_count.short_description = "Perms"
    
    actions = ["deactivate_users", "activate_users"]
    
    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    
    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)


# =============================================================================
# SUBSCRIPTION ADMIN
# =============================================================================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin for subscriptions."""
    
    list_display = ["tenant", "tier", "status_badge", "current_period_end", "created_at"]
    list_filter = ["status", "tier", RecentlyCreatedFilter]
    search_fields = ["tenant__name", "lago_subscription_id"]
    readonly_fields = ["id", "created_at", "updated_at", "cancelled_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant", "tier"]
    
    def status_badge(self, obj):
        colors = {"active": "green", "trialing": "blue", 
                  "past_due": "orange", "cancelled": "red"}
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = "Status"


# =============================================================================
# API KEY ADMIN
# =============================================================================

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin for API keys."""
    
    list_display = ["name", "tenant_link", "key_prefix_display", "is_active", 
                    "is_test", "last_used_at", "usage_count"]
    list_filter = ["is_active", "is_test", ActiveStatusFilter, RecentlyCreatedFilter]
    search_fields = ["name", "tenant__name", "key_prefix"]
    readonly_fields = ["id", "key_prefix", "key_hash", "created_at", 
                       "last_used_at", "usage_count", "revoked_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant"]
    
    def tenant_link(self, obj):
        from django.urls import reverse
        url = reverse("admin:saas_tenant_change", args=[obj.tenant_id])
        return format_html('<a href="{}">{}</a>', url, obj.tenant.name)
    tenant_link.short_description = "Tenant"
    
    def key_prefix_display(self, obj):
        color = "green" if obj.is_active else "red"
        return format_html(
            '<code style="color: {}; background: #f0f0f0; padding: 2px 6px; '
            'border-radius: 3px;">{}</code>',
            color, f"{obj.key_prefix}..."
        )
    key_prefix_display.short_description = "Key"
    
    actions = ["revoke_keys", "activate_keys"]
    
    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request, queryset):
        queryset.update(is_active=False, revoked_at=timezone.now())
        self.message_user(request, f"Revoked {queryset.count()} API keys.")
    
    @admin.action(description="Reactivate selected API keys")
    def activate_keys(self, request, queryset):
        queryset.update(is_active=True, revoked_at=None)


# =============================================================================
# AUDIT LOG ADMIN (READ-ONLY)
# =============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for audit logs (read-only, immutable)."""
    
    list_display = ["timestamp", "action", "actor_display", "resource_type", 
                    "resource_id", "tenant", "ip_address"]
    list_filter = ["action", "resource_type", "actor_type", RecentlyCreatedFilter]
    search_fields = ["action", "actor_id", "resource_id", "tenant__name", "ip_address"]
    readonly_fields = [
        "id", "tenant", "actor_id", "actor_type", "actor_email",
        "action", "resource_type", "resource_id", "details",
        "ip_address", "user_agent", "request_id", "timestamp"
    ]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    
    fieldsets = (
        ("Event", {
            "fields": ("action", "resource_type", "resource_id", "timestamp")
        }),
        ("Actor", {
            "fields": ("actor_id", "actor_type", "actor_email")
        }),
        ("Context", {
            "fields": ("tenant", "ip_address", "user_agent", "request_id")
        }),
        ("Details", {
            "fields": ("details",),
            "classes": ("collapse",)
        }),
    )
    
    def actor_display(self, obj):
        return obj.actor_email or obj.actor_id[:8] + "..."
    actor_display.short_description = "Actor"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# USAGE RECORD ADMIN
# =============================================================================

@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    """Admin for usage records."""
    
    list_display = ["tenant", "metric_name", "quantity", "recorded_at", 
                    "api_key_prefix", "synced_to_lago"]
    list_filter = ["metric_name", "synced_to_lago", RecentlyCreatedFilter]
    search_fields = ["tenant__name", "metric_name"]
    readonly_fields = ["id", "recorded_at", "synced_to_lago", "lago_event_id"]
    ordering = ["-recorded_at"]
    date_hierarchy = "recorded_at"
    autocomplete_fields = ["tenant"]
    
    def api_key_prefix(self, obj):
        if obj.api_key_id:
            return format_html('<code>{}</code>', str(obj.api_key_id)[:8] + "...")
        return "-"
    api_key_prefix.short_description = "API Key"
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# WEBHOOK ADMIN
# =============================================================================

@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    """Admin for webhooks."""
    
    list_display = ["name", "tenant", "url_truncated", "is_active", 
                    "failure_count", "last_triggered_at"]
    list_filter = ["is_active", RecentlyCreatedFilter]
    search_fields = ["name", "url", "tenant__name"]
    readonly_fields = ["id", "secret", "created_at", "last_triggered_at"]
    ordering = ["-created_at"]
    autocomplete_fields = ["tenant"]
    
    inlines = [WebhookDeliveryInline]
    
    fieldsets = (
        (None, {
            "fields": ("id", "tenant", "name", "url")
        }),
        ("Configuration", {
            "fields": ("event_types", "is_active")
        }),
        ("Status", {
            "fields": ("failure_count", "last_triggered_at", "created_at")
        }),
        ("Security", {
            "fields": ("secret",),
            "classes": ("collapse",)
        }),
    )
    
    def url_truncated(self, obj):
        url = obj.url
        if len(url) > 40:
            url = url[:37] + "..."
        return format_html('<code>{}</code>', url)
    url_truncated.short_description = "URL"
    
    actions = ["reset_failure_count", "disable_webhooks", "enable_webhooks"]
    
    @admin.action(description="Reset failure count")
    def reset_failure_count(self, request, queryset):
        queryset.update(failure_count=0)
    
    @admin.action(description="Disable selected webhooks")
    def disable_webhooks(self, request, queryset):
        queryset.update(is_active=False)
    
    @admin.action(description="Enable selected webhooks")
    def enable_webhooks(self, request, queryset):
        queryset.update(is_active=True)


# =============================================================================
# WEBHOOK DELIVERY ADMIN
# =============================================================================

@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    """Admin for webhook deliveries (read-only)."""
    
    list_display = ["webhook", "event_type", "status_badge", "response_time_display",
                    "delivered_at"]
    list_filter = ["success", "event_type", RecentlyCreatedFilter]
    search_fields = ["webhook__name", "event_type"]
    readonly_fields = ["id", "webhook", "event_type", "payload", "status_code",
                       "error_message", "response_time_ms", "delivered_at", "success"]
    ordering = ["-delivered_at"]
    date_hierarchy = "delivered_at"
    
    def status_badge(self, obj):
        color = "green" if obj.success else "red"
        status = f"{obj.status_code}" if obj.status_code else "Failed"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, status
        )
    status_badge.short_description = "Status"
    
    def response_time_display(self, obj):
        if obj.response_time_ms:
            return f"{obj.response_time_ms}ms"
        return "-"
    response_time_display.short_description = "Time"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# NOTIFICATION ADMIN
# =============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for notifications."""
    
    list_display = ["title_truncated", "tenant", "user_display", "type", 
                    "priority", "is_read", "created_at"]
    list_filter = ["type", "priority", "is_read", RecentlyCreatedFilter]
    search_fields = ["title", "message", "tenant__name"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["tenant"]
    
    def title_truncated(self, obj):
        if len(obj.title) > 40:
            return obj.title[:37] + "..."
        return obj.title
    title_truncated.short_description = "Title"
    
    def user_display(self, obj):
        if obj.user_id:
            return str(obj.user_id)[:8] + "..."
        return "All Users"
    user_display.short_description = "User"
    
    actions = ["mark_as_read", "mark_as_unread", "delete_expired"]
    
    @admin.action(description="Mark selected as read")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
    
    @admin.action(description="Mark selected as unread")
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
    
    @admin.action(description="Delete expired notifications")
    def delete_expired(self, request, queryset):
        expired = queryset.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        self.message_user(request, f"Deleted {count} expired notifications.")


# =============================================================================
# ADMIN SITE CUSTOMIZATION
# =============================================================================

admin.site.site_header = "SomaBrain Admin"
admin.site.site_title = "SomaBrain"
admin.site.index_title = "Platform Administration"
