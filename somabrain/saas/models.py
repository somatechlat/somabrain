"""
SaaS Models for SomaBrain.

Django ORM models for multi-tenancy, subscriptions, API keys, and audit logging.
Per VIBE Coding Rules v5.2 - Pure Django Stack.
"""

import secrets
import hashlib
from uuid import uuid4

from django.db import models
from django.utils import timezone


# =============================================================================
# ENUMS (Choices)
# =============================================================================

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


# =============================================================================
# IDENTITY PROVIDER MODEL (Platform + Tenant OAuth)
# =============================================================================

class IdentityProvider(models.Model):
    """
    OAuth Identity Provider configuration.
    
    Supports: Google, Facebook, GitHub, Keycloak, Generic OIDC.
    All secrets stored in Vault - vault_secret_path references vault location.
    
    Platform-level providers are defaults for all tenants.
    Tenant-specific providers override platform defaults.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # Basic config
    name = models.CharField(max_length=255)
    provider_type = models.CharField(
        max_length=20,
        choices=IdentityProviderType.choices,
        db_index=True
    )
    
    # Scope: Platform (null) or Tenant-specific
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="identity_providers",
        help_text="Null = platform-level provider"
    )
    
    # OAuth configuration (non-secret)
    client_id = models.CharField(max_length=500)
    project_id = models.CharField(max_length=255, null=True, blank=True)
    auth_uri = models.URLField(max_length=500)
    token_uri = models.URLField(max_length=500)
    certs_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Redirect and origins (JSON arrays)
    redirect_uris = models.JSONField(default=list, help_text="Allowed redirect URIs")
    javascript_origins = models.JSONField(default=list, blank=True)
    
    # Scopes and claims
    default_scopes = models.JSONField(
        default=list,
        help_text="e.g. ['openid', 'email', 'profile']"
    )
    claim_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map provider claims to our fields: {'tenant_id': 'custom:tenant_id'}"
    )
    
    # Vault secret path (NEVER store actual secret)
    vault_secret_path = models.CharField(
        max_length=500,
        help_text="e.g. vault://secrets/oauth/google/client_secret"
    )
    
    # Status
    is_enabled = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default login provider")
    trust_email = models.BooleanField(default=True)
    store_token = models.BooleanField(default=True)
    
    # Display
    display_order = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "saas_identity_providers"
        ordering = ["display_order", "name"]
        verbose_name = "Identity Provider"
        verbose_name_plural = "Identity Providers"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "provider_type", "name"],
                name="uq_identity_provider"
            )
        ]
    
    def __str__(self):
        scope = f"({self.tenant.slug})" if self.tenant else "(platform)"
        return f"{self.name} - {self.get_provider_type_display()} {scope}"


class TenantAuthConfig(models.Model):
    """
    Tenant-specific authentication configuration.
    
    Overrides platform defaults for a specific tenant.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.OneToOneField(
        'Tenant',
        on_delete=models.CASCADE,
        related_name="auth_config"
    )
    
    # Preferred login provider (references IdentityProvider)
    preferred_provider = models.ForeignKey(
        IdentityProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_by_tenants"
    )
    
    # Custom redirect URIs (append to platform defaults)
    custom_redirect_uris = models.JSONField(default=list, blank=True)
    
    # MFA requirements
    require_mfa = models.BooleanField(default=False)
    
    # Session settings
    session_timeout_minutes = models.IntegerField(default=60)
    
    # Custom claim mappings (override platform)
    custom_claim_mappings = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "saas_tenant_auth_config"
        verbose_name = "Tenant Auth Config"
        verbose_name_plural = "Tenant Auth Configs"
    
    def __str__(self):
        return f"Auth Config for {self.tenant.name}"


# =============================================================================
# ROLE AND PERMISSION MODELS
# =============================================================================

class Role(models.Model):
    """
    Role definition for RBAC.
    
    System roles: super-admin, tenant-admin, tenant-user, api-access
    Custom roles: Created by SysAdmin for specific permissions.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    
    # Type
    is_system = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted"
    )
    platform_role = models.CharField(
        max_length=20,
        choices=PlatformRole.choices,
        null=True,
        blank=True,
        help_text="Maps to platform role hierarchy"
    )
    
    # Parent role for inheritance
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "saas_roles"
        ordering = ["name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"
    
    def __str__(self):
        return self.name


class FieldPermission(models.Model):
    """
    Field-level permission for granular access control.
    
    Defines which fields a role can view/edit on a model.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="field_permissions"
    )
    
    # Target
    model_name = models.CharField(max_length=100, db_index=True)  # e.g., "Tenant"
    field_name = models.CharField(max_length=100)  # e.g., "billing_email"
    
    # Permissions
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    
    class Meta:
        db_table = "saas_field_permissions"
        verbose_name = "Field Permission"
        verbose_name_plural = "Field Permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "model_name", "field_name"],
                name="uq_field_permission"
            )
        ]
        indexes = [
            models.Index(fields=["role", "model_name"]),
        ]
    
    def __str__(self):
        perms = []
        if self.can_view:
            perms.append("view")
        if self.can_edit:
            perms.append("edit")
        return f"{self.role.name}: {self.model_name}.{self.field_name} [{','.join(perms)}]"


