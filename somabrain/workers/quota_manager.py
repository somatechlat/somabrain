"""Per-tenant quota management for outbox processing.

Extracted from outbox_publisher.py per monolithic-decomposition spec.
Provides TenantQuotaManager for rate limiting and backpressure.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from django.conf import settings


# Per-tenant quota configuration
PER_TENANT_QUOTA_LIMIT = max(
    1,
    int(getattr(settings, "outbox_tenant_quota_limit", 1000) or 1000),
)

PER_TENANT_QUOTA_WINDOW = max(
    1,
    int(getattr(settings, "outbox_tenant_quota_window", 60) or 60),
)


class TenantQuotaManager:
    """Manages per-tenant processing quotas and backpressure."""

    def __init__(self, quota_limit: int, quota_window: int):
        """Initialize the instance."""

        self.quota_limit = quota_limit
        self.quota_window = quota_window
        self.tenant_usage: dict[str, list[float]] = {}  # tenant -> list of timestamps
        self.tenant_backoff: dict[str, float] = {}  # tenant -> backoff until timestamp
        self._lock = threading.RLock()

    def can_process(self, tenant_id: str, count: int = 1) -> bool:
        """Check if tenant can process requested number of events.

        Args:
            tenant_id: The tenant identifier
            count: Number of events to process

        Returns:
            True if within quota, False if would exceed quota
        """
        with self._lock:
            now = time.time()
            tenant = tenant_id or "default"

            # Check if tenant is in backoff
            backoff_until = self.tenant_backoff.get(tenant, 0.0)
            if now < backoff_until:
                return False

            # Clean old usage records
            usage_times = self.tenant_usage.get(tenant, [])
            cutoff_time = now - self.quota_window
            recent_usage = [t for t in usage_times if t > cutoff_time]

            # Check quota
            if len(recent_usage) + count > self.quota_limit:
                # Apply backoff
                backoff_duration = min(self.quota_window, max(5.0, self.quota_window * 0.1))
                self.tenant_backoff[tenant] = now + backoff_duration
                return False

            return True

    def record_usage(self, tenant_id: str, count: int = 1) -> None:
        """Record processing usage for a tenant.

        Args:
            tenant_id: The tenant identifier
            count: Number of events processed
        """
        with self._lock:
            now = time.time()
            tenant = tenant_id or "default"

            # Record usage
            if tenant not in self.tenant_usage:
                self.tenant_usage[tenant] = []

            for _ in range(count):
                self.tenant_usage[tenant].append(now)

            # Clear backoff on successful processing
            if tenant in self.tenant_backoff:
                del self.tenant_backoff[tenant]

    def get_usage_stats(self) -> dict[str, dict[str, Any]]:
        """Get current usage statistics for all tenants.

        Returns:
            Dict mapping tenant IDs to their usage statistics
        """
        with self._lock:
            now = time.time()
            stats = {}
            cutoff_time = now - self.quota_window

            for tenant, usage_times in self.tenant_usage.items():
                recent_usage = [t for t in usage_times if t > cutoff_time]
                backoff_until = self.tenant_backoff.get(tenant, 0.0)

                stats[tenant] = {
                    "current_usage": len(recent_usage),
                    "quota_limit": self.quota_limit,
                    "usage_ratio": len(recent_usage) / self.quota_limit,
                    "in_backoff": now < backoff_until,
                    "backoff_remaining": max(0.0, backoff_until - now),
                }

            return stats

    def cleanup_old_tenants(self, max_age: float = 300.0) -> None:
        """Clean up old tenant data to prevent memory leaks.

        Args:
            max_age: Maximum age in seconds for tenant data
        """
        with self._lock:
            now = time.time()
            cutoff_time = now - max_age

            # Clean old usage records
            for tenant in list(self.tenant_usage.keys()):
                usage_times = self.tenant_usage[tenant]
                recent_usage = [t for t in usage_times if t > cutoff_time]

                if not recent_usage:
                    del self.tenant_usage[tenant]
                    if tenant in self.tenant_backoff:
                        del self.tenant_backoff[tenant]
                else:
                    self.tenant_usage[tenant] = recent_usage


# Global quota manager instance
_quota_manager: Optional[TenantQuotaManager] = None


def get_quota_manager() -> TenantQuotaManager:
    """Get or create the global quota manager instance."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = TenantQuotaManager(PER_TENANT_QUOTA_LIMIT, PER_TENANT_QUOTA_WINDOW)
    return _quota_manager


def reset_quota_manager() -> None:
    """Reset the global quota manager (for testing)."""
    global _quota_manager
    _quota_manager = None
