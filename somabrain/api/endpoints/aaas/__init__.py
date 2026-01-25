"""
AAAS Admin API Package.

Django Ninja endpoints for tenant management, API keys, billing.
"""

from .endpoints import router
from .schemas import (
    APIKeyCreateSchema,
    APIKeyCreatedSchema,
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
    "router",
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
]
