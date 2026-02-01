"""
AAAS Admin Package.

Django Admin configuration for all AAAS models.
"""

# Import all admin classes to trigger their registration
from .tenant import SubscriptionTierAdmin, TenantAdmin, TenantUserAdmin  # noqa: F401
from .billing import APIKeyAdmin, SubscriptionAdmin, UsageRecordAdmin  # noqa: F401
from .audit import (  # noqa: F401
    AuditLogAdmin,
    NotificationAdmin,
    WebhookAdmin,
    WebhookDeliveryAdmin,
)
