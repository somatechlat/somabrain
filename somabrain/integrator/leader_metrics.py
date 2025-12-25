"""Integrator Leader Metrics for Phase 2

Provides comprehensive metrics collection and monitoring for the
integrator leader election system, including dwell time, entropy,
and transition statistics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict

import somabrain.metrics as app_metrics

# Leader-specific metrics
LEADER_ELECTION_DURATION = app_metrics.get_histogram(
    "somabrain_leader_election_duration_ms",
    "Time taken to complete leader election process",
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000, 10000),
)

LEADER_TENURE_TRACKER = app_metrics.get_histogram(
    "somabrain_leader_tenure_duration_seconds",
    "Duration of leader tenure periods",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

LEADER_TRANSITIONS = app_metrics.get_counter(
    "somabrain_leader_transitions_total",
    "Total number of leader transitions",
    labelnames=["tenant", "reason", "success"],
)

LEADER_DWELL_ENFORCEMENT = app_metrics.get_counter(
    "somabrain_leader_dwell_enforcement_total",
    "Dwell time enforcement events",
    labelnames=["tenant", "action"],
)

LEADER_ENTROPY_VIOLATIONS = app_metrics.get_counter(
    "somabrain_leader_entropy_violations_total",
    "Entropy cap violations triggering transition",
    labelnames=["tenant"],
)

LEADER_HEALTH_SCORE = app_metrics.get_gauge(
    "somabrain_leader_health_score",
    "Overall leader health score (0-1)",
    labelnames=["tenant", "instance_id"],
)

LEADER_LOCK_EXPIRY = app_metrics.get_counter(
    "somabrain_leader_lock_expiry_total",
    "Redis lock expiry events",
    labelnames=["tenant", "expiry_type"],
)

LEADER_RENEWAL_FAILURES = app_metrics.get_counter(
    "somabrain_leader_renewal_failures_total",
    "Failed leader lock renewals",
    labelnames=["tenant", "reason"],
)

LEADER_INSTANCE_COUNT = app_metrics.get_gauge(
    "somabrain_leader_instance_count",
    "Number of instances participating in leader election",
    labelnames=["tenant"],
)

LEADER_TRANSITION_LATENCY = app_metrics.get_histogram(
    "somabrain_leader_transition_latency_ms",
    "Time between leadership change and processing resumption",
    buckets=(50, 100, 250, 500, 1000, 2500, 5000),
)

LEADER_CONFIG_VALIDATION = app_metrics.get_counter(
    "somabrain_leader_config_validation_total",
    "Leader configuration validation results",
    labelnames=["tenant", "valid"],
)

LEADER_METRICS_COLLECTION = app_metrics.get_counter(
    "somabrain_leader_metrics_collection_total",
    "Metrics collection events",
    labelnames=["tenant", "collection_type"],
)

# Dwell-specific metrics
LEADER_DWELL_CURRENT = app_metrics.get_gauge(
    "somabrain_leader_current_dwell_ms",
    "Current dwell time for active leader",
    labelnames=["tenant"],
)

LEADER_DWELL_MINIMUM = app_metrics.get_gauge(
    "somabrain_leader_dwell_minimum_ms",
    "Configured minimum dwell time",
    labelnames=["tenant"],
)

LEADER_DWELL_REMAINING = app_metrics.get_gauge(
    "somabrain_leader_dwell_remaining_ms",
    "Remaining dwell time before transition allowed",
    labelnames=["tenant"],
)

# Entropy-specific metrics
LEADER_ENTROPY_CURRENT = app_metrics.get_gauge(
    "somabrain_leader_current_entropy",
    "Current entropy value for leader decision",
    labelnames=["tenant"],
)

LEADER_ENTROPY_THRESHOLD = app_metrics.get_gauge(
    "somabrain_leader_entropy_threshold",
    "Configured entropy threshold",
    labelnames=["tenant"],
)

LEADER_ENTROPY_DIFF = app_metrics.get_gauge(
    "somabrain_leader_entropy_difference",
    "Difference between current entropy and threshold",
    labelnames=["tenant"],
)

# Decision metrics
LEADER_DECISION_FACTOR = app_metrics.get_counter(
    "somabrain_leader_decision_factors_total",
    "Factors considered in leader transition decisions",
    labelnames=["tenant", "factor", "outcome"],
)

LEADER_CONSTRAINT_EVALUATION = app_metrics.get_histogram(
    "somabrain_leader_constraint_evaluation_ms",
    "Time to evaluate leader transition constraints",
    buckets=(1, 5, 10, 25, 50, 100, 250, 500),
)


@dataclass
class LeaderMetrics:
    """Comprehensive metrics state for leader tracking."""

    tenant: str
    instance_id: str
    start_time: float
    last_transition: float
    transition_count: int = 0
    dwell_violations: int = 0
    entropy_violations: int = 0
    renewal_failures: int = 0

    def record_transition(self, reason: str, success: bool = True) -> None:
        """Record a leader transition."""
        self.transition_count += 1
        self.last_transition = time.time()

        LEADER_TRANSITIONS.labels(
            tenant=self.tenant, reason=reason, success=str(success).lower()
        ).inc()

        if success:
            tenure = time.time() - self.start_time
            LEADER_TENURE_TRACKER.observe(tenure)

    def record_dwell_violation(self, action: str) -> None:
        """Record a dwell time enforcement event."""
        self.dwell_violations += 1
        LEADER_DWELL_ENFORCEMENT.labels(tenant=self.tenant, action=action).inc()

    def record_entropy_violation(self) -> None:
        """Record an entropy cap violation."""
        self.entropy_violations += 1
        LEADER_ENTROPY_VIOLATIONS.labels(tenant=self.tenant).inc()

    def record_renewal_failure(self, reason: str) -> None:
        """Record a lock renewal failure."""
        self.renewal_failures += 1
        LEADER_RENEWAL_FAILURES.labels(tenant=self.tenant, reason=reason).inc()

    def update_health_score(self, health_score: float) -> None:
        """Update the overall health score metric."""
        LEADER_HEALTH_SCORE.labels(
            tenant=self.tenant, instance_id=self.instance_id
        ).set(health_score)

    def update_dwell_metrics(
        self, current_dwell_ms: float, min_dwell_ms: int, remaining_ms: float
    ) -> None:
        """Update dwell-related metrics."""
        LEADER_DWELL_CURRENT.labels(tenant=self.tenant).set(current_dwell_ms)
        LEADER_DWELL_MINIMUM.labels(tenant=self.tenant).set(min_dwell_ms)
        LEADER_DWELL_REMAINING.labels(tenant=self.tenant).set(max(0, remaining_ms))

    def update_entropy_metrics(self, current_entropy: float, threshold: float) -> None:
        """Update entropy-related metrics."""
        LEADER_ENTROPY_CURRENT.labels(tenant=self.tenant).set(current_entropy)
        LEADER_ENTROPY_THRESHOLD.labels(tenant=self.tenant).set(threshold)
        LEADER_ENTROPY_DIFF.labels(tenant=self.tenant).set(current_entropy - threshold)

    def record_decision_factor(self, factor: str, outcome: str) -> None:
        """Record a decision factor in transition logic."""
        LEADER_DECISION_FACTOR.labels(
            tenant=self.tenant, factor=factor, outcome=outcome
        ).inc()


class LeaderMetricsCollector:
    """Centralized metrics collection for leader election system."""

    def __init__(self) -> None:
        self._metrics: Dict[str, LeaderMetrics] = {}

    def get_metrics(self, tenant: str, instance_id: str) -> LeaderMetrics:
        """Get or create metrics for a tenant/instance."""
        key = f"{tenant}:{instance_id}"

        if key not in self._metrics:
            self._metrics[key] = LeaderMetrics(
                tenant=tenant,
                instance_id=instance_id,
                start_time=time.time(),
                last_transition=time.time(),
            )

        return self._metrics[key]

    def record_election_duration(self, duration_ms: float) -> None:
        """Record the duration of a leader election."""
        LEADER_ELECTION_DURATION.observe(duration_ms)

    def record_config_validation(self, tenant: str, valid: bool) -> None:
        """Record configuration validation result."""
        LEADER_CONFIG_VALIDATION.labels(tenant=tenant, valid=str(valid).lower()).inc()

    def record_collection_event(self, tenant: str, collection_type: str) -> None:
        """Record a metrics collection event."""
        LEADER_METRICS_COLLECTION.labels(
            tenant=tenant, collection_type=collection_type
        ).inc()

    def record_lock_expiry(self, tenant: str, expiry_type: str) -> None:
        """Record a Redis lock expiry."""
        LEADER_LOCK_EXPIRY.labels(tenant=tenant, expiry_type=expiry_type).inc()

    def update_instance_count(self, tenant: str, count: int) -> None:
        """Update the instance count metric."""
        LEADER_INSTANCE_COUNT.labels(tenant=tenant).set(count)

    def record_constraint_evaluation(self, duration_ms: float) -> None:
        """Record constraint evaluation time."""
        LEADER_CONSTRAINT_EVALUATION.observe(duration_ms)


# Global metrics collector
_global_collector = LeaderMetricsCollector()


def get_metrics_collector() -> LeaderMetricsCollector:
    """Get the global metrics collector instance."""
    return _global_collector


def record_election_complete(duration_ms: float) -> None:
    """Convenience function to record election completion."""
    _global_collector.record_election_duration(duration_ms)


def record_transition_complete(
    tenant: str, instance_id: str, reason: str, success: bool = True
) -> None:
    """Convenience function to record transition completion."""
    metrics = _global_collector.get_metrics(tenant, instance_id)
    metrics.record_transition(reason, success)


def record_constraint_check(
    tenant: str,
    instance_id: str,
    dwell_ms: float,
    min_dwell_ms: int,
    entropy: float,
    threshold: float,
    allowed: bool,
) -> None:
    """Record a constraint check decision."""
    metrics = _global_collector.get_metrics(tenant, instance_id)

    # Update dwell metrics
    remaining = min_dwell_ms - dwell_ms
    metrics.update_dwell_metrics(dwell_ms, min_dwell_ms, remaining)

    # Update entropy metrics
    metrics.update_entropy_metrics(entropy, threshold)

    # Record decision factors
    if dwell_ms < min_dwell_ms:
        metrics.record_decision_factor(
            "dwell_time", "blocked" if not allowed else "allowed"
        )
    else:
        metrics.record_decision_factor("dwell_time", "satisfied")

    if entropy > threshold:
        metrics.record_decision_factor(
            "entropy", "violation" if allowed else "enforced"
        )
    else:
        metrics.record_decision_factor("entropy", "compliant")

    if allowed:
        metrics.record_decision_factor("transition", "permitted")
    else:
        metrics.record_decision_factor("transition", "denied")


def calculate_health_score(tenant: str, instance_id: str) -> float:
    """Calculate overall leader health score (0-1)."""
    metrics = _global_collector.get_metrics(tenant, instance_id)

    # Health factors
    time.time() - metrics.start_time
    renewal_success_rate = max(
        0, 1 - (metrics.renewal_failures / max(1, metrics.transition_count * 10))
    )
    dwell_compliance = max(
        0, 1 - (metrics.dwell_violations / max(1, metrics.transition_count))
    )
    entropy_compliance = max(
        0, 1 - (metrics.entropy_violations / max(1, metrics.transition_count))
    )

    # Weighted health score
    health_score = (
        0.4 * renewal_success_rate + 0.3 * dwell_compliance + 0.3 * entropy_compliance
    )

    metrics.update_health_score(health_score)
    return health_score
