"""Central registry for the shared circuit breaker.

Provides a single CircuitBreaker instance so all services observe the same
failure state (memory service, sleep manager, health, etc.).
"""

from __future__ import annotations

from somabrain.infrastructure.circuit_breaker import CircuitBreaker
from common.config.settings import settings

_CB = CircuitBreaker(
    global_failure_threshold=settings.circuit_failure_threshold,
    global_reset_interval=settings.circuit_reset_interval,
    global_cooldown_interval=settings.circuit_cooldown_interval,
)


def get_cb() -> CircuitBreaker:
    return _CB
