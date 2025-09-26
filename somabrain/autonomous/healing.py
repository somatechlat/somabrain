"""
Autonomous Healing for SomaBrain.

This module provides self-healing capabilities for autonomous operations,
including automatic recovery from failures, circuit breaker management,
and system restoration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# use central prometheus helpers via somabrain.metrics
from .. import audit, metrics as app_metrics
from .config import AutonomousConfig

logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """Status of a recovery operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class RecoveryAction:
    """A recovery action to be executed."""

    action_id: str
    description: str
    execute_func: Callable
    rollback_func: Optional[Callable] = None
    timeout_seconds: int = 300
    priority: int = 1  # 1-10, 10 is highest priority
    dependencies: List[str] = field(default_factory=list)


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""

    action_id: str
    status: RecoveryStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class CircuitBreakerManager:
    """Manages circuit breakers for autonomous healing."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.recovery_history: List[RecoveryResult] = []
        # Use central application registry helpers (get-or-create)
        self.circuit_open_counter = app_metrics.get_counter(
            "soma_circuit_opened_total", "Circuit breakers opened"
        )
        self.circuit_reset_counter = app_metrics.get_counter(
            "soma_circuit_reset_total", "Circuit breakers reset/closed"
        )
        self.circuit_half_open_counter = app_metrics.get_counter(
            "soma_circuit_half_open_total", "Circuit breakers half-open"
        )

    def register_circuit_breaker(
        self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60
    ) -> None:
        """Register a circuit breaker."""
        self.circuit_breakers[name] = {
            "failure_count": 0,
            "last_failure_time": None,
            "state": "closed",  # 'closed', 'open', 'half_open'
            "failure_threshold": failure_threshold,
            "recovery_timeout": recovery_timeout,
            "recovery_action": None,
        }
        logger.info(f"Registered circuit breaker: {name}")

    def record_failure(self, name: str) -> None:
        """Record a failure for a circuit breaker."""
        if name not in self.circuit_breakers:
            logger.warning(f"Circuit breaker {name} not registered")
            return

        cb = self.circuit_breakers[name]
        cb["failure_count"] += 1
        cb["last_failure_time"] = datetime.now()

        # Check if we should open the circuit
        if cb["failure_count"] >= cb["failure_threshold"]:
            cb["state"] = "open"
            logger.warning(
                f"Circuit breaker {name} opened due to {cb['failure_count']} failures"
            )
            try:
                self.circuit_open_counter.inc()
            except Exception:
                pass

            # If a recovery orchestrator is wired and a recovery_action is configured, trigger it
            ra = cb.get("recovery_action")
            if (
                ra
                and hasattr(self, "recovery_orchestrator")
                and self.recovery_orchestrator
            ):
                try:
                    logger.info(f"Triggering recovery action {ra} for circuit {name}")
                    # audit the auto-trigger
                    try:
                        audit.log_admin_action(
                            request=type(
                                "R",
                                (),
                                {
                                    "url": type(
                                        "U", (), {"path": f"/autonomous/circuit/{name}"}
                                    ),
                                    "method": "AUTO",
                                    "client": type("C", (), {"host": "localhost"}),
                                    "headers": {},
                                },
                            )(),
                            action="circuit_auto_trigger",
                            details={"circuit": name, "recovery_action": ra},
                        )
                    except Exception:
                        pass
                    self.recovery_orchestrator.trigger_recovery(ra)
                except Exception as e:
                    logger.error(
                        f"Failed to trigger recovery action {ra} for circuit {name}: {e}"
                    )

    def check_circuit_state(self, name: str) -> str:
        """Check the state of a circuit breaker."""
        if name not in self.circuit_breakers:
            return "unknown"

        cb = self.circuit_breakers[name]

        # If circuit is open, check if we should try to close it
        if cb["state"] == "open" and cb["last_failure_time"]:
            time_since_failure = datetime.now() - cb["last_failure_time"]
            if time_since_failure.total_seconds() > cb["recovery_timeout"]:
                cb["state"] = "half_open"
                logger.info(f"Circuit breaker {name} moved to half-open state")
                try:
                    self.circuit_half_open_counter.inc()
                except Exception:
                    pass

        return cb["state"]

    def reset_circuit(self, name: str) -> bool:
        """Reset a circuit breaker."""
        if name not in self.circuit_breakers:
            logger.warning(f"Circuit breaker {name} not registered")
            return False

        cb = self.circuit_breakers[name]
        cb["failure_count"] = 0
        cb["last_failure_time"] = None
        cb["state"] = "closed"
        logger.info(f"Circuit breaker {name} reset")
        try:
            self.circuit_reset_counter.inc()
        except Exception:
            pass
        try:
            audit.log_admin_action(
                request=type(
                    "R",
                    (),
                    {
                        "url": type(
                            "U", (), {"path": f"/autonomous/circuit/{name}/reset"}
                        ),
                        "method": "AUTO",
                        "client": type("C", (), {"host": "localhost"}),
                        "headers": {},
                    },
                )(),
                action="circuit_reset",
                details={"circuit": name},
            )
        except Exception:
            pass
        return True

    def set_recovery_orchestrator(self, orchestrator: "RecoveryOrchestrator") -> None:
        """Wire a RecoveryOrchestrator so the circuit manager can trigger recovery actions."""
        self.recovery_orchestrator = orchestrator

    def set_recovery_action_for_cb(self, name: str, action_id: str) -> None:
        """Associate a recovery action id with a circuit breaker."""
        if name in self.circuit_breakers:
            self.circuit_breakers[name]["recovery_action"] = action_id

    def probe_and_reset(self, name: str, probe_func: Callable[[], bool]) -> bool:
        """When circuit is half-open, run probe_func; if it returns True reset the circuit, else reopen it.

        Returns True if reset performed, False otherwise.
        """
        if name not in self.circuit_breakers:
            return False
        cb = self.circuit_breakers[name]
        if cb["state"] != "half_open":
            return False

        try:
            ok = probe_func()
        except Exception:
            ok = False

        if ok:
            self.reset_circuit(name)
            return True
        else:
            # return to open and update last failure time
            cb["state"] = "open"
            cb["last_failure_time"] = datetime.now()
            try:
                audit.log_admin_action(
                    request=type(
                        "R",
                        (),
                        {
                            "url": type(
                                "U",
                                (),
                                {"path": f"/autonomous/circuit/{name}/probe_failed"},
                            ),
                            "method": "AUTO",
                            "client": type("C", (), {"host": "localhost"}),
                            "headers": {},
                        },
                    )(),
                    action="circuit_probe_failed",
                    details={"circuit": name},
                )
            except Exception:
                pass
            return False

    def auto_probe_all(self, probe_map: Dict[str, Callable[[], bool]]) -> int:
        """Probe all half-open circuits using provided probe map and attempt resets.

        probe_map: dict of circuit_name -> probe callable
        Returns number of circuits reset.
        """
        reset_count = 0
        for name, cb in self.circuit_breakers.items():
            if cb["state"] == "half_open" and name in probe_map:
                if self.probe_and_reset(name, probe_map[name]):
                    reset_count += 1
        return reset_count


class RecoveryOrchestrator:
    """Orchestrates recovery actions for autonomous healing."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        self.pending_actions: List[str] = []
        self.running_actions: List[str] = []
        self.completed_actions: List[RecoveryResult] = []
        # Recovery metrics
        self.recovery_attempts_counter = app_metrics.get_counter(
            "soma_recovery_attempts_total", "Total recovery attempts"
        )
        self.recovery_success_counter = app_metrics.get_counter(
            "soma_recovery_success_total", "Successful recoveries"
        )
        self.recovery_failure_counter = app_metrics.get_counter(
            "soma_recovery_failure_total", "Failed recoveries"
        )
        self.recovery_rollback_counter = app_metrics.get_counter(
            "soma_recovery_rollback_total", "Recovery rollbacks performed"
        )

    def register_recovery_action(self, action: RecoveryAction) -> None:
        """Register a recovery action."""
        self.recovery_actions[action.action_id] = action
        logger.info(f"Registered recovery action: {action.action_id}")

    def trigger_recovery(self, action_id: str) -> Optional[RecoveryResult]:
        """Trigger a specific recovery action."""
        if action_id not in self.recovery_actions:
            logger.error(f"Recovery action {action_id} not registered")
            return None

        action = self.recovery_actions[action_id]

        # Safety gating: require human oversight for critical actions if enabled
        try:
            safety = getattr(self.config, "safety", None)
            if (
                safety
                and getattr(safety, "emergency_stop_enabled", False)
                and getattr(safety, "human_oversight_required", False)
            ):
                # Use a naming convention: critical_ prefix requires approval
                if action_id.startswith("critical_"):
                    # Audit the blocked action
                    try:
                        audit.log_admin_action(
                            request=type(
                                "R",
                                (),
                                {
                                    "url": type(
                                        "U",
                                        (),
                                        {"path": f"/autonomous/recovery/{action_id}"},
                                    ),
                                    "method": "AUTO",
                                    "client": type("C", (), {"host": "localhost"}),
                                    "headers": {},
                                },
                            )(),
                            action="recovery_blocked_human_oversight",
                            details={"action_id": action_id},
                        )
                    except Exception:
                        pass
                    result = RecoveryResult(
                        action_id=action_id,
                        status=RecoveryStatus.FAILED,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        error="human_oversight_required",
                    )
                    self.completed_actions.append(result)
                    try:
                        self.recovery_failure_counter.inc()
                    except Exception:
                        pass
                    return result
        except Exception:
            pass

        # Check dependencies
        for dep_id in action.dependencies:
            if dep_id not in self.recovery_actions:
                logger.error(f"Dependency {dep_id} not found for action {action_id}")
                return None

        # Execute dependencies first
        for dep_id in action.dependencies:
            dep_result = self.trigger_recovery(dep_id)
            if dep_result and dep_result.status != RecoveryStatus.SUCCESS:
                logger.error(f"Dependency {dep_id} failed for action {action_id}")
                result = RecoveryResult(
                    action_id=action_id,
                    status=RecoveryStatus.FAILED,
                    start_time=datetime.now(),
                    error=f"Dependency {dep_id} failed",
                )
                self.completed_actions.append(result)
                return result

        # Execute the action
        result = RecoveryResult(
            action_id=action_id,
            status=RecoveryStatus.IN_PROGRESS,
            start_time=datetime.now(),
        )
        self.running_actions.append(action_id)

        # record attempt metric
        try:
            self.recovery_attempts_counter.inc()
        except Exception:
            pass

        try:
            # Execute the recovery action
            action_result = action.execute_func()

            result.status = RecoveryStatus.SUCCESS
            result.details = {"result": action_result}
            logger.info(f"Recovery action {action_id} completed successfully")
            try:
                self.recovery_success_counter.inc()
            except Exception:
                pass

        except Exception as e:
            result.status = RecoveryStatus.FAILED
            result.error = str(e)
            logger.error(f"Recovery action {action_id} failed: {e}")
            try:
                self.recovery_failure_counter.inc()
            except Exception:
                pass

            # Try rollback if available
            if action.rollback_func:
                try:
                    rollback_result = action.rollback_func()
                    result.details = {"rollback_result": rollback_result}
                    logger.info(f"Rollback for {action_id} completed")
                    try:
                        self.recovery_rollback_counter.inc()
                    except Exception:
                        pass
                except Exception as re:
                    logger.error(f"Rollback for {action_id} failed: {re}")

        result.end_time = datetime.now()
        self.running_actions.remove(action_id)
        self.completed_actions.append(result)

        return result

    def get_recovery_status(self, action_id: str) -> Optional[RecoveryStatus]:
        """Get the status of a recovery action."""
        # Check if running
        if action_id in self.running_actions:
            return RecoveryStatus.IN_PROGRESS

        # Check completed actions
        for result in self.completed_actions:
            if result.action_id == action_id:
                return result.status

        return None


