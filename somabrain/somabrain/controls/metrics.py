from __future__ import annotations

from prometheus_client import Counter, Histogram, CollectorRegistry

registry = None  # reuse app registry if available

def use_registry(r):
    global registry
    registry = r

def _reg():
    from .. import metrics as appm  # reuse main registry
    return getattr(appm, "registry", None) or registry

POLICY_DECISIONS = Counter(
    "somabrain_policy_decisions_total",
    "Policy decisions",
    ["decision"],
    registry=_reg(),
)
AUDIT_WRITES = Counter(
    "somabrain_audit_writes_total",
    "Audit log write events",
    registry=_reg(),
)

# Reality monitor
REALITY_OK = Counter(
    "somabrain_reality_ok_total",
    "Reality checks that passed",
    registry=_reg(),
)
REALITY_LOW = Counter(
    "somabrain_reality_low_total",
    "Reality checks that failed (low sources/confidence)",
    registry=_reg(),
)

# Drift monitor
from prometheus_client import Histogram as _Hist
DRIFT_SCORE = _Hist(
    "somabrain_drift_score",
    "Drift score (z-distance) of inputs",
    buckets=[i for i in range(0, 21)],
    registry=_reg(),
)
DRIFT_ALERT = Counter(
    "somabrain_drift_alert_total",
    "Drift alerts over threshold",
    registry=_reg(),
)
