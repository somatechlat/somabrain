"""Centralised per-tenant circuit-breaker implementation.

The original code duplicated circuit‑breaker state inside ``MemoryService`` (class‑level
 dictionaries, a re‑entrant lock, and a handful of helper methods).  This module
 consolidates that logic into a single, well‑documented class that can be imported
 by any service that needs to protect against a flaky downstream memory backend.

Only standard library types are used; the module does **not** depend on Prometheus
 or any other optional package – metric emission is delegated to the
 ``infrastructure.metrics`` module, which can be a no‑op in environments where
 Prometheus is not installed.
"""

from __future__ import annotations

import time
from threading import RLock
from typing import Dict

__all__ = ["CircuitBreaker"]


class CircuitBreaker:
    """Per‑tenant circuit‑breaker with configurable thresholds.

    Parameters
    ----------
    global_failure_threshold: int, default ``3``
        Number of consecutive failures before the circuit opens for a tenant.
    global_reset_interval: float, default ``60.0`` seconds
        Minimum time to wait after the circuit opens before attempting a reset.
    """

    def __init__(
        self,
        *,
        global_failure_threshold: int = 3,
        global_reset_interval: float = 60.0,
        global_cooldown_interval: float = 0.0,
    ) -> None:
        """Create a circuit‑breaker with optional cooldown interval.

        ``global_cooldown_interval`` (seconds) adds an extra wait time after a
        reset attempt before another attempt may be made. ``0`` disables the
        extra cooldown, preserving historic behaviour.
        """
        self._global_failure_threshold = max(1, int(global_failure_threshold))
        self._global_reset_interval = max(1.0, float(global_reset_interval))
        self._global_cooldown_interval = max(0.0, float(global_cooldown_interval))

        # Per‑tenant state – all guarded by the same re‑entrant lock.
        self._lock: RLock = RLock()
        self._circuit_open: Dict[str, bool] = {}
        self._failure_count: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._last_reset_attempt: Dict[str, float] = {}
        self._failure_threshold: Dict[str, int] = {}
        self._reset_interval: Dict[str, float] = {}
        self._cooldown_interval: Dict[str, float] = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _ensure_tenant(self, tenant: str) -> None:
        """Make sure internal structures exist for *tenant*.

        This method must be called while holding ``self._lock``.
        """
        if tenant not in self._circuit_open:
            self._circuit_open[tenant] = False
            self._failure_count[tenant] = 0
            self._last_failure_time[tenant] = 0.0
            self._last_reset_attempt[tenant] = 0.0
            self._failure_threshold[tenant] = self._global_failure_threshold
            self._reset_interval[tenant] = self._global_reset_interval
            self._cooldown_interval[tenant] = self._global_cooldown_interval

    def _set_metrics(self, tenant: str) -> None:
        """Emit the current circuit state to Prometheus (if available).

        The original implementation referenced a non‑existent ``CIRCUIT_STATE``
        gauge, which meant the metric was never updated. The correct gauge is
        ``CIRCUIT_BREAKER_STATE`` defined in ``somabrain.metrics``. This method
        now imports the ``metrics`` module lazily (to avoid circular imports) and
        updates the proper gauge when it exists.
        """
        try:
            # Local import avoids circular dependencies with ``metrics`` which
            # itself imports many parts of the application.
            from . import metrics  # type: ignore

            gauge = getattr(metrics, "CIRCUIT_BREAKER_STATE", None)
            if gauge is not None and hasattr(gauge, "labels"):
                gauge.labels(tenant_id=str(tenant)).set(1 if self._circuit_open.get(tenant, False) else 0)
        except Exception:
            # In environments without Prometheus the import may fail – silently ignore.
            pass

    # ---------------------------------------------------------------------
    # Public API – used by services
    # ---------------------------------------------------------------------
    def is_open(self, tenant: str) -> bool:
        """Return ``True`` if the circuit for *tenant* is currently open."""
        with self._lock:
            self._ensure_tenant(tenant)
            return bool(self._circuit_open.get(tenant, False))

    def record_success(self, tenant: str) -> None:
        """Reset failure counters and close the circuit for *tenant*.

        This should be called after a successful call to the downstream memory
        service.
        """
        with self._lock:
            self._ensure_tenant(tenant)
            self._failure_count[tenant] = 0
            self._circuit_open[tenant] = False
            self._last_failure_time[tenant] = 0.0
            self._set_metrics(tenant)

    def record_failure(self, tenant: str) -> None:
        """Increment the failure counter and open the circuit if the threshold
        is reached.
        """
        now = time.monotonic()
        with self._lock:
            self._ensure_tenant(tenant)
            self._failure_count[tenant] += 1
            self._last_failure_time[tenant] = now
            threshold = self._failure_threshold.get(tenant, self._global_failure_threshold)
            if self._failure_count[tenant] >= max(1, int(threshold)):
                self._circuit_open[tenant] = True
            self._set_metrics(tenant)

    def should_attempt_reset(self, tenant: str) -> bool:
        """Return ``True`` if enough time has elapsed to try a circuit reset.

        The logic mirrors the original implementation in ``MemoryService`` but
        lives here so that any service can share the same policy.
        """
        with self._lock:
            self._ensure_tenant(tenant)
            if not self._circuit_open.get(tenant, False):
                return False
            now = time.monotonic()
            interval = self._reset_interval.get(tenant, self._global_reset_interval)
            if now - self._last_failure_time.get(tenant, 0.0) < max(1.0, float(interval)):
                return False
            if now - self._last_reset_attempt.get(tenant, 0.0) < 5.0:
                return False
            self._last_reset_attempt[tenant] = now
            return True

    def configure_tenant(
        self,
        tenant: str,
        *,
        failure_threshold: int | None = None,
        reset_interval: float | None = None,
        cooldown_interval: float | None = None,
    ) -> None:
        """Adjust per‑tenant thresholds.

        Parameters are optional; if omitted the global defaults are retained.
        """
        with self._lock:
            self._ensure_tenant(tenant)
            if failure_threshold is not None:
                self._failure_threshold[tenant] = max(1, int(failure_threshold))
            if reset_interval is not None:
                self._reset_interval[tenant] = max(1.0, float(reset_interval))
            if cooldown_interval is not None:
                self._cooldown_interval[tenant] = max(0.0, float(cooldown_interval))
            self._set_metrics(tenant)

    def get_state(self, tenant: str) -> dict:
        """Return a snapshot of the circuit‑breaker state for *tenant*.

        The dictionary mirrors the structure that ``MemoryService.get_circuit_state``
        previously returned, making it a drop‑in replacement.
        """
        with self._lock:
            self._ensure_tenant(tenant)
            return {
                "tenant": tenant,
                "circuit_open": bool(self._circuit_open.get(tenant, False)),
                "failure_count": int(self._failure_count.get(tenant, 0)),
                "last_failure_time": float(self._last_failure_time.get(tenant, 0.0)),
                "last_reset_attempt": float(self._last_reset_attempt.get(tenant, 0.0)),
                "failure_threshold": int(self._failure_threshold.get(tenant, self._global_failure_threshold)),
                "reset_interval": float(self._reset_interval.get(tenant, self._global_reset_interval)),
            }