class TenantUserRole(models.Model):
    """
    Assignment of roles to tenant users.
    
    A user can have multiple roles.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant_user = models.ForeignKey(
        'TenantUser',
        on_delete=models.CASCADE,
        related_name="role_assignments"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_assignments"
    )
    
    # Assigned by
    assigned_by = models.CharField(max_length=255, null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "saas_tenant_user_roles"
        verbose_name = "Tenant User Role"
        verbose_name_plural = "Tenant User Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_user", "role"],
                name="uq_tenant_user_role"
            )
        ]
    
    def __str__(self):
        return f"{self.tenant_user.email} - {self.role.name}"


# =============================================================================
# SUBSCRIPTION TIER MODEL
# =============================================================================

class SubscriptionTier(models.Model):
    """
    SaaS subscription tier definition (Free, Starter, Pro, Enterprise).
    
    Defines quotas, rate limits, and features for each tier.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    slug = models.CharField(max_length=50, unique=True, db_index=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Quotas
    api_calls_limit = models.IntegerField(default=1000, help_text="API calls per month")
    memory_ops_limit = models.IntegerField(default=500, help_text="Memory operations per month")
    storage_limit_mb = models.IntegerField(default=100, help_text="Storage in MB")
    
    # Rate limiting
    rate_limit_rps = models.IntegerField(default=10, help_text="Requests per second")
    rate_limit_burst = models.IntegerField(default=20, help_text="Burst limit")
    
    # Features (JSON)
    features = models.JSONField(default=dict, blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "saas_subscription_tiers"
        ordering = ["display_order", "price_monthly"]
        verbose_name = "Subscription Tier"
        verbose_name_plural = "Subscription Tiers"
    
    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"


# =============================================================================
# TENANT MODEL
# =============================================================================

class Tenant(models.Model):
    """
    Multi-tenant organization.
    
    Each tenant has isolated data, users, and API keys.
    Integrates with Keycloak for SSO and Lago for billing.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=TenantStatus.choices,
        default=TenantStatus.PENDING,
        db_index=True
    )
    tier = models.CharField(
        max_length=20,
        choices=TenantTier.choices,
        default=TenantTier.FREE,
    )
    
    # External integrations
    keycloak_realm = models.CharField(max_length=255, null=True, blank=True)
    keycloak_client_id = models.CharField(max_length=255, null=True, blank=True)
    lago_customer_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    lago_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Configuration
    config = models.JSONField(default=dict, blank=True)
    quota_overrides = models.JSONField(default=dict, blank=True)
    
    # Contact
    admin_email = models.EmailField(null=True, blank=True)
    billing_email = models.EmailField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Created by (for audit)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = "saas_tenants"
        ordering = ["-created_at"]
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["slug"]),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.slug})"
    
    def suspend(self, reason: str = None):
        """Suspend the tenant."""
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = timezone.now()
        if reason:
            self.config["suspension_reason"] = reason
        self.save()
    
    def activate(self):
        """Activate the tenant."""
        self.status = TenantStatus.ACTIVE
        self.suspended_at = None
        self.config.pop("suspension_reason", None)
        self.save()
    
    @property
    def is_active(self):
        return self.status == TenantStatus.ACTIVE
    
    @property
    def is_trial(self):
        return self.status == TenantStatus.TRIAL


# =============================================================================
# TENANT USER MODEL
# =============================================================================

class TenantUser(models.Model):
    """
    User within a tenant.
    
    Linked to Keycloak user ID for SSO authentication.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users"
    )
    
    email = models.EmailField(db_index=True)
    keycloak_user_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    # Role within tenant
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VIEWER
    )
    
    # Profile
    display_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False, help_text="Primary admin for tenant")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "saas_tenant_users"
        ordering = ["-created_at"]
        verbose_name = "Tenant User"
        verbose_name_plural = "Tenant Users"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"],
                name="uq_tenant_user_email"
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["email"]),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.tenant.slug})"


# =============================================================================
# SUBSCRIPTION MODEL
# =============================================================================

