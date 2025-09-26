"""
Autonomous Configuration Management for SomaBrain.

This module provides configuration management for autonomous operations,
including adaptive settings, safety controls, and governance parameters.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict

import yaml

from .. import audit, metrics as app_metrics

logger = logging.getLogger(__name__)


@dataclass
class AutonomousSafetyConfig:
    """Safety configuration for autonomous operations."""

    emergency_stop_enabled: bool = True
    human_oversight_required: bool = True
    max_autonomous_actions_per_hour: int = 100
    critical_action_confirmation_timeout: int = 300  # seconds
    audit_logging_enabled: bool = True


@dataclass
class AutonomousLearningConfig:
    """Learning configuration for autonomous operations."""

    continuous_learning_enabled: bool = True
    performance_feedback_window: int = 3600  # seconds
    model_update_frequency: int = 86400  # seconds (daily)
    experiment_auto_approval: bool = False


@dataclass
class AutonomousMonitoringConfig:
    """Monitoring configuration for autonomous operations."""

    health_check_interval: int = 60  # seconds
    anomaly_detection_enabled: bool = True
    alert_threshold_cpu: float = 80.0  # percentage
    alert_threshold_memory: float = 85.0  # percentage
    alert_threshold_latency: float = 1000.0  # milliseconds
    # How many consecutive 'unhealthy' checks before auto-healing triggers
    consecutive_unhealthy_threshold: int = 3


@dataclass
class AutonomousConfig:
    """Main configuration class for autonomous operations."""

    enabled: bool = False
    safety: AutonomousSafetyConfig = field(default_factory=AutonomousSafetyConfig)
    learning: AutonomousLearningConfig = field(default_factory=AutonomousLearningConfig)
    monitoring: AutonomousMonitoringConfig = field(
        default_factory=AutonomousMonitoringConfig
    )
    # Adaptive configuration object (tunable behavior)
    adaptive: "AdaptiveConfig" = field(default_factory=lambda: AdaptiveConfig())
    custom_parameters: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AutonomousConfig":
        """Create AutonomousConfig from dictionary."""
        config = cls()

        if "autonomous" in config_dict:
            autonomous_config = config_dict["autonomous"]
            config.enabled = autonomous_config.get("enabled", False)

            # Safety configuration
            if "safety" in autonomous_config:
                safety_config = autonomous_config["safety"]
                config.safety = AutonomousSafetyConfig(
                    emergency_stop_enabled=safety_config.get(
                        "emergency_stop_enabled", True
                    ),
                    human_oversight_required=safety_config.get(
                        "human_oversight_required", True
                    ),
                    max_autonomous_actions_per_hour=safety_config.get(
                        "max_autonomous_actions_per_hour", 100
                    ),
                    critical_action_confirmation_timeout=safety_config.get(
                        "critical_action_confirmation_timeout", 300
                    ),
                    audit_logging_enabled=safety_config.get(
                        "audit_logging_enabled", True
                    ),
                )

            # Learning configuration
            if "learning" in autonomous_config:
                learning_config = autonomous_config["learning"]
                config.learning = AutonomousLearningConfig(
                    continuous_learning_enabled=learning_config.get(
                        "continuous_learning_enabled", True
                    ),
                    performance_feedback_window=learning_config.get(
                        "performance_feedback_window", 3600
                    ),
                    model_update_frequency=learning_config.get(
                        "model_update_frequency", 86400
                    ),
                    experiment_auto_approval=learning_config.get(
                        "experiment_auto_approval", False
                    ),
                )

            # Monitoring configuration
            if "monitoring" in autonomous_config:
                monitoring_config = autonomous_config["monitoring"]
                config.monitoring = AutonomousMonitoringConfig(
                    health_check_interval=monitoring_config.get(
                        "health_check_interval", 60
                    ),
                    anomaly_detection_enabled=monitoring_config.get(
                        "anomaly_detection_enabled", True
                    ),
                    alert_threshold_cpu=monitoring_config.get(
                        "alert_threshold_cpu", 80.0
                    ),
                    alert_threshold_memory=monitoring_config.get(
                        "alert_threshold_memory", 85.0
                    ),
                    alert_threshold_latency=monitoring_config.get(
                        "alert_threshold_latency", 1000.0
                    ),
                )

            # Custom parameters
            config.custom_parameters = autonomous_config.get("custom_parameters", {})
            # Adaptive configuration
            if "adaptive" in autonomous_config:
                try:
                    ac = autonomous_config.get("adaptive", {})
                    config.adaptive = AdaptiveConfig(
                        enabled=ac.get("enabled", True),
                        apply_interval=ac.get("apply_interval", 60),
                        max_changes_per_hour=ac.get("max_changes_per_hour", 10),
                        parameter_ranges=ac.get("parameter_ranges", {}),
                        window_seconds=ac.get("window_seconds", 3600),
                        max_changes_per_window=ac.get("max_changes_per_window", 10),
                        min_confidence=ac.get("min_confidence", 0.0),
                        per_parameter_cooldown_seconds=ac.get(
                            "per_parameter_cooldown_seconds", 300
                        ),
                        canary_mode=ac.get("canary_mode", False),
                    )
                except Exception:
                    pass

        return config

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "AutonomousConfig":
        """Create AutonomousConfig from YAML file."""
        try:
            with open(yaml_path, "r") as f:
                config_dict = yaml.safe_load(f)
            return cls.from_dict(config_dict)
        except Exception as e:
            logger.warning(f"Failed to load autonomous config from {yaml_path}: {e}")
            return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Convert AutonomousConfig to dictionary."""
        return {
            "autonomous": {
                "enabled": self.enabled,
                "safety": {
                    "emergency_stop_enabled": self.safety.emergency_stop_enabled,
                    "human_oversight_required": self.safety.human_oversight_required,
                    "max_autonomous_actions_per_hour": self.safety.max_autonomous_actions_per_hour,
                    "critical_action_confirmation_timeout": self.safety.critical_action_confirmation_timeout,
                    "audit_logging_enabled": self.safety.audit_logging_enabled,
                },
                "learning": {
                    "continuous_learning_enabled": self.learning.continuous_learning_enabled,
                    "performance_feedback_window": self.learning.performance_feedback_window,
                    "model_update_frequency": self.learning.model_update_frequency,
                    "experiment_auto_approval": self.learning.experiment_auto_approval,
                },
                "monitoring": {
                    "health_check_interval": self.monitoring.health_check_interval,
                    "anomaly_detection_enabled": self.monitoring.anomaly_detection_enabled,
                    "alert_threshold_cpu": self.monitoring.alert_threshold_cpu,
                    "alert_threshold_memory": self.monitoring.alert_threshold_memory,
                    "alert_threshold_latency": self.monitoring.alert_threshold_latency,
                },
                "custom_parameters": self.custom_parameters,
            }
        }

    def update_safety(self, **kwargs) -> None:
        """Update safety configuration."""
        for key, value in kwargs.items():
            if hasattr(self.safety, key):
                setattr(self.safety, key, value)
        logger.info("Updated autonomous safety configuration")

    def update_learning(self, **kwargs) -> None:
        """Update learning configuration."""
        for key, value in kwargs.items():
            if hasattr(self.learning, key):
                setattr(self.learning, key, value)
        logger.info("Updated autonomous learning configuration")

    def update_monitoring(self, **kwargs) -> None:
        """Update monitoring configuration."""
        for key, value in kwargs.items():
            if hasattr(self.monitoring, key):
                setattr(self.monitoring, key, value)
        logger.info("Updated autonomous monitoring configuration")

    def set_custom_parameter(self, key: str, value: Any) -> None:
        """Set a custom parameter."""
        self.custom_parameters[key] = value
        logger.info(f"Set custom parameter {key} = {value}")

    def get_custom_parameter(self, key: str, default: Any = None) -> Any:
        """Get a custom parameter."""
        return self.custom_parameters.get(key, default)


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive (auto-tuning) behavior."""

    enabled: bool = True
    apply_interval: int = 60  # seconds between adaptive apply attempts
    max_changes_per_hour: int = 10
    # A simple map of parameter -> (min, max) if numeric
    parameter_ranges: Dict[str, tuple] = field(default_factory=dict)
    # Time-windowed rate limiting
    window_seconds: int = 3600  # window size for rate limiting (default 1 hour)
    max_changes_per_window: int = 10
    # Minimum confidence required from optimizer to apply a change
    min_confidence: float = 0.0
    # Per-parameter cooldown to avoid flapping
    per_parameter_cooldown_seconds: int = 300
    # Canary mode (reserved; manager will stage instead of global apply)
    canary_mode: bool = False


class AdaptiveConfigManager:
    """Manager that applies optimization results safely to the running config.

    The manager is intentionally lightweight: it reads optimization results from
    a ParameterOptimizer and applies bounded changes into `AutonomousConfig.custom_parameters`.
    """

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.adaptive = AdaptiveConfig()
        self._applied_count = 0
        self._last_apply_ts = 0
        # timestamps of applied changes in the current rolling window
        self._applied_timestamps = deque()
        # per-parameter last-applied timestamp for cooldown
        self._param_last_applied: Dict[str, float] = {}
        # Promotion records for monitoring/rollback: {param: {'old':..., 'new':..., 'ts':...}}
        self._promotion_records: Dict[str, Dict[str, Any]] = {}
        # Prometheus metrics using central registry helpers (get-or-create)
        self.canary_promotions_counter = app_metrics.get_counter(
            "soma_canary_promotions_total", "Total canary promotions"
        )
        self.canary_promotion_skipped_counter = app_metrics.get_counter(
            "soma_canary_promotion_skipped_total", "Total skipped canary promotions"
        )
        self.canary_rollbacks_counter = app_metrics.get_counter(
            "soma_canary_rollbacks_total", "Total canary rollbacks"
        )
        # Adaptive apply metrics
        self.adaptive_applies_counter = app_metrics.get_counter(
            "soma_adaptive_applies_total", "Total adaptive parameter applies"
        )
        self.adaptive_apply_skipped_counter = app_metrics.get_counter(
            "soma_adaptive_apply_skipped_total", "Total skipped adaptive apply attempts"
        )

    def register_parameter_range(
        self, name: str, min_value: Any, max_value: Any
    ) -> None:
        self.adaptive.parameter_ranges[name] = (min_value, max_value)

    def can_apply(self) -> bool:
        # Simple rate limiting by count per hour (not time-window precise in this minimal impl)
        if not self.adaptive.enabled:
            return False
        # Clean up applied timestamps outside the window
        now = time.time()
        window_start = now - self.adaptive.window_seconds
        while self._applied_timestamps and self._applied_timestamps[0] < window_start:
            self._applied_timestamps.popleft()

        return len(self._applied_timestamps) < max(
            1, self.adaptive.max_changes_per_window
        )

    def apply_from_optimizer(self, optimizer) -> int:
        """Apply any pending optimization results from a ParameterOptimizer instance.

        Returns the number of parameters applied.
        """
        applied = 0
        if not self.can_apply():
            # record skipped attempt
            try:
                self.adaptive_apply_skipped_counter.inc()
            except Exception:
                pass
            return 0

        # Walk optimizer history and apply latest change for each parameter
        seen = set()
        for res in reversed(list(getattr(optimizer, "optimization_history", []))):
            name = getattr(res, "parameter", None)
            if not name or name in seen:
                continue
            seen.add(name)
            new_value = getattr(res, "new_value", None)
            # Respect per-parameter cooldown
            now = time.time()
            # Re-check global window rate limit before attempting each parameter
            if not self.can_apply():
                try:
                    self.adaptive_apply_skipped_counter.inc()
                except Exception:
                    pass
                # stop processing further results when window exhausted
                break
            last_applied = self._param_last_applied.get(name, 0)
            if now - last_applied < self.adaptive.per_parameter_cooldown_seconds:
                # skip applying due to cooldown
                try:
                    self.adaptive_apply_skipped_counter.inc()
                except Exception:
                    pass
                continue

            # If ranges are configured, clamp numeric values
            if name in self.adaptive.parameter_ranges and isinstance(
                new_value, (int, float)
            ):
                mn, mx = self.adaptive.parameter_ranges[name]
                new_value = max(mn, min(mx, new_value))

            # Enforce optimizer-provided confidence if available
            confidence = getattr(
                res, "confidence", getattr(res, "confidence_score", 0.0)
            )
            if confidence and confidence < self.adaptive.min_confidence:
                continue

            # Apply to config custom parameters
            try:
                if self.adaptive.canary_mode:
                    # In canary mode, record but do not globally apply (placeholder behavior)
                    # We'll store a special canary key to indicate staged change
                    self.config.set_custom_parameter(f"canary::{name}", new_value)
                else:
                    self.config.set_custom_parameter(name, new_value)

                applied += 1
                self._applied_count += 1
                self._applied_timestamps.append(now)
                self._param_last_applied[name] = now
            except Exception:
                continue

        # record applied metrics
        try:
            if applied:
                self.adaptive_applies_counter.inc(applied)
        except Exception:
            pass

        return applied

    def promote_canaries(
        self, experiment_manager, alpha: float = 0.05, min_effect: float = 0.1
    ) -> int:
        """Promote canary-staged parameters to live config based on experimental analysis.

        The experiment naming convention expected: `canary_{param}` where the experiment groups
        are `control` and `variant` (variant contains the canary value). The analysis must
        return a significant result and an effect size exceeding `min_effect` to promote.
        Returns the number of promotions performed.
        """
        promoted = 0
        # Iterate over canary keys in config.custom_parameters
        for key in list(self.config.custom_parameters.keys()):
            if not key.startswith("canary::"):
                continue
            param = key.split("canary::", 1)[1]
            # Look for an experiment named canary_{param}
            exp_name = f"canary_{param}"
            exp_id = None
            for eid, ex in getattr(experiment_manager, "experiments", {}).items():
                if ex.get("name") == exp_name or eid == exp_name:
                    exp_id = eid
                    break

            if not exp_id:
                continue

            analysis = None
            try:
                analysis = experiment_manager.analyze_experiment(
                    exp_id, metric="latency", alpha=alpha
                )
            except Exception:
                analysis = None

            if not analysis:
                self.canary_promotion_skipped_counter.inc()
                continue

            # effect: variant is group_b in analyze_experiment; improvement means mean_b < mean_a for latency
            mean_a = analysis.get("mean_a")
            mean_b = analysis.get("mean_b")
            effect = analysis.get("effect_size_cohen_d", 0.0)
            significant = analysis.get("significant", False)

            if not significant:
                self.canary_promotion_skipped_counter.inc()
                continue

            # For latency-like metrics, require lower mean (improvement) and min effect size
            if mean_b < mean_a and abs(effect) >= min_effect:
                # Promote: set param to canary value and remove canary key
                canary_value = self.config.get_custom_parameter(key)
                # if we stored canary value under canary::name, promote to name
                try:
                    # capture old value before overwriting
                    old_val = (
                        self.config.custom_parameters.get(param)
                        if param in self.config.custom_parameters
                        else None
                    )
                    self.config.set_custom_parameter(param, canary_value)
                    # record promotion for potential rollback
                    self._promotion_records[param] = {
                        "old": old_val,
                        "new": canary_value,
                        "ts": time.time(),
                    }
                    # remove canary entry
                    if key in self.config.custom_parameters:
                        del self.config.custom_parameters[key]
                    promoted += 1
                    try:
                        # audit the promotion (use a tiny fake request object to satisfy the helper signature)
                        audit.log_admin_action(
                            request=type(
                                "R",
                                (),
                                {
                                    "url": type(
                                        "U", (), {"path": f"/autonomous/canary/{param}"}
                                    ),
                                    "method": "AUTO",
                                    "client": type("C", (), {"host": "localhost"}),
                                    "headers": {},
                                },
                            )(),
                            action="canary_promote",
                            details={"param": param, "new_value": canary_value},
                        )
                    except Exception:
                        pass
                    self.canary_promotions_counter.inc()
                except Exception:
                    continue

        return promoted

    def monitor_promotions_and_rollback(
        self, experiment_manager, alpha: float = 0.05, min_effect: float = 0.05
    ) -> int:
        """Check recent promotions against experiments and rollback if statistically worse.

        Returns number of rollbacks performed.
        """
        rollbacks = 0
        for param, rec in list(self._promotion_records.items()):
            # Expect experiment named canary_{param}
            exp_name = f"canary_{param}"
            exp_id = None
            for eid, ex in getattr(experiment_manager, "experiments", {}).items():
                if ex.get("name") == exp_name or eid == exp_name:
                    exp_id = eid
                    break

            if not exp_id:
                continue

            analysis = experiment_manager.analyze_experiment(
                exp_id, metric="latency", alpha=alpha
            )
            if not analysis:
                continue

            mean_a = analysis.get("mean_a")
            mean_b = analysis.get("mean_b")
            effect = analysis.get("effect_size_cohen_d", 0.0)
            significant = analysis.get("significant", False)

            # For latency, regression if variant mean higher (worse)
            if significant and mean_b > mean_a and abs(effect) >= min_effect:
                # rollback to old
                old = rec.get("old")
                if old is not None:
                    self.config.set_custom_parameter(param, old)
                else:
                    # if no old, remove param
                    if param in self.config.custom_parameters:
                        del self.config.custom_parameters[param]

                # remove promotion record
                del self._promotion_records[param]
                try:
                    # audit the rollback
                    audit.log_admin_action(
                        request=type(
                            "R",
                            (),
                            {
                                "url": type(
                                    "U",
                                    (),
                                    {"path": f"/autonomous/canary/{param}/rollback"},
                                ),
                                "method": "AUTO",
                                "client": type("C", (), {"host": "localhost"}),
                                "headers": {},
                            },
                        )(),
                        action="canary_rollback",
                        details={"param": param, "restored_value": old},
                    )
                except Exception:
                    pass
                self.canary_rollbacks_counter.inc()
                rollbacks += 1

        return rollbacks
