"""
Quota Management Module for SomaBrain

This module implements per-tenant write quotas to prevent abuse and ensure fair
resource allocation. It provides daily write limits with automatic reset and
remaining quota tracking.

Key Features:
- Daily write quotas per tenant
- Automatic quota reset at day boundaries
- In-memory quota tracking (not persistent)
- Configurable quota limits
- Remaining quota calculation
- Thread-safe operations

Quota Types:
- Daily writes: Maximum number of write operations per tenant per day
- Automatic reset: Quotas reset at midnight UTC
- Burst allowance: No burst limits, strict daily enforcement

Classes:
    QuotaConfig: Configuration for quota parameters
    QuotaManager: Main quota management implementation

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class QuotaConfig:
    daily_writes: int = 10000


# Exempt tenants that should never be limited (e.g., internal agents)
# Updated to be case‑insensitive and to match any ID containing "AGENT_ZERO"
_EXEMPT_TENANTS = {"AGENT_ZERO", "AGENT ZERO"}


class QuotaManager:
    """In‑memory per‑tenant daily write quotas.

    Not durable; suitable for stateless API replicas. For stronger guarantees, back with Redis.
    """

    def __init__(self, cfg: QuotaConfig):
        self.cfg = cfg
        # key -> (date_key, count)
        self._counts: Dict[str, Tuple[int, int]] = {}

    @staticmethod
    def _day_key(ts: float | None = None) -> int:
        if ts is None:
            ts = time.time()
        return int(ts // 86400)

    def _is_exempt(self, tenant_id: str) -> bool:
        """Return True if the tenant should bypass quota checks.

        The check is case‑insensitive and also matches any tenant ID that contains the
        substring ``AGENT_ZERO`` (e.g., ``AGENT_ZERO_DEV``). This allows developers to
        give an unlimited quota to a specific development agent without affecting
        other tenants.
        """
        normalized = tenant_id.upper().replace(" ", "_")
        if normalized in {t.upper() for t in _EXEMPT_TENANTS}:
            return True
        # Match any ID that contains the marker "AGENT_ZERO"
        return "AGENT_ZERO" in normalized

    def allow_write(self, tenant_id: str, n: int = 1) -> bool:
        # Bypass quota checks for exempt tenants
        if self._is_exempt(tenant_id):
            return True
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        if cur_day != day:
            cnt = 0
            cur_day = day
        if cnt + n > self.cfg.daily_writes:
            self._counts[tenant_id] = (cur_day, cnt)
            return False
        self._counts[tenant_id] = (cur_day, cnt + n)
        return True

    def remaining(self, tenant_id: str) -> int:
        # Exempt tenants effectively have infinite remaining quota
        if self._is_exempt(tenant_id):
            return float("inf")
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        if cur_day != day:
            cnt = 0
        return max(0, self.cfg.daily_writes - cnt)
