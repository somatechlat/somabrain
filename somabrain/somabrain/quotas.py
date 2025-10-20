from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class QuotaConfig:
    daily_writes: int = 10000


class QuotaManager:
    """In-memory per-tenant daily write quotas.

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

    def allow_write(self, tenant_id: str, n: int = 1) -> bool:
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
        day = self._day_key()
        cur_day, cnt = self._counts.get(tenant_id, (day, 0))
        if cur_day != day:
            cnt = 0
        return max(0, self.cfg.daily_writes - cnt)

