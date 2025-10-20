from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class RateConfig:
    rps: float = 50.0
    burst: int = 100


class TokenBucket:
    def __init__(self, rps: float, burst: int):
        self.rate = float(rps)
        self.capacity = int(burst)
        self.tokens = float(burst)
        self.ts = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        dt = now - self.ts
        self.ts = now
        self.tokens = min(self.capacity, self.tokens + dt * self.rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimiter:
    def __init__(self, cfg: RateConfig):
        self.cfg = cfg
        self._buckets: Dict[str, TokenBucket] = {}

    def allow(self, key: str) -> bool:
        b = self._buckets.get(key)
        if b is None:
            b = TokenBucket(self.cfg.rps, self.cfg.burst)
            self._buckets[key] = b
        return b.allow()

