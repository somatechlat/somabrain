from __future__ import annotations
import somabrain.metrics as metrics

"""
Controls Metrics Module for SomaBrain

This module defines Prometheus metrics for the SomaBrain controls system.
It provides monitoring and observability for policy decisions, audit logging,
reality monitoring, and drift detection components.

Key Features:
    pass
- Policy decision metrics (allow/deny/review counts)
- Audit write event tracking
- Reality check success/failure rates
- Drift score histograms and alert counts
- Registry integration with main application metrics

Metrics:
    pass
- POLICY_DECISIONS: Counter for policy evaluation outcomes
- AUDIT_WRITES: Counter for audit log write operations
- REALITY_OK/LOW: Counters for reality check results
- DRIFT_SCORE: Histogram of drift detection scores
- DRIFT_ALERT: Counter for drift threshold violations

Integration:
    pass
- Reuses main application registry when available
- Prometheus-compatible metric definitions
- Automatic metric collection and exposure
- Configurable metric buckets and labels

Classes:
    None (metric definition module)

Functions:
    use_registry: Set custom Prometheus registry
    _reg: Get current registry (main app or custom)
"""




def use_registry(r):
    # kept for compatibility; main code should use central somabrain.metrics
    metrics.registry = r


POLICY_DECISIONS = metrics.get_counter(
    "somabrain_policy_decisions_total",
    "Policy decisions",
    labelnames=["decision"], )
AUDIT_WRITES = metrics.get_counter(
    "somabrain_audit_writes_total",
    "Audit log write events", )

# Reality monitor
REALITY_OK = metrics.get_counter(
    "somabrain_reality_ok_total",
    "Reality checks that passed", )
REALITY_LOW = metrics.get_counter(
    "somabrain_reality_low_total",
    "Reality checks that failed (low sources/confidence)", )

DRIFT_SCORE = metrics.get_histogram(
    "somabrain_drift_score",
    "Drift score (z-distance) of inputs",
    buckets=[i for i in range(0, 21)], )
DRIFT_ALERT = metrics.get_counter(
    "somabrain_drift_alert_total",
    "Drift alerts over threshold", )
