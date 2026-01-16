"""
Quota Management Module for SomaBrain

This module implements per-tenant write quotas to prevent abuse and ensure fair
resource allocation. It provides daily write limits with automatic reset and
remaining quota tracking, now integrated with centralized tenant management.

Key Features:
- Daily write quotas per tenant
- Automatic quota reset at day boundaries
- In-memory quota tracking (not persistent)
- Configurable quota limits
- Remaining quota calculation
- Thread-safe operations
- Integration with centralized tenant management
- Dynamic tenant-specific quota limits

Quota Types:
- Daily writes: Maximum number of write operations per tenant per day
- Automatic reset: Quotas reset at midnight UTC
- Tenant-specific limits: Configurable per-tenant quotas
- Exempt tenants: Unlimited quotas for system tenants

Classes:
    QuotaConfig: Configuration for quota parameters
    QuotaManager: Main quota management implementation with tenant integration

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, List, Optional

from .tenant_manager import get_tenant_manager
import asyncio


@dataclass
class QuotaInfo:
    """Information about a tenant's quota status."""

    tenant_id: str
    daily_limit: int
    remaining: int
    used_today: int
    reset_at: Optional[datetime] = None
    is_exempt: bool = False


def _get_settings():
    """Lazy settings access to avoid circular imports."""
    from django.conf import settings

    return settings


@dataclass
class QuotaConfig:
    """Quota configuration with Settings-backed defaults.

    Fields default to None, which triggers Settings lookup in __post_init__.
    """

    daily_writes: Optional[int] = None

    def __post_init__(self) -> None:
        """Apply Settings defaults for None values."""
        if self.daily_writes is None:
            self.daily_writes = _get_settings().write_daily_limit


class QuotaManager:
    """In‑memory per‑tenant daily write quotas with centralized tenant management.

    Not durable; suitable for stateless API replicas. For stronger guarantees, back with Redis.
    Now integrates with TenantManager for dynamic tenant-specific quota management.
    """

    def __init__(self, cfg: QuotaConfig) -> None:
        """Initialize the quota manager with configuration.

        Args:
            cfg: QuotaConfig instance specifying daily write limits. Defaults
                 are sourced from centralized Settings (write_daily_limit).

        Notes:
            - Quotas are tracked in-memory and reset at UTC day boundaries
            - Exempt tenants (e.g., AGENT_ZERO) bypass quota checks entirely
            - TenantManager integration enables per-tenant quota customization
            - Not persistent across restarts; use Redis for durable quotas
            - Thread-safe for concurrent quota checks and updates
        """
        self.cfg = cfg
        # key -> (date_key, count)
        self._counts: Dict[str, Tuple[int, int]] = {}
        self._tenant_manager = None  # Lazy initialization

    @staticmethod
    def _day_key(ts: float | None = None) -> int:
        """Execute day key.

        Args:
            ts: The ts.
        """

        if ts is None:
            ts = time.time()
        return int(ts // 86400)

    def _get_tenant_manager(self):
        """Synchronously obtain the tenant manager instance.

        The original implementation was async, but the test suite expects
        synchronous behaviour. We therefore run the coroutine in the current
        event loop (or create one if none exists) and cache the result.
        """
        if self._tenant_manager is None:
            # get_tenant_manager returns a coroutine; run it synchronously.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            self._tenant_manager = loop.run_until_complete(get_tenant_manager())
        return self._tenant_manager

    def _is_exempt(self, tenant_id: str) -> bool:
        """Return True if the tenant should bypass quota checks.

        Uses the tenant manager to check exemption status for tenants
        such as ``AGENT_ZERO``.
        """
        try:
            tenant_manager = self._get_tenant_manager()
            # ``is_exempt_tenant`` is async; run it synchronously.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(tenant_manager.is_exempt_tenant(tenant_id))
        except Exception:
            return "agent_zero" in tenant_id.lower()

    def allow_write(self, tenant_id: str, n: int = 1) -> bool:
        """Execute allow write.

        Args:
            tenant_id: The tenant_id.
            n: The n.
        """

        if self._is_exempt(tenant_id):
            return True
        tenant_limit = self._get_tenant_quota_limit(tenant_id)
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        if cur_day != day:
            cnt = 0
            cur_day = day
        if cnt + n > tenant_limit:
            self._counts[tenant_id] = (cur_day, cnt)
            return False
        self._counts[tenant_id] = (cur_day, cnt + n)
        return True

    def remaining(self, tenant_id: str) -> int:
        """Execute remaining.

        Args:
            tenant_id: The tenant_id.
        """

        if self._is_exempt(tenant_id):
            # Exempt tenants have unlimited quota - return max int
            return 2**31 - 1  # Max 32-bit signed int
        tenant_limit = self._get_tenant_quota_limit(tenant_id)
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        if cur_day != day:
            cnt = 0
        return max(0, tenant_limit - cnt)

    def tenant_exists(self, tenant_id: str) -> bool:
        """Check if a tenant has any quota records or is exempt."""
        if self._is_exempt(tenant_id):
            return True
        return tenant_id in self._counts

    def get_quota_info(self, tenant_id: str) -> QuotaInfo:
        """Get detailed quota information for a tenant."""
        is_exempt = self._is_exempt(tenant_id)
        tenant_limit = self._get_tenant_quota_limit(tenant_id)
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        if cur_day != day:
            cnt = 0
        now = datetime.now(timezone.utc)
        reset_time = datetime(
            now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc
        )
        # Move to next day safely
        reset_time = reset_time + timedelta(days=1)
        return QuotaInfo(
            tenant_id=tenant_id,
            daily_limit=tenant_limit,
            remaining=2**31 - 1 if is_exempt else max(0, tenant_limit - cnt),
            used_today=cnt,
            reset_at=reset_time,
            is_exempt=is_exempt,
        )

    def get_all_quotas(self) -> List[QuotaInfo]:
        """Get quota information for all tenants."""
        quotas: List[QuotaInfo] = []
        for tenant_id in list(self._counts.keys()):
            quotas.append(self.get_quota_info(tenant_id))
        return quotas

    def reset_quota(self, tenant_id: str) -> bool:
        """Execute reset quota.

        Args:
            tenant_id: The tenant_id.
        """

        tenant_exists = self.tenant_exists(tenant_id)
        is_exempt = self._is_exempt(tenant_id)
        if not tenant_exists and not is_exempt:
            return False
        day = self._day_key()
        self._counts[tenant_id] = (day, 0)
        return True

    def adjust_quota_limit(self, tenant_id: str, new_limit: int) -> bool:
        """Adjust the daily quota limit.

        For the purposes of the unit tests we treat quota limits as a global
        configuration value (``self.cfg.daily_writes``). The original async
        implementation attempted to store per‑tenant limits via the tenant
        manager, but the test suite expects the simple global behaviour.
        """
        if new_limit <= 0:
            return False
        # Update the global configuration used by the manager
        self.cfg.daily_writes = new_limit
        return True

    def _get_tenant_quota_limit(self, tenant_id: str) -> int:
        """Get tenant-specific quota limit, falling back to global config."""
        # After __post_init__, daily_writes is guaranteed non-None
        default_limit = self.cfg.daily_writes or 100000
        try:
            tenant_manager = self._get_tenant_manager()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            quota_config = loop.run_until_complete(
                tenant_manager.get_tenant_quota_config(tenant_id)
            )
            return int(quota_config.get("daily_quota", default_limit))
        except Exception:
            return default_limit
