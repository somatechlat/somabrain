"""
AAAS Admin API Package.

Django Ninja endpoints for tenant management, API keys, billing.
"""

from .endpoints import router
from .schemas import (
    APIKeyCreatedSchema,
    APIKeyCreateSchema,
    APIKeyResponseSchema,
    SubscriptionChangeSchema,
    SubscriptionResponseSchema,
    SubscriptionTierCreateSchema,
    SubscriptionTierResponseSchema,
    SubscriptionTierUpdateSchema,
    TenantCreateSchema,
    TenantListSchema,
    TenantResponseSchema,
    TenantUpdateSchema,
    UsageEventSchema,
    UsageReportSchema,
)

__all__ = [
    "APIKeyCreateSchema",
    "APIKeyCreatedSchema",
    "APIKeyResponseSchema",
    "SubscriptionChangeSchema",
    "SubscriptionResponseSchema",
    "SubscriptionTierCreateSchema",
    "SubscriptionTierResponseSchema",
    "SubscriptionTierUpdateSchema",
    "TenantCreateSchema",
    "TenantListSchema",
    "TenantResponseSchema",
    "TenantUpdateSchema",
    "UsageEventSchema",
    "UsageReportSchema",
    "router",
]