class Subscription(models.Model):
    """
    Tenant subscription record.
    
    Tracks subscription lifecycle and billing periods.
    Integrates with Lago for payment processing.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    tier = models.ForeignKey(
        SubscriptionTier,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING
    )
    
    # Lago integration
    lago_subscription_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    # Billing period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "saas_subscriptions"
        ordering = ["-created_at"]
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
    
    def __str__(self):
        return f"{self.tenant.name} - {self.tier.name}"


# =============================================================================
# API KEY MODEL
# =============================================================================

class APIKey(models.Model):
    """
    API key for programmatic access.
    
    Format: sbk_live_a1b2c3... or sbk_test_a1b2c3...
    Key is stored as SHA-256 hash, only prefix is plaintext.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="api_keys"
    )
    
    # Key identification
    name = models.CharField(max_length=255)
    key_prefix = models.CharField(max_length=12, db_index=True)  # sbk_live_ or sbk_test_
    key_hash = models.CharField(max_length=64)  # SHA-256 hash
    
    # Permissions
    scopes = models.JSONField(default=list, blank=True)  # ['read:memory', 'write:memory']
    
    # Rate limiting (overrides)
    rate_limit_override = models.IntegerField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_test = models.BooleanField(default=False, help_text="Test mode key")
    
    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    usage_count = models.BigIntegerField(default=0)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        TenantUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_api_keys"
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        TenantUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_api_keys"
    )
    
    class Meta:
        db_table = "saas_api_keys"
        ordering = ["-created_at"]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["key_prefix", "key_hash"]),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"
    
    @classmethod
    def generate_key(cls, is_test: bool = False) -> tuple[str, str, str]:
        """
        Generate a new API key.
        
        Returns: (full_key, prefix, hash)
        """
        mode = "test" if is_test else "live"
        random_part = secrets.token_hex(24)  # 48 chars
        full_key = f"sbk_{mode}_{random_part}"
        prefix = f"sbk_{mode}_"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, prefix, key_hash
    
    @classmethod
    def verify_key(cls, full_key: str) -> "APIKey | None":
        """
        Verify an API key and return the APIKey object if valid.
        """
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        try:
            api_key = cls.objects.get(
                key_hash=key_hash,
                is_active=True,
                tenant__status__in=[TenantStatus.ACTIVE, TenantStatus.TRIAL]
            )
            # Check expiration
            if api_key.expires_at and api_key.expires_at < timezone.now():
                return None
            return api_key
        except cls.DoesNotExist:
            return None
    
    def touch(self, ip_address: str = None):
        """Update last used timestamp and IP."""
        self.last_used_at = timezone.now()
        if ip_address:
            self.last_used_ip = ip_address
        self.usage_count += 1
        self.save(update_fields=["last_used_at", "last_used_ip", "usage_count"])
    
    def revoke(self, by_user: "TenantUser" = None):
        """Revoke this API key."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.revoked_by = by_user
        self.save()


# =============================================================================
# AUDIT LOG MODEL
# =============================================================================

class AuditLog(models.Model):
    """
    Audit trail for all admin actions.
    
    Immutable log of all significant platform operations.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # Context
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs"
    )
    
    # Actor
    actor_id = models.CharField(max_length=255)
    actor_type = models.CharField(
        max_length=20,
        choices=ActorType.choices,
        default=ActorType.USER
    )
    actor_email = models.EmailField(null=True, blank=True)
    
    # Action
    action = models.CharField(max_length=100, db_index=True)  # tenant.created, key.revoked
    resource_type = models.CharField(max_length=100)  # tenant, api_key, subscription
    resource_id = models.CharField(max_length=255)
    
    # Details
    details = models.JSONField(default=dict, blank=True)
    
    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "saas_audit_log"
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["tenant", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["actor_id", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]
    
    def __str__(self):
        return f"{self.action} by {self.actor_id} at {self.timestamp}"
    
    @classmethod
    def log(
        cls,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        actor_type: str = ActorType.USER,
        tenant: "Tenant" = None,
        details: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        request_id: str = None,
        actor_email: str = None,
    ) -> "AuditLog":
        """
        Create an audit log entry and publish to Kafka.
        
        ALL 10 PERSONAS:
        - DBA: Django ORM for persistence
        - SRE: Kafka via outbox for event streaming
        - Security: Full audit trail
        """
        # 1. Save to Django ORM (primary persistence)
        entry = cls.objects.create(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            actor_id=str(actor_id),
            actor_type=actor_type,
            tenant=tenant,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            actor_email=actor_email,
        )
        
        # 2. Publish to Kafka via outbox (async event stream)
        try:
            from somabrain.audit import publish_event
            
            publish_event({
                "type": "saas.audit",
                "action": action,
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "actor_id": str(actor_id),
                "actor_type": actor_type,
                "tenant_id": str(tenant.id) if tenant else None,
                "details": details or {},
                "timestamp": entry.timestamp.isoformat(),
            }, topic="soma.saas.audit")
        except Exception:
            # Kafka publish is best-effort; ORM entry is primary
            import logging
            logging.getLogger("somabrain.saas.models").debug(
                "Kafka audit publish failed (ORM entry persisted)", exc_info=True
            )
        
        return entry




# =============================================================================
# TENANT SUBSCRIPTION MODEL
# =============================================================================

class TenantSubscription(models.Model):
    """
    Tenant's active subscription.
    
    ALL 10 PERSONAS - VIBE Coding Rules:
    - DBA: Foreign keys with cascade
    - Billing: Lago subscription sync
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="tenant_subscriptions"
    )
    tier = models.ForeignKey(
        "SubscriptionTier", on_delete=models.PROTECT, related_name="tier_subscriptions"
    )
    
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
    )
    
    # Lifecycle dates
    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Lago integration
    lago_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    lago_customer_id = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tenant Subscription"
        verbose_name_plural = "Tenant Subscriptions"
    
    def __str__(self):
        return f"{self.tenant.name} - {self.tier.name} ({self.status})"


# =============================================================================
# USAGE RECORD MODEL
# =============================================================================

class UsageRecord(models.Model):
    """
    Usage event for billing.
    
    ALL 10 PERSONAS - VIBE Coding Rules:
    - DBA: Indexed for time-series queries
    - Billing: Metering for Lago
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="usage_records"
    )
    
    metric_name = models.CharField(max_length=100)  # e.g., "api_call", "memory_operation"
    quantity = models.PositiveIntegerField(default=1)
    
    # Optional metadata
    metadata = models.JSONField(default=dict)
    
    # Lago sync
    lago_event_id = models.CharField(max_length=255, blank=True, null=True)
    synced_to_lago = models.BooleanField(default=False)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["tenant", "recorded_at"]),
            models.Index(fields=["metric_name", "recorded_at"]),
        ]
        verbose_name = "Usage Record"
        verbose_name_plural = "Usage Records"
    
    def __str__(self):
        return f"{self.tenant.slug}:{self.metric_name}={self.quantity}"