class FailurePredictor:
    """Predicts system failures based on patterns and metrics."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.failure_patterns: Dict[str, List[Dict[str, Any]]] = {}
        self.prediction_history: List[Dict[str, Any]] = []

    def register_failure_pattern(
        self, pattern_name: str, pattern_data: Dict[str, Any]
    ) -> None:
        """Register a failure pattern."""
        if pattern_name not in self.failure_patterns:
            self.failure_patterns[pattern_name] = []

        self.failure_patterns[pattern_name].append(pattern_data)
        logger.info(f"Registered failure pattern: {pattern_name}")

    def predict_failure(self, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Predict potential failures based on current metrics."""
        prediction = {
            "failure_likely": False,
            "predicted_failures": [],
            "confidence": 0.0,
            "recommendations": [],
        }

        # Simple pattern matching (in a real implementation, this would use ML)
        for pattern_name, patterns in self.failure_patterns.items():
            for pattern in patterns:
                match_count = 0
                total_metrics = len(pattern.get("metrics", {}))

                for metric_name, threshold in pattern.get("metrics", {}).items():
                    if metric_name in current_metrics:
                        if current_metrics[metric_name] > threshold:
                            match_count += 1

                if total_metrics > 0:
                    confidence = match_count / total_metrics
                    if confidence > 0.7:  # 70% threshold
                        prediction["failure_likely"] = True
                        prediction["predicted_failures"].append(
                            {"type": pattern_name, "confidence": confidence}
                        )
                        prediction["confidence"] = max(
                            prediction["confidence"], confidence
                        )

                        # Add recommendations
                        recommendations = pattern.get("recommendations", [])
                        prediction["recommendations"].extend(recommendations)

        if prediction["failure_likely"]:
            logger.warning(
                f"Failure predicted with confidence {prediction['confidence']:.2f}"
            )

        return prediction


class AutonomousHealer:
    """Main healer for autonomous operations."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.circuit_breaker_manager = CircuitBreakerManager(config)
        self.recovery_orchestrator = RecoveryOrchestrator(config)
        self.failure_predictor = FailurePredictor(config)
        self.is_healing = False
        self.last_healing_cycle: datetime = datetime.now()

    def start_healing(self) -> None:
        """Start autonomous healing."""
        if self.is_healing:
            logger.warning("Healing already running")
            return

        self.is_healing = True
        logger.info("Autonomous healing started")

    def stop_healing(self) -> None:
        """Stop autonomous healing."""
        self.is_healing = False
        logger.info("Autonomous healing stopped")

    def run_healing_cycle(self, current_metrics: Dict[str, float]) -> None:
        """Run a single healing cycle."""
        if not self.is_healing:
            return

        # Predict potential failures
        prediction = self.failure_predictor.predict_failure(current_metrics)

        if prediction["failure_likely"]:
            logger.warning(
                f"Potential failure detected: {prediction['predicted_failures']}"
            )
            # In a real implementation, this would trigger appropriate recovery actions

        self.last_healing_cycle = datetime.now()
