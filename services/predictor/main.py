"""Unified Predictor Service

Consolidates state / agent / action predictor loops into a single process
with shared bootstrap, tracing, calibration scaling, and metrics.

VIBE COMPLIANT: Pure Django - No FastAPI, No uvicorn.
Health endpoint provided via Django management command.

Goals:
- Remove duplicated health server + tracing code across three separate mains.
- Apply calibration temperature scaling uniformly.
- Preserve existing per-domain topics and schema usage.
- Maintain SOMA compatibility emission when enabled via runtime config.

Strict mode assumptions:
- Avro encode via `common.kafka_utils.encode` with schema names: belief_update,
  belief_update_soma (optional), next_event.
- Confluent Kafka producer from `common.kafka_utils.make_producer`.

Environment / runtime_config keys (mirroring legacy mains):
- *_update_period for each domain (state_update_period, agent_update_period, action_update_period)
- *_model_ver for each domain
- soma_compat flag to emit SOMA-compatible belief updates
"""

from __future__ import annotations

from django.conf import settings
import random
import time
from typing import Dict, Any, Tuple

import numpy as np

from somabrain.observability.provider import init_tracing, get_tracer

from common.kafka_utils import make_producer, encode, TOPICS
from common.events import build_next_event

try:
    from somabrain import metrics as _metrics
except Exception:  # pragma: no cover
    _metrics = None

try:
    from somabrain.calibration.calibration_metrics import calibration_tracker as _calib
except Exception:  # pragma: no cover
    _calib = None

try:
    from somabrain.predictors.base import build_predictor_from_env
except Exception as e:  # pragma: no cover
    raise RuntimeError(f"predictor.unified: predictor base unavailable: {e}")


DOMAIN_CONFIG = {
    "state": {
        "topic": TOPICS["state"],
        "model_ver_key": "state_model_ver",
        "period_key": "state_update_period",
        "default_period": 0.5,
        "posterior_fn": lambda _: {},
        "next_state_fn": lambda delta_error: (
            "stable" if delta_error < 0.3 else "shifting"
        ),
    },
    "agent": {
        "topic": TOPICS["agent"],
        "model_ver_key": "agent_model_ver",
        "period_key": "agent_update_period",
        "default_period": 0.7,
        "posterior_fn": lambda _: {
            "intent": random.choice(["browse", "purchase", "support"])
        },
        "next_state_fn": lambda posterior: f"intent:{posterior['intent']}",
    },
    "action": {
        "topic": TOPICS["action"],
        "model_ver_key": "action_model_ver",
        "period_key": "action_update_period",
        "default_period": 0.9,
        "posterior_fn": lambda _: {
            "next_action": random.choice(["search", "quote", "checkout", "cancel"])
        },
        "next_state_fn": lambda posterior: f"action:{posterior['next_action']}",
    },
}


def _calibrated(domain: str, tenant: str, confidence: float) -> float:
    """Execute calibrated.

    Args:
        domain: The domain.
        tenant: The tenant.
        confidence: The confidence.
    """

    if _calib is None:
        return confidence
    try:
        scaler = _calib.temperature_scalers[domain][tenant]
        if getattr(scaler, "is_fitted", False):
            return float(scaler.scale(float(confidence)))
    except Exception:
        return confidence
    return confidence


def _get_runtime():
    """Load the runtime configuration.

    In production environments the ``somabrain.runtime_config`` module must be
    importable. The predictor enforces strict external-backend usage
    (see ``SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS``). A clear ``RuntimeError``
    is raised if the import fails, preventing silent fallback to default values.
    """
    try:
        from somabrain import runtime_config as _rt

        return _rt
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Failed to import somabrain.runtime_config – required for the "
            "predictor when external backends are enforced."
        ) from exc


def _metrics_handles():  # pragma: no cover
    """Execute metrics handles."""

    if _metrics is None:
        return {}, None, None
    counters = {
        d: _metrics.get_counter(
            f"somabrain_predictor_{d}_emitted_total",
            f"BeliefUpdate records emitted ({d})",
        )
        for d in DOMAIN_CONFIG.keys()
    }
    next_counter = _metrics.get_counter(
        "somabrain_predictor_next_total", "NextEvent records emitted (unified)"
    )
    err_hist = _metrics.get_histogram(
        "somabrain_predictor_error",
        "Per-update prediction error (MSE)",
        labelnames=["domain"],
    )
    return counters, next_counter, err_hist