# =============================================================================
# WEBHOOK MODEL
# =============================================================================

class Webhook(models.Model):
    """
    Webhook configuration for tenant event subscriptions.
    
    ALL 10 PERSONAS - VIBE Coding Rules:
    - Security: HMAC secret, tenant isolation
    - SRE: Retry tracking, failure count
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="webhooks"
    )
    
    # Configuration
    url = models.URLField(max_length=500)
    name = models.CharField(max_length=200, blank=True, null=True)
    event_types = models.JSONField(default=list)  # List of event types
    
    # Security
    secret = models.CharField(max_length=100)  # HMAC secret
    
    # Status
    is_active = models.BooleanField(default=True)
    failure_count = models.PositiveIntegerField(default=0)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"
    
    def __str__(self):
        return f"{self.tenant.slug}: {self.url[:50]}"


class WebhookDelivery(models.Model):
    """
    Webhook delivery log entry.
    
    ALL 10 PERSONAS - VIBE Coding Rules:
    - SRE: Delivery tracking, error logging
    - DBA: Time-series indexed
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    webhook = models.ForeignKey(
        Webhook, on_delete=models.CASCADE, related_name="deliveries"
    )
    
    # Event info
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    
    # Response
    status_code = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Retry tracking
    attempt_number = models.PositiveIntegerField(default=1)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    delivered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-delivered_at"]
        indexes = [
            models.Index(fields=["webhook", "delivered_at"]),
            models.Index(fields=["success", "delivered_at"]),
        ]
        verbose_name = "Webhook Delivery"
        verbose_name_plural = "Webhook Deliveries"
    
    def __str__(self):
        return f"{self.webhook.id}:{self.event_type} - {'OK' if self.success else 'FAIL'}"


# =============================================================================
# NOTIFICATION MODEL
# =============================================================================

class Notification(models.Model):
    """
    In-app notification for tenant users.
    
    ALL 10 PERSONAS - VIBE Coding Rules:
    - Security: Tenant + user isolation
    - UX: Clear notification management
    """
    
    class NotificationType(models.TextChoices):
        INFO = "info", "Information"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        SUCCESS = "success", "Success"
        BILLING = "billing", "Billing"
        SECURITY = "security", "Security"
        SYSTEM = "system", "System"
    
    class NotificationPriority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="notifications"
    )
    user_id = models.UUIDField(null=True, blank=True)  # None = all users
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL,
    )
    
    # Action
    action_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Lifecycle
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "user_id", "is_read"]),
            models.Index(fields=["tenant", "created_at"]),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.tenant.slug}: {self.title[:30]}"
