"""
Autonomous Learning for SomaBrain.

This module provides continuous learning capabilities for autonomous operations,
including performance feedback collection, model adaptation, and optimization.
"""

import hashlib
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

from .config import AutonomousConfig

logger = logging.getLogger(__name__)


@dataclass
class FeedbackRecord:
    """Record of performance feedback."""

    metric: str
    value: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    success: bool = True


@dataclass
class OptimizationResult:
    """Result of an optimization process."""

    parameter: str
    old_value: Any
    new_value: Any
    improvement: float
    timestamp: datetime
    confidence: float = 0.0


class FeedbackCollector:
    """Collects performance feedback for autonomous learning."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.feedback_history: Dict[str, deque] = {}
        self.max_history_size = 10000

    def add_feedback(
        self,
        metric: str,
        value: float,
        context: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """Add a feedback record."""
        if metric not in self.feedback_history:
            self.feedback_history[metric] = deque(maxlen=self.max_history_size)

        record = FeedbackRecord(
            metric=metric,
            value=value,
            timestamp=datetime.now(),
            context=context or {},
            success=success,
        )

        self.feedback_history[metric].append(record)
        logger.debug(f"Added feedback: {metric} = {value}")

    def get_recent_feedback(
        self, metric: str, window_seconds: int = 3600
    ) -> List[FeedbackRecord]:
        """Get recent feedback records for a metric."""
        if metric not in self.feedback_history:
            return []

        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
        recent_records = [
            record
            for record in self.feedback_history[metric]
            if record.timestamp >= cutoff_time
        ]

        return recent_records

    def get_performance_trend(
        self, metric: str, window_seconds: int = 3600
    ) -> Optional[float]:
        """Calculate performance trend for a metric."""
        recent_feedback = self.get_recent_feedback(metric, window_seconds)

        if len(recent_feedback) < 2:
            return None

        # Calculate linear regression slope
        timestamps = [
            (record.timestamp - recent_feedback[0].timestamp).total_seconds()
            for record in recent_feedback
        ]
        values = [record.value for record in recent_feedback]

        if len(set(timestamps)) < 2:  # All timestamps are the same
            return None

        # Simple linear regression
        x = np.array(timestamps)
        y = np.array(values)
        slope = np.polyfit(x, y, 1)[0]

        return slope


class ParameterOptimizer:
    """Optimizes system parameters based on feedback."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.optimization_history: List[OptimizationResult] = []
        self.parameter_ranges: Dict[str, tuple] = {}  # min, max values
        self.current_values: Dict[str, Any] = {}

    def register_parameter(
        self,
        name: str,
        current_value: Any,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
    ) -> None:
        """Register a parameter for optimization."""
        self.current_values[name] = current_value
        if min_value is not None and max_value is not None:
            self.parameter_ranges[name] = (min_value, max_value)
        logger.info(f"Registered parameter for optimization: {name}")

    def optimize_parameter(
        self,
        parameter: str,
        feedback_metric: str,
        feedback_collector: FeedbackCollector,
    ) -> Optional[OptimizationResult]:
        """Optimize a parameter based on feedback."""
        if parameter not in self.current_values:
            logger.warning(f"Parameter {parameter} not registered for optimization")
            return None

        # Get recent feedback
        trend = feedback_collector.get_performance_trend(feedback_metric)

        if trend is None:
            logger.debug(f"Not enough feedback data to optimize {parameter}")
            return None

        old_value = self.current_values[parameter]
        new_value = old_value

        # Simple optimization logic
        if parameter in self.parameter_ranges:
            min_val, max_val = self.parameter_ranges[parameter]

            # Adjust based on trend
            if trend < 0:  # Performance decreasing
                if isinstance(old_value, (int, float)):
                    adjustment = (max_val - min_val) * 0.05  # 5% adjustment
                    new_value = min(old_value + adjustment, max_val)
            elif trend > 0:  # Performance increasing
                if isinstance(old_value, (int, float)):
                    adjustment = (max_val - min_val) * 0.02  # 2% adjustment
                    new_value = max(old_value - adjustment, min_val)

        # Apply bounds
        if parameter in self.parameter_ranges:
            min_val, max_val = self.parameter_ranges[parameter]
            if isinstance(new_value, (int, float)):
                new_value = max(min(new_value, max_val), min_val)

        # Calculate improvement (simplified)
        improvement = abs(trend) if trend is not None else 0.0

        result = OptimizationResult(
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            improvement=improvement,
            timestamp=datetime.now(),
            confidence=min(1.0, abs(trend) * 10) if trend is not None else 0.0,
        )

        self.optimization_history.append(result)
        self.current_values[parameter] = new_value

        logger.info(
            f"Optimized {parameter}: {old_value} -> {new_value} "
            f"(improvement: {improvement:.4f}, confidence: {result.confidence:.2f})"
        )

        return result


