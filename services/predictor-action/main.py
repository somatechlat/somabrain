from __future__ import annotations

import json
import os
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
except Exception:  # pragma: no cover
    _metrics = None  # type: ignore

TOPIC = TOPICS["action"]
NEXT_TOPIC = TOPICS["next"]
SOMA_TOPIC = TOPICS["soma_action"]


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
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
    tracer = get_tracer("somabrain.predictor.action")
    _EMITTED = (
        _metrics.get_counter(
            "somabrain_predictor_action_emitted_total",
            "BeliefUpdate records emitted (action)",
        )
        if _metrics
        else None
    )
    _NEXT_EMITTED = (
        _metrics.get_counter(
            "somabrain_predictor_action_next_total",
            "NextEvent records emitted (action)",
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
        if os.getenv("HEALTH_PORT"):
            from fastapi import FastAPI
            import uvicorn  # type: ignore

            app = FastAPI(title="Predictor-Action Health")

            @app.get("/healthz")
            async def _hz():  # type: ignore
                return {"ok": True, "service": "predictor_action"}

            # Prometheus metrics endpoint (optional)
            try:
                from somabrain import metrics as _M  # type: ignore

                @app.get("/metrics")
                async def _metrics_ep():  # type: ignore
                    return await _M.metrics_endpoint()

            except Exception:
                pass

            port = int(os.getenv("HEALTH_PORT"))
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            threading.Thread(target=server.run, daemon=True).start()
    except Exception:
        pass
    # Default ON to ensure predictor is always available unless explicitly disabled
    from somabrain.modes import feature_enabled

    try:
        from somabrain import runtime_config as _rt

        composite = _rt.get_bool("cog_composite", True)
    except Exception:
        composite = True
    if not (composite or feature_enabled("learner")):
        print("predictor-action: disabled by mode; exiting.")
        return
    prod = _make_producer()
    if prod is None:
        print("predictor-action: Kafka not available; exiting.")
        return
    serde = _serde()
    next_serde = _next_serde()
    soma_serde = _soma_serde()
    from somabrain import runtime_config as _rt

    tenant = os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
    model_ver = _rt.get_str("action_model_ver", "v1")
    period = _rt.get_float("action_update_period", 0.9)
    soma_compat = _rt.get_bool("soma_compat", False)
    actions = ["search", "quote", "checkout", "cancel"]
    # Diffusion-backed predictor setup (supports production graph via env)
    from somabrain.predictors.base import build_predictor_from_env

    predictor, dim = build_predictor_from_env("action")
    source_idx = 2
    try:
        while True:
            with tracer.start_as_current_span("predictor_action_emit"):
                observed = np.zeros(dim, dtype=float)
                observed[(source_idx + 3) % dim] = 1.0
                _, delta_error, confidence = predictor.step(
                    source_idx=source_idx, observed=observed
                )
                # Apply calibration temperature scaling if available
                try:
                    from somabrain.calibration.calibration_metrics import (
                        calibration_tracker as _calib,
                    )  # type: ignore

                    scaler = _calib.temperature_scalers["action"][tenant]
                    if getattr(scaler, "is_fitted", False):
                        confidence = float(scaler.scale(float(confidence)))
                except Exception:
                    pass
                posterior = {"next_action": random.choice(actions)}
                rec = {
                    "domain": "action",
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "delta_error": float(delta_error),
                    "confidence": float(confidence),
                    "evidence": {"tenant": tenant, "source": "predictor-action"},
                    "posterior": posterior,
                    "model_ver": model_ver,
                    "latency_ms": int(8 + 10 * random.random()),
                }
                prod.send(TOPIC, value=_encode(rec, serde))
                if _EMITTED is not None:
                    try:
                        _EMITTED.inc()
                    except Exception:
                        pass
                if _ERR_HIST is not None:
                    try:
                        _ERR_HIST.labels(domain="action").observe(float(delta_error))
                    except Exception:
                        pass
                if soma_compat:
                    try:
                        ts_ms = int(time.time() * 1000)
                        soma_rec = {
                            "stream": "ACTION",
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
                    except Exception:
                        pass
                # NextEvent emission (derived) from next action
                predicted_state = f"action:{posterior['next_action']}"
                # Include optional tenant and computed regret for learner observability
                next_ev = build_next_event(
                    "action", tenant, float(confidence), predicted_state
                )
                prod.send(NEXT_TOPIC, value=_encode(next_ev, next_serde))
                if _NEXT_EMITTED is not None:
                    try:
                        _NEXT_EMITTED.inc()
                    except Exception:
                        pass
                source_idx = (source_idx + 1) % dim
                time.sleep(period)
    finally:
        try:
            prod.flush(2)
            prod.close()
        except Exception:
            pass


if __name__ == "__main__":  # pragma: no cover
    run_forever()