def run_forever() -> None:  # pragma: no cover
    """Run the predictor loop forever.

    This function initializes tracing and runs the prediction loop.
    Health checks are provided via Django's built-in health endpoints
    (see somabrain/api/endpoints/health.py).
    """
    init_tracing()
    tracer = get_tracer("somabrain.predictor.unified")
    rt = _get_runtime()
    from somabrain.modes import feature_enabled

    # Deterministic test mode – seed all RNGs at startup if enabled.
    if getattr(settings, "TEST_MODE", False):
        random.seed(0)
        np.random.seed(0)

    try:
        composite = rt.get_bool("cog_composite", True)
    except Exception:
        composite = True
    if not (composite or feature_enabled("learner")):
        print("predictor-unified: disabled by mode; exiting.")
        return
    prod = make_producer()
    if prod is None:
        print("predictor-unified: Kafka not available; exiting.")
        return
    tenant = settings.default_tenant
    soma_compat = rt.get_bool("soma_compat", False)
    belief_schema = "belief_update"
    soma_schema = "belief_update_soma"
    next_schema = "next_event"
    # Build predictors per domain
    predictors: Dict[str, Tuple[Any, int]] = {}
    for d in DOMAIN_CONFIG.keys():
        predictors[d] = build_predictor_from_env(d)
    # Per-domain source index seeds for simple synthetic activity
    src_idx: Dict[str, int] = {"state": 0, "agent": 1, "action": 2}
    counters, next_counter, err_hist = _metrics_handles()
    last_emit: Dict[str, float] = {d: 0.0 for d in DOMAIN_CONFIG.keys()}
    periods: Dict[str, float] = {}
    model_versions: Dict[str, str] = {}
    for d, cfg in DOMAIN_CONFIG.items():
        periods[d] = rt.get_float(cfg["period_key"], cfg["default_period"])
        model_versions[d] = rt.get_str(cfg["model_ver_key"], "v1")
    try:
        while True:
            now = time.time()
            for domain, (predictor, dim) in predictors.items():
                per = periods[domain]
                if now - last_emit[domain] < per:
                    continue
                last_emit[domain] = now
                with tracer.start_as_current_span(f"predictor_emit_{domain}"):
                    observed = np.zeros(dim, dtype=float)
                    observed[(src_idx[domain] + 1) % dim] = 1.0
                    _, delta_error, confidence = predictor.step(
                        source_idx=src_idx[domain], observed=observed
                    )
                    src_idx[domain] = (src_idx[domain] + 1) % dim
                    # Posterior + derived next state
                    posterior = DOMAIN_CONFIG[domain]["posterior_fn"](predictor)
                    if domain == "agent":
                        next_state = DOMAIN_CONFIG[domain]["next_state_fn"](posterior)
                    elif domain == "action":
                        next_state = DOMAIN_CONFIG[domain]["next_state_fn"](posterior)
                    else:
                        next_state = DOMAIN_CONFIG[domain]["next_state_fn"](delta_error)
                    confidence = _calibrated(domain, tenant, float(confidence))
                    # Use configurable latency jitter from settings.
                    latency_min = getattr(settings, "PREDICTOR_LATENCY_MIN", 5)
                    latency_max = getattr(settings, "PREDICTOR_LATENCY_MAX", 15)
                    latency_ms = random.randint(latency_min, latency_max)
                    rec = {
                        "domain": domain,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "delta_error": float(delta_error),
                        "confidence": float(confidence),
                        "evidence": {"tenant": tenant, "source": "predictor-unified"},
                        "posterior": posterior,
                        "model_ver": model_versions[domain],
                        "latency_ms": latency_ms,
                    }
                    prod.send(
                        DOMAIN_CONFIG[domain]["topic"], value=encode(rec, belief_schema)
                    )
                    if counters.get(domain):
                        try:
                            counters[domain].inc()
                        except Exception:
                            pass
                    if err_hist is not None:
                        try:
                            err_hist.labels(domain=domain).observe(float(delta_error))
                        except Exception:
                            pass
                    if soma_compat:
                        try:
                            soma_rec = {
                                "stream": domain.upper(),
                                "timestamp": int(time.time() * 1000),
                                "delta_error": float(delta_error),
                                "info_gain": None,
                                "metadata": {"tenant": tenant},
                            }
                            prod.send(
                                TOPICS[f"soma_{domain}"],
                                value=encode(soma_rec, soma_schema),
                            )
                        except Exception:
                            pass
                    next_ev = build_next_event(
                        domain, tenant, float(confidence), next_state
                    )
                    prod.send(TOPICS["next"], value=encode(next_ev, next_schema))
                    if next_counter is not None:
                        try:
                            next_counter.inc()
                        except Exception:
                            pass
            time.sleep(0.05)
    finally:
        try:
            prod.flush(2)
            prod.close()
        except Exception:
            pass


if __name__ == "__main__":  # pragma: no cover
    run_forever()