class ExperimentManager:
    """Manages A/B testing and experiments for autonomous learning."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.experiments: Dict[str, Dict[str, Any]] = {}
        self.running_experiments: List[str] = []
        # storage for per-experiment collected samples: {exp_id: {group: [values]}}
        self._samples: Dict[str, Dict[str, List[float]]] = {}

    def create_experiment(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        control_group: str = "control",
    ) -> str:
        """Create a new experiment."""
        experiment_id = (
            f"exp_{len(self.experiments) + 1}_{name.replace(' ', '_').lower()}"
        )

        self.experiments[experiment_id] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "groups": {control_group: {}},
            "created_at": datetime.now(),
            "started_at": None,
            "ended_at": None,
            "results": {},
        }

        logger.info(f"Created experiment {experiment_id}: {name}")
        return experiment_id

    def add_experiment_group(
        self, experiment_id: str, group_name: str, parameters: Dict[str, Any]
    ) -> bool:
        """Add a group to an experiment."""
        if experiment_id not in self.experiments:
            logger.error(f"Experiment {experiment_id} not found")
            return False

        self.experiments[experiment_id]["groups"][group_name] = parameters
        logger.info(f"Added group {group_name} to experiment {experiment_id}")
        return True

    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        if experiment_id not in self.experiments:
            logger.error(f"Experiment {experiment_id} not found")
            return False

        self.experiments[experiment_id]["started_at"] = datetime.now()
        self.running_experiments.append(experiment_id)
        logger.info(f"Started experiment {experiment_id}")
        # initialize sample storage
        if experiment_id not in self._samples:
            self._samples[experiment_id] = {}
        return True

    def evaluate_pending(self) -> None:
        """Evaluate all running experiments and perform statistical analysis.

        For each experiment currently marked as running, if both the ``control`` and
        ``variant`` groups have collected at least two samples for the configured
        metric, we invoke :meth:`analyze_experiment` to compute Welch's t‑test and
        Cohen's d. The result is stored back into the experiment's ``results``
        dictionary under the key ``analysis`` for later promotion/rollback logic.
        """
        for exp_id in list(self.running_experiments):
            # Ensure we have sample data for this experiment
            if exp_id not in self._samples:
                continue
            groups = self._samples[exp_id]
            # Require both control and variant groups present
            if not ({"control", "variant"} <= set(groups.keys())):
                continue
            # Require at least two samples per group for statistical validity
            if any(len(groups[g]) < 2 for g in ("control", "variant")):
                continue
            # Determine the metric used – we assume the first metric recorded is the target
            # The ``record_experiment_result`` stores metric values per group; we can infer metric name
            # from the experiment's ``results`` structure if present, otherwise default to "latency"
            metric = "latency"
            # Perform analysis using the existing method
            analysis = self.analyze_experiment(exp_id, metric)
            if analysis:
                # Store analysis for external consumers (e.g., promotion logic)
                self.experiments[exp_id].setdefault("analysis", analysis)
                logger.info(
                    f"Analyzed experiment {exp_id}: p={analysis.get('p_value'):.4f}, d={analysis.get('effect_size_cohen_d'):.4f}"
                )
                # Optionally stop the experiment after analysis
                self.stop_experiment(exp_id)
            else:
                logger.debug(f"Insufficient data to analyze experiment {exp_id}")

    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop an experiment."""
        if experiment_id not in self.experiments:
            logger.error(f"Experiment {experiment_id} not found")
            return False

        self.experiments[experiment_id]["ended_at"] = datetime.now()
        if experiment_id in self.running_experiments:
            self.running_experiments.remove(experiment_id)
        logger.info(f"Stopped experiment {experiment_id}")
        return True

    def record_experiment_result(
        self, experiment_id: str, group_name: str, metric: str, value: float
    ) -> bool:
        """Record a result for an experiment group."""
        if experiment_id not in self.experiments:
            logger.error(f"Experiment {experiment_id} not found")
            return False

        if group_name not in self.experiments[experiment_id]["groups"]:
            logger.error(f"Group {group_name} not found in experiment {experiment_id}")
            return False

        if "results" not in self.experiments[experiment_id]:
            self.experiments[experiment_id]["results"] = {}

        if group_name not in self.experiments[experiment_id]["results"]:
            self.experiments[experiment_id]["results"][group_name] = {}

        self.experiments[experiment_id]["results"][group_name][metric] = value
        # store sample for offline analysis (metric is the key; we store per metric)
        grp_samples = self._samples.setdefault(experiment_id, {}).setdefault(
            group_name, []
        )
        grp_samples.append(float(value))
        logger.debug(
            f"Recorded result for {experiment_id}/{group_name}: {metric} = {value}"
        )
        return True

    def assign_to_group(
        self, experiment_id: str, subject_id: str, seed: Optional[str] = None
    ) -> Optional[str]:
        """Deterministically assign a subject (e.g., user id or tenant) to an experiment group.

        Uses a stable hashing mechanism to ensure reproducible assignment.
        """
        if experiment_id not in self.experiments:
            return None
        groups = list(self.experiments[experiment_id]["groups"].keys())
        if not groups:
            return None
        h = hashlib.sha256()
        # Combine subject id and seed for stability
        h.update(str(subject_id).encode("utf-8"))
        if seed:
            h.update(str(seed).encode("utf-8"))
        digest = h.digest()
        # Map digest to index
        idx = int.from_bytes(digest[:8], "big") % len(groups)
        return groups[idx]

    def analyze_experiment(
        self, experiment_id: str, metric: str, alpha: float = 0.05
    ) -> Optional[Dict[str, Any]]:
        """Perform a two-sample t-test (Welch's t-test) between groups for the given metric.

        Returns a result dict with t, p, effect_size (Cohen's d), and per-group stats.
        """
        if experiment_id not in self._samples:
            return None
        groups = self._samples[experiment_id]
        if len(groups) < 2:
            return None

        # We'll compare first two groups deterministically
        group_names = list(groups.keys())[:2]
        a = np.array(groups[group_names[0]], dtype=float)
        b = np.array(groups[group_names[1]], dtype=float)
        if len(a) < 2 or len(b) < 2:
            return None

        # Welch's t-test
        mean_a = float(a.mean())
        mean_b = float(b.mean())
        var_a = float(a.var(ddof=1))
        var_b = float(b.var(ddof=1))
        n_a = len(a)
        n_b = len(b)

        # t statistic
        denom = math.sqrt(var_a / n_a + var_b / n_b)
        if denom == 0:
            return None
        t_stat = (mean_a - mean_b) / denom

        # degrees of freedom (Welch–Satterthwaite equation)
        df_num = (var_a / n_a + var_b / n_b) ** 2
        df_den = (var_a**2) / (n_a**2 * (n_a - 1)) + (var_b**2) / (n_b**2 * (n_b - 1))
        if df_den == 0:
            df = max(1, n_a + n_b - 2)
        else:
            df = df_num / df_den

        # two-tailed p-value from t distribution using survival function via math and numpy
        # We'll use scipy if available for accuracy, otherwise approximate using t cdf from numpy
        try:
            from scipy import stats

            p_val = float(stats.t.sf(abs(t_stat), df) * 2)
        except Exception:
            # Alternative: use normal approximation for large df
            p_val = float(
                2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t_stat) / math.sqrt(2.0))))
            )

        # Cohen's d for effect size (pooled std)
        pooled_sd = (
            math.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
            if (n_a + n_b - 2) > 0
            else math.sqrt((var_a + var_b) / 2)
        )
        cohen_d = (mean_a - mean_b) / pooled_sd if pooled_sd > 0 else 0.0

        return {
            "group_a": group_names[0],
            "group_b": group_names[1],
            "n_a": n_a,
            "n_b": n_b,
            "mean_a": mean_a,
            "mean_b": mean_b,
            "t_stat": float(t_stat),
            "df": float(df),
            "p_value": float(p_val),
            "effect_size_cohen_d": float(cohen_d),
            "significant": p_val < alpha,
        }

    def exp_retrieval_alpha_vs_tau(
        self,
        param_name: str,
        control_value: Any,
        variant_value: Any,
        metric: str = "latency",
        alpha: float = 0.05,
    ) -> str:
        """Create and start a two‑group experiment comparing `control_value` vs `variant_value`
        for a given parameter.

        Returns the experiment ID. The caller can later record results via
        ``record_experiment_result`` and analyse with ``analyze_experiment``.
        """
        # Create experiment with descriptive name
        exp_name = f"exp_{param_name}_vs_{control_value}_vs_{variant_value}"
        description = (
            f"Experiment to compare {param_name} values {control_value} (control) "
            f"and {variant_value} (variant) using metric '{metric}'."
        )
        # No extra parameters needed beyond the param being varied
        exp_id = self.create_experiment(
            name=exp_name,
            description=description,
            parameters={},
            control_group="control",
        )
        # Add variant group with the alternative value
        self.add_experiment_group(exp_id, "variant", {param_name: variant_value})
        # Control group may have the default value (or empty dict if not needed)
        self.add_experiment_group(exp_id, "control", {param_name: control_value})
        # Start the experiment immediately
        self.start_experiment(exp_id)
        logger.info(
            f"Started experiment {exp_id} for param {param_name}: "
            f"control={control_value}, variant={variant_value}, metric={metric}"
        )
        return exp_id


