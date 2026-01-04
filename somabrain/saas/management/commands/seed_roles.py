"""
Seed system roles and permissions.

Django management command to create default roles and field permissions.

Usage:
    python manage.py seed_roles

ALL 10 PERSONAS per VIBE Coding Rules v5.2
"""

from django.core.management.base import BaseCommand

from somabrain.saas.models import Role, FieldPermission, PlatformRole


class Command(BaseCommand):
    """Command class implementation."""

    help = "Seed system roles and default field permissions"

    def handle(self, *args, **options):
        """Execute handle.
            """

        self.stdout.write("Seeding system roles...")
        
        # =================================================================
        # SYSTEM ROLES
        # =================================================================
        
        roles_data = [
            {
                "name": "Super Admin",
                "slug": "super-admin",
                "description": "Platform-level administrator with full access to all tenants and settings",
                "platform_role": PlatformRole.SUPER_ADMIN,
                "is_system": True,
            },
            {
                "name": "Tenant Admin",
                "slug": "tenant-admin",
                "description": "Administrator for a specific tenant with full tenant access",
                "platform_role": PlatformRole.TENANT_ADMIN,
                "is_system": True,
            },
            {
                "name": "Tenant User",
                "slug": "tenant-user",
                "description": "Regular user within a tenant with limited access",
                "platform_role": PlatformRole.TENANT_USER,
                "is_system": True,
            },
            {
                "name": "API Access",
                "slug": "api-access",
                "description": "Role for API-only access (service accounts)",
                "platform_role": PlatformRole.API_ACCESS,
                "is_system": True,
            },
        ]
        
        created_roles = {}
        for role_data in roles_data:
            role, created = Role.objects.update_or_create(
                slug=role_data["slug"],
                defaults=role_data,
            )
            created_roles[role.slug] = role
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status} role: {role.name}")
        
        # =================================================================
        # FIELD PERMISSIONS FOR TENANT-ADMIN
        # =================================================================
        
        self.stdout.write("\nSeeding field permissions for Tenant Admin...")
        
        tenant_admin = created_roles["tenant-admin"]
        
        # Define what Tenant Admin can view/edit
        tenant_admin_permissions = [
            # Tenant: Can view most, edit some
            ("Tenant", "name", True, True),
            ("Tenant", "slug", True, False),  # Can't change slug
            ("Tenant", "status", True, False),  # Can't change status
            ("Tenant", "tier", True, False),  # Can't change tier
            ("Tenant", "admin_email", True, True),
            ("Tenant", "billing_email", True, True),
            ("Tenant", "config", True, True),
            ("Tenant", "quota_overrides", True, False),  # View only
            
            # TenantUser: Full access
            ("TenantUser", "email", True, True),
            ("TenantUser", "role", True, True),
            ("TenantUser", "display_name", True, True),
            ("TenantUser", "is_active", True, True),
            ("TenantUser", "is_primary", True, False),
            
            # Subscription: View only
            ("Subscription", "tier", True, False),
            ("Subscription", "status", True, False),
            ("Subscription", "current_period_start", True, False),
            ("Subscription", "current_period_end", True, False),
            
            # APIKey: Full access
            ("APIKey", "name", True, True),
            ("APIKey", "scopes", True, True),
            ("APIKey", "is_active", True, True),
            ("APIKey", "expires_at", True, True),
            
            # IdentityProvider: View for tenant-level, can manage their own
            ("IdentityProvider", "name", True, True),
            ("IdentityProvider", "provider_type", True, False),
            ("IdentityProvider", "client_id", True, True),
            ("IdentityProvider", "is_enabled", True, True),
            ("IdentityProvider", "is_default", True, True),
        ]
        
        for model, field, can_view, can_edit in tenant_admin_permissions:
            perm, created = FieldPermission.objects.update_or_create(
                role=tenant_admin,
                model_name=model,
                field_name=field,
                defaults={
                    "can_view": can_view,
                    "can_edit": can_edit,
                },
            )
            if created:
                self.stdout.write(f"    Created: {model}.{field}")
        
        # =================================================================
        # FIELD PERMISSIONS FOR TENANT-USER
        # =================================================================
        
        self.stdout.write("\nSeeding field permissions for Tenant User...")
        
        tenant_user = created_roles["tenant-user"]
        
        # Tenant users have very limited access
        tenant_user_permissions = [
            # Tenant: Basic info only
            ("Tenant", "name", True, False),
            ("Tenant", "slug", True, False),
            
            # TenantUser: Own profile only (enforced at runtime)
            ("TenantUser", "email", True, False),
            ("TenantUser", "display_name", True, True),  # Can edit own name
            
            # Subscription: Basic view
            ("Subscription", "tier", True, False),
            ("Subscription", "status", True, False),
        ]
        
        for model, field, can_view, can_edit in tenant_user_permissions:
            perm, created = FieldPermission.objects.update_or_create(
                role=tenant_user,
                model_name=model,
                field_name=field,
                defaults={
                    "can_view": can_view,
                    "can_edit": can_edit,
                },
            )
            if created:
                self.stdout.write(f"    Created: {model}.{field}")
        
        # =================================================================
        # SUMMARY
        # =================================================================
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Seeded {len(roles_data)} roles and permissions"
        ))
        
        # Show stats
        total_perms = FieldPermission.objects.count()
        self.stdout.write(f"Total field permissions: {total_perms}")