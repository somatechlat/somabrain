"""
AAAS Models - Authentication and Authorization.

Identity providers, roles, and permissions for RBAC.
"""

from uuid import uuid4

from django.db import models

from .enums import IdentityProviderType, PlatformRole


class IdentityProvider(models.Model):
    """
    OAuth Identity Provider configuration.

    Supports: Google, Facebook, GitHub, Keycloak, Generic OIDC.
    All secrets stored in Vault - vault_secret_path references vault location.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(max_length=255)
    provider_type = models.CharField(
        max_length=20, choices=IdentityProviderType.choices, db_index=True
    )

    tenant = models.ForeignKey(
        "Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="identity_providers",
        help_text="Null = platform-level provider",
    )

    client_id = models.CharField(max_length=500)
    project_id = models.CharField(max_length=255, null=True, blank=True)
    auth_uri = models.URLField(max_length=500)
    token_uri = models.URLField(max_length=500)
    certs_url = models.URLField(max_length=500, null=True, blank=True)

    redirect_uris = models.JSONField(default=list, help_text="Allowed redirect URIs")
    javascript_origins = models.JSONField(default=list, blank=True)

    default_scopes = models.JSONField(
        default=list, help_text="e.g. ['openid', 'email', 'profile']"
    )
    claim_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map provider claims to our fields",
    )

    vault_secret_path = models.CharField(
        max_length=500, help_text="e.g. vault://secrets/oauth/google/client_secret"
    )

    is_enabled = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default login provider")
    trust_email = models.BooleanField(default=True)
    store_token = models.BooleanField(default=True)

    display_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_identity_providers"
        ordering = ["display_order", "name"]
        verbose_name = "Identity Provider"
        verbose_name_plural = "Identity Providers"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "provider_type", "name"], name="uq_identity_provider"
            )
        ]

    def __str__(self):
        """Return string representation."""
        scope = f"({self.tenant.slug})" if self.tenant else "(platform)"
        return f"{self.name} - {self.get_provider_type_display()} {scope}"


class TenantAuthConfig(models.Model):
    """Tenant-specific authentication configuration."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.OneToOneField(
        "Tenant", on_delete=models.CASCADE, related_name="auth_config"
    )

    preferred_provider = models.ForeignKey(
        IdentityProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_by_tenants",
    )

    custom_redirect_uris = models.JSONField(default=list, blank=True)
    require_mfa = models.BooleanField(default=False)
    session_timeout_minutes = models.IntegerField(default=60)
    custom_claim_mappings = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_tenant_auth_config"
        verbose_name = "Tenant Auth Config"
        verbose_name_plural = "Tenant Auth Configs"

    def __str__(self):
        """Return string representation."""
        return f"Auth Config for {self.tenant.name}"


class Role(models.Model):
    """Role definition for RBAC."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)

    is_system = models.BooleanField(
        default=False, help_text="System roles cannot be deleted"
    )
    platform_role = models.CharField(
        max_length=20,
        choices=PlatformRole.choices,
        null=True,
        blank=True,
        help_text="Maps to platform role hierarchy",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_roles"
        ordering = ["name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        """Return string representation."""
        return self.name


class FieldPermission(models.Model):
    """Field-level permission for granular access control."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="field_permissions"
    )

    model_name = models.CharField(max_length=100, db_index=True)
    field_name = models.CharField(max_length=100)

    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_field_permissions"
        verbose_name = "Field Permission"
        verbose_name_plural = "Field Permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "model_name", "field_name"], name="uq_field_permission"
            )
        ]
        indexes = [
            models.Index(fields=["role", "model_name"]),
        ]

    def __str__(self):
        """Return string representation."""
        perms = []
        if self.can_view:
            perms.append("view")
        if self.can_edit:
            perms.append("edit")
        return f"{self.role.name}: {self.model_name}.{self.field_name} [{','.join(perms)}]"


class TenantUserRole(models.Model):
    """Assignment of roles to tenant users."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant_user = models.ForeignKey(
        "TenantUser", on_delete=models.CASCADE, related_name="role_assignments"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="user_assignments"
    )

    assigned_by = models.CharField(max_length=255, null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_tenant_user_roles"
        verbose_name = "Tenant User Role"
        verbose_name_plural = "Tenant User Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_user", "role"], name="uq_tenant_user_role"
            )
        ]

    def __str__(self):
        """Return string representation."""
        return f"{self.tenant_user.email} - {self.role.name}"
