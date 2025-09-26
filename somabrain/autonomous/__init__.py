"""
Autonomous Operations Package for SomaBrain.

This package contains all components for autonomous system management,
including self-monitoring, adaptive configuration, self-healing,
and continuous learning capabilities.
"""

from .config import (
    AdaptiveConfig,
    AdaptiveConfigManager,
    AutonomousConfig,
    AutonomousLearningConfig,
    AutonomousMonitoringConfig,
    AutonomousSafetyConfig,
)
from .coordinator import (
    AutonomousCoordinator,
    AutonomousStatus,
    get_autonomous_coordinator,
    initialize_autonomous_operations,
)
from .healing import (
    AutonomousHealer,
    CircuitBreakerManager,
    FailurePredictor,
    RecoveryAction,
    RecoveryOrchestrator,
    RecoveryResult,
    RecoveryStatus,
)
from .learning import (
    AutonomousLearner,
    ExperimentManager,
    FeedbackCollector,
    FeedbackRecord,
    OptimizationResult,
    ParameterOptimizer,
)
from .monitor import (
    AlertManager,
    Anomaly,
    AnomalyDetector,
    AutonomousMonitor,
    HealthChecker,
    HealthStatus,
)

__all__ = [
    # Configuration
    "AutonomousConfig",
    "AutonomousSafetyConfig",
    "AutonomousLearningConfig",
    "AutonomousMonitoringConfig",
    # Monitoring
    "AutonomousMonitor",
    "HealthChecker",
    "AnomalyDetector",
    "AlertManager",
    "HealthStatus",
    "Anomaly",
    # Learning
    "AutonomousLearner",
    "FeedbackCollector",
    "ParameterOptimizer",
    "ExperimentManager",
    "FeedbackRecord",
    "OptimizationResult",
    # Healing
    "AutonomousHealer",
    "CircuitBreakerManager",
    "RecoveryOrchestrator",
    "FailurePredictor",
    "RecoveryAction",
    "RecoveryResult",
    "RecoveryStatus",
    # Adaptive
    "AdaptiveConfig",
    "AdaptiveConfigManager",
    # Coordinator
    "AutonomousCoordinator",
    "AutonomousStatus",
    "get_autonomous_coordinator",
    "initialize_autonomous_operations",
]
