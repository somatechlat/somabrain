"""
Autonomous Operations Coordinator for SomaBrain.

This module coordinates all autonomous operations including monitoring,
learning, and healing capabilities.
"""

from __future__ import annotations

import asyncio
import datetime
import os
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from fastapi import FastAPI

from .config import AdaptiveConfig, AdaptiveConfigManager, AutonomousConfig
from .healing import AutonomousHealer
from .learning import AutonomousLearner
from .monitor import AutonomousMonitor
from somabrain.storage.feedback import FeedbackStore
from somabrain.autonomous.learning import (
    ExperimentManager,
    ParameterOptimizer,
    FeedbackCollector,
)
from somabrain import audit

logger = logging.getLogger(__name__)


@dataclass
class AutonomousStatus:
    """Overall status of autonomous operations."""

    enabled: bool = False
    monitoring_active: bool = False
    learning_active: bool = False
    healing_active: bool = False
    last_update: datetime = field(default_factory=lambda: datetime.datetime.now())
    metrics: Dict[str, Any] = field(default_factory=dict)


class AutonomousCoordinator:
    """Coordinates all autonomous operations."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.monitor = AutonomousMonitor(config)
        self.learner = AutonomousLearner(config)
        self.healer = AutonomousHealer(config)
        # Adaptive config manager to apply optimizer results safely
        self.adaptive_manager = AdaptiveConfigManager(config)
        # Initialize adaptive manager with ranges from config.adaptive if present
        try:
            for pname, rng in getattr(
                self.config, "adaptive", AdaptiveConfig()
            ).parameter_ranges.items():
                self.adaptive_manager.register_parameter_range(pname, rng[0], rng[1])
        except Exception:
            pass
        # Track consecutive unhealthy counts per component for auto-healing
        self._consecutive_unhealthy: Dict[str, int] = {}
        self.status = AutonomousStatus()
        self.is_running = False
        self.coordinator_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()

    def start(self) -> None:
        """Start all autonomous operations."""
        if self.is_running:
            logger.warning("Autonomous coordinator already running")
            return

        # Start individual components
        if self.config.enabled:
            self.monitor.start_monitoring()
            self.learner.start_learning()
            self.healer.start_healing()
            self.status.enabled = True

        # Start coordinator thread
        self.shutdown_event.clear()
        self.coordinator_thread = threading.Thread(
            target=self._run_coordinator, daemon=True
        )
        self.coordinator_thread.start()
        self.is_running = True

        logger.info("Autonomous coordinator started")

    def stop(self) -> None:
        """Stop all autonomous operations."""
        if not self.is_running:
            logger.warning("Autonomous coordinator not running")
            return

        # Signal shutdown
        self.shutdown_event.set()

        # Stop individual components
        self.monitor.stop_monitoring()
        self.learner.stop_learning()
        self.healer.stop_healing()

        # Wait for coordinator thread to finish
        if self.coordinator_thread and self.coordinator_thread.is_alive():
            self.coordinator_thread.join(timeout=5.0)

        self.is_running = False
        self.status.enabled = False
        logger.info("Autonomous coordinator stopped")

    def _run_coordinator(self) -> None:
        """Main coordinator loop."""
        logger.info("Autonomous coordinator loop started")
        last_adaptive_apply = 0.0

        while not self.shutdown_event.is_set():
            try:
                # Run monitoring cycle
                if self.monitor.is_running:
                    self.monitor.run_monitoring_cycle()
                    self.status.monitoring_active = True
                else:
                    self.status.monitoring_active = False

                # Run learning cycle
                if self.learner.is_learning:
                    self.learner.run_learning_cycle()
                    self.status.learning_active = True
                else:
                    self.status.learning_active = False

                # Apply adaptive config updates from optimizer (bounded and rate-limited)
                try:
                    # Respect adaptive apply interval if configured
                    adaptive_interval = getattr(
                        getattr(self.config, "adaptive", None), "apply_interval", None
                    )
                    now_ts = time.time()
                    should_apply = False
                    if adaptive_interval and adaptive_interval > 0:
                        if now_ts - last_adaptive_apply >= adaptive_interval:
                            should_apply = True
                    else:
                        # Fall back to applying once per main loop
                        should_apply = True

                    if should_apply:
                        applied = self.adaptive_manager.apply_from_optimizer(
                            self.learner.parameter_optimizer
                        )
                        last_adaptive_apply = now_ts
                        if applied > 0:
                            logger.info(f"Applied {applied} adaptive parameter updates")
                except Exception as e:
                    logger.error(f"Adaptive config application failed: {e}")

                # Run healing cycle
                if self.healer.is_healing:
                    # Get current metrics from monitor
                    metrics = {}
                    for (
                        component,
                        health_status,
                    ) in self.monitor.health_checker.health_status.items():
                        metrics.update(health_status.metrics)

                    # Evaluate auto-healing triggers based on health statuses
                    try:
                        self._evaluate_healing_triggers(
                            self.monitor.health_checker.health_status
                        )
                    except Exception as e:
                        logger.error(f"Error evaluating healing triggers: {e}")

                    self.healer.run_healing_cycle(metrics)
                    self.status.healing_active = True
                    # Periodically check canary promotions and rollbacks
                    try:
                        # If learner exposes an experiment manager, check promotions/rollbacks
                        em = getattr(self.learner, "experiment_manager", None)
                        if em:
                            rb = self.adaptive_manager.monitor_promotions_and_rollback(
                                em
                            )
                            if rb > 0:
                                logger.info(f"Performed {rb} canary rollback(s)")
                    except Exception as e:
                        logger.error(f"Error monitoring promotions/rollbacks: {e}")

                    # Auto-probe half-open circuits using simple probes from monitor
                    try:
                        probe_map = {}
                        # if monitor provides probes for components, use them
                        if hasattr(self.monitor, "probe_map"):
                            probe_map = getattr(self.monitor, "probe_map")
                        reset_count = (
                            self.healer.circuit_breaker_manager.auto_probe_all(
                                probe_map
                            )
                        )
                        if reset_count:
                            logger.info(
                                f"Auto-probed and reset {reset_count} circuit(s)"
                            )
                    except Exception as e:
                        logger.error(f"Error auto-probing circuits: {e}")
                else:
                    self.status.healing_active = False

                # Update status
                self.status.last_update = datetime.datetime.now()

                # Sleep for monitoring interval
                interval = self.config.monitoring.health_check_interval
                if self.shutdown_event.wait(timeout=interval):
                    break

            except Exception as e:
                logger.error(f"Error in autonomous coordinator loop: {e}")
                if self.shutdown_event.wait(timeout=1.0):
                    break

        logger.info("Autonomous coordinator loop stopped")

    def update_config(self, new_config: AutonomousConfig) -> None:
        """Update autonomous configuration."""
        old_enabled = self.config.enabled
        self.config = new_config
        # Propagate adaptive settings to adaptive manager
        try:
            if hasattr(self.config, "adaptive"):
                self.adaptive_manager.adaptive = self.config.adaptive
                # re-register parameter ranges
                for pname, rng in getattr(
                    self.config.adaptive, "parameter_ranges", {}
                ).items():
                    try:
                        self.adaptive_manager.register_parameter_range(
                            pname, rng[0], rng[1]
                        )
                    except Exception:
                        continue
        except Exception:
            logger.exception("Failed to update adaptive manager from new config")

        # Handle enable/disable changes
        if old_enabled and not new_config.enabled:
            self.stop()
        elif not old_enabled and new_config.enabled:
            self.start()

        logger.info("Autonomous configuration updated")

    def get_status(self) -> AutonomousStatus:
        """Get current autonomous operations status."""
        # Update metrics from components
        metrics = {}

        # Add monitoring metrics
        for (
            component,
            health_status,
        ) in self.monitor.health_checker.health_status.items():
            metrics[f"{component}_status"] = health_status.status
            metrics.update(
                {f"{component}_{k}": v for k, v in health_status.metrics.items()}
            )

        # Add learning metrics
        metrics["learning_active"] = self.learner.is_learning
        metrics["feedback_metrics_count"] = len(
            self.learner.feedback_collector.feedback_history
        )

        # Add healing metrics
        metrics["healing_active"] = self.healer.is_healing
        metrics["circuit_breakers_count"] = len(
            self.healer.circuit_breaker_manager.circuit_breakers
        )

        self.status.metrics = metrics
        self.status.last_update = datetime.datetime.now()

        return self.status

    def trigger_manual_recovery(self, action_id: str) -> Dict[str, Any]:
        """Trigger a manual recovery action."""
        try:
            result = self.healer.recovery_orchestrator.trigger_recovery(action_id)
            if result:
                return {
                    "success": True,
                    "action_id": result.action_id,
                    "status": result.status.value,
                    "details": result.details,
                    "error": result.error,
                }
            else:
                return {
                    "success": False,
                    "error": f"Recovery action {action_id} not found or failed to execute",
                }
        except Exception as e:
            logger.error(f"Error triggering manual recovery {action_id}: {e}")
            return {"success": False, "error": str(e)}

    def _evaluate_healing_triggers(self, health_statuses: Dict[str, Any]) -> None:
        """Evaluate consecutive unhealthy statuses and trigger recovery actions when thresholds exceeded."""
        # Threshold from config
        threshold = getattr(
            self.config.monitoring, "consecutive_unhealthy_threshold", 3
        )

        for component, hs in health_statuses.items():
            # Initialize counter if needed
            if component not in self._consecutive_unhealthy:
                self._consecutive_unhealthy[component] = 0

            if hs.status == "unhealthy":
                self._consecutive_unhealthy[component] += 1
                logger.debug(
                    f"Component {component} unhealthy count: {self._consecutive_unhealthy[component]}"
                )
            else:
                # Reset counter on non-unhealthy status
                if self._consecutive_unhealthy.get(component, 0) != 0:
                    logger.debug(
                        f"Component {component} recovered, resetting unhealthy counter"
                    )
                self._consecutive_unhealthy[component] = 0

            # If threshold exceeded, trigger a recovery action if available
            if self._consecutive_unhealthy[component] >= threshold:
                # Compose a default action id for the component
                action_id = f"auto_recover_{component}"
                # If an action is registered, trigger it
                if action_id in self.healer.recovery_orchestrator.recovery_actions:
                    logger.info(
                        f"Auto-triggering recovery for {component} via action {action_id}"
                    )
                    try:
                        self.healer.recovery_orchestrator.trigger_recovery(action_id)
                    except Exception as e:
                        logger.error(f"Auto recovery for {component} failed: {e}")
                else:
                    logger.warning(
                        f"No auto-recovery action registered for {component} (expected id {action_id})"
                    )
                # Reset counter after triggering to avoid repeated triggers
                self._consecutive_unhealthy[component] = 0


# Global autonomous coordinator instance
_autonomous_coordinator: Optional[AutonomousCoordinator] = None


def get_autonomous_coordinator(
    config: Optional[AutonomousConfig] = None,
) -> AutonomousCoordinator:
    """Get or create the global autonomous coordinator instance."""
    global _autonomous_coordinator

    if _autonomous_coordinator is None:
        if config is None:
            config = AutonomousConfig()
        _autonomous_coordinator = AutonomousCoordinator(config)

    return _autonomous_coordinator


def initialize_autonomous_operations(
    config_path: Optional[str] = None,
) -> AutonomousCoordinator:
    """Initialize autonomous operations with configuration."""
    global _autonomous_coordinator

    # Load configuration
    if config_path:
        config = AutonomousConfig.from_yaml(config_path)
    else:
        config = AutonomousConfig()

    # Create or update coordinator
    if _autonomous_coordinator is None:
        _autonomous_coordinator = AutonomousCoordinator(config)
    else:
        _autonomous_coordinator.update_config(config)

    return _autonomous_coordinator


# Removed duplicate imports and redundant definitions. Keep helper functions.


def get_feedback_store() -> FeedbackStore:
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store


def get_experiment_manager(
    config: Optional[AutonomousConfig] = None,
) -> ExperimentManager:
    """Retrieve the global ExperimentManager, creating it if necessary.

    The original implementation instantiated ``ExperimentManager`` without a
    configuration, which raises a ``TypeError`` because the constructor
    requires an ``AutonomousConfig`` instance.  We now accept an optional
    ``config`` argument; if none is provided we fall back to a default
    ``AutonomousConfig``.  This keeps backward compatibility for callers that
    do not supply a config while fixing the error for internal usage.
    """
    global _experiment_manager
    if _experiment_manager is None:
        cfg = config if config is not None else AutonomousConfig()
        _experiment_manager = ExperimentManager(cfg)
    return _experiment_manager


def get_parameter_optimizer() -> ParameterOptimizer:
    global _parameter_optimizer
    if _parameter_optimizer is None:
        _parameter_optimizer = ParameterOptimizer()
    return _parameter_optimizer


async def _poll_feedback_loop(app: FastAPI) -> None:
    """Background task that runs every POLL_INTERVAL seconds.

    It fetches recent feedback events, feeds them to FeedbackCollector, and
    triggers the experiment manager to evaluate any pending experiments.
    """
    poll_interval = int(
        os.getenv("SOMABRAIN_COORDINATOR_POLL_SEC", "300")
    )  # default 5 min
    while True:
        try:
            store = get_feedback_store()
            # Retrieve events from the last poll interval
            since = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=poll_interval
            )
            recent = store.get_events_since(since.isoformat())
            if recent:
                collector = FeedbackCollector()
                for ev in recent:
                    # Expected keys: utility, reward, tenant_id
                    collector.record(
                        tenant_id=ev.get("tenant_id", "default"),
                        utility=ev.get("utility"),
                        reward=ev.get("reward"),
                    )
                # Run optimizer on aggregated feedback
                optimizer = get_parameter_optimizer()
                optimizer.optimize(collector)
                # Evaluate experiments
                exp_mgr = get_experiment_manager()
                exp_mgr.evaluate_pending()
        except Exception as exc:
            # Log but do not crash the loop
            audit.publish_event({"action": "coordinator_error", "error": str(exc)})
        await asyncio.sleep(poll_interval)


def setup_coordinator(app: FastAPI) -> None:
    """Attach the coordinator to a FastAPI app via lifespan events.

    Usage: in the main FastAPI creation file, call ``setup_coordinator(app)``.
    """

    @app.on_event("startup")
    async def start_coordinator() -> None:
        # Kick off the background poller
        asyncio.create_task(_poll_feedback_loop(app))

    @app.on_event("shutdown")
    async def stop_coordinator() -> None:
        # No explicit shutdown needed; the task will exit when the event loop stops.
        pass
