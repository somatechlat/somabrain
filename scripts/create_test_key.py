
import os
import django
import hashlib
import uuid

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
django.setup()

from somabrain.aaas.models import Tenant, APIKey, TenantStatus

def create_key():
    # 1. Ensure Tenant exists
    tenant, created = Tenant.objects.get_or_create(
        slug="test-tenant",
        defaults={
            "name": "Test Tenant",
            "tier": "enterprise",
            "status": TenantStatus.ACTIVE
        }
    )
    if created:
        print(f"Created tenant: {tenant.id}")
    else:
        print(f"Using existing tenant: {tenant.id}")

    # 2. Create API Key
    # We want a predictable key for testing if possible, or we print it
    # APIKeyAuth expects "sbk_" prefix.
    # The Model hashes it. APIKeyAuth._verify_key hashes input and looks up.

    raw_key = "sbk_test_integration_key_12345"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Check if exists
    if APIKey.objects.filter(key_hash=key_hash).exists():
        print(f"Key already exists: {raw_key}")
        return

    api_key = APIKey.objects.create(
        tenant=tenant,
        name="Integration Test Key",
        key_prefix="sbk_test",
        key_hash=key_hash,
        scopes=["super-admin", "admin", "read:memory", "write:memory"],
        is_test=True,
        is_active=True
    )
    print(f"Created API Key: {raw_key}")

if __name__ == "__main__":
    create_key()
