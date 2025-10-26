from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, Optional

try:
    from observability.provider import init_tracing, get_tracer  # type: ignore
except Exception:  # pragma: no cover
    def init_tracing():
        return None

    def get_tracer(name: str):  # type: ignore
        class _Noop:
            def start_as_current_span(self, *_args, **_kwargs):
                class _Span:
                    def __enter__(self):
                        return self

                    def __exit__(self, *a):
                        return False

                return _Span()

        return _Noop()
try:
    from kafka import KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaProducer = None  # type: ignore

try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore

TOPIC = "cog.action.updates"
NEXT_TOPIC = "cog.next.events"
SOMA_TOPIC = "soma.belief.action"


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _make_producer():
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
    tracer = get_tracer("somabrain.predictor.action")
    ff = (os.getenv("SOMABRAIN_FF_PREDICTOR_ACTION", "0").strip().lower() in ("1", "true", "yes", "on"))
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in ("1", "true", "yes", "on")
    if not ff and not composite:
        print("predictor-action: feature flag disabled; exiting.")
        return
    prod = _make_producer()
    if prod is None:
        print("predictor-action: Kafka not available; exiting.")
        return
    serde = _serde()
    next_serde = _next_serde()
    soma_serde = _soma_serde()
    tenant = os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
    model_ver = os.getenv("ACTION_MODEL_VER", "v1")
    period = float(os.getenv("ACTION_UPDATE_PERIOD", "0.9"))
    soma_compat = os.getenv("SOMA_COMPAT", "0").strip().lower() in ("1", "true", "yes", "on")
    actions = ["search", "quote", "checkout", "cancel"]
    try:
        while True:
            with tracer.start_as_current_span("predictor_action_emit"):
                confidence = max(0.0, min(1.0, 0.4 + 0.5 * random.random()))
                delta_error = max(0.0, min(1.0, 0.1 + 0.35 * random.random()))
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
                if soma_compat:
                    try:
                        ts_ms = int(time.time() * 1000)
                        soma_rec = {
                            "stream": "ACTION",
                            "timestamp": ts_ms,
                            "delta_error": float(delta_error),
                            "info_gain": None,
                            "metadata": {k: str(v) for k, v in (rec.get("evidence") or {}).items()},
                        }
                        payload = _encode(soma_rec, soma_serde)
                        prod.send(SOMA_TOPIC, value=payload)
                    except Exception:
                        pass
                # NextEvent emission (derived) from next action
                predicted_state = f"action:{posterior['next_action']}"
                next_ev = {
                    "frame_id": f"action:{rec['ts']}",
                    "predicted_state": predicted_state,
                    "confidence": float(confidence),
                    "ts": rec["ts"],
                }
                prod.send(NEXT_TOPIC, value=_encode(next_ev, next_serde))
                time.sleep(period)
    finally:
        try:
            prod.flush(2)
            prod.close()
        except Exception:
            pass


if __name__ == "__main__":  # pragma: no cover
    run_forever()