class AutonomousLearner:
    """Main learner for autonomous operations."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.feedback_collector = FeedbackCollector(config)
        self.parameter_optimizer = ParameterOptimizer(config)
        self.experiment_manager = ExperimentManager(config)
        # Parameter tuner will drive the optimizer using collected feedback
        self.parameter_tuner = ParameterTuner(
            self.parameter_optimizer, self.feedback_collector
        )
        self.is_learning = False
        self.last_learning_cycle: datetime = datetime.now()

    def start_learning(self) -> None:
        """Start autonomous learning."""
        if self.is_learning:
            logger.warning("Learning already running")
            return

        self.is_learning = True
        logger.info("Autonomous learning started")

    def stop_learning(self) -> None:
        """Stop autonomous learning."""
        self.is_learning = False
        logger.info("Autonomous learning stopped")

    def run_learning_cycle(self) -> None:
        """Run a single learning cycle."""
        if not self.is_learning:
            return

        # In a real implementation, this would:
        # 1. Collect feedback from various system components
        # 2. Analyze performance trends
        # 3. Optimize parameters based on feedback
        # 4. Manage ongoing experiments
        # 5. Update system behavior based on learnings

        self.last_learning_cycle = datetime.now()
        # Run the tuner to attempt parameter optimization and populate optimizer history
        try:
            self.parameter_tuner.tune()
        except Exception:
            logger.exception("Parameter tuner failed during learning cycle")

        logger.debug("Completed learning cycle")


class ParameterTuner:
    """Simple tuning wrapper that invokes the ParameterOptimizer and appends results to
    the optimizer's history for consumption by AdaptiveConfigManager.
    """

    def __init__(self, optimizer: ParameterOptimizer, feedback: FeedbackCollector):
        self.optimizer = optimizer
        self.feedback = feedback

    def tune(self) -> int:
        """Attempt tuning for all registered parameters and return number of results produced."""
        produced = 0
        for param in list(self.optimizer.current_values.keys()):
            # In this minimal implementation we'll use a metric name convention: param -> `${param}_metric`
            metric_name = f"{param}_metric"
            try:
                res = self.optimizer.optimize_parameter(
                    param, metric_name, self.feedback
                )
                if res is not None:
                    # already appended by optimizer; count it
                    produced += 1
            except Exception:
                continue

        return produced
