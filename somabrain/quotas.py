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
from datetime import datetime, timezone
from typing import Dict, Tuple, List, Optional, Any

from .tenant_manager import get_tenant_manager


@dataclass
class QuotaInfo:
    """Information about a tenant's quota status."""
    tenant_id: str
    daily_limit: int
    remaining: int
    used_today: int
    reset_at: Optional[datetime] = None
    is_exempt: bool = False


@dataclass
class QuotaConfig:
    daily_writes: int = 10000


class QuotaManager:
    """In‑memory per‑tenant daily write quotas with centralized tenant management.

    Not durable; suitable for stateless API replicas. For stronger guarantees, back with Redis.
    Now integrates with TenantManager for dynamic tenant-specific quota management.
    """

    def __init__(self, cfg: QuotaConfig):
        self.cfg = cfg
        # key -> (date_key, count)
        self._counts: Dict[str, Tuple[int, int]] = {}
        self._tenant_manager = None  # Lazy initialization

    @staticmethod
    def _day_key(ts: float | None = None) -> int:
        if ts is None:
            ts = time.time()
        return int(ts // 86400)

    async def _get_tenant_manager(self):
        """Get tenant manager instance with lazy initialization."""
        if self._tenant_manager is None:
            self._tenant_manager = await get_tenant_manager()
        return self._tenant_manager

    async def _is_exempt(self, tenant_id: str) -> bool:
        """Return True if the tenant should bypass quota checks.

        Now uses centralized tenant management for dynamic exempt tenant detection.
        Supports both system-defined exempt tenants and tenant-specific configurations.
        """
        try:
            tenant_manager = await self._get_tenant_manager()
            return await tenant_manager.is_exempt_tenant(tenant_id)
        except Exception:
            # Fallback to legacy behavior for backward compatibility
            # This will be removed in a future version
            return "agent_zero" in tenant_id.lower()

    async def allow_write(self, tenant_id: str, n: int = 1) -> bool:
        # Bypass quota checks for exempt tenants
        if await self._is_exempt(tenant_id):
            return True
        
        # Get tenant-specific quota limit
        tenant_limit = await self._get_tenant_quota_limit(tenant_id)
        
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

    async def remaining(self, tenant_id: str) -> int:
        # Exempt tenants effectively have infinite remaining quota
        if await self._is_exempt(tenant_id):
            return float("inf")
        
        # Get tenant-specific quota limit
        tenant_limit = await self._get_tenant_quota_limit(tenant_id)
        
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        if cur_day != day:
            cnt = 0
        return max(0, tenant_limit - cnt)

    async def tenant_exists(self, tenant_id: str) -> bool:
        """Check if a tenant has any quota records.
        
        Returns True if the tenant has existing quota records or is exempt.
        """
        # Exempt tenants always "exist"
        if await self._is_exempt(tenant_id):
            return True
        # Check if tenant has quota records
        return tenant_id in self._counts

    async def get_quota_info(self, tenant_id: str) -> QuotaInfo:
        """Get detailed quota information for a tenant."""
        is_exempt = await self._is_exempt(tenant_id)
        tenant_limit = await self._get_tenant_quota_limit(tenant_id)
        
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        
        # If day has changed, reset count
        if cur_day != day:
            cnt = 0
            
        # Calculate reset time (next midnight UTC)
        now = datetime.now(timezone.utc)
        reset_time = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
        reset_time = reset_time.replace(day=now.day + 1)  # Next day
        
        return QuotaInfo(
            tenant_id=tenant_id,
            daily_limit=tenant_limit,
            remaining=float("inf") if is_exempt else max(0, tenant_limit - cnt),
            used_today=cnt,
            reset_at=reset_time,
            is_exempt=is_exempt
        )

    async def get_all_quotas(self) -> List[QuotaInfo]:
        """Get quota information for all tenants."""
        quotas = []
        
        # Add all tenants with existing quota records
        for tenant_id in self._counts.keys():
            quota_info = await self.get_quota_info(tenant_id)
            quotas.append(quota_info)
            
        return quotas

    async def reset_quota(self, tenant_id: str) -> bool:
        """Reset quota counter for a specific tenant.
        
        Returns True if reset was successful, False if tenant not found.
        """
        tenant_exists = await self.tenant_exists(tenant_id)
        is_exempt = await self._is_exempt(tenant_id)
        
        if not tenant_exists and not is_exempt:
            return False
            
        # Reset the quota counter for today
        day = self._day_key()
        self._counts[tenant_id] = (day, 0)
        return True

    async def adjust_quota_limit(self, tenant_id: str, new_limit: int) -> bool:
        """Adjust the daily quota limit for a specific tenant.
        
        Updates tenant-specific quota configuration through the tenant manager.
        For global limits, use the configuration system.
        
        Returns True if adjustment was successful.
        """
        if new_limit <= 0:
            return False
            
        try:
            tenant_manager = await self._get_tenant_manager()
            tenant_config = await tenant_manager.get_tenant_config(tenant_id)
            
            # Update tenant-specific quota limit
            tenant_config["quota"] = tenant_config.get("quota", {})
            tenant_config["quota"]["daily_quota"] = new_limit
            
            # Save updated configuration
            await tenant_manager.update_tenant_config(tenant_id, tenant_config)
            return True
            
        except Exception:
            return False
    
    async def _get_tenant_quota_limit(self, tenant_id: str) -> int:
        """Get tenant-specific quota limit."""
        try:
            tenant_manager = await self._get_tenant_manager()
            quota_config = await tenant_manager.get_tenant_quota_config(tenant_id)
            return quota_config.get("daily_quota", self.cfg.daily_writes)
        except Exception:
            # Fallback to global configuration
            return self.cfg.daily_writes
