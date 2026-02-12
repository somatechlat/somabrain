"""Circuit Breaker pattern implementation with per-tenant support.

Supports both global (single instance) and per-tenant (multi-tenant) modes.
Per Requirements F2.1-F2.5 for per-tenant circuit isolation.

NO STUBS. NO MOCKS. NO HARDCODED RETURNS.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TenantCircuitState:
    """Circuit state for a single tenant."""

    failures: int = 0
    successes: int = 0
    last_failure_time: float = 0.0
    state: str = "CLOSED"  # CLOSED, OPEN, HALF-OPEN


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

    def _get_tenant_state(self, tenant: Optional[str]) -> TenantCircuitState:
        """Get or create state for a tenant. None = global."""
        if tenant is None:
            return self._global_state
        if tenant not in self._tenant_states:
            self._tenant_states[tenant] = TenantCircuitState()
        return self._tenant_states[tenant]

    def allow_request(self, tenant: Optional[str] = None) -> bool:
        """Check if a request should be allowed.

        Args:
            tenant: Optional tenant ID. None uses global state.

        Returns:
            True if request is allowed, False if circuit is OPEN.
        """
        state = self._get_tenant_state(tenant)

        if state.state == "OPEN":
            if time.time() - state.last_failure_time > self.recovery_timeout:
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
            if time.time() - state.last_failure_time > self.recovery_timeout:
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

        if state.failures >= self.failure_threshold:
            state.state = "OPEN"
            logger.warning(
                "Circuit %s opened for tenant %s due to %d failures",
                self.name,
                tenant or "global",
                state.failures,
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

    def call(self, func: Callable, *args, tenant: Optional[str] = None, **kwargs) -> Any:
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

