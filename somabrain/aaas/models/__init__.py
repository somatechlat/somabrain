"""
AAAS Models Package.

Django ORM models for multi-tenancy, subscriptions, API keys, and audit logging.
"""

from .enums import (
    ActorType,
    IdentityProviderType,
    PlatformRole,
    SubscriptionStatus,
    TenantStatus,
    TenantTier,
    UserRole,
)
from .tenant import Tenant, TenantUser
from .auth import (
    FieldPermission,
    IdentityProvider,
    Role,
    TenantAuthConfig,
    TenantUserRole,
)
from .billing import (
    Subscription,
    SubscriptionTier,
    TenantSubscription,
    UsageRecord,
)
from .api import APIKey
from .audit import AuditLog
from .webhooks import Notification, Webhook, WebhookDelivery

__all__ = [
    # Enums
    "ActorType",
    "IdentityProviderType",
    "PlatformRole",
    "SubscriptionStatus",
    "TenantStatus",
    "TenantTier",
    "UserRole",
    # Tenant
    "Tenant",
    "TenantUser",
    # Auth
    "FieldPermission",
    "IdentityProvider",
    "Role",
    "TenantAuthConfig",
    "TenantUserRole",
    # Billing
    "Subscription",
    "SubscriptionTier",
    "TenantSubscription",
    "UsageRecord",
    # API
    "APIKey",
    # Audit
    "AuditLog",
    # Webhooks
    "Notification",
    "Webhook",
    "WebhookDelivery",
]
