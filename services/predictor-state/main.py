from __future__ import annotations

from common.config.settings import settings
from common.logging import logger
import random
import time
import threading
import numpy as np

from somabrain.observability.provider import init_tracing, get_tracer  # type: ignore

try:
    from somabrain import metrics as _metrics  # type: ignore
except Exception:  # pragma: no cover
    _metrics = None  # type: ignore

from somabrain.common.kafka import make_producer, encode, TOPICS
from somabrain.common.events import build_next_event
from somabrain.services.calibration_service import calibration_service

# Diffusion predictor
from somabrain.predictors.base import (
    build_predictor_from_env,
)


TOPIC = TOPICS["state"]
NEXT_TOPIC = TOPICS["next"]
SOMA_TOPIC = TOPICS["soma_state"]


def run_forever() -> None:  # pragma: no cover
    init_tracing()
    tracer = get_tracer("somabrain.predictor.state")
    # Metrics (lazy and optional)
    _EMITTED = (
        _metrics.get_counter(
            "somabrain_predictor_state_emitted_total",
            "BeliefUpdate records emitted (state)",
        )
        if _metrics
        else None
    )
    _NEXT_EMITTED = (
        _metrics.get_counter(
            "somabrain_predictor_state_next_total", "NextEvent records emitted (state)"
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

            app = FastAPI(title="Predictor-State Health")

            @app.get("/healthz")
            async def _hz():  # type: ignore
                return {"ok": True, "service": "predictor_state"}

            # Prometheus metrics endpoint (optional)
            try:
                from somabrain import metrics as _M  # type: ignore

                @app.get("/metrics")
                async def _metrics_ep():  # type: ignore
                    return await _M.metrics_endpoint()

            except Exception:
                logger.exception("Failed to set up metrics endpoint for health server")

            port = int(settings.health_port)
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            threading.Thread(target=server.run, daemon=True).start()
    except Exception:
        logger.exception("Health server startup failed")
    # Default ON to ensure predictor is always available unless explicitly disabled
    from somabrain.modes import feature_enabled

    try:
        from somabrain import runtime_config as _rt

        composite = _rt.get_bool("cog_composite", True)
    except Exception:
        composite = True
    if not (composite or feature_enabled("learner")):
        print("predictor-state: disabled by mode; exiting.")
        return
    prod = make_producer()
    if prod is None:
        print("predictor-state: Kafka not available; exiting.")
        return
    # Schema names used by encoder utility
    belief_schema = "belief_update"
    next_schema = "next_event"
    soma_schema = "belief_update_soma"
    from somabrain import runtime_config as _rt

    tenant = settings.default_tenant  # tenancy from centralized Settings
    model_ver = _rt.get_str("state_model_ver", "v1")
    period = _rt.get_float("state_update_period", 0.5)
    soma_compat = _rt.get_bool("soma_compat", False)
    # Diffusion-backed predictor setup (supports production graph via env)
    predictor, dim = build_predictor_from_env("state")
    source_idx = 0
    try:
        while True:
            # Simple synthetic delta_error stream (bounded noise + slow wave)
            with tracer.start_as_current_span("predictor_state_emit"):
                # Build observed vector as next one-hot (simple deterministic proxy)
                observed = np.zeros(dim, dtype=float)
                observed[(source_idx + 1) % dim] = 1.0
                _, delta_error, confidence = predictor.step(
                    source_idx=source_idx, observed=observed
                )
                # Apply calibration temperature scaling if available
                try:
                    from somabrain.calibration.calibration_metrics import (
                        calibration_tracker as _calib,
                    )  # type: ignore

                    scaler = _calib.temperature_scalers["state"][tenant]
                    if getattr(scaler, "is_fitted", False):
                        confidence = float(scaler.scale(float(confidence)))
                except Exception as exc:
                    # Log calibration failures; they should not stop the predictor.
                    from common.logging import logger
                    logger.exception("Calibration scaling failed in predictor-state: %s", exc)

                # Calibration tracking
                if calibration_service.enabled:
                    # In production, this would use actual accuracy from feedback
                    # For now, use confidence as a proxy for demo purposes
                    calibration_service.record_prediction(
                        domain="state",
                        tenant=tenant,
                        confidence=float(confidence),
                        accuracy=float(1.0 - delta_error),  # Proxy for actual accuracy
                    )

                rec = {
                    "domain": "state",
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "delta_error": float(delta_error),
                    "confidence": float(confidence),
                    "evidence": {"tenant": tenant, "source": "predictor-state"},
                    "posterior": {},
                    "model_ver": model_ver,
                    "latency_ms": int(5 + 5 * random.random()),
                    "calibration": (
                        {
                            "enabled": calibration_service.enabled,
                            "temperature": calibration_service.get_calibration_status(
                                "state", tenant
                            ).get("temperature", 1.0),
                        }
                        if calibration_service.enabled
                        else {}
                    ),
                }
                prod.send(TOPIC, value=encode(rec, belief_schema))
                if _EMITTED is not None:
                    try:
                        _EMITTED.inc()
                    except Exception:
                        logger.exception("Failed to increment emitted metric")
                if _ERR_HIST is not None:
                    try:
                        _ERR_HIST.labels(domain="state").observe(float(delta_error))
                    except Exception:
                        logger.exception("Failed to record error histogram")
                if soma_compat:
                    # Map to soma-compatible BeliefUpdate
                    try:
                        ts_ms = int(time.time() * 1000)
                        soma_rec = {
                            "stream": "STATE",
                            "timestamp": ts_ms,
                            "delta_error": float(delta_error),
                            "info_gain": None,
                            "metadata": {
                                k: str(v)
                                for k, v in (rec.get("evidence") or {}).items()
                            },
                        }
                        payload = encode(soma_rec, soma_schema)
                        prod.send(SOMA_TOPIC, value=payload)
                    except Exception:
                        logger.exception("Failed to emit soma-compatible belief update")
                # NextEvent emission (derived): predicted_state based on stability
                predicted_state = "stable" if delta_error < 0.3 else "shifting"
                next_ev = build_next_event(
                    "state", tenant, float(confidence), predicted_state
                )
                prod.send(NEXT_TOPIC, value=encode(next_ev, next_schema))
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
            logger.exception("Failed during producer cleanup")


if __name__ == "__main__":  # pragma: no cover
    run_forever()
