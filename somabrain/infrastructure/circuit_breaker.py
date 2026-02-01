import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Basic Circuit Breaker pattern implementation.
    """
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        global_failure_threshold: int | None = None,
        global_reset_interval: int | None = None,
        global_cooldown_interval: int | None = None,
    ):
        self.name = name
        self.failure_threshold = global_failure_threshold if global_failure_threshold is not None else failure_threshold
        # reset_interval usually means recovery timeout
        self.recovery_timeout = global_reset_interval if global_reset_interval is not None else recovery_timeout
        # cooldown might be used for half-open state or same as recovery
        if global_cooldown_interval is not None:
             self.recovery_timeout = max(self.recovery_timeout, global_cooldown_interval)

        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def allow_request(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                return True
            return False
        return True

    def record_success(self):
        if self.state == "HALF-OPEN":
            self.state = "CLOSED"
            self.failures = 0
        elif self.state == "CLOSED":
            self.failures = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit {self.name} opened due to {self.failures} failures")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if not self.allow_request():
            raise RuntimeError(f"Circuit {self.name} is OPEN")
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise
