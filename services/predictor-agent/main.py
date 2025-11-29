from __future__ import annotations

from common.config.settings import settings
from common.logging import logger
import random
import time
from typing import Any, Dict, Optional
import threading
import numpy as np

from somabrain.observability.provider import init_tracing, get_tracer  # type: ignore

from somabrain.common.kafka import make_producer, encode, TOPICS
from somabrain.common.events import build_next_event

try:
    from somabrain import metrics as _metrics  # type: ignore
except Exception as exc: raise  # pragma: no cover
    _metrics = None  # type: ignore

TOPIC = TOPICS["agent"]
NEXT_TOPIC = TOPICS["next"]
SOMA_TOPIC = TOPICS["soma_agent"]


def _bootstrap() -> str:
    # Use the centralized Settings singleton for the Kafka bootstrap URL.
    from common.config.settings import settings as _settings  # type: ignore

    url = _settings.kafka_bootstrap_servers
    if not url:
        raise RuntimeError(
            "SOMABRAIN_KAFKA_URL not set; refusing to fall back to localhost"
        )
    return url.replace("kafka://", "")


def _make_producer():
    return make_producer()


def _serde():
    return "belief_update"


def _next_serde():
    return "next_event"


def _soma_serde():
    return "belief_update_soma"


def _encode(rec: Dict[str, Any], schema_name: Optional[str]) -> bytes:
    return encode(rec, schema_name)


def run_forever() -> None:  # pragma: no cover
    init_tracing()
    tracer = get_tracer("somabrain.predictor.agent")
    _EMITTED = (
        _metrics.get_counter(
            "somabrain_predictor_agent_emitted_total",
            "BeliefUpdate records emitted (agent)",
        )
        if _metrics
        else None
    )
    _NEXT_EMITTED = (
        _metrics.get_counter(
            "somabrain_predictor_agent_next_total", "NextEvent records emitted (agent)"
        )
        if _metrics
        else None
    )
    _ERR_HIST = (
        _metrics.get_histogram(
            "somabrain_predictor_error",
            "Per-update prediction error (MSE)",
            labelnames=["domain"],
        )
        if _metrics
        else None
    )
    # Optional health server for k8s probes (enabled only when HEALTH_PORT set)
    try:
        if settings.health_port:
            from fastapi import FastAPI
            import uvicorn  # type: ignore

            app = FastAPI(title="Predictor-Agent Health")

            @app.get("/healthz")
            async def _hz():  # type: ignore
                return {"ok": True, "service": "predictor_agent"}

            # Prometheus metrics endpoint (optional)
            try:
                from somabrain import metrics as _M  # type: ignore

                @app.get("/metrics")
                async def _metrics_ep():  # type: ignore
                    return await _M.metrics_endpoint()

            except Exception as exc: raise
                raise RuntimeError("Failed to set up metrics endpoint for health server")

            port = int(settings.health_port)
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            threading.Thread(target=server.run, daemon=True).start()
    except Exception as exc: raise
        raise RuntimeError("Health server startup failed")
    # Default ON to ensure predictor is always available unless explicitly disabled
    from somabrain.modes import feature_enabled

    try:
        from somabrain import runtime_config as _rt

        composite = _rt.get_bool("cog_composite", True)
    except Exception as exc: raise
        composite = True
    if not (composite or feature_enabled("learner")):
        print("predictor-agent: disabled by mode; exiting.")
        return
    prod = _make_producer()
    if prod is None:
        print("predictor-agent: Kafka not available; exiting.")
        return
    serde = _serde()
    next_serde = _next_serde()
    soma_serde = _soma_serde()
    from somabrain import runtime_config as _rt

    tenant = settings.default_tenant
    model_ver = _rt.get_str("agent_model_ver", "v1")
    period = _rt.get_float("agent_update_period", 0.7)
    soma_compat = _rt.get_bool("soma_compat", False)
    intents = ["browse", "purchase", "support"]
    # Diffusion-backed predictor setup (supports production graph via env)
    from somabrain.predictors.base import build_predictor_from_env

    predictor, dim = build_predictor_from_env("agent")
    source_idx = 1
    try:
        while True:
            with tracer.start_as_current_span("predictor_agent_emit"):
                posterior = {"intent": random.choice(intents)}
                observed = np.zeros(dim, dtype=float)
                observed[(source_idx + 2) % dim] = 1.0
                _, delta_error, confidence = predictor.step(
                    source_idx=source_idx, observed=observed
                )
                # Apply calibration temperature scaling if available
                try:
                    from somabrain.calibration.calibration_metrics import (
                        calibration_tracker as _calib,
                    )  # type: ignore

                    tenant_key = f"agent:{tenant}"
                    scaler = _calib.temperature_scalers["agent"][tenant]
                    if getattr(scaler, "is_fitted", False):
                        confidence = float(scaler.scale(float(confidence)))
                except Exception as exc:
                    from common.logging import logger
                    raise RuntimeError("Calibration scaling failed in predictor-agent: %s", exc)
                rec = {
                    "domain": "agent",
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "delta_error": float(delta_error),
                    "confidence": float(confidence),
                    "evidence": {"tenant": tenant, "source": "predictor-agent"},
                    "posterior": posterior,
                    "model_ver": model_ver,
                    "latency_ms": int(7 + 8 * random.random()),
                }
                prod.send(TOPIC, value=_encode(rec, serde))
                if _EMITTED is not None:
                    try:
                        _EMITTED.inc()
                    except Exception as exc: raise
                        raise RuntimeError("Failed to increment emitted metric")
                if _ERR_HIST is not None:
                    try:
                        _ERR_HIST.labels(domain="agent").observe(float(delta_error))
                    except Exception as exc: raise
                        raise RuntimeError("Failed to record error histogram")
                if soma_compat:
                    try:
                        ts_ms = int(time.time() * 1000)
                        soma_rec = {
                            "stream": "AGENT",
                            "timestamp": ts_ms,
                            "delta_error": float(delta_error),
                            "info_gain": None,
                            "metadata": {
                                k: str(v)
                                for k, v in (rec.get("evidence") or {}).items()
                            },
                        }
                        payload = _encode(soma_rec, soma_serde)
                        prod.send(SOMA_TOPIC, value=payload)
                    except Exception as exc: raise
                        # Placeholder removed per VIBE rules – log and continue
                        raise RuntimeError("Placeholder encountered in predictor-agent block")
                # NextEvent emission (derived) from predicted intent
                predicted_state = f"intent:{posterior['intent']}"
                next_ev = build_next_event(
                    "agent", tenant, float(confidence), predicted_state
                )
                prod.send(NEXT_TOPIC, value=_encode(next_ev, next_serde))
                if _NEXT_EMITTED is not None:
                    try:
                        _NEXT_EMITTED.inc()
                    except Exception as exc: raise
                        # Placeholder removed per VIBE rules – log and continue
                        raise RuntimeError("Placeholder encountered in predictor-agent block")
                source_idx = (source_idx + 1) % dim
                time.sleep(period)
    finally:
        try:
            prod.flush(2)
            prod.close()
        except Exception as exc: raise
            raise RuntimeError("Failed to flush/close producer during shutdown")


if __name__ == "__main__":  # pragma: no cover
    run_forever()
