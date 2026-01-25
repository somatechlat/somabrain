"""
Django Migration: Rename saas_* tables to aaas_*

This migration renames all database tables from the legacy 'saas_' prefix
to the new 'aaas_' (Agent-As-A-Service) prefix.

Run with: python manage.py migrate somabrain.aaas

VIBE Compliance:
- Rule 10: Django ORM only
- Rule 100: Centralized configuration
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Rename all saas_* tables to aaas_*."""

    dependencies = [
        # This should be the last migration before this one
        ("aaas", "0005_notifications"),
    ]

    operations = [
        # Core tenant tables
        migrations.AlterModelTable(
            name="tenant",
            table="aaas_tenants",
        ),
        migrations.AlterModelTable(
            name="tenantuser",
            table="aaas_tenant_users",
        ),
        migrations.AlterModelTable(
            name="tenantsubscription",
            table="aaas_subscriptions",
        ),
        migrations.AlterModelTable(
            name="subscriptiontier",
            table="aaas_subscription_tiers",
        ),
        # Auth and RBAC tables
        migrations.AlterModelTable(
            name="identityprovider",
            table="aaas_identity_providers",
        ),
        migrations.AlterModelTable(
            name="tenantauthconfig",
            table="aaas_tenant_auth_config",
        ),
        migrations.AlterModelTable(
            name="role",
            table="aaas_roles",
        ),
        migrations.AlterModelTable(
            name="fieldpermission",
            table="aaas_field_permissions",
        ),
        migrations.AlterModelTable(
            name="tenantuserrole",
            table="aaas_tenant_user_roles",
        ),
        # API and Audit tables
        migrations.AlterModelTable(
            name="apikey",
            table="aaas_api_keys",
        ),
        migrations.AlterModelTable(
            name="auditlog",
            table="aaas_audit_log",
        ),
    ]
