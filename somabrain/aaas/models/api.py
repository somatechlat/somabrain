"""
AAAS Models - API Keys.

API key management with secure hashing.
"""

import hashlib
import secrets
from uuid import uuid4

from django.db import models
from django.utils import timezone

from .enums import TenantStatus


class APIKey(models.Model):
    """
    API key for programmatic access.

    Format: sbk_live_a1b2c3... or sbk_test_a1b2c3...
    Key is stored as SHA-256 hash, only prefix is plaintext.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    tenant = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE, related_name="api_keys"
    )

    name = models.CharField(max_length=255)
    key_prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=64)

    scopes = models.JSONField(default=list, blank=True)

    rate_limit_override = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_test = models.BooleanField(default=False, help_text="Test mode key")

    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    usage_count = models.BigIntegerField(default=0)

    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "TenantUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_api_keys",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        "TenantUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_api_keys",
    )

    class Meta:
        """Meta configuration."""

        db_table = "aaas_api_keys"
        ordering = ["-created_at"]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["key_prefix", "key_hash"]),
        ]

    def __str__(self):
        """Return string representation."""
        return f"{self.name} ({self.key_prefix}...)"

    @classmethod
    def generate_key(cls, is_test: bool = False) -> tuple[str, str, str]:
        """Generate a new API key. Returns: (full_key, prefix, hash)."""
        mode = "test" if is_test else "live"
        random_part = secrets.token_hex(24)
        full_key = f"sbk_{mode}_{random_part}"
        prefix = f"sbk_{mode}_"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, prefix, key_hash

    @classmethod
    def verify_key(cls, full_key: str) -> "APIKey | None":
        """Verify an API key and return the APIKey object if valid."""
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        try:
            api_key = cls.objects.get(
                key_hash=key_hash,
                is_active=True,
                tenant__status__in=[TenantStatus.ACTIVE, TenantStatus.TRIAL],
            )
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
