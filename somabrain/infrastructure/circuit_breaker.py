"""Circuit Breaker pattern implementation with per-tenant support.

Supports both global (single instance) and per-tenant (multi-tenant) modes.
Per Requirements F2.1-F2.5 for per-tenant circuit isolation.

NO STUBS. NO MOCKS. NO HARDCODED RETURNS.
"""

import time
import logging
import types
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TenantCircuitState:
    """Circuit state for a single tenant."""

    failures: int = 0
    successes: int = 0
    last_failure_time: float = 0.0
    state: str = "CLOSED"  # CLOSED, OPEN, HALF-OPEN


@dataclass
class TenantCircuitConfig:
    """Per-tenant circuit-breaker thresholds and timing."""

    failure_threshold: Optional[int] = None
    recovery_timeout: Optional[float] = None


class CircuitBreaker:
    """Circuit Breaker with per-tenant isolation.

    Supports both:
    - Global mode: record_failure() / record_success() without tenant
    - Per-tenant mode: record_failure(tenant) / record_success(tenant)

    Per Requirements F2.1-F2.5:
    - F2.1: Each tenant has independent circuit state
    - F2.2: Tenant A open does not affect Tenant B
    - F2.3: Reset is per-tenant
    - F2.4: Recovery is per-tenant
    - F2.5: Metrics are labeled by tenant
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
        global_failure_threshold: Optional[int] = None,
        global_reset_interval: Optional[int] = None,
        global_cooldown_interval: Optional[int] = None,
    ):
        """Initialize CircuitBreaker.

        Args:
            name: Circuit breaker name for logging
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before transitioning to HALF-OPEN
            half_open_max_calls: Max calls in HALF-OPEN state (unused currently)
            global_failure_threshold: Override for failure_threshold (backwards compat)
            global_reset_interval: Override for recovery_timeout (backwards compat)
            global_cooldown_interval: Additional cooldown time (backwards compat)
        """
        self.name = name
        self.failure_threshold = (
            global_failure_threshold
            if global_failure_threshold is not None
            else failure_threshold
        )
        self.recovery_timeout = (
            global_reset_interval
            if global_reset_interval is not None
            else recovery_timeout
        )
        self.half_open_max_calls = half_open_max_calls

        # Apply cooldown if specified
        if global_cooldown_interval is not None:
            self.recovery_timeout = max(self.recovery_timeout, global_cooldown_interval)

        # Global state (backwards compatibility)
        self._global_state = TenantCircuitState()

        # Per-tenant states
        self._tenant_states: Dict[str, TenantCircuitState] = {}

        # Per-tenant configuration overrides
        self._tenant_configs: Dict[str, TenantCircuitConfig] = {}

    def _get_tenant_state(self, tenant: Optional[str]) -> TenantCircuitState:
        """Get or create state for a tenant. None = global."""
        if tenant is None:
            return self._global_state
        if tenant not in self._tenant_states:
            self._tenant_states[tenant] = TenantCircuitState()
        return self._tenant_states[tenant]

    def _failure_threshold_for(self, tenant: Optional[str]) -> int:
        """Return the failure threshold for *tenant*, falling back to global."""
        if tenant is not None:
            cfg = self._tenant_configs.get(tenant)
            if cfg is not None and cfg.failure_threshold is not None:
                return cfg.failure_threshold
        return self.failure_threshold

    def _recovery_timeout_for(self, tenant: Optional[str]) -> float:
        """Return the recovery timeout for *tenant*, falling back to global."""
        if tenant is not None:
            cfg = self._tenant_configs.get(tenant)
            if cfg is not None and cfg.recovery_timeout is not None:
                return cfg.recovery_timeout
        return self.recovery_timeout

    def allow_request(self, tenant: Optional[str] = None) -> bool:
        """Check if a request should be allowed.

        Args:
            tenant: Optional tenant ID. None uses global state.

        Returns:
            True if request is allowed, False if circuit is OPEN.
        """
        state = self._get_tenant_state(tenant)

        if state.state == "OPEN":
            if time.time() - state.last_failure_time > self._recovery_timeout_for(tenant):
                state.state = "HALF-OPEN"
                return True
            return False
        return True

    def is_open(self, tenant: Optional[str] = None) -> bool:
        """Check if circuit is open for a tenant.

        Args:
            tenant: Tenant ID. None checks global state.

        Returns:
            True if circuit is OPEN, False otherwise.
        """
        state = self._get_tenant_state(tenant)

        # Check for HALF-OPEN transition
        if state.state == "OPEN":
            if time.time() - state.last_failure_time > self._recovery_timeout_for(tenant):
                state.state = "HALF-OPEN"
                return False  # HALF-OPEN allows requests

        return state.state == "OPEN"

    def record_success(self, tenant: Optional[str] = None) -> None:
        """Record a successful operation.

        Args:
            tenant: Tenant ID. None uses global state.
        """
        state = self._get_tenant_state(tenant)
        state.successes += 1

        if state.state == "HALF-OPEN":
            state.state = "CLOSED"
            state.failures = 0
            logger.info(
                "Circuit %s closed for tenant %s after successful call",
                self.name,
                tenant or "global",
            )
        elif state.state == "CLOSED":
            state.failures = 0

    def record_failure(self, tenant: Optional[str] = None) -> None:
        """Record a failed operation.

        Args:
            tenant: Tenant ID. None uses global state.
        """
        state = self._get_tenant_state(tenant)
        state.failures += 1
        state.last_failure_time = time.time()

        threshold = self._failure_threshold_for(tenant)
        if state.failures >= threshold:
            state.state = "OPEN"
            logger.warning(
                "Circuit %s opened for tenant %s due to %d failures (threshold=%s)",
                self.name,
                tenant or "global",
                state.failures,
                threshold,
            )

    def reset(self, tenant: Optional[str] = None) -> None:
        """Reset circuit to CLOSED state.

        Args:
            tenant: Tenant ID. None resets global state.
        """
        state = self._get_tenant_state(tenant)
        state.failures = 0
        state.successes = 0
        state.last_failure_time = 0.0
        state.state = "CLOSED"
        logger.info("Circuit %s reset for tenant %s", self.name, tenant or "global")

    def get_stats(self, tenant: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a tenant's circuit.

        Args:
            tenant: Tenant ID. None gets global stats.

        Returns:
            Dict with failure_count, success_count, state, last_failure_time
        """
        state = self._get_tenant_state(tenant)
        return {
            "failure_count": state.failures,
            "success_count": state.successes,
            "state": state.state,
            "last_failure_time": state.last_failure_time,
            "tenant": tenant or "global",
        }

    def should_attempt_reset(self, tenant: Optional[str] = None) -> bool:
        """Return True if the circuit is ready for a half-open probe.

        A circuit is ready when it is OPEN and the recovery timeout has
        elapsed since the last failure. Callers should perform a health check
        and, if successful, invoke ``record_success(tenant)`` to close it.
        """
        state = self._get_tenant_state(tenant)
        if state.state != "OPEN":
            return False
        if state.last_failure_time <= 0.0:
            return False
        return time.time() - state.last_failure_time > self._recovery_timeout_for(tenant)

    def get_state(self, tenant: Optional[str] = None) -> Dict[str, Any]:
        """Return a circuit-state snapshot compatible with ``MemoryService``.

        The returned dict includes an ``open`` boolean, the current state
        label, failure/success counts, and the tenant identifier.
        """
        state = self._get_tenant_state(tenant)
        return {
            "open": state.state == "OPEN",
            "state": state.state,
            "failure_count": state.failures,
            "success_count": state.successes,
            "last_failure_time": state.last_failure_time,
            "tenant": tenant or "global",
        }

    def configure_tenant(
        self,
        tenant: str,
        *,
        failure_threshold: Optional[int] = None,
        reset_interval: Optional[float] = None,
    ) -> None:
        """Configure per-tenant circuit-breaker thresholds.

        Args:
            tenant: Tenant identifier.
            failure_threshold: Optional failure threshold override.
            reset_interval: Optional recovery timeout override (seconds).
        """
        if not tenant:
            raise ValueError("tenant must be a non-empty string")
        cfg = self._tenant_configs.get(tenant)
        if cfg is None:
            cfg = TenantCircuitConfig()
            self._tenant_configs[tenant] = cfg
        if failure_threshold is not None:
            cfg.failure_threshold = int(failure_threshold)
        if reset_interval is not None:
            cfg.recovery_timeout = float(reset_interval)
        # Ensure the tenant state record exists so discovery helpers work.
        self._get_tenant_state(tenant)

    @property
    def _circuit_open(self) -> types.MappingProxyType:
        """Read-only view of tenants whose circuits are currently OPEN.

        This property exists for backwards compatibility with callers that
        enumerate open circuits via ``breaker._circuit_open.keys()``.
        """
        return types.MappingProxyType(
            {
                tenant: state
                for tenant, state in self._tenant_states.items()
                if state.state == "OPEN"
            }
        )

    def call(
        self, func: Callable, *args, tenant: Optional[str] = None, **kwargs
    ) -> Any:
        """Execute a function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments for func
            tenant: Optional tenant ID for per-tenant circuit
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            RuntimeError: If circuit is OPEN
            Any exception from func (also records failure)
        """
        if not self.allow_request(tenant):
            raise RuntimeError(
                f"Circuit {self.name} is OPEN for tenant {tenant or 'global'}"
            )
        try:
            result = func(*args, **kwargs)
            self.record_success(tenant)
            return result
        except Exception:
            self.record_failure(tenant)
            raise
