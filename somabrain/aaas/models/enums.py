"""
AAAS Models - Enums and Choice Classes.

Django TextChoices for all AAAS domain enums.
"""

from django.db import models


class TenantStatus(models.TextChoices):
    """Tenant lifecycle states."""

    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DISABLED = "disabled", "Disabled"
    PENDING = "pending", "Pending"
    TRIAL = "trial", "Trial"


class TenantTier(models.TextChoices):
    """Subscription tier levels."""

    FREE = "free", "Free"
    STARTER = "starter", "Starter"
    PRO = "pro", "Pro"
    ENTERPRISE = "enterprise", "Enterprise"
    SYSTEM = "system", "System"


class UserRole(models.TextChoices):
    """Roles within a tenant."""

    ADMIN = "admin", "Admin"
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


class SubscriptionStatus(models.TextChoices):
    """Subscription lifecycle states."""

    ACTIVE = "active", "Active"
    TRIAL = "trial", "Trial"
    PAST_DUE = "past_due", "Past Due"
    CANCELLED = "cancelled", "Cancelled"
    PENDING = "pending", "Pending"


class ActorType(models.TextChoices):
    """Actor types for audit logging."""

    USER = "user", "User"
    API_KEY = "api_key", "API Key"
    SYSTEM = "system", "System"
    ADMIN = "admin", "Admin"


class IdentityProviderType(models.TextChoices):
    """Supported OAuth identity provider types."""

    KEYCLOAK = "keycloak", "Keycloak"
    GOOGLE = "google", "Google OAuth"
    FACEBOOK = "facebook", "Facebook OAuth"
    GITHUB = "github", "GitHub OAuth"
    OIDC_GENERIC = "oidc", "Generic OIDC"


class PlatformRole(models.TextChoices):
    """Platform-level roles for Eye of God admin."""

    SUPER_ADMIN = "super-admin", "Super Admin"
    TENANT_ADMIN = "tenant-admin", "Tenant Admin"
    TENANT_USER = "tenant-user", "Tenant User"
    API_ACCESS = "api-access", "API Access"
