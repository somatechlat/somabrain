from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, Optional
import threading
import numpy as np

from observability.provider import init_tracing, get_tracer  # type: ignore

try:  # optional deps
    from kafka import KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaProducer = None  # type: ignore

try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore

try:
    # Optional Prometheus metrics via shared module
    from somabrain import metrics as _metrics  # type: ignore
except Exception:  # pragma: no cover
    _metrics = None  # type: ignore

# Diffusion predictor
from somabrain.predictors.base import (
    HeatDiffusionPredictor,
    PredictorConfig,
    make_line_graph_laplacian,
    matvec_from_matrix,
    build_predictor_from_env,
)


TOPIC = "cog.state.updates"
NEXT_TOPIC = "cog.next.events"
SOMA_TOPIC = "soma.belief.state"


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _make_producer():  # pragma: no cover - integration path
    if KafkaProducer is None:
        return None
    return KafkaProducer(bootstrap_servers=_bootstrap(), acks="1", linger_ms=5)


def _serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("belief_update"))  # type: ignore[arg-type]
    except Exception:
        return None


def _next_serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("next_event"))  # type: ignore[arg-type]
    except Exception:
        return None


def _soma_serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("belief_update_soma"))  # type: ignore[arg-type]
    except Exception:
        return None


def _encode(rec: Dict[str, Any], serde: Optional[AvroSerde]) -> bytes:
    if serde is not None:
        try:
            return serde.serialize(rec)
        except Exception:
            pass
    return json.dumps(rec).encode("utf-8")


def run_forever() -> None:  # pragma: no cover
    init_tracing()
    tracer = get_tracer("somabrain.predictor.state")
    # Metrics (lazy and optional)
    _EMITTED = _metrics.get_counter("somabrain_predictor_state_emitted_total", "BeliefUpdate records emitted (state)") if _metrics else None
    _NEXT_EMITTED = _metrics.get_counter("somabrain_predictor_state_next_total", "NextEvent records emitted (state)") if _metrics else None
    _ERR_HIST = _metrics.get_histogram("somabrain_predictor_error", "Per-update prediction error (MSE)", labelnames=["domain"]) if _metrics else None
    # Optional health server for k8s probes (enabled only when HEALTH_PORT set)
    try:
        if os.getenv("HEALTH_PORT"):
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
                pass

            port = int(os.getenv("HEALTH_PORT"))
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            threading.Thread(target=server.run, daemon=True).start()
    except Exception:
        pass
    # Default ON to ensure predictor is always available unless explicitly disabled
    ff = (os.getenv("SOMABRAIN_FF_PREDICTOR_STATE", "1").strip().lower() in ("1", "true", "yes", "on"))
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in ("1", "true", "yes", "on")
    if not ff:
        if not composite:
            print("predictor-state: feature flag disabled; exiting.")
            return
    prod = _make_producer()
    if prod is None:
        print("predictor-state: Kafka not available; exiting.")
        return
    serde = _serde()
    next_serde = _next_serde()
    soma_serde = _soma_serde()
    tenant = os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
    model_ver = os.getenv("STATE_MODEL_VER", "v1")
    period = float(os.getenv("STATE_UPDATE_PERIOD", "0.5"))
    soma_compat = os.getenv("SOMA_COMPAT", "0").strip().lower() in ("1", "true", "yes", "on")
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
                _, delta_error, confidence = predictor.step(source_idx=source_idx, observed=observed)
                rec = {
                    "domain": "state",
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "delta_error": float(delta_error),
                    "confidence": float(confidence),
                    "evidence": {"tenant": tenant, "source": "predictor-state"},
                    "posterior": {},
                    "model_ver": model_ver,
                    "latency_ms": int(5 + 5 * random.random()),
                }
                prod.send(TOPIC, value=_encode(rec, serde))
                if _EMITTED is not None:
                    try:
                        _EMITTED.inc()
                    except Exception:
                        pass
                if _ERR_HIST is not None:
                    try:
                        _ERR_HIST.labels(domain="state").observe(float(delta_error))
                    except Exception:
                        pass
                if soma_compat:
                    # Map to soma-compatible BeliefUpdate
                    try:
                        ts_ms = int(time.time() * 1000)
                        soma_rec = {
                            "stream": "STATE",
                            "timestamp": ts_ms,
                            "delta_error": float(delta_error),
                            "info_gain": None,
                            "metadata": {k: str(v) for k, v in (rec.get("evidence") or {}).items()},
                        }
                        payload = _encode(soma_rec, soma_serde)
                        prod.send(SOMA_TOPIC, value=payload)
                    except Exception:
                        pass
                # NextEvent emission (derived): predicted_state based on stability
                predicted_state = "stable" if delta_error < 0.3 else "shifting"
                next_ev = {
                    "frame_id": f"state:{rec['ts']}",
                    "predicted_state": predicted_state,
                    "confidence": float(confidence),
                    "ts": rec["ts"],
                }
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
