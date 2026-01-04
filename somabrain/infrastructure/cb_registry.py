"""Central registry for the shared circuit breaker.

Provides a single CircuitBreaker instance so all services observe the same
failure state (memory service, sleep manager, health, etc.).
"""

from __future__ import annotations

from somabrain.infrastructure.circuit_breaker import CircuitBreaker
from django.conf import settings

_CB = CircuitBreaker(
    global_failure_threshold=settings.SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD,
    global_reset_interval=settings.SOMABRAIN_CIRCUIT_RESET_INTERVAL,
    global_cooldown_interval=settings.SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL,
)


def get_cb() -> CircuitBreaker:
    """Retrieve cb.
        """

    return _CB