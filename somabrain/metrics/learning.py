"""Learning and Adaptation Metrics for SomaBrain.

This module contains all metrics related to the learning and adaptation system:
- Retrieval weight metrics (alpha, beta, gamma, tau)
- Utility weight metrics (lambda, mu, nu)
- Feedback loop metrics
- Learner (next-event) metrics
- Adaptation dynamics metrics
- Tau/entropy adaptive knob metrics
- Regret KPIs

Helper functions for updating these metrics are also provided.
"""

from __future__ import annotations

from somabrain.metrics.core import (
    get_counter,
    get_gauge,
    get_histogram,
)


# ---------------------------------------------------------------------------
# Retrieval Weights (per-tenant adaptation state)
# ---------------------------------------------------------------------------

LEARNING_RETRIEVAL_ALPHA = get_gauge(
    "somabrain_learning_retrieval_alpha",
    "Semantic weight in retrieval (α) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_RETRIEVAL_BETA = get_gauge(
    "somabrain_learning_retrieval_beta",
    "Graph weight in retrieval (β) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_RETRIEVAL_GAMMA = get_gauge(
    "somabrain_learning_retrieval_gamma",
    "Recent weight in retrieval (γ) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_RETRIEVAL_TAU = get_gauge(
    "somabrain_learning_retrieval_tau",
    "Temperature for diversity (τ) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_TAU = get_gauge(
    "somabrain_learning_tau",
    "Current retrieval temperature per tenant",
    ["tenant_id"],
)

LEARNING_ENTROPY_CAP_HITS = get_counter(
    "somabrain_learning_entropy_cap_hits_total",
    "Count of retrieval weight vectors that exceeded entropy cap",
    ["tenant_id"],
)


# ---------------------------------------------------------------------------
# Utility Weights (per-tenant adaptation state)
# ---------------------------------------------------------------------------

LEARNING_UTILITY_LAMBDA = get_gauge(
    "somabrain_learning_utility_lambda",
    "Semantic utility weight (λ) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_UTILITY_MU = get_gauge(
    "somabrain_learning_utility_mu",
    "Graph utility weight (μ) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_UTILITY_NU = get_gauge(
    "somabrain_learning_utility_nu",
    "Recent utility weight (ν) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_GAIN = get_gauge(
    "somabrain_learning_gain",
    "Configured adaptation gain per component",
    labelnames=["tenant_id", "component"],
)

LEARNING_BOUND = get_gauge(
    "somabrain_learning_bound",
    "Adaptation bounds per component and side",
    labelnames=["tenant_id", "component", "bound"],
)


# ---------------------------------------------------------------------------
# Feedback Loop Metrics
# ---------------------------------------------------------------------------

LEARNING_FEEDBACK_APPLIED = get_counter(
    "somabrain_learning_feedback_applied_total",
    "Total feedback applications (success) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_FEEDBACK_REJECTED = get_counter(
    "somabrain_learning_feedback_rejected_total",
    "Feedback rejected due to outliers or bounds per tenant",
    labelnames=["tenant_id", "reason"],
)

