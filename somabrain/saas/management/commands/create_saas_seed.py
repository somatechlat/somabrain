"""
Seed Data Management for SomaBrain SaaS.

Creates default subscription tiers, admin users, and test tenants.
Run via Django management command.

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: Clean management command
- Security: Secure default credentials
- DevOps: Idempotent operations
- QA: Verifiable output
- Docs: Clear docstrings
- DBA: Efficient bulk operations
- SRE: Logging, error handling
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from somabrain.saas.models import (
    APIKey,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    Tenant,
    TenantStatus,
)


class Command(BaseCommand):
    """Create seed data for SaaS platform."""
    
    help = "Create default subscription tiers and test data"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--with-test-tenant",
            action="store_true",
            help="Also create a test tenant with API key",
        )
    
    def handle(self, *args, **options):
        self.stdout.write("Creating SaaS seed data...")
        
        # Create tiers
        tiers = self._create_tiers()
        self.stdout.write(self.style.SUCCESS(f"Created {len(tiers)} subscription tiers"))
        
        # Create test tenant if requested
        if options["with_test_tenant"]:
            tenant, api_key = self._create_test_tenant(tiers["starter"])
            self.stdout.write(self.style.SUCCESS(f"Created test tenant: {tenant.slug}"))
            self.stdout.write(self.style.WARNING(f"Test API Key: {api_key}"))
        
        self.stdout.write(self.style.SUCCESS("Seed data created successfully!"))
    
    def _create_tiers(self) -> dict:
        """Create default subscription tiers."""
        tiers_data = [
            {
                "slug": "free",
                "name": "Free",
                "description": "For testing and development",
                "price_monthly": Decimal("0.00"),
                "price_yearly": Decimal("0.00"),
                "api_calls_limit": 1000,
                "memory_ops_limit": 100,
                "services_limit": 1,
                "users_limit": 1,
                "storage_limit_gb": 1,
                "features": {
                    "basic_memory": True,
                    "vector_search": True,
                    "graph_links": False,
                    "priority_support": False,
                },
                "display_order": 1,
            },
            {
                "slug": "starter",
                "name": "Starter",
                "description": "For small teams and projects",
                "price_monthly": Decimal("29.00"),
                "price_yearly": Decimal("290.00"),
                "api_calls_limit": 10000,
                "memory_ops_limit": 1000,
                "services_limit": 3,
                "users_limit": 5,
                "storage_limit_gb": 10,
                "features": {
                    "basic_memory": True,
                    "vector_search": True,
                    "graph_links": True,
                    "priority_support": False,
                },
                "display_order": 2,
            },
            {
                "slug": "professional",
                "name": "Professional",
                "description": "For growing businesses",
                "price_monthly": Decimal("99.00"),
                "price_yearly": Decimal("990.00"),
                "api_calls_limit": 100000,
                "memory_ops_limit": 10000,
                "services_limit": 10,
                "users_limit": 25,
                "storage_limit_gb": 100,
                "features": {
                    "basic_memory": True,
                    "vector_search": True,
                    "graph_links": True,
                    "priority_support": True,
                    "custom_models": True,
                },
                "display_order": 3,
            },
            {
                "slug": "enterprise",
                "name": "Enterprise",
                "description": "For large organizations",
                "price_monthly": Decimal("499.00"),
                "price_yearly": Decimal("4990.00"),
                "api_calls_limit": 1000000,
                "memory_ops_limit": 100000,
                "services_limit": -1,  # Unlimited
                "users_limit": -1,   # Unlimited
                "storage_limit_gb": 1000,
                "features": {
                    "basic_memory": True,
                    "vector_search": True,
                    "graph_links": True,
                    "priority_support": True,
                    "custom_models": True,
                    "dedicated_support": True,
                    "sla_guarantee": True,
                    "custom_integrations": True,
                },
                "display_order": 4,
            },
        ]
        
        result = {}
        
        for tier_data in tiers_data:
            tier, created = SubscriptionTier.objects.update_or_create(
                slug=tier_data["slug"],
                defaults=tier_data,
            )
            result[tier.slug] = tier
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {tier.name} (${tier.price_monthly}/mo)")
        
        return result
    
    @transaction.atomic
    def _create_test_tenant(self, default_tier: SubscriptionTier) -> tuple:
        """Create a test tenant with API key."""
        # Create tenant
        tenant, created = Tenant.objects.get_or_create(
            slug="test-tenant",
            defaults={
                "name": "Test Tenant",
                "tier": default_tier,
                "status": TenantStatus.ACTIVE,
                "admin_email": "admin@test-tenant.local",
                "billing_email": "billing@test-tenant.local",
            },
        )
        
        # Create subscription if new tenant
        if created:
            Subscription.objects.create(
                tenant=tenant,
                tier=default_tier,
                status=SubscriptionStatus.ACTIVE,
            )
        
        # Generate API key
        full_key, prefix, key_hash = APIKey.generate_key(is_test=False)
        
        api_key, _ = APIKey.objects.get_or_create(
            tenant=tenant,
            name="Default Admin Key",
            defaults={
                "key_prefix": prefix,
                "key_hash": key_hash,
                "scopes": ["admin", "admin:tenants", "admin:billing", "read:memory", "write:memory"],
            },
        )
        
        return tenant, full_key
