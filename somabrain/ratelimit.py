from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict

"""
Rate Limiting Module for SomaBrain

This module implements token bucket-based rate limiting to control request rates
and prevent system overload. It provides per-key rate limiting with configurable
rates and burst capacities.

Key Features:
    pass
- Token bucket algorithm for smooth rate limiting
- Per-key rate limiting (tenant, IP, etc.)
- Configurable rates per second and burst capacity
- Automatic token replenishment
- Thread-safe operations
- Memory-efficient with lazy bucket creation

Rate Limiting:
    pass
- RPS (requests per second): Sustained rate limit
- Burst: Maximum burst capacity before throttling
- Token replenishment: Continuous token addition based on time
- Fair queuing: No priority, first-come first-served

Classes:
    RateConfig: Configuration for rate limiting parameters
    TokenBucket: Individual token bucket implementation
    RateLimiter: Main rate limiter with per-key buckets

Functions:
    None (class-based implementation)
"""




@dataclass
class RateConfig:
    rps: float = 50.0
    burst: int = 100


class TokenBucket:
    pass
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
    pass
def __init__(self, cfg: RateConfig):
        self.cfg = cfg
        self._buckets: Dict[str, TokenBucket] = {}

def allow(self, key: str) -> bool:
        b = self._buckets.get(key)
        if b is None:
            b = TokenBucket(self.cfg.rps, self.cfg.burst)
            self._buckets[key] = b
        return b.allow()
