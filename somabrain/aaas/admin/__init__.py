"""
AAAS Admin Package.

Django Admin configuration for all AAAS models.
"""

# Import all admin classes to trigger their registration
from .audit import (  # noqa: F401
    AuditLogAdmin,
    NotificationAdmin,
    WebhookAdmin,
    WebhookDeliveryAdmin,
)
from .billing import APIKeyAdmin, SubscriptionAdmin, UsageRecordAdmin  # noqa: F401
from .tenant import SubscriptionTierAdmin, TenantAdmin, TenantUserAdmin  # noqa: F401
