"""Central registry for the shared circuit breaker.

Provides a single CircuitBreaker instance so all services observe the same
failure state (memory service, sleep manager, health, etc.).
"""

from __future__ import annotations

from functools import lru_cache

from somabrain.infrastructure.circuit_breaker import CircuitBreaker


@lru_cache(maxsize=1)
def _build_cb() -> CircuitBreaker:
    """Construct the shared circuit breaker lazily.

    Accessing Django settings at import time breaks unit-test collection and
    any module import that happens before pytest-django configures settings.
    """
    from django.conf import settings

    return CircuitBreaker(
        global_failure_threshold=settings.SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD,
        global_reset_interval=settings.SOMABRAIN_CIRCUIT_RESET_INTERVAL,
        global_cooldown_interval=settings.SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL,
    )


def get_cb() -> CircuitBreaker:
    """Return the shared circuit breaker instance for the current process."""
    return _build_cb()