LEARNING_FEEDBACK_LATENCY = get_histogram(
    "somabrain_learning_feedback_latency_seconds",
    "Latency of feedback application (end-to-end) per tenant",
    labelnames=["tenant_id"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
)


# ---------------------------------------------------------------------------
# Learner (next-event) Metrics
# ---------------------------------------------------------------------------

LEARNER_EVENTS_CONSUMED = get_counter(
    "somabrain_learner_events_consumed_total",
    "Next-event messages consumed",
    labelnames=["tenant_id"],
)

LEARNER_EVENTS_PRODUCED = get_counter(
    "somabrain_learner_events_produced_total",
    "Config updates produced by learner",
    labelnames=["tenant_id"],
)

LEARNER_EVENTS_FAILED = get_counter(
    "somabrain_learner_events_failed_total",
    "Next-event processing failures",
    labelnames=["tenant_id", "phase"],
)

LEARNER_EVENT_LATENCY = get_histogram(
    "somabrain_learner_event_latency_seconds",
    "End-to-end processing latency for next-event messages",
    labelnames=["tenant_id"],
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

LEARNER_DLQ_TOTAL = get_counter(
    "somabrain_learner_dlq_total",
    "Learner DLQ writes",
    labelnames=["tenant_id", "reason"],
)

LEARNER_LAG_SECONDS = get_gauge(
    "somabrain_learner_lag_seconds",
    "Time since last next-event processed per tenant",
    labelnames=["tenant_id"],
)


# ---------------------------------------------------------------------------
# Adaptation Dynamics
# ---------------------------------------------------------------------------

LEARNING_EFFECTIVE_LR = get_gauge(
    "somabrain_learning_effective_lr",
    "Effective learning rate (lr_eff) per tenant",
    labelnames=["tenant_id"],
)

LEARNING_ROLLBACKS = get_counter(
    "somabrain_learning_rollbacks_total",
    "Number of weight rollbacks triggered per tenant",
    labelnames=["tenant_id"],
)

LEARNING_WM_LENGTH = get_gauge(
    "somabrain_learning_wm_length",
    "Working memory length per session/tenant",
    labelnames=["session_id", "tenant_id"],
)


# ---------------------------------------------------------------------------
# Autonomous Experiments
# ---------------------------------------------------------------------------

LEARNING_EXPERIMENT_ACTIVE = get_gauge(
    "somabrain_learning_experiment_active",
    "Number of active A/B experiments",
    labelnames=["experiment_name"],
)

LEARNING_EXPERIMENT_PROMOTIONS = get_counter(
    "somabrain_learning_experiment_promotions_total",
    "Number of successful canary promotions",
    labelnames=["experiment_name"],
)


# ---------------------------------------------------------------------------
# Phase-1 Adaptive Knob Metrics
# ---------------------------------------------------------------------------

tau_decay_events = get_counter(
    "somabrain_tau_decay_events_total",
    "Tau decay applications per tenant",
    labelnames=["tenant_id"],
)

tau_anneal_events = get_counter(
    "somabrain_tau_anneal_events_total",
    "Tau annealing applications per tenant (any schedule)",
    labelnames=["tenant_id"],
)

entropy_cap_events = get_counter(
    "somabrain_entropy_cap_events_total",
    "Entropy cap sharpen events per tenant",
    labelnames=["tenant_id"],
)

LEARNING_RETRIEVAL_ENTROPY = get_gauge(
    "somabrain_learning_retrieval_entropy",
    "Entropy of retrieval weight distribution per tenant",
    labelnames=["tenant_id"],
)


# ---------------------------------------------------------------------------
# Regret KPIs
# ---------------------------------------------------------------------------

LEARNING_REGRET = get_histogram(
    "somabrain_learning_regret",
    "Regret distribution per tenant",
    labelnames=["tenant_id"],
    buckets=[i / 20.0 for i in range(0, 21)],
)

LEARNING_REGRET_EWMA = get_gauge(
    "somabrain_learning_regret_ewma",
    "EWMA regret per tenant",
    labelnames=["tenant_id"],
)

soma_next_event_regret = get_gauge(
    "soma_next_event_regret",
    "Instantaneous next-event regret (0-1)",
    labelnames=["tenant_id"],
)

# Internal state for EWMA calculation
_regret_ema: dict[str, float] = {}
_REGRET_ALPHA = 0.15


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def update_learning_retrieval_weights(
    tenant_id: str, alpha: float, beta: float, gamma: float, tau: float
) -> None:
    """Update per-tenant retrieval weight metrics."""
    LEARNING_RETRIEVAL_ALPHA.labels(tenant_id=tenant_id).set(alpha)
    LEARNING_RETRIEVAL_BETA.labels(tenant_id=tenant_id).set(beta)
    LEARNING_RETRIEVAL_GAMMA.labels(tenant_id=tenant_id).set(gamma)
    LEARNING_RETRIEVAL_TAU.labels(tenant_id=tenant_id).set(tau)


def update_learning_utility_weights(
    tenant_id: str, lambda_: float, mu: float, nu: float
) -> None:
    """Update per-tenant utility weight metrics."""
    LEARNING_UTILITY_LAMBDA.labels(tenant_id=tenant_id).set(lambda_)
    LEARNING_UTILITY_MU.labels(tenant_id=tenant_id).set(mu)
    LEARNING_UTILITY_NU.labels(tenant_id=tenant_id).set(nu)


def update_learning_gains(tenant_id: str, **gains: float) -> None:
    """Record configured adaptation gains per component."""
    for component, value in gains.items():
        LEARNING_GAIN.labels(tenant_id=tenant_id, component=component).set(float(value))


def update_learning_bounds(tenant_id: str, **bounds: float) -> None:
    """Record adaptation bounds (min/max) for each component."""
    for key, value in bounds.items():
        if key.endswith("_min"):
            component = key[:-4]
            LEARNING_BOUND.labels(
                tenant_id=tenant_id, component=component, bound="min"
            ).set(float(value))
        elif key.endswith("_max"):
            component = key[:-4]
            LEARNING_BOUND.labels(
                tenant_id=tenant_id, component=component, bound="max"
            ).set(float(value))


def record_learning_feedback_applied(tenant_id: str) -> None:
    """Increment feedback applied counter for tenant."""
    LEARNING_FEEDBACK_APPLIED.labels(tenant_id=tenant_id).inc()


def record_learning_feedback_rejected(tenant_id: str, reason: str) -> None:
    """Increment feedback rejected counter for tenant."""
    LEARNING_FEEDBACK_REJECTED.labels(tenant_id=tenant_id, reason=reason).inc()


def record_learning_feedback_latency(tenant_id: str, latency_seconds: float) -> None:
    """Record feedback latency for tenant."""
    LEARNING_FEEDBACK_LATENCY.labels(tenant_id=tenant_id).observe(latency_seconds)


def update_learning_effective_lr(tenant_id: str, lr_eff: float) -> None:
    """Update effective learning rate metric for tenant."""
    LEARNING_EFFECTIVE_LR.labels(tenant_id=tenant_id).set(lr_eff)


def record_regret(tenant_id: str, regret: float) -> None:
    """Record regret value and update EWMA for tenant."""
    try:
        t = tenant_id or "public"
        r = max(0.0, min(1.0, float(regret)))
        LEARNING_REGRET.labels(tenant_id=t).observe(r)
        prev = _regret_ema.get(t)
        if prev is None:
            ema = r
        else:
            ema = _REGRET_ALPHA * r + (1.0 - _REGRET_ALPHA) * prev
        _regret_ema[t] = ema
        LEARNING_REGRET_EWMA.labels(tenant_id=t).set(ema)
    except Exception:
        pass


def update_learning_retrieval_entropy(tenant_id: str, entropy: float) -> None:
    """Update retrieval entropy metric for tenant."""
    try:
        LEARNING_RETRIEVAL_ENTROPY.labels(tenant_id=tenant_id).set(float(entropy))
    except Exception:
        pass


def record_learning_rollback(tenant_id: str) -> None:
    """Increment rollback counter for tenant."""
    LEARNING_ROLLBACKS.labels(tenant_id=tenant_id).inc()


def update_learning_wm_length(session_id: str, tenant_id: str, length: int) -> None:
    """Update working memory length metric for session/tenant."""
    LEARNING_WM_LENGTH.labels(session_id=session_id, tenant_id=tenant_id).set(length)


__all__ = [
    # Retrieval weights
    "LEARNING_RETRIEVAL_ALPHA",
    "LEARNING_RETRIEVAL_BETA",
    "LEARNING_RETRIEVAL_GAMMA",
    "LEARNING_RETRIEVAL_TAU",
    "LEARNING_TAU",
    "LEARNING_ENTROPY_CAP_HITS",
    # Utility weights
    "LEARNING_UTILITY_LAMBDA",
    "LEARNING_UTILITY_MU",
    "LEARNING_UTILITY_NU",
    "LEARNING_GAIN",
    "LEARNING_BOUND",
    # Feedback
    "LEARNING_FEEDBACK_APPLIED",
    "LEARNING_FEEDBACK_REJECTED",
    "LEARNING_FEEDBACK_LATENCY",
    # Learner
    "LEARNER_EVENTS_CONSUMED",
    "LEARNER_EVENTS_PRODUCED",
    "LEARNER_EVENTS_FAILED",
    "LEARNER_EVENT_LATENCY",
    "LEARNER_DLQ_TOTAL",
    "LEARNER_LAG_SECONDS",
    # Dynamics
    "LEARNING_EFFECTIVE_LR",
    "LEARNING_ROLLBACKS",
    "LEARNING_WM_LENGTH",
    # Experiments
    "LEARNING_EXPERIMENT_ACTIVE",
    "LEARNING_EXPERIMENT_PROMOTIONS",
    # Adaptive knobs
    "tau_decay_events",
    "tau_anneal_events",
    "entropy_cap_events",
    "LEARNING_RETRIEVAL_ENTROPY",
    # Regret
    "LEARNING_REGRET",
    "LEARNING_REGRET_EWMA",
    "soma_next_event_regret",
    # Helper functions
    "update_learning_retrieval_weights",
    "update_learning_utility_weights",
    "update_learning_gains",
    "update_learning_bounds",
    "record_learning_feedback_applied",
    "record_learning_feedback_rejected",
    "record_learning_feedback_latency",
    "update_learning_effective_lr",
    "record_regret",
    "update_learning_retrieval_entropy",
    "record_learning_rollback",
    "update_learning_wm_length",
]
